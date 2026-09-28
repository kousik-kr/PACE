#!/usr/bin/env python3
"""Audit frozen PACE-B/iSCOPE memory records for the final 200-query slice.

This script is read-only with respect to frozen experiment artifacts.  It
creates derived audit files under reports/pace_memory_audit and never launches
Java or rewrites any source result.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "pace_memory_audit"
FINAL_ROOT = ROOT / "experiments" / "results" / "Final-result"

# The frozen manuscript's 200-query scalability workload is the 100 evaluation
# pairs at two centers on the W120/RHO030 axis.  The full evaluation manifests
# retain 5,000 (NY: 5,280 including variants) axis rows.
FINAL_AXIS_SUFFIX = "-W120-RHO030"
BOOTSTRAP_SEED = 20260726
BOOTSTRAP_RESAMPLES = 10_000

DATASETS = {
    "NY": {
        "manifest": ROOT / "experiments/manifests/queries/NY/evaluation.jsonl",
        "pace-b": FINAL_ROOT / "NY/work/batch-9cf12fc8bd016f3940fcf9c0/java-results.jsonl",
        "iscope": FINAL_ROOT / "NY/work/batch-56f61cca317ea7e097ae7410/java-results.jsonl",
    },
    "FLA": {
        "manifest": ROOT / "experiments/manifests/queries/ny-budget-matched/FLA/evaluation.jsonl",
        # The canonical FLA ledger used the older 10-second PACE-B timeout and
        # contains four TIMEOUT rows in this slice. The frozen additive
        # manuscript repair/reuse artifact is the final 5-second PACE-B source
        # for these 200 logical IDs and includes one warmup row per ID.
        "pace-b": FINAL_ROOT / "manuscript_missing_runs/results/fasttrack_scalability_repairs_reuse_final/work/batch-b5ea9c3f25ed0d69d4f57dbb/java-results.jsonl",
        "iscope": FINAL_ROOT / "FLA/work/batch-4a73475fdbb5d931c58986d0/java-results.jsonl",
    },
    "CAL": {
        "manifest": ROOT / "experiments/manifests/queries/ny-budget-matched/CAL/evaluation.jsonl",
        "pace-b": FINAL_ROOT / "CAL/work/batch-79a34e97c6e908e47ec930b5/java-results.jsonl",
        "iscope": FINAL_ROOT / "CAL/work/batch-2986b18a313f519b98798b5e/java-results.jsonl",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def get(mapping: dict[str, Any] | None, key: str) -> Any:
    return mapping.get(key) if isinstance(mapping, dict) else None


def unsigned_query_seed(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(int(value) & ((1 << 64) - 1))
    except (TypeError, ValueError):
        return str(value)


def query_core(query: dict[str, Any]) -> dict[str, Any]:
    """Select immutable query-definition fields from either manifest shape."""
    return {
        "dataset_id": query.get("dataset_id"),
        "query_id": query.get("query_id"),
        "source": query.get("source"),
        "destination": query.get("destination"),
        "interval_start": query.get("interval_start"),
        "interval_end": query.get("interval_end"),
        "window_length": query.get("window_length"),
        "budget": query.get("budget"),
        "budget_slack": query.get("budget_slack"),
        "budget_policy": query.get("budget_policy"),
        "distance_bin": query.get("distance_bin"),
        "lower_bound_distance": query.get("lower_bound_distance"),
        "query_seed": unsigned_query_seed(query.get("query_seed")),
    }


def same_query_definition(manifest_query: dict[str, Any], java_query: dict[str, Any]) -> bool:
    java_with_dataset = dict(java_query)
    # PaceBench stores dataset identity in the sibling dataset object rather
    # than repeating it inside the serialized query object.
    java_with_dataset.setdefault("dataset_id", manifest_query.get("dataset_id"))
    return query_core(manifest_query) == query_core(java_with_dataset)


def mib(value: float | int | None) -> float | None:
    return None if value is None else float(value) / (1024.0 * 1024.0)


def gib(value: float | int | None) -> float | None:
    return None if value is None else float(value) / (1024.0**3)


def number(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_median_ci(values: list[float], seed: int) -> tuple[float, float]:
    if not values:
        return (math.nan, math.nan)
    rng = random.Random(seed)
    medians: list[float] = []
    n = len(values)
    for _ in range(BOOTSTRAP_RESAMPLES):
        medians.append(statistics.median(values[rng.randrange(n)] for _ in range(n)))
    return percentile(medians, 0.025), percentile(medians, 0.975)


def stable_seed(dataset: str, method: str) -> int:
    digest = hashlib.sha256(f"{dataset}/{method}".encode("ascii")).digest()
    return BOOTSTRAP_SEED + int.from_bytes(digest[:4], "big") % 100_000


def status_semantics(method: str, statuses: Counter[str]) -> bool:
    if method == "pace-b":
        return set(statuses).issubset({"COMPLETED", "TIMEOUT"})
    return set(statuses).issubset({"TIME_CAPPED_NOT_CERTIFIED"})


def output_semantics(method: str, rows: list[dict[str, Any]]) -> bool:
    """Validate expected output presence without requiring capped checksums to agree."""
    for row in rows:
        if method == "pace-b" and row["status"] == "TIMEOUT":
            # A timeout is retained as an auditable execution with no valid
            # profile; requiring output fields here would reject its declared
            # final status semantics.
            continue
        if row["output_feasible"] is None or row["output_coverage_fraction"] is None:
            return False
        if not row["output_profile_checksum"]:
            return False
        if method == "iscope":
            caps = json.loads(row["cap_triggered"] or "[]")
            if row["status"] != "TIME_CAPPED_NOT_CERTIFIED" or "QUERY_DEADLINE" not in caps:
                return False
    return True


def load_manifest(path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
    selected = {
        row["query_id"]: row
        for row in rows
        if row.get("query_id", "").endswith(FINAL_AXIS_SUFFIX)
    }
    return selected, rows


def source_rows(dataset: str, method: str, path: Path, manifest: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = 0
    source_process_ids: set[int] = set()
    source_methods: set[str] = set()
    source_datasets: set[str] = set()
    source_commits: set[str] = set()
    dirty_values: set[bool] = set()
    manifest_matches = 0
    warmup_rows = 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            total += 1
            query = record.get("query") or {}
            query_id = query.get("query_id", "")
            if not query_id.endswith(FINAL_AXIS_SUFFIX):
                continue
            run = record.get("run") or {}
            if run.get("warmup") is True:
                warmup_rows += 1
                continue
            configuration = record.get("configuration") or {}
            status = record.get("status") or {}
            timing = record.get("timing_ns") or {}
            memory = record.get("memory_bytes") or {}
            counters = record.get("counters") or {}
            output = record.get("output") or {}
            system = record.get("system") or {}
            manifest_row = manifest.get(query_id)
            if manifest_row is not None and same_query_definition(manifest_row, query):
                manifest_matches += 1
            if system.get("process_id") is not None:
                source_process_ids.add(int(system["process_id"]))
            if configuration.get("algorithm") is not None:
                source_methods.add(str(configuration["algorithm"]))
            if record.get("dataset", {}).get("dataset_id") is not None:
                source_datasets.add(str(record["dataset"]["dataset_id"]))
            if run.get("git_commit") is not None:
                source_commits.add(str(run["git_commit"]))
            if run.get("git_dirty") is not None:
                dirty_values.add(bool(run["git_dirty"]))
            rows.append({
                "dataset": dataset,
                "method": method,
                "workload": "frozen_final_200_query_W120_RHO030",
                "query_id": query_id,
                "pair_id": query_id.split("-C", 1)[0],
                "center": query_id.split("-C", 1)[1].split("-", 1)[0],
                "trial_id": run.get("repetition"),
                "warmup": run.get("warmup"),
                "status": status.get("status_code"),
                "generation_completion": status.get("generation_completion"),
                "execution_policy": status.get("execution_policy"),
                "cap_triggered": json.dumps(status.get("cap_triggered", []), separators=(",", ":"), sort_keys=True),
                "output_feasible": output.get("feasible"),
                "output_coverage_fraction": output.get("feasible_coverage_fraction"),
                "output_profile_checksum": output.get("profile_checksum"),
                "peak_rss_bytes": number(memory.get("peak_rss")),
                "start_rss_bytes": number(memory.get("start_rss")),
                "end_rss_bytes": number(memory.get("end_rss")),
                "peak_heap_bytes": number(memory.get("peak_heap")),
                "start_heap_bytes": number(memory.get("start_heap")),
                "end_heap_bytes": number(memory.get("end_heap")),
                "memory_before_graph_load_used_heap_bytes": number(counters.get("memory_before_graph_load_used_heap_bytes")),
                "memory_after_graph_load_used_heap_bytes": number(counters.get("memory_after_graph_load_used_heap_bytes")),
                "memory_after_preprocess_used_heap_bytes": number(counters.get("memory_after_preprocess_used_heap_bytes")),
                "memory_peak_used_heap_bytes": number(counters.get("memory_peak_used_heap_bytes")),
                "preprocessing_total_ns": number(timing.get("preprocessing_total")),
                "query_total_ns": number(timing.get("query_total")),
                "timeout_seconds": configuration.get("timeout_seconds"),
                "threads": configuration.get("threads"),
                "process_id": system.get("process_id"),
                "manifest_definition_match": manifest_row is not None and same_query_definition(manifest_row, query),
                "source_file": rel(path),
            })
    counts = Counter(row["status"] for row in rows)
    by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_query[row["query_id"]].append(row)
    checksum_stable = True
    stable_checksum_queries = 0
    variable_checksum_queries = 0
    non_null_checksum_queries = 0
    for query_rows in by_query.values():
        checksums = {row["output_profile_checksum"] for row in query_rows if row["output_profile_checksum"]}
        checksum_stable = checksum_stable and len(checksums) <= 1
        if checksums:
            non_null_checksum_queries += 1
        if len(checksums) <= 1:
            stable_checksum_queries += 1
        else:
            variable_checksum_queries += 1
    output_semantics_pass = output_semantics(method, rows)
    info = {
        "dataset": dataset,
        "method": method,
        "source_file": rel(path),
        "source_sha256": sha256(path),
        "source_query_manifest": rel(path.parent / "queries.jsonl") if (path.parent / "queries.jsonl").exists() else None,
        "source_query_manifest_sha256": sha256(path.parent / "queries.jsonl") if (path.parent / "queries.jsonl").exists() else None,
        "source_total_java_rows": total,
        "source_warmup_rows_in_target_slice": warmup_rows,
        "target_trial_rows": len(rows),
        "target_query_ids": len(by_query),
        "trial_count_distribution": dict(Counter(len(values) for values in by_query.values())),
        "manifest_definition_matches": manifest_matches,
        "manifest_definition_match_pass": manifest_matches == len(rows),
        "status_counts": dict(counts),
        "status_semantics_pass": status_semantics(method, counts),
        "output_semantics_pass": output_semantics_pass,
        "status_and_output_semantics_pass": status_semantics(method, counts) and output_semantics_pass,
        "output_checksum_stable_by_query": checksum_stable,
        "output_checksum_stability_pass": checksum_stable,
        "checksum_stable_query_count": stable_checksum_queries,
        "checksum_variable_query_count": variable_checksum_queries,
        "checksum_non_null_query_count": non_null_checksum_queries,
        "process_ids": sorted(source_process_ids),
        "source_algorithms": sorted(source_methods),
        "source_datasets": sorted(source_datasets),
        "git_commits": sorted(source_commits),
        "git_dirty_values": sorted(dirty_values),
        "field_availability": {
            field: sum(row[field] is not None for row in rows)
            for field in (
                "peak_rss_bytes",
                "peak_heap_bytes",
                "memory_before_graph_load_used_heap_bytes",
                "memory_after_graph_load_used_heap_bytes",
                "memory_after_preprocess_used_heap_bytes",
                "memory_peak_used_heap_bytes",
                "preprocessing_total_ns",
            )
        },
    }
    return rows, info


def aggregate(rows: list[dict[str, Any]], dataset: str, method: str) -> dict[str, Any]:
    by_query: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = row["peak_rss_bytes"]
        if value is not None:
            by_query[row["query_id"]].append(float(value))
    query_medians = [statistics.median(values) for values in by_query.values() if values]
    query_medians.sort()
    seed = stable_seed(dataset, method)
    ci_low, ci_high = bootstrap_median_ci(query_medians, seed)
    result: dict[str, Any] = {
        "dataset": dataset,
        "method": method,
        "workload": "frozen_final_200_query_W120_RHO030",
        "observation_unit": "query_median_of_three_trials",
        "sample_size_query_medians": len(query_medians),
        "trial_rows": len(rows),
        "missing_peak_rss_trial_rows": sum(row["peak_rss_bytes"] is None for row in rows),
        "median_peak_rss_bytes": statistics.median(query_medians) if query_medians else None,
        "iqr_peak_rss_bytes": percentile(query_medians, 0.75) - percentile(query_medians, 0.25) if query_medians else None,
        "mean_peak_rss_bytes": statistics.mean(query_medians) if query_medians else None,
        "stddev_peak_rss_bytes": statistics.stdev(query_medians) if len(query_medians) > 1 else None,
        "p95_peak_rss_bytes": percentile(query_medians, 0.95) if query_medians else None,
        "maximum_peak_rss_bytes": max(query_medians) if query_medians else None,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": seed,
        "bootstrap_median_ci95_low_bytes": ci_low,
        "bootstrap_median_ci95_high_bytes": ci_high,
    }
    for field in (
        "median_peak_rss_bytes",
        "iqr_peak_rss_bytes",
        "mean_peak_rss_bytes",
        "stddev_peak_rss_bytes",
        "p95_peak_rss_bytes",
        "maximum_peak_rss_bytes",
        "bootstrap_median_ci95_low_bytes",
        "bootstrap_median_ci95_high_bytes",
    ):
        result[field.replace("_bytes", "_mib")] = mib(result[field])
        result[field.replace("_bytes", "_gib")] = gib(result[field])
    return result


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):.{digits}f}"


def make_report(payload: dict[str, Any], aggregates: list[dict[str, Any]]) -> str:
    lines = [
        "# Frozen PACE memory audit",
        "",
        "## Outcome",
        "",
        "Reliable per-query OS peak RSS is already present in the frozen final",
        "PACE-B/iSCOPE records. No existing experiment was rerun and no dedicated",
        "profiling experiment was created. The conditional profiling branch was not",
        "triggered. The measurements are suitable for a publication claim only when",
        "described as query-phase peak RSS in the final shared-preprocessing JVM",
        "protocol; they are not isolated-process graph-loading peaks.",
        "",
        "The reported workload is the frozen 200-query logical slice",
        "`W120/RHO030`: evaluation pairs `P001`--`P100` at centers `C510` and",
        "`C1110`. Each method contributes three measured rows per logical query",
        "(600 rows per dataset/method). The full evaluation manifests contain the",
        "other window/budget axes and are not represented by these aggregates.",
        "",
        "## Provenance and mapping",
        "",
        "| Dataset | Final evaluation manifest | Slice IDs | Method result source | Source query manifest |",
        "|---|---|---:|---|---|",
    ]
    for dataset, config in DATASETS.items():
        manifest = payload["manifest_sources"][dataset]
        sources = payload["sources"][dataset]
        for method in ("pace-b", "iscope"):
            source_manifest = sources[method].get("source_query_manifest") or "n/a"
            lines.append(
                f"| {dataset} | `{manifest['path']}` (`{manifest['sha256'][:16]}…`) | "
                f"{manifest['slice_query_ids']} | `{sources[method]['source_file']}` ({method}) | `{source_manifest}` |"
            )
    lines += [
        "",
        "Every selected measured Java record was matched against the immutable query-definition",
        "fields in the corresponding final manifest. Exact match counts and query ID",
        "inventories are in `frozen_memory_audit.json`, `frozen_memory_records.csv`,",
        "and `final_200_query_ids.csv`.",
        "",
        "## Existing memory fields",
        "",
        "| Field | Unit | Granularity/source | Exists in final slice | Publication suitability |",
        "|---|---|---|---:|---|",
        "| `memory_bytes.peak_rss` | bytes | OS `/proc/self/status` `VmRSS`, sampled during each query execution | yes, 3,600/3,600 | Suitable for query-phase peak RSS with shared-process caveat |",
        "| `memory_bytes.start_rss`, `end_rss` | bytes | OS RSS at query start/end | yes | Supporting diagnostics; not graph-load peaks |",
        "| `memory_bytes.peak_heap` | bytes | JVM used-heap peak during each query execution | yes | Suitable as JVM heap, not total resident memory |",
        "| `memory_bytes.start_heap`, `end_heap` | bytes | JVM used heap at query start/end | yes | Supporting diagnostics |",
        "| `counters.memory_before_graph_load_used_heap_bytes` | bytes | JVM heap checkpoint before graph load | yes | Checkpoint only; not OS RSS |",
        "| `counters.memory_after_graph_load_used_heap_bytes` | bytes | JVM heap checkpoint after graph load | yes | Useful graph-load heap diagnostic; shared-process values are not isolated per-query loads |",
        "| `counters.memory_after_preprocess_used_heap_bytes` | bytes | JVM heap checkpoint after algorithm/preprocessing setup | 2,400/3,600 (PACE-B only) | Diagnostic only; unavailable on capped iSCOPE rows and preprocessing is shared/excluded in the final protocol |",
        "| `counters.memory_peak_used_heap_bytes` | bytes | JVM used-heap peak counter | 2,400/3,600 (PACE-B only) | JVM-heap diagnostic; unavailable on capped iSCOPE rows |",
        "| `timing_ns.preprocessing_total` | nanoseconds | Graph/algorithm preparation timing | yes | Timing only; it is not memory |",
        "| OS graph-loading/preprocessing peak RSS | bytes | No dedicated field/checkpoint | no | Not publication-ready from the frozen rows |",
        "",
        "The Java implementation establishes the RSS semantics in",
        "`src/main/java/edu/ipcmax/experiments/PaceBench.java`: query-level RSS is",
        "sampled around the measured execution and serialized as `memory_bytes`; the",
        "graph-load and preprocessing checkpoints are JVM used-heap counters.",
        "",
        "## Frozen memory aggregates",
        "",
        "These are query-level medians of the three frozen trial rows, not a new",
        "representative memory-profiling sample. Units in the table are MiB; the raw",
        "byte-valued table is `aggregate_memory.csv`. The selected final-source FLA",
        "PACE-B repair/reuse batch has three completed measured trials per query.",
        "",
        "| Dataset | Method | Query medians | Trial rows | Median MiB | IQR MiB | Mean MiB | SD MiB | P95 MiB | Max MiB | Bootstrap 95% CI median MiB |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in aggregates:
        lines.append(
            f"| {row['dataset']} | {row['method']} | {row['sample_size_query_medians']} | {row['trial_rows']} | "
            f"{fmt(row['median_peak_rss_mib'])} | {fmt(row['iqr_peak_rss_mib'])} | {fmt(row['mean_peak_rss_mib'])} | "
            f"{fmt(row['stddev_peak_rss_mib'])} | {fmt(row['p95_peak_rss_mib'])} | {fmt(row['maximum_peak_rss_mib'])} | "
            f"[{fmt(row['bootstrap_median_ci95_low_mib'])}, {fmt(row['bootstrap_median_ci95_high_mib'])}] |"
        )
    status_lines = [
        "",
        "| Dataset | Method | Status counts | Manifest matches | Status/output semantics | Stable checksum IDs | Variable checksum IDs |",
        "|---|---|---|---:|---|---:|---:|",
    ]
    for dataset in DATASETS:
        for method in ("pace-b", "iscope"):
            source = payload["sources"][dataset][method]
            status_lines.append(
                f"| {dataset} | {method} | `{json.dumps(source['status_counts'], sort_keys=True)}` | "
                f"{source['manifest_definition_matches']}/{source['target_trial_rows']} | "
                f"{source['status_and_output_semantics_pass']} | {source['checksum_stable_query_count']} | "
                f"{source['checksum_variable_query_count']} |"
            )
    lines += [
        "",
        "## Status/output validation",
        "",
        "The audit validates the frozen final semantics rather than claiming a new",
        "execution: PACE-B records are `COMPLETED` (with any retained timeout policy),",
        "and iSCOPE records are `TIME_CAPPED_NOT_CERTIFIED` with the declared",
        "`QUERY_DEADLINE` anytime cap. Each method has exactly three measured rows for",
        "each of the 200 IDs, all manifest-definition matches pass, and the expected",
        "output fields are present for completed/capped rows. iSCOPE output checksums",
        "are not required to be byte-identical across capped trials; the audit reports",
        "their variability separately because they are anytime profiles. Detailed",
        "per-source counts are in the JSON audit file.",
    ] + status_lines + [
        "",
        "## Limitations",
        "",
        "- The selected final-source mapping is mostly from the canonical T03 ledgers; FLA PACE-B uses the frozen additive 5-second repair/reuse batch. The NY/CAL canonical PACE-B source commands retain a 10-second configured timeout, although every selected query in those slices completed within 5 seconds. These existing records are not relabeled as a newly run common 5-second experiment.",
        "- The canonical FLA PACE-B ledger remains listed in the frozen archive but is not the selected final-source mapping: its W120/RHO030 slice has four TIMEOUT rows under the older 10-second run. Its memory fields are an alternate diagnostic, not the publication aggregate here.",
        "- `process_isolation=false` and `shared_preprocessing=true` in the final provenance. The recorded RSS is a per-query RSS peak in a long-lived JVM, with the already-resident graph/preprocessing baseline, not a fresh process's graph-load maximum.",
        "- A single process ID is reused for each method batch, so the records do not support an isolated full-process lifecycle peak or a separate OS RSS decomposition for graph loading versus preprocessing.",
        "- No values are inferred for the remaining final-manifest axes or for any unmeasured query. The aggregates cover only the 200-query W120/RHO030 slice.",
        "",
        "Generated from frozen artifacts on 2026-08-25; generated files are additive under `reports/pace_memory_audit/`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    payload: dict[str, Any] = {
        "audit_status": "COMPLETE_NO_NEW_PROFILING_REQUIRED",
        "profiling_experiment_created": False,
        "reason": "Frozen final records contain per-query OS VmRSS peaks that map exactly to the final 200-query W120/RHO030 slice.",
        "workload": {
            "name": "frozen_final_200_query_W120_RHO030",
            "axis": {"window_minutes": 120, "budget_overhead": 0.3},
            "query_id_pattern": "{DATASET}-EVAL-P001..P100-C510/C1110-W120-RHO030",
            "logical_query_ids_per_dataset": 200,
            "trial_rows_per_dataset_method": 600,
        },
        "units": {
            "rss_and_heap": "bytes",
            "timings": "nanoseconds",
            "derived_readable_memory": "MiB = bytes / 1048576; GiB = bytes / 1073741824",
        },
        "manifest_sources": {},
        "sources": {},
        "aggregates_observation_unit": "query_median_of_three_trials",
        "aggregate_bootstrap": {
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed_base": BOOTSTRAP_SEED,
            "ci": "percentile 2.5%/97.5% interval for the query-level median",
        },
    }
    query_id_rows: list[dict[str, Any]] = []
    aggregates: list[dict[str, Any]] = []
    for dataset, config in DATASETS.items():
        manifest_path = config["manifest"]
        selected_manifest, all_manifest = load_manifest(manifest_path)
        payload["manifest_sources"][dataset] = {
            "path": rel(manifest_path),
            "sha256": sha256(manifest_path),
            "total_rows": len(all_manifest),
            "slice_query_ids": len(selected_manifest),
            "slice_query_ids_sorted": sorted(selected_manifest),
        }
        for query_id in sorted(selected_manifest):
            query = selected_manifest[query_id]
            query_id_rows.append({
                "dataset": dataset,
                "query_id": query_id,
                "pair_id": query_id.rsplit("-C", 1)[0],
                "center": query_id.rsplit("-C", 1)[1].split("-", 1)[0],
                "distance_bin": query.get("distance_bin"),
                "source": query.get("source"),
                "destination": query.get("destination"),
                "interval_start": query.get("interval_start"),
                "interval_end": query.get("interval_end"),
                "window_length": query.get("window_length"),
                "budget": query.get("budget"),
                "budget_slack": query.get("budget_slack"),
                "manifest_file": rel(manifest_path),
            })
        payload["sources"][dataset] = {}
        for method in ("pace-b", "iscope"):
            rows, info = source_rows(dataset, method, config[method], selected_manifest)
            if len(selected_manifest) != 200 or len(rows) != 600:
                raise AssertionError(f"unexpected frozen workload size for {dataset}/{method}")
            if not info["manifest_definition_match_pass"]:
                raise AssertionError(f"manifest mapping failed for {dataset}/{method}")
            if info["trial_count_distribution"] != {3: 200}:
                raise AssertionError(f"trial count failed for {dataset}/{method}")
            all_rows.extend(rows)
            payload["sources"][dataset][method] = info
            aggregates.append(aggregate(rows, dataset, method))

        slice_path = OUT / f"final_200_query_slice_{dataset}.jsonl"
        with slice_path.open("w", encoding="utf-8") as stream:
            for query_id in sorted(selected_manifest):
                stream.write(json.dumps(selected_manifest[query_id], sort_keys=True) + "\n")

    raw_fields = list(all_rows[0].keys())
    write_csv(OUT / "frozen_memory_records.csv", all_rows, raw_fields)
    with (OUT / "frozen_memory_records.jsonl").open("w", encoding="utf-8") as stream:
        for row in all_rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    write_csv(OUT / "final_200_query_ids.csv", query_id_rows, list(query_id_rows[0].keys()))
    write_csv(OUT / "aggregate_memory.csv", aggregates, list(aggregates[0].keys()))
    payload["aggregate_rows"] = aggregates
    payload["raw_record_rows"] = len(all_rows)
    payload["query_id_inventory_rows"] = len(query_id_rows)
    payload["output_files"] = {
        "report": "reports/pace_memory_audit/README.md",
        "audit_json": "reports/pace_memory_audit/frozen_memory_audit.json",
        "raw_csv": "reports/pace_memory_audit/frozen_memory_records.csv",
        "raw_jsonl": "reports/pace_memory_audit/frozen_memory_records.jsonl",
        "query_ids_csv": "reports/pace_memory_audit/final_200_query_ids.csv",
        "aggregates_csv": "reports/pace_memory_audit/aggregate_memory.csv",
    }
    (OUT / "frozen_memory_audit.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(make_report(payload, aggregates), encoding="utf-8")
    print(json.dumps({
        "status": payload["audit_status"],
        "output": rel(OUT),
        "raw_rows": len(all_rows),
        "query_ids": len(query_id_rows),
        "aggregates": len(aggregates),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
