"""Phase-A audit of the raw/final PACE result tree.

This script is deliberately audit-only. It reads result files under
experiments/results/Final-result and writes audit tables/reports under
revised_figures_v3. It never writes to the raw result tree and never renders a
figure.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PACKAGE = HERE.parent
RAW = PACKAGE.parents[3] / "experiments" / "results" / "Final-result"

T03_BATCHES = {
    "NY": "9cf12fc8bd016f3940fcf9c0",
    "FLA": "11b15beaa4848abf224725ab",
    "CAL": "79a34e97c6e908e47ec930b5",
}
T03_ISCOPE_BATCHES = {
    "NY": "56f61cca317ea7e097ae7410",
    "FLA": "4a73475fdbb5d931c58986d0",
    "CAL": "2986b18a313f519b98798b5e",
}


def out(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def measured(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not r.get("run", {}).get("warmup", False)]


def qinc(values: list[float], p: float) -> float:
    values = sorted(values)
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * p
    lo = int(position)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (position - lo) * (values[hi] - values[lo])


def finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def fmt(value, digits=6) -> str:
    if value is None or not finite(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def logical_groups(rows: list[dict], predicate=None) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for row in rows:
        if predicate is None or predicate(row):
            groups[row["query"]["query_id"]].append(row)
    return dict(groups)


def status_normal(row: dict) -> bool:
    return row.get("status", {}).get("status_code") == "COMPLETED"


def runtime(row: dict) -> float | None:
    value = row.get("timing_ns", {}).get("query_total")
    return float(value) / 1e9 if finite(value) else None


def score0(row: dict) -> float:
    score = row.get("output", {}).get("average_selected_score")
    coverage = row.get("output", {}).get("feasible_coverage_fraction")
    score = float(score) if finite(score) else 0.0
    coverage = min(1.0, max(0.0, float(coverage))) if finite(coverage) else 0.0
    return score * coverage


def query_summary(rows: list[dict], accepted_statuses=("COMPLETED",)) -> dict:
    accepted = [r for r in rows if r.get("status", {}).get("status_code") in accepted_statuses]
    runtimes = [runtime(r) for r in accepted if runtime(r) is not None]
    scores = [score0(r) for r in accepted]
    coverages = [
        float(r["output"]["feasible_coverage_fraction"])
        for r in accepted
        if finite(r.get("output", {}).get("feasible_coverage_fraction"))
    ]
    checksums = [r.get("output", {}).get("profile_checksum") for r in accepted]
    checksum = Counter(x for x in checksums if x).most_common(1)
    return {
        "all_trials_normal": bool(rows) and len(accepted) == len(rows),
        "normal_trial_count": len(accepted),
        "runtime_s": statistics.median(runtimes) if runtimes else float("nan"),
        "score0": statistics.median(scores) if scores else 0.0,
        "coverage": statistics.median(coverages) if coverages else 0.0,
        "checksum": checksum[0][0] if checksum else "",
        "statuses": ";".join(f"{k}:{v}" for k, v in sorted(Counter(r.get("status", {}).get("status_code") for r in rows).items())),
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with out(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_t03(dataset: str, method: str) -> list[dict]:
    batch = T03_BATCHES[dataset] if method == "PACE-B" else T03_ISCOPE_BATCHES[dataset]
    return read_jsonl(RAW / dataset / "work" / f"batch-{batch}" / "java-results.jsonl")


def principal_groups(dataset: str, method: str) -> dict[str, list[dict]]:
    rows = read_t03(dataset, method)
    return logical_groups(rows, lambda r: r["query"].get("window_length") == 120 and
                         r["query"].get("budget_slack") == 0.3)


def audit_large_network() -> tuple[list[dict], list[dict]]:
    audit_rows, figure_rows = [], []
    for dataset in ("NY", "FLA", "CAL"):
        groups = principal_groups(dataset, "PACE-B")
        completed = []
        normal_trials = []
        all_trial_status = Counter()
        for qid, rows in groups.items():
            all_trial_status.update(r["status"]["status_code"] for r in rows)
            q = query_summary(rows)
            if q["all_trials_normal"]:
                completed.append(q["runtime_s"])
            normal_trials.extend(runtime(r) for r in rows if status_normal(r) and runtime(r) is not None)
        audit_rows.append({
            "dataset": dataset,
            "workload_filter": "window_minutes=120,rho=0.30",
            "n_total_logical_queries": len(groups),
            "n_completed_logical_queries": len(completed),
            "n_incomplete_logical_queries": len(groups) - len(completed),
            "normal_completed_trial_rows": len(normal_trials),
            "minimum_runtime_s_completed_logical": min(completed) if completed else "",
            "median_runtime_s_completed_logical": statistics.median(completed) if completed else "",
            "maximum_runtime_s_completed_logical": max(completed) if completed else "",
            "completed_logical_queries_runtime_ge_5s": sum(x >= 5 for x in completed),
            "normal_trial_rows_runtime_ge_5s": sum(x >= 5 for x in normal_trials),
            "status_counts": ";".join(f"{k}:{v}" for k, v in sorted(all_trial_status.items())),
            "incomplete_query_ids": ";".join(sorted(
                qid for qid, rows in groups.items()
                if not query_summary(rows)["all_trials_normal"]
            )),
            "all_completed_logical_queries_below_5s": str(bool(completed) and all(x < 5 for x in completed)).lower(),
        })

        for method in ("PACE-B", "iSCOPE"):
            groups_m = principal_groups(dataset, method)
            accepted = ("COMPLETED",) if method == "PACE-B" else ("TIME_CAPPED_NOT_CERTIFIED",)
            qrows = {qid: query_summary(rows, accepted) for qid, rows in groups_m.items()}
            runtime_values = [q["runtime_s"] for q in qrows.values() if finite(q["runtime_s"])]
            score_values = [q["score0"] for q in qrows.values()]
            resolved = sum(q["coverage"] > 0 for q in qrows.values())
            normal_q = sum(q["all_trials_normal"] for q in qrows.values()) if method == "PACE-B" else 0
            b = next((r for r in audit_rows if r["dataset"] == dataset), None)
            figure_rows.append({
                "dataset": dataset,
                "method": method,
                "window_minutes": 120,
                "rho": 0.30,
                "n_total_logical_queries": len(qrows),
                "n_completed_logical_queries": normal_q,
                "reported_resolution_pct": 100.0 * resolved / len(qrows) if qrows else "",
                "median_completed_query_runtime_s": statistics.median(runtime_values) if runtime_values else "",
                "minimum_completed_query_runtime_s": min(runtime_values) if runtime_values else "",
                "maximum_completed_query_runtime_s": max(runtime_values) if runtime_values else "",
                "runtime_ge_5s_completed_queries": sum(x >= 5 for x in runtime_values),
                "reported_full_window_score_zero_unreported": statistics.median(score_values) if score_values else "",
                "runtime_cutoff_semantics": "PACE-B normal COMPLETED only" if method == "PACE-B" else "iSCOPE TIME_CAPPED_NOT_CERTIFIED rows under 5-s cutoff",
                "notes": "PACE-B FLA has four incomplete logical queries; resolution is among query records with a full reported coverage value." if dataset == "FLA" and method == "PACE-B" else "",
            })
    return audit_rows, figure_rows


def audit_exact_and_policy() -> tuple[list[dict], list[dict]]:
    exact_root = RAW / "manuscript_missing_runs" / "final_ny_exact" / "raw"
    exact = {}
    for method in ("pace-x", "pace-b"):
        rows = []
        for p in sorted((exact_root / method).glob("trial-*.jsonl")):
            rows.extend(measured(read_jsonl(p)))
        exact[method] = logical_groups(rows)

    fig3, fig4 = [], []
    for budget in (5.0, 10.0, 15.0):
        qids = sorted({qid for qid, rows in exact["pace-x"].items() if rows[0]["query"].get("budget") == budget})
        xrt = [query_summary(exact["pace-x"][qid])["runtime_s"] for qid in qids]
        brt = [query_summary(exact["pace-b"][qid])["runtime_s"] for qid in qids]
        xscore = {qid: query_summary(exact["pace-x"][qid])["score0"] for qid in qids}
        bscore = {qid: query_summary(exact["pace-b"][qid])["score0"] for qid in qids}
        gaps = [100 * (xscore[qid] - bscore[qid]) / xscore[qid] for qid in qids if xscore[qid] > 0]
        equal = [query_summary(exact["pace-x"][qid])["checksum"] == query_summary(exact["pace-b"][qid])["checksum"] for qid in qids]
        for method, values in (("PACE-X", xrt), ("PACE-B", brt)):
            fig3.append({
                "budget_min": budget,
                "method": method,
                "n_logical_queries": len(qids),
                "n_completed_logical_queries": len(qids),
                "median_runtime_s": statistics.median(values),
                "q1_runtime_s": qinc(values, .25),
                "q3_runtime_s": qinc(values, .75),
                "iqr_runtime_s": qinc(values, .75) - qinc(values, .25),
                "median_score_zero_unreported": statistics.median(xscore.values() if method == "PACE-X" else bscore.values()),
                "median_relative_gap_pct_pace_b_vs_pace_x": statistics.median(gaps) if method == "PACE-B" else "",
                "checksum_equal_queries": sum(equal) if method == "PACE-B" else "",
                "checksum_agreement_median_pct": statistics.median([100.0 if x else 0.0 for x in equal]) if method == "PACE-B" else "",
                "source_note": "Final exact study; runtime IQR recomputed from 20 logical-query medians; raw study does not serialize a named error-bar field.",
            })

    stage_map = [
        ("plus-theta", "Depth cap"), ("plus-l", "Top-L"),
        ("plus-fastconnector", "Single connector"), ("plus-kf", "Kf retention"),
        ("plus-mb", "Mb production guard (not requested Figure 4 stage)"),
    ]
    policy_root = RAW / "manuscript_missing_runs" / "final_ny_policy" / "raw"
    for directory, label in stage_map:
        rows = []
        for p in sorted((policy_root / directory).glob("trial-*.jsonl")):
            rows.extend(measured(read_jsonl(p)))
        groups = logical_groups(rows)
        runtimes, gaps, equal = [], [], []
        for qid, rs in groups.items():
            q = query_summary(rs)
            runtimes.append(q["runtime_s"])
            xq = query_summary(exact["pace-x"][qid])
            if xq["score0"] > 0:
                gaps.append(100 * (xq["score0"] - q["score0"]) / xq["score0"])
            equal.append(q["checksum"] == xq["checksum"])
        fig4.append({
            "stage_directory": directory,
            "stage_label": label,
            "n_logical_queries": len(groups),
            "n_completed_logical_queries": sum(query_summary(rs)["all_trials_normal"] for rs in groups.values()),
            "median_runtime_s_completed_queries": statistics.median(runtimes) if runtimes else "",
            "median_relative_gap_pct_vs_pace_x": statistics.median(gaps) if gaps else "",
            "median_path_agreement_pct_checksum_proxy": statistics.median([100.0 if x else 0.0 for x in equal]) if equal else "",
            "checksum_equal_queries": sum(equal),
            "source_note": "Checksum equality is the available raw proxy; path-agreement fraction is not serialized.",
        })
    return fig3, fig4


def audit_budget() -> list[dict]:
    rows = []
    for dataset, batch in T03_BATCHES.items():
        path = RAW / dataset / "work" / f"batch-{batch}" / "queries.jsonl"
        by = {}
        for row in read_jsonl(path):
            if row.get("window_length") == 120 and row.get("budget_slack") == 0.3:
                by[row["query_id"]] = row
        for qid, row in sorted(by.items()):
            rows.append({"dataset": dataset, "query_id": qid, "window_minutes": 120, "rho": 0.30, "budget_min": row["budget"], "source": str(path)})
    return rows


def audit_sensitivity() -> list[dict]:
    rows = []
    agg_path = RAW / "NY-EXACT" / "summaries" / "aggregate_records.csv"
    with agg_path.open(encoding="utf-8") as stream:
        for r in csv.DictReader(stream):
            if r.get("algorithm_id") != "pace-b":
                continue
            axis = json.loads(r["axis_json"])
            setting = None
            parameter = None
            if axis.get("pivot_limit_l") in (1, 2, 4, 8) and axis.get("connector_limit_kc") == 1 and axis.get("frontier_limit_kf") == 1:
                parameter, setting = "L", axis["pivot_limit_l"]
            elif axis.get("frontier_limit_kf") in (1, 2, 4, 8) and axis.get("pivot_limit_l") == 1 and axis.get("connector_limit_kc") == 1:
                parameter, setting = "Kf", axis["frontier_limit_kf"]
            if parameter is None:
                continue
            total = int(float(r["planned"]))
            complete = int(float(r["successful"]))
            rows.append({
                "parameter": parameter,
                "setting": setting,
                "source": str(agg_path),
                "total_query_count": total,
                "completed_query_count": complete,
                "incomplete_query_count": total - complete,
                "completion_pct": 100 * complete / total if total else "",
                "median_completed_runtime_s": float(r["median_wall_time_ns"]) / 1e9,
                "runtime_definition": "aggregate median over successful rows; raw summary excludes unsuccessful rows",
                "configuration": r["axis_json"],
            })

    fast_root = RAW / "manuscript_missing_runs" / "results" / "fasttrack_parameter_final" / "work"
    for path in sorted(fast_root.glob("*/java-results.jsonl")):
        measured_rows = measured(read_jsonl(path))
        if not measured_rows:
            continue
        theta = measured_rows[0]["configuration"].get("theta")
        if theta not in (0, 1, 2, 3):
            continue
        groups = logical_groups(measured_rows)
        completed = []
        for rs in groups.values():
            normal = [runtime(r) for r in rs if status_normal(r) and runtime(r) is not None]
            if len(normal) == len(rs):
                completed.append(statistics.median(normal))
        total = len(groups)
        rows.append({
            "parameter": "theta",
            "setting": theta,
            "source": str(path),
            "total_query_count": total,
            "completed_query_count": len(completed),
            "incomplete_query_count": total - len(completed),
            "completion_pct": 100 * len(completed) / total if total else "",
            "median_completed_runtime_s": statistics.median(completed) if completed else "",
            "runtime_definition": "median of three measured trial runtimes for logical queries with three normal COMPLETED trials",
            "configuration": json.dumps(measured_rows[0]["configuration"], sort_keys=True),
        })
    return sorted(rows, key=lambda r: (r["parameter"], float(r["setting"])))


def audit_workload() -> list[dict]:
    rows = []
    p = RAW / "NY" / "work" / f"batch-{T03_BATCHES['NY']}" / "java-results.jsonl"
    all_rows = read_jsonl(p)
    settings = [("window", w, 0.3) for w in (120, 240, 360)] + [("rho", 120, rho) for rho in (0.1, 0.3, 0.5)]
    for parameter, value, rho in settings:
        def keep(r):
            q = r["query"]
            return q.get("window_length") == value if parameter == "window" else q.get("window_length") == 120 and q.get("budget_slack") == rho
        if parameter == "window":
            keep = lambda r, rho=rho, value=value: r["query"].get("window_length") == value and r["query"].get("budget_slack") == rho
        groups = logical_groups(all_rows, keep)
        completed = []
        score_values = []
        for rs in groups.values():
            q = query_summary(rs)
            if q["all_trials_normal"]:
                completed.append(q["runtime_s"])
            score_values.append(q["score0"])
        rows.append({
            "parameter": parameter,
            "setting": value,
            "fixed_rho": rho,
            "source": str(p),
            "total_query_count": len(groups),
            "completed_query_count": len(completed),
            "incomplete_query_count": len(groups) - len(completed),
            "completion_pct": 100 * len(completed) / len(groups) if groups else "",
            "median_completed_runtime_s": statistics.median(completed) if completed else "",
            "reported_full_window_score_zero_unreported": statistics.median(score_values) if score_values else "",
            "runtime_definition": "median of logical-query medians over queries with three normal COMPLETED trials",
        })

    density_root = RAW / "manuscript_missing_runs" / "results" / "fasttrack_density_final" / "work"
    for path in sorted(density_root.glob("*/java-results.jsonl")):
        rs = measured(read_jsonl(path))
        groups = logical_groups(rs)
        completed = []
        for qrows in groups.values():
            vals = [runtime(r) for r in qrows if status_normal(r) and runtime(r) is not None]
            if len(vals) == len(qrows):
                completed.append(statistics.median(vals))
        density = rs[0]["dataset"].get("anchor_density", "")
        rows.append({
            "parameter": "score-bearing-edge-density",
            "setting": density,
            "fixed_rho": 0.3,
            "source": str(path),
            "total_query_count": len(groups),
            "completed_query_count": len(completed),
            "incomplete_query_count": len(groups) - len(completed),
            "completion_pct": 100 * len(completed) / len(groups) if groups else "",
            "median_completed_runtime_s": statistics.median(completed) if completed else "",
            "reported_full_window_score_zero_unreported": "",
            "runtime_definition": "median of logical-query medians over three normal COMPLETED trials",
        })
    return rows


def write_provenance() -> None:
    rows = [
        {"figure": "Figure 3", "panel": "a/b", "plotted_metric": "runtime, score gap, checksum-agreement proxy", "derived_file": "plot_data/fig3_controlled.csv", "raw_source_file": "manuscript_missing_runs/final_ny_exact/raw/{pace-x,pace-b}/trial-*.jsonl", "query_filter": "NY final exact; B=5,10,15; 20 logical query IDs per budget", "completion_filter": "three measured COMPLETED trials", "aggregation": "median of logical-query trial medians; score gap per query", "normalization": "none", "notes": "Available; raw study supports these budgets. Raw path_agreement_fraction is absent; profile checksum equality is a proxy."},
        {"figure": "Figure 4", "panel": "trade-off", "plotted_metric": "runtime, relative score gap, path agreement", "derived_file": "plot_data/fig4_restrictions.csv", "raw_source_file": "manuscript_missing_runs/final_ny_policy/raw/{plus-theta,plus-l,plus-fastconnector,plus-kf}/trial-*.jsonl", "query_filter": "NY final policy B=5; 20 logical query IDs", "completion_filter": "three measured COMPLETED trials", "aggregation": "median of logical-query trial medians; score gap against paired PACE-X", "normalization": "relative gap vs paired exact PACE-X score", "notes": "Available for the four requested stages, but score-gap values differ from the current manuscript table."},
        {"figure": "Figure 5", "panel": "a/b/c", "plotted_metric": "runtime, resolution, full-window score", "derived_file": "plot_data/fig5_large_network.csv", "raw_source_file": "{NY,FLA,CAL}/work/batch-*/java-results.jsonl", "query_filter": "window=120, rho=0.30; 200 logical query IDs per network", "completion_filter": "PACE-B runtime uses all-normal logical queries; iSCOPE uses TIME_CAPPED_NOT_CERTIFIED records", "aggregation": "logical-query medians then dataset median", "normalization": "iSCOPE score relative to PACE-B within network", "notes": "BLOCKED: FLA completed logical-query runtimes exceed 5 s and four logical queries contain timeout trials."},
        {"figure": "Figure 6", "panel": "distribution", "plotted_metric": "query-specific travel-time budget", "derived_file": "plot_data/fig6_budget_distribution.csv", "raw_source_file": "{NY,FLA,CAL}/work/batch-*/queries.jsonl", "query_filter": "window=120, rho=0.30; unique query_id", "completion_filter": "manifest records", "aggregation": "min, inclusive Q1, median, inclusive Q3, max", "normalization": "none", "notes": "Available; 200 unique budgets per network."},
        {"figure": "Figure 7", "panel": "L/Kf/theta", "plotted_metric": "completed-query median runtime and completion", "derived_file": "plot_data/fig7_algorithmic_sensitivity.csv", "raw_source_file": "NY-EXACT/summaries/aggregate_records.csv and manuscript_missing_runs/results/fasttrack_parameter_final/work/*/java-results.jsonl", "query_filter": "one-at-a-time configurations", "completion_filter": "failed/incomplete logical queries excluded from runtime median", "aggregation": "summary successful counts; logical-query medians for theta fasttrack", "normalization": "none", "notes": "Available as an audit; source families are not one fully crossed experiment."},
        {"figure": "Figure 8", "panel": "window/rho/density", "plotted_metric": "completed-query median runtime and absolute score", "derived_file": "plot_data/fig8_workload_sensitivity.csv", "raw_source_file": "NY/work/batch-*/java-results.jsonl and manuscript_missing_runs/results/fasttrack_density_final/work/*/java-results.jsonl", "query_filter": "NY T03 requested settings", "completion_filter": "failed/incomplete logical queries excluded from runtime median", "aggregation": "logical-query medians then setting median", "normalization": "absolute zero-unreported full-window score", "notes": "Available for audit; current Figure 8 window values used rho=0.10 for two points despite labeling rho=0.30."},
    ]
    write_csv(HERE / "plot_data" / "PROVENANCE.csv", rows, list(rows[0]))


def write_reports(large, fig3, fig4, budget, sensitivity, workload) -> None:
    # Required machine-readable artifacts.
    write_csv(HERE / "LARGE_NETWORK_RUNTIME_AUDIT.csv", large, list(large[0]))
    write_csv(HERE / "SENSITIVITY_RUNTIME_AUDIT.csv", sensitivity, list(sensitivity[0]))
    write_csv(HERE / "plot_data" / "fig3_controlled.csv", fig3, list(fig3[0]))
    write_csv(HERE / "plot_data" / "fig4_restrictions.csv", fig4, list(fig4[0]))

    large_fields = list(large[0])
    write_csv(HERE / "plot_data" / "fig5_large_network.csv", [
        {k: r.get(k, "") for k in large_fields} for r in audit_large_network()[1]
    ], list(audit_large_network()[1][0]))
    write_csv(HERE / "plot_data" / "fig6_budget_distribution.csv", budget, list(budget[0]))
    write_csv(HERE / "plot_data" / "fig7_algorithmic_sensitivity.csv", sensitivity, list(sensitivity[0]))
    write_csv(HERE / "plot_data" / "fig8_workload_sensitivity.csv", workload, list(workload[0]))
    write_provenance()

    md = f"""# Phase-A raw-data audit

