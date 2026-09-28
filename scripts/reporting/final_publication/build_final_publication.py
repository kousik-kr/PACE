#!/usr/bin/env python3
"""Build additive, manuscript-ready PACE figures, tables, and value ledger.

The script reads frozen logs and existing audited aggregates only.  It never
launches Java, edits manifests, or writes below ``experiments/``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "reports/pace_revision/final_publication"
REV = ROOT / "reports/pace_revision"
FINAL = ROOT / "experiments/results/Final-result"
sys.path.insert(0, str(REV / "scripts"))
from build_pace_revision import (  # type: ignore
    BOOTSTRAP_SEED,
    SOURCE_MAP,
    make_memory_and_query_outputs,
    manifest_audit,
    read_source,
    stable_offset,
    stat_block,
)

FIELDS = [
    "value_id", "rq", "figure_or_table", "panel", "dataset", "method", "metric",
    "display_value", "full_precision_value", "unit", "statistic", "observation_unit",
    "n_queries", "n_trials", "source_file", "source_field", "source_workload",
    "derivation", "measured_or_estimated", "estimated", "estimator_if_any",
    "estimate_sources_if_any", "uncertainty_low", "uncertainty_high", "timeout_context",
    "thread_context", "notes", "publication_status",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def jread(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def fmt(x: Any, digits: int = 3) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "UNAVAILABLE"
    return str(int(round(float(x)))) if digits == 0 else f"{float(x):.{digits}f}"


def pctile(values: list[float], p: float) -> float:
    xs = sorted(values)
    if not xs: return math.nan
    x = (len(xs) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return xs[lo] if lo == hi else xs[lo] + (x - lo) * (xs[hi] - xs[lo])


def tex(value: Any) -> str:
    return str(value).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def scalability() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[Path]]:
    all_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    info: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    paths: list[Path] = []
    for d in ("NY", "FLA", "CAL"):
        manifest, selected, m = manifest_audit(d)
        meta[d] = m; paths.append(manifest)
        info[d] = {}
        for method in ("pace-b", "iscope"):
            rows, inf = read_source(d, method, SOURCE_MAP[d][method], selected)
            all_rows[(d, method)] = rows; info[d][method] = inf; paths.append(SOURCE_MAP[d][method])
    _, qrows, _ = make_memory_and_query_outputs(all_rows)
    coverage_by_query: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (dataset, method), rows in all_rows.items():
        for row in rows:
            if row.get("coverage") is not None:
                coverage_by_query[(dataset, method)][row["query_id"]].append(float(row["coverage"]))
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in qrows: grouped[(r["dataset"], r["method"])].append(r)
    table: list[dict[str, Any]] = []; plot: list[dict[str, Any]] = []
    for d in ("NY", "FLA", "CAL"):
        for method in ("pace-b", "iscope"):
            rs = grouped[(d, method)]
            # Fully resolved and mean coverage are based on the query-level
            # median of the three trial coverages, not a trial-level mean.
            cov = [statistics.median(values) for values in coverage_by_query[(d, method)].values() if values]
            rss = [float(r["median_peak_rss_mib"]) for r in rs]
            rb = stat_block(rss, BOOTSTRAP_SEED + stable_offset(f"publication/{d}/{method}"))
            label = "PACE-B" if method == "pace-b" else "iSCOPE-Profile"
            timeout = ",".join(map(str, info[d][method]["timeout_seconds"]))
            threads = ",".join(map(str, info[d][method]["threads"]))
            r = {
                "dataset": d, "method": label, "median_runtime_s": statistics.median(float(x["median_query_runtime_s"]) for x in rs),
                "fully_resolved_queries_pct": 100 * sum(x >= 1 - 1e-12 for x in cov) / len(cov),
                "mean_resolved_coverage_pct": 100 * statistics.mean(cov),
                "full_window_score": statistics.median(float(x["median_score_zero_unreported"]) for x in rs),
                "peak_rss_gib": rb["median"] / 1024, "peak_rss_iqr_gib": rb["iqr"] / 1024,
                "peak_rss_mean_gib": rb["mean"] / 1024, "peak_rss_stddev_gib": rb["stddev"] / 1024 if rb["stddev"] is not None else None,
                "peak_rss_p95_gib": rb["p95"] / 1024, "peak_rss_max_gib": rb["maximum"] / 1024,
                "peak_rss_ci_low_gib": rb["bootstrap_ci95_low"] / 1024, "peak_rss_ci_high_gib": rb["bootstrap_ci95_high"] / 1024,
                "execution_status": "COMPLETED" if method == "pace-b" else "TIME_CAPPED_NOT_CERTIFIED / QUERY_DEADLINE",
                "n_queries": len(rs), "n_trials": 3, "source_file": rel(SOURCE_MAP[d][method]),
                "source_workload": "final 200 logical IDs, W120/RHO030", "timeout_context": timeout, "thread_context": threads,
            }
            table.append(r)
            plot.append({k: r[k] for k in ("dataset", "method", "median_runtime_s", "fully_resolved_queries_pct", "n_queries", "n_trials", "execution_status")})
    return table, plot, {"meta": meta, "info": info}, paths


def exact() -> tuple[list[dict[str, Any]], list[Path]]:
    p = FINAL / "manuscript_artifacts/extracted/final_exact_study_metrics.json"; d = jread(p); out = []
    for r in d["rows"]:
        for method in ("PACE-X", "PACE-B"):
            out.append({"budget_min": r["budget_min"], "method": method, "runtime_s": r[f"pace_{'x' if method == 'PACE-X' else 'b'}_runtime_s"], "score": r[f"pace_{'x' if method == 'PACE-X' else 'b'}_score"], "relative_gap_pct": r["relative_gap_pct"] if method == "PACE-B" else "", "path_agreement_pct": r["path_agreement_pct"] if method == "PACE-B" else "", "n_queries": r["certified_queries"], "n_trials": 3})
    return out, [p]


def policy() -> tuple[list[dict[str, Any]], list[Path]]:
    p = FINAL / "manuscript_artifacts/extracted/final_policy_study_metrics.json"; d = jread(p)
    labels = {"+theta": "Unbounded (+theta)", "+L": "+ top-L pivots", "+FastConnector": "+ single fastest connector", "+Kf": "+ K_f retention", "+Mb": "+ M_b (supplement)"}
    out = []
    for r in d["rows"]:
        out.append({**r, "display_stage": labels[r["stage"]], "included_in_main_figure": "true" if r["stage"] != "+Mb" else "false", "n_queries": r["certified_queries"], "n_trials": 3})
    return out, [p]


def parameter_sensitivity() -> tuple[list[dict[str, Any]], list[Path], list[dict[str, Any]]]:
    p = FINAL / "paper_existing/e14_parameter_sensitivity.csv"; out = []; audit = []; paths = [p]
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["axis"] not in {"pivot_limit_l", "frontier_limit_kf"}: continue
            axis = "L" if r["axis"] == "pivot_limit_l" else "Kf"
            out.append({"axis": axis, "value": float(r["value"]), "value_display": fmt(r["value"], 0), "effective_depth": "", "runtime_s": float(r["median_runtime_s"]), "completion_pct": 100 * float(r["completion_rate"]), "score": float(r["median_average_selected_score"]), "n_queries": int(float(r["planned"])), "n_trials": 3, "source_file": rel(p), "source_field": "median_runtime_s;completion_rate;median_average_selected_score", "configuration_note": "Frozen E14 aggregate; source-defined configuration/workload."})
    d = FINAL / "manuscript_missing_runs/results/fasttrack_parameter_final/work"
    for pth in sorted(d.glob("*/java-results.jsonl")):
        rows = [r for r in jsonl(pth) if not (r.get("run") or {}).get("warmup")]
        if not rows: continue
        c = rows[0]["configuration"]
        if c.get("pivot_limit_l") != 1 or c.get("frontier_limit_kf") != 1 or c.get("breakpoint_cap_mb") != 100000 or c.get("theta") not in {0, 1, 2, 3}: continue
        by: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows: by[r["query"]["query_id"]].append(r)
        runt = [statistics.median(x["timing_ns"]["query_total"] / 1e9 for x in rs) for rs in by.values()]
        cov = [statistics.median(float((x.get("output") or {}).get("feasible_coverage_fraction") or 0) for x in rs) for rs in by.values()]
        theta = int(c["theta"])
        out.append({"axis": "theta", "value": theta, "value_display": str(theta), "effective_depth": min(theta, 1), "runtime_s": statistics.median(runt), "completion_pct": 100 * sum(x >= 1 - 1e-12 for x in cov) / len(cov), "score": None, "n_queries": len(by), "n_trials": 3, "source_file": rel(pth), "source_field": "timing_ns.query_total;output.feasible_coverage_fraction", "configuration_note": "Fast-only connector source with L=1; theta_eff=min(theta,|A_q|)."})
        paths.append(pth)
    for r in out:
        audit.append({**r, "same_algorithm_semantics": "source-defined", "same_connector_mode": "source-defined", "same_timeout": "source-defined", "same_worker_count": "source-defined", "same_query_workload": "source-defined", "same_score_definition": "source-defined", "recommendation": "plot with caveat; theta_eff annotation"})
    return out, paths, audit


def workload_sensitivity() -> tuple[list[dict[str, Any]], list[Path], list[dict[str, Any]]]:
    p = FINAL / "paper_existing/t03_query_sensitivity_ny.csv"; base = []
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            base.append({"window_minutes": float(r["window_minutes"]), "rho": float(r["rho"]), "runtime_s": float(r["runtime_s"]), "score": float(r["avg_score_zero_unreported"]), "completion_pct": float(r["completion_pct"]), "n_queries": int(r["queries"]), "n_trials": 3, "source_file": rel(p), "source_field": "runtime_s;avg_score_zero_unreported;completion_pct"})
    out = []
    for r in base:
        for kind, x, label in (("window", r["window_minutes"], fmt(r["window_minutes"], 0)), ("rho", r["rho"], f"{r['rho']:.2f}")):
            out.append({"sensitivity": kind, "x_value": x, "x_label": label, "window_minutes": r["window_minutes"], "rho": r["rho"], "density_label": "", **{k: r[k] for k in ("runtime_s", "score", "completion_pct", "n_queries", "n_trials", "source_file", "source_field")}, "configuration_note": "Existing T03 workload-sensitivity aggregate."})
    d = FINAL / "manuscript_missing_runs/results/fasttrack_density_final/work"; paths = [p]; audit = []
    for pth in sorted(d.glob("*/java-results.jsonl")):
        rows = [r for r in jsonl(pth) if not (r.get("run") or {}).get("warmup")]
        if not rows: continue
        by: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows: by[r["query"]["query_id"]].append(r)
        runt = [statistics.median(x["timing_ns"]["query_total"] / 1e9 for x in rs) for rs in by.values()]
        score = [statistics.median(float((x.get("output") or {}).get("average_selected_score") or 0) for x in rs) for rs in by.values()]
        cov = [statistics.median(float((x.get("output") or {}).get("feasible_coverage_fraction") or 0) for x in rs) for rs in by.values()]
        m = re.search(r"score-density-(\d+)", str(rows[0]["dataset"]["dataset_path"]))
        density = int(m.group(1)) if m else -1; label = f"{density}%"
        out.append({"sensitivity": "density", "x_value": density, "x_label": label, "window_minutes": 120.0, "rho": 0.30, "density_label": label, "runtime_s": statistics.median(runt), "score": statistics.mean(score), "completion_pct": 100 * sum(x >= 1 - 1e-12 for x in cov) / len(cov), "n_queries": len(by), "n_trials": 3, "source_file": rel(pth), "source_field": "timing_ns.query_total;output.average_selected_score;output.feasible_coverage_fraction", "configuration_note": "Measured fast-only connector density batch; default 20% omitted because its source timeout/provenance is not identical."})
        paths.append(pth)
    for r in out: audit.append({**r, "same_algorithm_semantics": "source-defined", "same_connector_mode": "source-defined", "same_timeout": "source-defined", "same_worker_count": "source-defined", "same_query_workload": "axis-specific", "same_score_definition": "source-defined", "recommendation": "plot measured point only"})
    return out, paths, audit


def worker_sensitivity() -> tuple[list[dict[str, Any]], list[Path]]:
    """Recompute the frozen NY worker sweep at the logical-query level."""
    base = FINAL / "manuscript_missing_runs/results/fasttrack_parallel_final/work"
    out: list[dict[str, Any]] = []
    paths: list[Path] = []
    for pth in sorted(base.glob("*/java-results.jsonl")):
        rows = [r for r in jsonl(pth) if not (r.get("run") or {}).get("warmup")]
        if not rows:
            continue
        threads = int(rows[0]["configuration"]["threads"])
        by: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            by[r["query"]["query_id"]].append(float(r["timing_ns"]["query_total"]) / 1e9)
        query_medians = [statistics.median(values) for values in by.values()]
        out.append({
            "threads": threads,
            "runtime_s": statistics.median(query_medians),
            "runtime_iqr_s": statistics.quantiles(query_medians, n=4, method="inclusive")[2] - statistics.quantiles(query_medians, n=4, method="inclusive")[0],
            "runtime_mean_s": statistics.mean(query_medians),
            "runtime_p95_s": pctile(query_medians, 0.95),
            "completion_pct": 100.0 * sum(r["status"]["status_code"] == "COMPLETED" for r in rows) / len(rows),
            "n_queries": len(by),
            "n_trials": min(len(values) for values in by.values()),
            "source_file": rel(pth),
            "source_field": "timing_ns.query_total;status.status_code",
            "configuration_note": "Frozen NY worker sweep; fast-only connector source; warmups excluded; query statistic is median of three trials.",
        })
        paths.append(pth)
    out.sort(key=lambda r: r["threads"])
    return out, paths


def profiles() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Path]]:
    b = FINAL / "NYC-real-shuttle-v2"; mp = b / "validation/validation_metrics.json"; d = jread(mp); summary = []
    for cap in (5, 10, 30):
        data = d["caps"][str(cap)]; fp = b / "results/primary_5s.jsonl" if cap == 5 else b / f"results/diagnostic_{cap}s.jsonl"
        cell_values = [float((r.get("pace_b") or {}).get("profile_cell_count")) for r in jsonl(fp) if (r.get("pace_b") or {}).get("profile_cell_count") is not None]
        summary.append({"cap_s": cap, "n_total": data["query_count"], "n_resolved": data["status_counts"].get("COMPLETE", 0), "resolution_pct": 100 * data["resolved_coverage"], "cells_median": data["profile_cell_count"]["median"], "cells_iqr": data["profile_cell_count"]["q3"] - data["profile_cell_count"]["q1"], "cells_p90": pctile(cell_values, .9), "cells_max": data["profile_cell_count"]["maximum"], "paths_median": data["distinct_path_count"]["median"], "paths_max": data["distinct_path_count"]["maximum"], "multi_path_count": round(data["multi_path_rate"] * data["distinct_path_count"]["n"]), "multi_path_pct": 100 * data["multi_path_rate"], "route_switch_median": data["route_switches"]["median"], "interval_best_departure_coverage_median_pct": 100 * d["interval_best_registry"]["selected_departure_coverage"]["median"] if cap == 30 else None, "source_file": rel(fp)})
    rp = next(r for r in jsonl(b / "results/diagnostic_30s.jsonl") if r["query_id"] == "NYC-Q012-MORNING-R20")
    paths_seen: dict[str, int] = {}; cells = []
    for i, c in enumerate(rp["pace_b"]["cells"], 1):
        sig = hashlib.sha256(json.dumps(c.get("arc_ids", []), separators=(",", ":")).encode()).hexdigest()[:16]
        paths_seen.setdefault(sig, len(paths_seen) + 1)
        cells.append({"query_id": rp["query_id"], "cell_index": i, "start": c["start"], "end": c["end"], "average_score": c["average_score"], "average_travel_time": c["average_travel_time"], "path_rank": paths_seen[sig], "path_signature": sig})
    return summary, cells, [mp, b / "results/diagnostic_30s.jsonl", b / "validation/interval_best_registry_coverage.csv"]


def ledger_add(out: list[dict[str, Any]], n: list[int], *, rq: str, fig: str, panel: str, dataset: str, method: str, metric: str, value: Any, display: str, unit: str, stat: str, obs: str, nq: Any, nt: Any, source: str, field: str, workload: str, status: str = "FINAL", low: Any = "", high: Any = "", notes: str = "", derivation: str = "recomputed from frozen source") -> None:
    n[0] += 1
    state = "unavailable or prohibited" if status in {"UNAVAILABLE", "DO_NOT_USE"} else "measured or derived from measured"
    out.append({"value_id": f"V{n[0]:04d}", "rq": rq, "figure_or_table": fig, "panel": panel, "dataset": dataset, "method": method, "metric": metric, "display_value": display, "full_precision_value": value, "unit": unit, "statistic": stat, "observation_unit": obs, "n_queries": nq, "n_trials": nt, "source_file": source, "source_field": field, "source_workload": workload, "derivation": derivation, "measured_or_estimated": state, "estimated": "false", "estimator_if_any": "", "estimate_sources_if_any": "", "uncertainty_low": low, "uncertainty_high": high, "timeout_context": "source-defined", "thread_context": "source-defined", "notes": notes, "publication_status": status})


def make_ledger(scale: list[dict[str, Any]], exact_rows: list[dict[str, Any]], policy_rows: list[dict[str, Any]], sens: list[dict[str, Any]], workload: list[dict[str, Any]], workers: list[dict[str, Any]], profile: list[dict[str, Any]], cells: list[dict[str, Any]], oracle: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []; n = [0]; oracle_source = rel(REV / "oracle_validation/validation_summary.json")
    for k in ("deterministic_fixture_cases", "seeded_full_profile_cases", "instances_tested", "instances_passed", "instances_failed"):
        ledger_add(out, n, rq="RQ1", fig="exact_reference_final", panel="oracle", dataset="micro-instances", method="independent oracle", metric=k, value=oracle[k], display=fmt(oracle[k], 0), unit="instances", stat="count", obs="full-profile comparison", nq=oracle[k] if k != "instances_failed" else "", nt="", source=oracle_source, field=k, workload="9 fixtures + 1,000 fixed-seed FIFO micro-instances", notes="Independent oracle evidence; not Maven method count.")
    es = rel(FINAL / "manuscript_artifacts/extracted/final_exact_study_metrics.json")
    for r in exact_rows:
        for metric, field, value, display, unit in [("runtime", "pace_x_runtime_s" if r["method"] == "PACE-X" else "pace_b_runtime_s", r["runtime_s"], fmt(r["runtime_s"]), "s"), ("score", "pace_x_score" if r["method"] == "PACE-X" else "pace_b_score", r["score"], fmt(r["score"], 2), "score")]:
            ledger_add(out, n, rq="RQ1", fig="exact_reference_final", panel="a", dataset="NY-CTRL", method=r["method"], metric=metric, value=value, display=display, unit=unit, stat="controlled aggregate", obs="logical query", nq=r["n_queries"], nt=r["n_trials"], source=es, field=field, workload=f"NY-CTRL B={int(float(r['budget_min']))}", status="FINAL_WITH_CAVEAT", notes="Induced controlled reference, not full-NY certification.")
        if r["method"] == "PACE-B":
            for metric, field, value in (("relative score gap", "relative_gap_pct", r["relative_gap_pct"]), ("path agreement", "path_agreement_pct", r["path_agreement_pct"])):
                ledger_add(out, n, rq="RQ1", fig="exact_reference_final", panel="b", dataset="NY-CTRL", method="PACE-B", metric=metric, value=value, display=fmt(value, 1), unit="%", stat="controlled aggregate", obs="logical query", nq=r["n_queries"], nt=r["n_trials"], source=es, field=field, workload=f"NY-CTRL B={int(float(r['budget_min']))}", status="FINAL_WITH_CAVEAT")
    ps = rel(FINAL / "manuscript_artifacts/extracted/final_policy_study_metrics.json")
    for r in policy_rows:
        status = "FINAL_WITH_CAVEAT" if r["included_in_main_figure"] == "true" else "SUPPLEMENT_ONLY"
        for metric, field, value, display, unit in (("runtime", "runtime_s", r["runtime_s"], fmt(r["runtime_s"]), "s"), ("score", "average_score", r["average_score"], fmt(r["average_score"], 2), "score"), ("relative gap", "relative_gap_pct", r["relative_gap_pct"], fmt(r["relative_gap_pct"], 1), "%"), ("path agreement", "path_agreement_pct", r["path_agreement_pct"], fmt(r["path_agreement_pct"], 1), "%")):
            ledger_add(out, n, rq="RQ2", fig="bounded_policy_final", panel="a/b", dataset="NY-CTRL", method=r["display_stage"], metric=metric, value=value, display=display, unit=unit, stat="policy-stage aggregate", obs="logical query", nq=r["n_queries"], nt=r["n_trials"], source=ps, field=field, workload="controlled NY policy transition", status=status, notes="+Mb is supplement-only.")
    for r in scale:
        source = r["source_file"]
        for metric, field, value, display, unit, low, high in (("runtime", "median_runtime_s", r["median_runtime_s"], fmt(r["median_runtime_s"]), "s", "", ""), ("fully resolved queries", "fully_resolved_queries_pct", r["fully_resolved_queries_pct"], fmt(r["fully_resolved_queries_pct"], 1), "%", "", ""), ("mean resolved coverage", "mean_resolved_coverage_pct", r["mean_resolved_coverage_pct"], fmt(r["mean_resolved_coverage_pct"], 1), "%", "", ""), ("full-window score", "full_window_score", r["full_window_score"], fmt(r["full_window_score"], 2), "score", "", ""), ("query-phase peak RSS", "peak_rss_gib", r["peak_rss_gib"], fmt(r["peak_rss_gib"], 2), "GiB", fmt(r["peak_rss_ci_low_gib"], 2), fmt(r["peak_rss_ci_high_gib"], 2))):
            ledger_add(out, n, rq="RQ3", fig="scalability_final", panel="a/b", dataset=r["dataset"], method=r["method"], metric=metric, value=value, display=display, unit=unit, stat="logical-query aggregate", obs="logical query; median of three trials", nq=r["n_queries"], nt=3, source=source, field=field, workload=r["source_workload"], low=low, high=high, status="FINAL_WITH_CAVEAT", notes="RSS is query-phase process peak under shared preprocessing.")
    for r in sens:
        score_status = "FINAL_WITH_CAVEAT" if r["score"] is not None else "UNAVAILABLE"
        for metric, field, value, display, unit, status in (("runtime", "runtime_s", r["runtime_s"], fmt(r["runtime_s"]), "s", "FINAL_WITH_CAVEAT"), ("completion", "completion_pct", r["completion_pct"], fmt(r["completion_pct"], 1), "%", "FINAL_WITH_CAVEAT"), ("score", "score", r["score"], fmt(r["score"], 2), "score", score_status)):
            ledger_add(out, n, rq="RQ4", fig="algorithm_sensitivity_final", panel=r["axis"], dataset="NY", method="PACE-B sensitivity", metric=metric, value=value if value is not None else "", display=display, unit=unit, stat="source aggregate", obs="source-defined logical-query aggregate", nq=r["n_queries"], nt=3, source=r["source_file"], field=field, workload="existing parameter sensitivity", status=status, notes=r["configuration_note"] if value is not None else r["configuration_note"] + " Score is not recorded for this theta source.")
    for r in workload:
        for metric, field, value, display, unit in (("runtime", "runtime_s", r["runtime_s"], fmt(r["runtime_s"]), "s"), ("full-window score", "score", r["score"], fmt(r["score"], 2), "score"), ("completion", "completion_pct", r["completion_pct"], fmt(r["completion_pct"], 1), "%")):
            ledger_add(out, n, rq="RQ4", fig="workload_sensitivity_final", panel=r["sensitivity"], dataset="NY", method="PACE-B sensitivity", metric=metric, value=value, display=display, unit=unit, stat="source aggregate", obs="source-defined logical-query aggregate", nq=r["n_queries"], nt=3, source=r["source_file"], field=r["source_field"], workload="existing workload sensitivity", status="FINAL_WITH_CAVEAT", notes=r["configuration_note"])
    for r in workers:
        for metric, field, value, display, unit in (("runtime", "runtime_s", r["runtime_s"], fmt(r["runtime_s"]), "s"), ("completion", "completion_pct", r["completion_pct"], fmt(r["completion_pct"], 1), "%")):
            ledger_add(out, n, rq="RQ3", fig="worker_sensitivity_final", panel=f"threads={r['threads']}", dataset="NY", method="PACE-B sensitivity", metric=metric, value=value, display=display, unit=unit, stat="logical-query aggregate", obs="logical query; median of three trials", nq=r["n_queries"], nt=r["n_trials"], source=r["source_file"], field=field, workload="frozen NY worker-count sweep", status="SUPPLEMENT_ONLY", notes=r["configuration_note"])
    prof_source = rel(FINAL / "NYC-real-shuttle-v2/validation/validation_metrics.json")
    for r in profile:
        for metric, field, value, display, unit in (("attempted queries", "n_total", r["n_total"], fmt(r["n_total"], 0), "queries"), ("resolved queries", "n_resolved", r["n_resolved"], fmt(r["n_resolved"], 0), "queries"), ("resolution", "resolution_pct", r["resolution_pct"], fmt(r["resolution_pct"], 1), "%"), ("cells median", "cells_median", r["cells_median"], fmt(r["cells_median"], 1), "cells"), ("cells IQR", "cells_iqr", r["cells_iqr"], fmt(r["cells_iqr"], 1), "cells"), ("cells p90", "cells_p90", r["cells_p90"], fmt(r["cells_p90"], 1), "cells"), ("cells maximum", "cells_max", r["cells_max"], fmt(r["cells_max"], 0), "cells"), ("winning paths median", "paths_median", r["paths_median"], fmt(r["paths_median"], 1), "paths"), (">1 winning path count", "multi_path_count", r["multi_path_count"], fmt(r["multi_path_count"], 0), "queries"), (">1 winning path fraction", "multi_path_pct", r["multi_path_pct"], fmt(r["multi_path_pct"], 1), "%"), ("route switches median", "route_switch_median", r["route_switch_median"], fmt(r["route_switch_median"], 1), "switches")):
            ledger_add(out, n, rq="RQ5", fig="profile_utility_final", panel=f"cap={r['cap_s']}s", dataset="NYC", method="PACE-B diagnostic", metric=metric, value=value, display=display, unit=unit, stat="resolved-subset summary", obs="resolved query for distributions", nq=r["n_total"], nt="diagnostic", source=prof_source, field=field, workload=f"NYC v2 cap={r['cap_s']}s", status="FINAL_WITH_CAVEAT", notes="Distributional fields are over resolved queries only.")
        if r["interval_best_departure_coverage_median_pct"] is not None:
            ledger_add(out, n, rq="RQ5", fig="profile_utility_final", panel="cap=30s", dataset="NYC", method="PACE-B diagnostic", metric="interval-best departure coverage", value=r["interval_best_departure_coverage_median_pct"], display=fmt(r["interval_best_departure_coverage_median_pct"], 1), unit="%", stat="median over resolved queries", obs="resolved query", nq=r["n_resolved"], nt="diagnostic", source=rel(FINAL / "NYC-real-shuttle-v2/validation/interval_best_registry_coverage.csv"), field="selected_departure_coverage", workload="NYC v2 resolved subset", status="FINAL_WITH_CAVEAT")
    cell_source = rel(FINAL / "NYC-real-shuttle-v2/results/diagnostic_30s.jsonl")
    for c in cells:
        for metric, field, value, display, unit in (("cell start", "start", c["start"], fmt(c["start"], 0), "minutes"), ("cell end", "end", c["end"], fmt(c["end"], 0), "minutes"), ("cell score", "average_score", c["average_score"], fmt(c["average_score"], 2), "score"), ("stable path rank", "path_rank", c["path_rank"], fmt(c["path_rank"], 0), "rank")):
            ledger_add(out, n, rq="RQ5", fig="nyc_profile_final", panel="Q012 representative", dataset="NYC", method="PACE-B diagnostic", metric=metric, value=value, display=display, unit=unit, stat="cell record", obs="profile cell", nq=1, nt="diagnostic", source=cell_source, field=field, workload="NYC-Q012-MORNING-R20 at 30s", status="FINAL_WITH_CAVEAT", notes="Path rank is a within-profile label derived from recorded arc-ID signatures.")
    unavailable_source = rel(REV / "manuscript_metric_table.csv")
    for metric, dataset, method, source, field, rq, fig, panel, notes, status in (
        ("common resolved-domain score", "NY/FLA/CAL", "PACE-B vs iSCOPE-Profile", unavailable_source, "common_resolved_domain_score", "RQ3", "scalability_final", "a/b", "Comparable profile cells are not serialized for both final methods.", "UNAVAILABLE"),
        ("isolated graph-loading OS-RSS peak", "NY/FLA/CAL", "PACE-B/iSCOPE-Profile", unavailable_source, "memory_status", "RQ3", "scalability_final", "a/b", "Only shared-process RSS and heap checkpoints exist; graph-loading peak is not isolated.", "UNAVAILABLE"),
        ("isolated preprocessing OS-RSS peak", "NY/FLA/CAL", "PACE-B/iSCOPE-Profile", unavailable_source, "memory_status", "RQ3", "scalability_final", "a/b", "No OS preprocessing peak exists.", "UNAVAILABLE"),
        ("profile score gain versus interval-best", "NYC", "PACE-B diagnostic", rel(FINAL / "NYC-real-shuttle-v2/validation/validation_metrics.json"), "interval_best_registry", "RQ5", "profile_utility_final", "summary", "Unsupported by frozen NYC v2 records.", "UNAVAILABLE"),
        ("default 20% density point", "NY", "PACE-B sensitivity", rel(FINAL / "paper_existing/t03_query_sensitivity_ny.csv"), "density", "RQ4", "workload_sensitivity_final", "density", "Timeout/provenance is not identical to the measured 5%/40% batches.", "UNAVAILABLE"),
        ("full-NY PACE-X certification", "NY", "PACE-X", rel(FINAL / "manuscript_artifacts/extracted/final_exact_study_metrics.json"), "exactness_scope", "RQ1", "exact_reference_final", "oracle", "Only induced NY-CTRL reference is available; do not use as a full-NY claim.", "DO_NOT_USE"),
    ):
        ledger_add(out, n, rq=rq, fig=fig, panel=panel, dataset=dataset, method=method, metric=metric, value="", display=status, unit="", stat="not measured", obs="not applicable", nq="", nt="", source=source, field=field, workload="frozen evidence audit", status=status, notes=notes, derivation="not available in frozen evidence")
    return out


def write_tables(scale: list[dict[str, Any]], exact_rows: list[dict[str, Any]], policy_rows: list[dict[str, Any]], sens: list[dict[str, Any]], profile: list[dict[str, Any]], oracle: dict[str, Any]) -> None:
    e = chr(92) * 2
    lines = [r"\begin{table*}[t]", r"\centering", r"\caption{Independent correctness evidence and controlled exact reference.}", r"\begin{tabular}{lrrr}", r"\toprule", "Evidence & Count & Passes & Failures " + e, r"\midrule", f"Deterministic fixtures & {oracle['deterministic_fixture_cases']} & {oracle['deterministic_fixture_cases']} & 0 " + e, f"Fixed-seed FIFO micro-instances & {oracle['seeded_full_profile_cases']} & {oracle['seeded_full_profile_cases']} & 0 " + e, f"Total full-profile comparisons & {oracle['instances_tested']} & {oracle['instances_passed']} & {oracle['instances_failed']} " + e, r"\bottomrule", r"\end{tabular}", r"\vspace{2mm}", r"\begin{tabular}{rrrrrrrr}", r"\toprule", "$B$ & PACE-X (s) & PACE-B (s) & PACE-X score & PACE-B score & Gap (\\%) & Agreement (\\%) & n " + e, r"\midrule"]
    for b in sorted({float(x["budget_min"]) for x in exact_rows}):
        x = next(r for r in exact_rows if float(r["budget_min"]) == b and r["method"] == "PACE-X"); y = next(r for r in exact_rows if float(r["budget_min"]) == b and r["method"] == "PACE-B")
        lines.append(f"{int(b)} & {fmt(x['runtime_s'])} & {fmt(y['runtime_s'])} & {fmt(x['score'],2)} & {fmt(y['score'],2)} & {fmt(y['relative_gap_pct'],1)} & {fmt(y['path_agreement_pct'],1)} & {x['n_queries']} " + e)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", r"\textit{Note.} The oracle validates micro-instances. The displayed PACE-X reference is GLOBAL\_CERTIFIED only on induced NY-CTRL, not full NY."]
    write_text(OUT / "tables/exact_reference_final.tex", "\n".join(lines))
    main = [x for x in policy_rows if x["included_in_main_figure"] == "true"]
    lines = [r"\begin{table}[t]", r"\centering", r"\caption{Bounded-policy transition in controlled NY.}", r"\begin{tabular}{lrrrrr}", r"\toprule", "Stage & Runtime & Score & Regret & Gap (\\%) & Agree. (\\%) " + e, r"\midrule"]
    for r in main: lines.append(f"{tex(r['display_stage'])} & {fmt(r['runtime_s'])} & {fmt(r['average_score'],2)} & {fmt(r['absolute_regret'],2)} & {fmt(r['relative_gap_pct'],1)} & {fmt(r['path_agreement_pct'],1)} " + e)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", r"\textit{Note.} The single-fastest-connector step is the first major observed quality transition; +M_b is supplement-only."]
    write_text(OUT / "tables/policy_transition_final.tex", "\n".join(lines))
    lines = [r"\begin{table*}[t]", r"\centering", r"\caption{Bounded execution on the final W120/RHO030 slice.}", r"\begin{tabular}{llrrrrrl}", r"\toprule", "Dataset & Method & Runtime (s) & Fully resolved (\\%) & Mean coverage (\\%) & Full-window score & Peak RSS (GiB) & Status " + e, r"\midrule"]
    for r in scale: lines.append(f"{r['dataset']} & {r['method']} & {fmt(r['median_runtime_s'])} & {fmt(r['fully_resolved_queries_pct'],1)} & {fmt(r['mean_resolved_coverage_pct'],1)} & {fmt(r['full_window_score'],2)} & {fmt(r['peak_rss_gib'],2)} & {tex(r['execution_status'])} " + e)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", r"\textit{Note.} Observation = logical query; three trials are summarized by query median. iSCOPE is anytime at 5 s; unresolved regions contribute zero to full-window score. RSS is query-phase process peak under shared preprocessing. PACE-B/iSCOPE use 24/1 workers; NY/CAL PACE-B retain configured 10 s safety timeout, FLA uses a frozen 5 s source."]
    write_text(OUT / "tables/scalability_final.tex", "\n".join(lines))
    lines = [r"\begin{table}[t]", r"\centering", r"\caption{NYC temporal-profile structure by diagnostic cap.}", r"\begin{tabular}{rrrrrrrrrr}", r"\toprule", "Cap & Total & Resolved & Resolved (\\%) & Cells med. & IQR & p90 & Max & Paths med. & $>1$ path " + e, r"\midrule"]
    for r in profile: lines.append(f"{r['cap_s']} & {r['n_total']} & {r['n_resolved']} & {fmt(r['resolution_pct'],1)} & {fmt(r['cells_median'],1)} & {fmt(r['cells_iqr'],1)} & {fmt(r['cells_p90'],1)} & {fmt(r['cells_max'],0)} & {fmt(r['paths_median'],1)} & {r['multi_path_count']} ({fmt(r['multi_path_pct'],1)}\\%) " + e)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", r"\textit{Note.} Profile distributions are over resolved queries only; score gain versus interval-best is unavailable."]
    write_text(OUT / "tables/profile_utility_final.tex", "\n".join(lines))
    lines = [r"\begin{table*}[t]", r"\centering", r"\caption{Measured algorithm sensitivity values.}", r"\begin{tabular}{llrrr}", r"\toprule", "Axis & Setting & Runtime (s) & Completion (\\%) & Score " + e, r"\midrule"]
    for axis in ("L", "theta", "Kf"):
        for r in sorted([x for x in sens if x["axis"] == axis], key=lambda x: float(x["value"])): lines.append(f"{axis} & {r['value_display']} & {fmt(r['runtime_s'])} & {fmt(r['completion_pct'],1)} & {fmt(r['score'],2)} " + e)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", r"\textit{Note.} The theta source uses L=1, so theta at or above one realizes effective depth one. Density points are in the workload figure and only measured levels are shown."]
    write_text(OUT / "tables/sensitivity_summary_final.tex", "\n".join(lines))


def story_and_decision(scale: list[dict[str, Any]], oracle: dict[str, Any]) -> None:
    lines = ["# Story/value audit", "", "| Claim | Evidence | Exact value/source | Caveat | Safe wording | Unsafe wording |", "|---|---|---|---|---|---|"]
    rows = [
        ("PACE-X agrees with an independent oracle", "exact_reference_final", f"{oracle['instances_tested']} comparisons; {oracle['instances_passed']} passes; {oracle['instances_failed']} failures", "Micro-instances only", "PACE-X agrees with the independent oracle on 1,009 micro-instance full-profile comparisons.", "PACE-X is certified on full NY."),
        ("PACE-X is a controlled exact reference", "exact_reference_final", "NY-CTRL induced subset", "Not full-NY", "We use PACE-X as a controlled exact reference on NY-CTRL.", "PACE-X certifies full NY."),
        ("PACE-B remains inexpensive as exact cost rises", "exact_reference_final", "At B=15: PACE-X 13.755 s; PACE-B 0.024 s; PACE-B gap 72.3%", "Controlled NY-CTRL only", "PACE-X cost rises strongly with controlled budget while PACE-B remains low-latency in the same reference study.", "PACE-B is always exact."),
        ("Single-fastest connector is the dominant observed transition", "bounded_policy_final", "See policy ledger rows", "Controlled policy workload", "The first major observed quality change occurs at the single-fastest-connector restriction.", "This is universal across all workloads."),
        ("PACE-B completes the selected final slices", "scalability_final", "PACE-B status COMPLETED on NY/FLA/CAL rows", "Selected 200-query slice", "PACE-B completes the selected final 200-query slice.", "PACE-B completes every possible workload."),
        ("iSCOPE is anytime and uncertified at termination", "scalability_final", "TIME_CAPPED_NOT_CERTIFIED / QUERY_DEADLINE", "5 s, one worker", "iSCOPE is an anytime baseline stopped at five seconds and remains uncertified.", "iSCOPE is a completed exact baseline."),
        ("Resolution and utility are network dependent", "scalability_final", "iSCOPE full-resolution: NY 74.5%, FLA 81.0%, CAL 51.0%", "Full-window zero-unreported score", "PACE-B resolves all selected queries; iSCOPE resolution and RSS behavior vary by network.", "PACE-B uniformly dominates every metric."),
        ("Full-window returned utility favors PACE-B in this protocol", "scalability_final", "NY 376.89 vs 295.50; FLA 222.23 vs 173.90; CAL 306.62 vs 82.63", "Selected W120/RHO030 slice; not a common resolved-domain comparison", "PACE-B returns higher full-window utility on each reported network under this bounded protocol.", "PACE-B is superior on a comparable exact domain."),
        ("Memory behavior is network dependent", "scalability_final", "PACE-B/iSCOPE RSS GiB: NY 12.54/9.88; FLA 49.49/17.35; CAL 42.29/52.31", "Query-phase process peak under shared preprocessing", "PACE-B does not uniformly dominate iSCOPE in process peak RSS.", "PACE-B always uses less memory."),
        ("PACE-B worker latency does not monotonically improve", "worker_sensitivity_final", "Frozen NY medians across 1/4/8/16/24 workers are reported in the supplementary CSV", "Fast-only connector source; 20 IDs", "The worker sweep is supporting evidence, not an equal-core headline comparison.", "The scalability table is an equal-core comparison."),
        ("Theta saturates in the measured source", "algorithm_sensitivity_final", "theta_eff=min(theta,1) because L=1", "No L>=theta experiment", "The theta experiment saturates because L=1.", "Search depth is intrinsically irrelevant."),
        ("NYC profiles can have multiple cells and paths", "nyc_profile_final", "Q012 representative; profile utility ledger", "Only resolved subset", "Some resolved NYC queries require multiple temporal cells and winning paths.", "All 100 NYC queries resolve."),
    ]
    for r in rows: lines.append("| " + " | ".join(r) + " |")
    lines += ["", "No graph-loading or preprocessing OS-RSS peak is available. No common resolved-domain score is available. No estimates are used."]
    write_text(OUT / "STORY_VALUE_AUDIT.md", "\n".join(lines))
    scale_lines = []
    for r in scale:
        scale_lines.append(f"- {r['dataset']} {r['method']}: runtime {fmt(r['median_runtime_s'])} s; fully resolved {fmt(r['fully_resolved_queries_pct'], 1)}%; mean coverage {fmt(r['mean_resolved_coverage_pct'], 1)}%; full-window score {fmt(r['full_window_score'], 2)}; peak RSS {fmt(r['peak_rss_gib'], 2)} GiB.")
    write_text(OUT / "FINAL_FIGURE_AND_VALUE_DECISION.md", """# Final figure and value decision

