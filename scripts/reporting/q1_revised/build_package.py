"""Build six publication figures using frozen files within q1_figures_v2 only.

Run from revised_figures_v3 with:
    PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_package.py

No existing v2 builder is invoked: those builders reference external ledgers.
"""
from __future__ import annotations

import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil

from common import OUTPUT, PACKAGE, inside, raw_csv, sha256, write_csv, write_json, write_path

STATEMENT = "No experiments were rerun. Figure derived exclusively from frozen data under q1_figures_v2."
COPIES = {
    "plot_data/exact_reference_final_q1.csv": "plot_data/exact_reference_final_q1.csv",
    "plot_data/bounded_policy_final_q1.csv": "plot_data/bounded_policy_final_q1.csv",
    "plot_data/scalability_final_q1.csv": "plot_data/scalability_final_q1.csv",
    "plot_data/algorithm_sensitivity_final_q1.csv": "plot_data/algorithm_sensitivity_final_q1.csv",
    "plot_data/workload_sensitivity_final_q1.csv": "plot_data/workload_sensitivity_final_q1.csv",
    "plot_data/scalability_budget_audit.csv": "plot_data/scalability_budget_audit.csv",
    "derived_values/scalability_budget_summary.csv": "plot_data/scalability_budget_summary.csv",
    "plot_data/error_bar_provenance.csv": "plot_data/error_bar_provenance.csv",
    "FINAL_FIGURE_VALUE_AUDIT.csv": "plot_data/FINAL_FIGURE_VALUE_AUDIT.csv",
}
SPECS = [
    {"stem": "fig03_exact_reference_v3", "module": "plot_exact_reference", "number": "3",
     "sources": ["plot_data/exact_reference_final_q1.csv", "plot_data/error_bar_provenance.csv"],
     "filters": "Exact-reference CSV lines 2–7: all six runtime rows; PACE-B rows 3,5,7 for gaps and median agreement; oracle counts from line 2, consistent across all rows. Error provenance lines 2–7.",
     "transformation": "None: runtime_s, runtime_half_iqr_s, relative_gap_pct, path_agreement_pct and oracle counts preserved. Log runtime axis. Rounded labels only."},
    {"stem": "fig04_successive_policy_tradeoff_v3", "module": "plot_policy_tradeoff", "number": "4",
     "sources": ["plot_data/bounded_policy_final_q1.csv"],
     "filters": "CSV lines 2–5; all stage_index=0,1,2,3 rows, in that introduction order.",
     "transformation": "Map x=runtime_s and y=relative_gap_pct; label path_agreement_pct. No jitter or new statistic. Runtime half-IQR preserved in CSV but not drawn because the final-stage bars overlap."},
    {"stem": "fig05_large_network_comparison_v3", "module": "plot_scalability", "number": "5",
     "sources": ["plot_data/scalability_final_q1.csv"],
     "filters": "CSV lines 2–7; all NY/FLA/CAL × PACE-B/iSCOPE-Profile rows. Fields runtime_s, fully_resolved_pct, relative_utility_pct; deadline_s=5.",
     "transformation": "Existing normalization retained: 100 * full_window_score(method,network) / full_window_score(PACE-B,network). No change to the unresolved-portion handling inherited from the frozen metric."},
    {"stem": "fig06_algorithm_sensitivity_v3", "module": "plot_algorithm_sensitivity", "number": "6",
     "sources": ["plot_data/algorithm_sensitivity_final_q1.csv"],
     "filters": "CSV lines 2–5: L=1,2,4,8; lines 6–9: K_f=1,2,4,8; lines 10–13: theta=0,1,2,3. All rows preserved, including effective_depth and source reference flags.",
     "transformation": "None. Common runtime/completion axes; effective depth is the stored 0,1,1,1. Dashed reference settings from canonical_default, without implying common experimental configurations."},
    {"stem": "fig07_workload_sensitivity_v3", "module": "plot_workload_sensitivity", "number": "7",
     "sources": ["plot_data/workload_sensitivity_final_q1.csv"],
     "filters": "CSV lines 2–4: window=120,240,360; lines 5–7: rho=.1,.3,.5; lines 8–9: density=5,40. Runtime for every row; scores only for window/rho. Density score fields remain blank.",
     "transformation": "None. Two measured density points use markers only; no density interpolation and no density score panel."},
    {"stem": "figS1_budget_distribution_v3", "module": "plot_budget_distribution", "number": "S1",
     "sources": ["plot_data/scalability_budget_audit.csv", "derived_values/scalability_budget_summary.csv"],
     "filters": "Budget observations CSV lines 2–601: all 600 rows; summary CSV lines 2–4: NY/FLA/CAL. Overall summary line 5 preserved for validation, not drawn as a fourth row.",
     "transformation": "Stored min/Q1/median/Q3/max and all exact budget_min observations retained. n_queries read from summary. Quartiles independently checked with inclusive quantiles; no runtime inferred."},
]


def inventory():
    records = []
    for directory, dirs, files in os.walk(PACKAGE, followlinks=False):
        current = Path(directory)
        dirs[:] = sorted(d for d in dirs if not (current / d).is_symlink() and current / d != OUTPUT)
        for name in sorted(files):
            path = current / name
            if path.is_symlink():
                records.append({"file": str(path.relative_to(PACKAGE)), "kind": "symlink-not-followed", "bytes": "", "sha256": ""})
                continue
            path = inside(path)
            records.append({"file": str(path.relative_to(PACKAGE)), "kind": path.suffix,
                            "bytes": path.stat().st_size, "sha256": sha256(path)})
    return sorted(records, key=lambda r: r["file"])