Date: 2026-09-11

## Status

Phase A is complete. Phase B is **stopped before figure regeneration** because
the requested principal large-network protocol is not supported by the raw
results: at window 120 min and rho=0.30, all 196 fully completed FLA logical
queries have completed-query median runtimes above 5 s, and the other four FLA
logical queries contain timeout trials. The raw evidence must not be forced into
the requested publication claim.

The raw result tree contains 138,368 files. No file under
`experiments/results/Final-result` was modified.

## Principal large-network runtime audit

| Dataset | Logical queries | Fully completed logical queries | Incomplete logical queries | Completed-query median (s) | Minimum (s) | Maximum (s) | Completed logical queries >=5 s | Normal trial rows >=5 s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
"""
    for r in large:
        md += f"| {r['dataset']} | {r['n_total_logical_queries']} | {r['n_completed_logical_queries']} | {r['n_incomplete_logical_queries']} | {fmt(r['median_runtime_s_completed_logical'], 6)} | {fmt(r['minimum_runtime_s_completed_logical'], 6)} | {fmt(r['maximum_runtime_s_completed_logical'], 6)} | {r['completed_logical_queries_runtime_ge_5s']} | {r['normal_trial_rows_runtime_ge_5s']} |\n"
    md += """
`n_completed` counts a logical query only when all three measured trials have
status `COMPLETED`. Runtime medians are formed from the three measured trial
times per completed logical query and then summarized across logical queries.
The FLA timeout query IDs are recorded in the CSV-producing audit logic and are
not silently discarded from the completion audit.