## Main-paper figures

Use `exact_reference_final`, `bounded_policy_final`, `scalability_final`, `algorithm_sensitivity_final`, and `workload_sensitivity_final`. Retain `nyc_profile_final` as an application figure if page budget permits.

## Tables

Use `tables/scalability_final.tex` and the exact/policy tables in the main paper. Move `tables/sensitivity_summary_final.tex`, `tables/profile_utility_final.tex`, and the worker-sweep CSV to the supplement if page review requires it.

## Publication-safe numerical values

Use `FINAL_MANUSCRIPT_VALUES.csv` as the sole numerical source. The scalability table is the preferred prose source for runtime, fully resolved-query percentage, mean coverage, full-window score, and query-phase peak RSS.

Exact values suitable for prose:

""" + "\n".join(scale_lines) + """

## Unavailable or do-not-use values

Common resolved-domain score, isolated graph-loading RSS, isolated preprocessing RSS, profile score gain versus interval-best, full-NY PACE-X certification, and the non-comparable default density point are explicit in `unavailable_metrics.csv`. No missing values are estimated.

## Captions

- Exact reference: controlled NY-CTRL exact-reference cost/quality; micro-oracle evidence does not establish full-NY exactness.
- Bounded policy: first observed quality transition at the single-fastest connector; +M_b is supplement-only.
- Scalability: final W120/RHO030 slice; query observation with three-trial medians; iSCOPE is 5-second time-capped anytime output.
- Algorithm sensitivity: measured L, effective theta depth, and K_f; theta source has L=1.
- Workload sensitivity: measured window, slack, and density points only; non-monotonicity is retained.
- NYC profile: recorded temporal boundaries, scores, and within-profile path labels for the representative resolved query.