def main():
    for directory in ("figures", "previews", "scripts", "plot_data", "provenance", "review"):
        write_path(OUTPUT / directory / ".sentinel").parent.mkdir(parents=True, exist_ok=True)
    snapshot = OUTPUT / "provenance/original_package_inventory.csv"
    if snapshot.exists():
        originals = raw_csv(snapshot)
        assert all(not r["sha256"] or sha256(PACKAGE / r["file"]) == r["sha256"] for r in originals), "An original v2 file changed."
    else:
        originals = inventory()
        write_csv(snapshot, originals, ["file", "kind", "bytes", "sha256"])
    copy_rows = []
    for original, copied in COPIES.items():
        source, dest = inside(PACKAGE / original), write_path(OUTPUT / copied)
        if dest.exists():
            assert sha256(dest) == sha256(source), f"Frozen input copy changed: {copied}"
        else:
            shutil.copyfile(source, dest)
        copy_rows.append({"original_relative_to_q1_figures_v2": original,
                          "copy_relative_to_v3": copied, "sha256": sha256(source),
                          "byte_identical": "true"})
    write_csv(OUTPUT / "provenance/input_copies.csv", copy_rows,
              ["original_relative_to_q1_figures_v2", "copy_relative_to_v3", "sha256", "byte_identical"])
    old_hashes = []
    for row in raw_csv(PACKAGE / "provenance/figure_hashes.csv"):
        actual = sha256(PACKAGE / row["file"])
        old_hashes.append({"file": row["file"], "old_manifest_sha256": row["sha256"],
                           "actual_sha256": actual, "matches": str(row["sha256"] == actual).lower()})
    write_csv(OUTPUT / "provenance/original_hash_manifest_audit.csv", old_hashes,
              ["file", "old_manifest_sha256", "actual_sha256", "matches"])
    for spec in SPECS:
        importlib.import_module(spec["module"]).main()
        print(f"Rendered {spec['stem']}", flush=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    manifest, value_records, hashes = [], [], []
    for spec in SPECS:
        stem = spec["stem"]
        script = OUTPUT / "scripts" / f"{spec['module']}.py"
        pdf, png = OUTPUT / "figures" / f"{stem}.pdf", OUTPUT / "previews" / f"{stem}.png"
        source_records = [{"original_relative_to_q1_figures_v2": src,
                           "copy_relative_to_v3": COPIES[src],
                           "sha256": sha256(OUTPUT / COPIES[src])} for src in spec["sources"]]
        record = {"figure_name": stem, "suggested_figure_number": spec["number"],
                  "source_files": json.dumps(source_records), "exact_input_rows_filters": spec["filters"],
                  "transformation": spec["transformation"], "script": str(script.relative_to(OUTPUT)),
                  "script_sha256": sha256(script), "shared_script": "scripts/common.py",
                  "shared_script_sha256": sha256(OUTPUT / "scripts/common.py"),
                  "builder_sha256": sha256(Path(__file__)),
                  "final_pdf": str(pdf.relative_to(OUTPUT)), "final_pdf_sha256": sha256(pdf),
                  "final_png": str(png.relative_to(OUTPUT)), "final_png_sha256": sha256(png),
                  "timestamp_utc": timestamp, "statement": STATEMENT}
        manifest.append(record)
        write_json(OUTPUT / "provenance" / f"{stem}.json", {**record, "source_files": source_records})
        render = json.loads(inside(OUTPUT / "review" / f"{stem}_render.json").read_text())
        value_records.extend({"figure": stem, **row} for row in render["used_values"])
    write_csv(OUTPUT / "provenance/figure_sources.csv", manifest, list(manifest[0]))
    write_csv(OUTPUT / "provenance/plotted_values.csv", value_records,
              ["figure", "source", "csv_line", "field", "frozen_value", "used_value"])
    for directory in ("figures", "previews", "scripts", "plot_data"):
        for path in sorted((OUTPUT / directory).iterdir()):
            if path.is_file():
                hashes.append({"file": str(path.relative_to(OUTPUT)), "sha256": sha256(path), "timestamp_utc": timestamp})
    write_csv(OUTPUT / "provenance/figure_hashes.csv", hashes, ["file", "sha256", "timestamp_utc"])
    # A small review index provides one-click access without another scientific plot.
    cards = "\n".join(f'<article><h2>Figure {r["suggested_figure_number"]}</h2><a href="../{r["final_pdf"]}"><img src="../{r["final_png"]}" alt="{r["figure_name"]}"></a></article>' for r in manifest)
    write_path(OUTPUT / "review/index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>PACE revised figures v3</title>'
        '<style>body{font:16px system-ui;margin:32px auto;max-width:1100px;color:#30353b}article{border-top:1px solid #ddd;margin:30px 0;padding:16px 0}img{width:100%;height:auto}h2{font-size:18px}</style>'
        '<h1>PACE revised figures v3</h1><p>Click a preview to open the vector PDF. '
        'Frozen local data; no experiments rerun.</p>' + cards, encoding="utf-8")
    assert all(not r["sha256"] or sha256(PACKAGE / r["file"]) == r["sha256"] for r in originals)
    print(f"Built {len(SPECS)} figures; copied {len(COPIES)} frozen inputs; preserved {len(originals)} original files.")


if __name__ == "__main__":
    main()