## Figure 3 — controlled exact reference

Raw source: `manuscript_missing_runs/final_ny_exact/`.
The final exact study does contain 20 logical queries at each requested budget
B=5, 10, and 15 min, with three measured trials per method. The recomputed
PACE-X and PACE-B runtime medians match the current manuscript values to the
reported precision. The runtime error bars are not a named statistic in the raw
study summary; the audit table provides the recomputed Q1/Q3/IQR of logical-query
medians. The raw quality object does not serialize `path_agreement_fraction` or
`relative_score_gap_percent`; this audit uses profile-checksum equality as an
explicit proxy for path agreement and recomputes score gap from paired
`average_selected_score` values.

The recomputed median score gaps are approximately 39.25%, 64.89%, and 75.55%
for B=5, 10, and 15, respectively, when the per-query gap is summarized over
nonzero exact-reference scores. The current manuscript values 36.9%, 62.8%,
and 72.3% therefore do not match the raw final exact study.

## Figure 4 — successive policy

Raw source: `manuscript_missing_runs/final_ny_policy/`, paired to the B=5
PACE-X records in `final_ny_exact/`. The four requested stages are present and
all 20 logical queries complete across three measured trials. Runtime medians
recompute as 0.07320, 0.04255, 0.02804, and 0.02694 s. The checksum-agreement
proxy has medians 100%, 100%, 0%, and 0%. The recomputed median score gaps are
0%, 0%, 39.25%, and 39.25%, so the currently printed 36.9% gap is not supported
by this raw final exact/policy pairing.