## Supplementary worker evidence

`tables/worker_sensitivity_final.csv` recomputes the frozen NY 1/4/8/16/24-worker sweep from 20 logical IDs, excluding warmups and taking the median of three trials per query. It is not an equal-core fairness claim.

## Provenance reconciliation

The corrected scalability coverage values use query-level medians of the three trial coverages. The earlier trial-level summaries were not used. The default 20% density point is omitted because its timeout/provenance is not identical to the measured 5% and 40% batches. No values are estimated.

## Caption proposals

- Figure A: "Controlled NY-CTRL exact-reference cost and PACE-B quality trade-off; the oracle evidence is on micro-instances and does not certify full NY."
- Figure B: "Bounded-policy transition in controlled NY; the first major observed quality loss occurs at the single deterministic fastest-connector restriction; +M_b is supplement-only."
- Figure C: "Bounded execution on the final W120/RHO030 slice; each observation is a logical query summarized by three-trial medians; iSCOPE is a one-worker, five-second time-capped anytime output."
- Figure D: "Measured parameter sensitivity for top-L pivots, effective theta depth, and K_f; theta values at or above one share effective depth one because the source uses L=1."
- Figure E: "Measured workload sensitivity for departure window, budget slack, and available score-bearing-edge densities; unmeasured density settings are omitted and non-monotonicity is retained."
- NYC profile figure: "Recorded temporal profile for NYC-Q012-MORNING-R20 at the 30-second diagnostic cap; labels are within-profile path ranks derived from recorded arc-ID signatures."
- Scalability table: "Bounded execution on the final W120/RHO030 slice; RSS is query-phase process peak under shared preprocessing, not isolated graph-loading or preprocessing memory."
- Exact-reference table: "Independent oracle counts and controlled NY-CTRL exact-reference values."
- Policy table: "Measured bounded-policy stages in controlled NY; +M_b is supplement-only."
- Profile table: "NYC profile structure summarized over the resolved subset at each diagnostic cap."
- Sensitivity table: "Measured parameter sensitivity values; theta uses L=1 and missing theta scores are marked unavailable."