## Figure 5 — large-network comparison

Raw source: the six canonical T03 batches for NY, FLA, and CAL. Each requested
setting has 200 logical query IDs and three measured trials. iSCOPE rows carry
status `TIME_CAPPED_NOT_CERTIFIED` under its configured 5 s cutoff. The only
5 s interpretation supported by the raw configuration is the iSCOPE cutoff;
PACE-B was executed with a 10 s internal limit in these T03 batches.

The PACE-B audit fails the requested all-below-5-s publication check for FLA.
Consequently, no Figure 5 replacement was generated. The existing figure must
not be relabeled as a common 5 s protocol or retain a PACE-B 10 s boundary.

## Figure 6 — travel-time budget distribution

Raw source: the T03 `queries.jsonl` manifests. The requested filter yields 200
unique query budgets per network. The recomputed inclusive five-number summaries
are stored in `plot_data/fig6_budget_distribution.csv`; they agree with the
current budget-distribution values.

## Figure 7 — algorithmic sensitivity

The L/Kf rows are supported by the NY-EXACT aggregate summary generated from
the raw E14 records. The theta rows are supported by the fasttrack parameter
records, with failed/no-feasible logical queries excluded from the runtime
median and counted in completion. The source families are not one fully crossed
experiment: L/Kf use the E14 parameter grid, while theta uses the fasttrack
L=1 configuration. All per-setting counts and completed-query runtime medians
are in `SENSITIVITY_RUNTIME_AUDIT.csv`.