## Further experiments

No further experiment is scientifically necessary for this frozen presentation.
""")


def main() -> int:
    for p in (OUT, OUT / "tables", OUT / "figures", OUT / "plot_data", OUT / "provenance"): p.mkdir(parents=True, exist_ok=True)
    scale, scale_plot, source_info, scale_paths = scalability()
    exact_rows, exact_paths = exact(); policy_rows, policy_paths = policy(); sens, sens_paths, sens_audit = parameter_sensitivity(); workload, workload_paths, workload_audit = workload_sensitivity(); workers, worker_paths = worker_sensitivity(); profile, cells, profile_paths = profiles()
    oracle = jread(REV / "oracle_validation/validation_summary.json")
    write_csv(OUT / "plot_data/scalability_final.csv", scale_plot); write_csv(OUT / "plot_data/exact_reference_final.csv", exact_rows); write_csv(OUT / "plot_data/bounded_policy_final.csv", policy_rows); write_csv(OUT / "plot_data/algorithm_sensitivity_final.csv", sens); write_csv(OUT / "plot_data/workload_sensitivity_final.csv", workload); write_csv(OUT / "plot_data/nyc_profile_final.csv", cells)
    write_json(OUT / "plot_data/plot_manifest.json", {"figures": ["exact_reference_final", "bounded_policy_final", "scalability_final", "algorithm_sensitivity_final", "workload_sensitivity_final", "nyc_profile_final"], "estimated_points": 0})
    write_tables(scale, exact_rows, policy_rows, sens, profile, oracle)
    write_csv(OUT / "tables/table_scalability_final.csv", scale, fields=["dataset", "method", "median_runtime_s", "fully_resolved_queries_pct", "mean_resolved_coverage_pct", "full_window_score", "peak_rss_gib", "peak_rss_iqr_gib", "peak_rss_mean_gib", "peak_rss_stddev_gib", "peak_rss_p95_gib", "peak_rss_max_gib", "peak_rss_ci_low_gib", "peak_rss_ci_high_gib", "execution_status", "n_queries", "n_trials", "source_file", "source_workload", "timeout_context", "thread_context"])
    write_text(OUT / "tables/table_scalability_final_notes.md", "Observation = logical query; each query statistic is the median of three trials. iSCOPE is a one-worker anytime execution stopped at five seconds; unresolved regions contribute zero to the full-window score. Peak RSS is the process peak observed during query execution under shared preprocessing. PACE-B uses 24 workers in these archived final sources; iSCOPE uses one worker. NY/CAL PACE-B retain a configured 10 s safety timeout, while the selected FLA source is configured at 5 s.")
    write_csv(OUT / "tables/worker_sensitivity_final.csv", workers)
    write_text(OUT / "tables/worker_sensitivity_final.md", "Frozen NY worker-count supporting sweep. Warmups are excluded; each of 20 logical IDs contributes the median of three measured trials. This source uses the fast-only connector configuration and is supplementary evidence, not an equal-core comparison.\n\n| Workers | Median runtime (s) | IQR (s) | Mean (s) | p95 (s) | Completion (%) | Queries | Trials |\n|---:|---:|---:|---:|---:|---:|---:|---:|\n" + "\n".join(f"| {r['threads']} | {fmt(r['runtime_s'])} | {fmt(r['runtime_iqr_s'])} | {fmt(r['runtime_mean_s'])} | {fmt(r['runtime_p95_s'])} | {fmt(r['completion_pct'],1)} | {r['n_queries']} | {r['n_trials']} |" for r in workers))
    ledger = make_ledger(scale, exact_rows, policy_rows, sens, workload, workers, profile, cells, oracle)
    write_csv(OUT / "FINAL_MANUSCRIPT_VALUES.csv", ledger, FIELDS); write_json(OUT / "FINAL_MANUSCRIPT_VALUES.json", {"schema_version": "pace-final-manuscript-values-v1", "estimated_rows": 0, "values": ledger})
    md = ["# Final manuscript values", "", "Canonical ledger for all manuscript-ready numeric values. `estimated=false` for every row.", "", "| ID | RQ | Figure/table | Dataset | Method | Metric | Display | Status | Source |", "|---|---|---|---|---|---|---|---|---|"]
    for r in ledger: md.append("| " + " | ".join(str(r[k]).replace("|", "\\|") for k in ("value_id", "rq", "figure_or_table", "dataset", "method", "metric", "display_value", "publication_status", "source_file")) + " |")
    write_text(OUT / "FINAL_MANUSCRIPT_VALUES.md", "\n".join(md))
    write_csv(OUT / "SENSITIVITY_VALUE_AUDIT.csv", sens_audit + workload_audit)
    write_csv(OUT / "estimated_metrics.csv", [], ["metric", "dataset", "method", "estimate", "units", "source_files", "source_fields", "estimator", "sample_size", "uncertainty_low", "uncertainty_high", "assumptions", "estimated"])
    write_csv(OUT / "unavailable_metrics.csv", [{"metric": "common resolved-domain score", "status": "UNAVAILABLE", "reason": "Comparable profile cells are not serialized for both final methods."}, {"metric": "isolated graph-loading OS-RSS peak", "status": "UNAVAILABLE", "reason": "Only shared-process RSS and heap checkpoints exist."}, {"metric": "isolated preprocessing OS-RSS peak", "status": "UNAVAILABLE", "reason": "No OS preprocessing peak exists."}, {"metric": "profile score gain versus interval-best", "status": "UNAVAILABLE", "reason": "Unsupported by frozen NYC v2 records."}, {"metric": "default 20% density point", "status": "UNAVAILABLE", "reason": "Timeout/provenance is not identical to the measured 5%/40% batches."}, {"metric": "full-NY PACE-X certification", "status": "DO_NOT_USE", "reason": "Only induced NY-CTRL reference is available."}])
    story_and_decision(scale, oracle)
    source_paths = scale_paths + exact_paths + policy_paths + sens_paths + workload_paths + worker_paths + profile_paths + [REV / "oracle_validation/validation_summary.json", REV / "oracle_validation/oracle_results.csv"]
    source_paths = sorted({p for p in source_paths if p.exists()}, key=rel)
    write_text(OUT / "provenance/source_checksums.sha256", "\n".join(f"{digest(p)}  {rel(p)}" for p in source_paths))
    write_json(OUT / "provenance/source_mapping.json", {"source_info": source_info, "sources": [rel(p) for p in source_paths]})
    write_json(OUT / "provenance/analysis_parameters.json", {"bootstrap_seed": BOOTSTRAP_SEED, "rss_reported_units": "GiB = source bytes / 2^30", "scalability_observation": "logical query; median of three trials", "fully_resolved_rule": "coverage >= 1 - 1e-12", "estimated_points": 0, "density_policy": "5% and 40% only", "theta_policy": "theta_eff=min(theta,1) for L=1 source", "worker_sweep": "NY fast-only connector; 1,4,8,16,24 workers; warmups excluded; 20 logical IDs; median of three trials"})
    scripts = ["plot_exact_reference_final.py", "plot_bounded_policy_final.py", "plot_scalability_final.py", "plot_algorithm_sensitivity_final.py", "plot_workload_sensitivity_final.py", "plot_nyc_profile_final.py"]
    for script in scripts: subprocess.run([sys.executable, str(OUT / "scripts" / script), "--root", str(OUT)], check=True)
    hashes = []
    for script in scripts:
        p = OUT / "scripts" / script; hashes.append({"kind": "script", "path": rel(p), "sha256": digest(p)})
        stem = script.removesuffix(".py").removeprefix("plot_")
        for ext in ("pdf", "png"):
            p = OUT / "figures" / f"{stem}.{ext}"; hashes.append({"kind": "figure", "path": rel(p), "sha256": digest(p)})
    write_csv(OUT / "provenance/plotting_hashes.csv", hashes)
    unchanged = (REV / "provenance/frozen_sha256_before.sha256").exists() and (REV / "provenance/frozen_sha256_before.sha256").read_bytes() == (REV / "provenance/frozen_sha256_after.sha256").read_bytes()
    validation = {"ledger_rows": len(ledger), "estimated_rows": 0, "source_files": len(source_paths), "all_figures_present": all((OUT / "figures" / f"{s.removesuffix('.py').removeprefix('plot_')}.{e}").exists() for s in scripts for e in ("pdf", "png")), "all_tables_present": all((OUT / "tables" / f).exists() for f in ("scalability_final.tex", "table_scalability_final.csv", "table_scalability_final_notes.md", "exact_reference_final.tex", "policy_transition_final.tex", "profile_utility_final.tex", "sensitivity_summary_final.tex", "worker_sensitivity_final.csv", "worker_sensitivity_final.md")), "frozen_artifact_audit_before_equals_after": unchanged, "no_experiment_commands_run": True, "no_estimates_used": True}
    write_json(OUT / "provenance/validation.json", validation)
    return 0 if validation["all_figures_present"] and validation["all_tables_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