## Figure 8 — workload sensitivity

The NY T03 raw records support window 120/240/360 min and rho 0.10/0.30/0.50,
with runtime medians computed over fully completed logical queries only. The
current workload CSV labels all window points as rho=0.30, but its 240- and
360-minute runtime values correspond to rho=0.10 in the raw source. The raw
rho=0.30 values are 3.2854, 3.3475, and 3.4945 s for windows 120, 240, and
360 min. Density records at approximately 5% and 40% are also present, with no
comparable score values.

## Query counts, filtering, and aggregation

- Repeated process trials were grouped by `query.query_id`; they were not
  counted as separate logical queries.
- Warmup records were excluded before all measured-runtime calculations.
- Sensitivity runtime medians exclude logical queries without three normal
  measured completions; failures and incomplete records are counted separately.
- T03 score audit values use `output.average_selected_score` multiplied by
  `output.feasible_coverage_fraction`, treating missing/unresolved score as zero.
- Figure 5(c) normalization is 100 times the iSCOPE zero-unreported workload
  score divided by the corresponding PACE-B score. It is not an approximation
  ratio.

## Required next decision

Before Phase B can be authorized, reconcile the manuscript's principal FLA
protocol with the raw T03 result: either supply a valid below-5-s PACE-B result
set for the stated comparison or revise the protocol/claim and captions. No
figure was regenerated after this discrepancy was found.
"""
    out(HERE / "DATA_AUDIT.md").write_text(md, encoding="utf-8")

    score_md = """# Score metric audit

## Raw fields and observed aggregation

The T03 result records expose `output.average_selected_score` and
`output.feasible_coverage_fraction`. The local extraction logic in
`Final-result/pace_existing_data_extract.py` constructs the publication-level
zero-unreported score as:

`score_zero_unreported = average_selected_score * clamp(feasible_coverage_fraction, 0, 1)`

Missing selected scores and unresolved coverage therefore contribute zero. The
raw summaries distinguish this field from `avg_score_reported_resolved_only`.
The recomputed Figure 5 absolute score medians are:

| Dataset | PACE-B zero-unreported score | iSCOPE zero-unreported score | iSCOPE / PACE-B |
|---|---:|---:|---:|
| NY | 376.8917 | 295.4968 | 78.4036% |
| FLA | 222.2292 | 173.8963 | 78.2509% |
| CAL | 306.6167 | 82.6259 | 26.9476% |

These ratios are workload-level normalized scores, not approximation ratios.

## Independent cell-duration check

The T03 JSONL records contain aggregate output values and envelope-cell counts,
but no serialized per-cell score durations or profile interval table. Therefore
an independent exact-duration recomputation from temporal cells cannot be
performed from the raw Final-result snapshot. No temporal sampling or new score
definition was introduced.

## Exact and policy score comparisons

The final NY exact/policy records expose paired `average_selected_score` values
and profile checksums but do not serialize `relative_score_gap_percent` or
`path_agreement_fraction`. The audit recomputes the relative score gap per
paired logical query and marks checksum equality as a clearly identified path
agreement proxy. This is why the recomputed exact/policy gap differs from the
current manuscript values.
"""
    out(HERE / "SCORE_METRIC_AUDIT.md").write_text(score_md, encoding="utf-8")

    changelog = """# Phase-A plot changelog

No publication figure was regenerated in this run. The mandatory FLA runtime
check failed before Phase B, so the current v3 PDFs/PNGs remain untouched.

| Requested figure | Phase-A result | Required publication action |
|---|---|---|
| Figure 3 | Raw final exact study supports B=5/10/15 and runtime medians; score gaps differ from current manuscript values | Recompute from `plot_data/fig3_controlled.csv` only after the manuscript discrepancy is accepted |
| Figure 4 | Four cumulative policy stages are present; runtime and checksum-agreement proxy reproduce the stage pattern; score gap differs | Recompute from `plot_data/fig4_restrictions.csv` only after the discrepancy is accepted |
| Figure 5 | BLOCKED: FLA PACE-B violates the requested all-below-5-s condition; PACE-B raw T03 configuration uses a 10 s internal limit | Do not generate a replacement until protocol/claim is reconciled |
| Figure 6 | Budget manifests support 200 unique queries per network and the current five-number summaries | Safe to regenerate after Figure 5 decision |
| Figure 7 | Sensitivity raw records exist, but L/Kf and theta come from different evaluated configuration families | Use completed-query runtime labels and disclose source-family distinction |
| Figure 8 | Raw T03 supports requested window/rho settings; two current window runtimes are labeled with the wrong rho | Regenerate with raw filters, completed-query medians, and absolute scores |

Explicit cleanup requirements recorded for Phase B:

1. Remove all obsolete 10 s PACE-B boundary wording from publication-facing
   plots/captions/README files.
2. Label the 5 s line as the iSCOPE-Profile cutoff only.
3. Use completed-query-only runtime medians for every sensitivity setting.
4. Preserve unresolved=0 in full-window score aggregation.
5. Report all raw-data discrepancies against the current manuscript instead of
   forcing agreement.
"""
    out(HERE / "PLOT_CHANGELOG.md").write_text(changelog, encoding="utf-8")


def main() -> None:
    large, fig5 = audit_large_network()
    fig3, fig4 = audit_exact_and_policy()
    budget = audit_budget()
    sensitivity = audit_sensitivity()
    workload = audit_workload()
    write_reports(large, fig3, fig4, budget, sensitivity, workload)
    print("Phase-A audit written; Phase-B figure generation intentionally not run.")
    for row in large:
        print(f"{row['dataset']}: n={row['n_total_logical_queries']} completed={row['n_completed_logical_queries']} median={fmt(row['median_runtime_s_completed_logical'])} max={fmt(row['maximum_runtime_s_completed_logical'])} ge5={row['completed_logical_queries_runtime_ge_5s']}")


if __name__ == "__main__":
    main()
