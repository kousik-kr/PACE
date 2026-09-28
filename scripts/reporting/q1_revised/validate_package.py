"""Validate frozen values, provenance, PDF fonts and PDF-rendered previews locally."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

from common import OUTPUT, PACKAGE, inside, raw_csv, sha256, write_csv, write_json, write_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-previews", action="store_true")
    args = parser.parse_args()
    copies = raw_csv(OUTPUT / "provenance/input_copies.csv")
    for row in copies:
        assert sha256(PACKAGE / row["original_relative_to_q1_figures_v2"]) == row["sha256"]
        assert sha256(OUTPUT / row["copy_relative_to_v3"]) == row["sha256"]
    snapshot = raw_csv(OUTPUT / "provenance/original_package_inventory.csv")
    for row in snapshot:
        assert not row["sha256"] or sha256(PACKAGE / row["file"]) == row["sha256"]
    hash_rows = raw_csv(OUTPUT / "provenance/figure_hashes.csv")
    for row in hash_rows:
        assert sha256(OUTPUT / row["file"]) == row["sha256"], row
    plotted = raw_csv(OUTPUT / "provenance/plotted_values.csv")
    for row in plotted:
        source = raw_csv(OUTPUT / row["source"])[int(row["csv_line"]) - 2]
        assert source[row["field"]] == row["frozen_value"], row
        assert float(source[row["field"]]) == float(row["used_value"]), row
    ledger = raw_csv(OUTPUT / "plot_data/FINAL_FIGURE_VALUE_AUDIT.csv")
    assert all(r["matches_ledger"] == "true" for r in ledger)
    direct = {r["value_id"]: float(r["plotted_value"]) for r in ledger if r["derived"] == "false"}
    id_fields = {"runtime_s": "runtime_value_id", "relative_gap_pct": "gap_value_id",
                 "path_agreement_pct": "path_agreement_value_id", "completion_pct": "completion_value_id",
                 "fully_resolved_pct": "fully_resolved_value_id", "score": "score_value_id"}
    checked_ledger = 0
    for filename in ["exact_reference_final_q1.csv", "bounded_policy_final_q1.csv", "scalability_final_q1.csv",
                     "algorithm_sensitivity_final_q1.csv", "workload_sensitivity_final_q1.csv"]:
        for row in raw_csv(OUTPUT / "plot_data" / filename):
            for field, id_field in id_fields.items():
                value_id = row.get(id_field)
                if value_id in direct and row.get(field):
                    assert float(row[field]) == direct[value_id], (filename, field, value_id)
                    checked_ledger += 1
    scalability = raw_csv(OUTPUT / "plot_data/scalability_final_q1.csv")
    for row in scalability:
        baseline = next(r for r in scalability if r["dataset"] == row["dataset"] and r["method"] == "PACE-B")
        expected = 100 * float(row["full_window_score"]) / float(baseline["full_window_score"])
        assert math.isclose(float(row["relative_utility_pct"]), expected, abs_tol=1e-12, rel_tol=0)
    algorithm = raw_csv(OUTPUT / "plot_data/algorithm_sensitivity_final_q1.csv")
    for parameter in ("L", "K_f"):
        assert [r["setting"] for r in algorithm if r["parameter"] == parameter] == ["1", "2", "4", "8"]
    assert [r["effective_depth"] for r in algorithm if r["parameter"] == "theta"] == ["0", "1", "1", "1"]
    workload = raw_csv(OUTPUT / "plot_data/workload_sensitivity_final_q1.csv")
    density = [r for r in workload if r["parameter"] == "density"]
    assert [r["x_value"] for r in density] == ["5", "40"]
    assert all(r["score"] == "" for r in density)
    errors = raw_csv(OUTPUT / "plot_data/error_bar_provenance.csv")
    assert len(errors) == 10 and all(r["validated"] == "true" for r in errors)
    for filename in ("exact_reference_final_q1.csv", "bounded_policy_final_q1.csv"):
        for row in raw_csv(OUTPUT / "plot_data" / filename):
            match = next(r for r in errors if r["value_id_or_source_reference"].split(";")[0] == row["runtime_value_id"])
            assert float(match["half_iqr"]) == float(row["runtime_half_iqr_s"])
    budgets = raw_csv(OUTPUT / "plot_data/scalability_budget_audit.csv")
    summary = raw_csv(OUTPUT / "plot_data/scalability_budget_summary.csv")
    assert len(budgets) == 600
    assert len({(r["dataset"], r["logical_query_id"]) for r in budgets}) == 600
    assert all(r["validated"] == "true" for r in budgets)
    for row in summary:
        values = [float(r["budget_min"]) for r in budgets if row["dataset"] == "overall" or r["dataset"] == row["dataset"]]
        quartiles = statistics.quantiles(values, n=4, method="inclusive")
        expected = [min(values), quartiles[0], statistics.median(values), quartiles[2], max(values)]
        actual = [float(row[f]) for f in ["min_budget_min", "q1_budget_min", "median_budget_min", "q3_budget_min", "max_budget_min"]]
        assert len(values) == int(row["n_queries"])
        assert all(math.isclose(a, b, rel_tol=0, abs_tol=1e-11) for a, b in zip(actual, expected))
    figures = raw_csv(OUTPUT / "provenance/figure_sources.csv")
    checks, preview_hashes = [], []
    for row in figures:
        pdf = inside(OUTPUT / row["final_pdf"])
        png = inside(OUTPUT / row["final_png"])
        assert sha256(pdf) == row["final_pdf_sha256"] and sha256(png) == row["final_png_sha256"]
        assert sha256(OUTPUT / row["script"]) == row["script_sha256"]
        assert sha256(OUTPUT / row["shared_script"]) == row["shared_script_sha256"]
        assert sha256(OUTPUT / "scripts/build_package.py") == row["builder_sha256"]
        for source in json.loads(row["source_files"]):
            assert sha256(OUTPUT / source["copy_relative_to_v3"]) == source["sha256"]
        render = json.loads(inside(OUTPUT / "review" / f"{row['figure_name']}_render.json").read_text())
        assert render["text_overflows"] == []
        assert 7 <= render["width_inches"] <= 7.2
        fonts = subprocess.run(["pdffonts", str(pdf)], check=True, capture_output=True, text=True).stdout
        font_lines = fonts.splitlines()[2:]
        assert font_lines and all("yes" in line for line in font_lines), fonts
        assert "Type 3" not in fonts, fonts
        images = subprocess.run(["pdfimages", "-list", str(pdf)], check=True, capture_output=True, text=True).stdout
        assert len(images.strip().splitlines()) == 2, images
        extracted = subprocess.run(["pdftotext", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
        assert len(extracted.strip()) > 50, "PDF text is not extractable."
        write_path(OUTPUT / "review/pdf_text" / f"{row['figure_name']}.txt").write_text(extracted)
        write_path(OUTPUT / "review/font_reports" / f"{row['figure_name']}.txt").write_text(fonts)
        with Image.open(png) as im:
            assert min(im.info.get("dpi", (0, 0))) >= 599
            dims = f"{im.width} × {im.height}"
        if args.render_previews:
            for directory, extra in [("pdf_previews", []), ("grayscale", ["-gray"])]:
                prefix = write_path(OUTPUT / "review" / directory / row["figure_name"])
                subprocess.run(["pdftoppm", "-singlefile", "-png", "-r", "180", *extra, str(pdf), str(prefix)], check=True)
        for directory in ("pdf_previews", "grayscale"):
            path = inside(OUTPUT / "review" / directory / f"{row['figure_name']}.png")
            assert path.is_file()
            preview_hashes.append({"file": str(path.relative_to(OUTPUT)), "sha256": sha256(path),
                                   "source_pdf_sha256": sha256(pdf)})
        checks.append({"figure": row["figure_name"], "values_match_frozen_input": "PASS",
                       "embedded_vector_fonts": "PASS", "raster_images_in_pdf": 0,
                       "text_within_page": "PASS", "minimum_font_size_pt": min(t["font_size_pt"] for t in render["text_items"]),
                       "png_pixels": dims, "png_dpi": 600})
    write_csv(OUTPUT / "review/technical_validation.csv", checks, list(checks[0]))
    write_csv(OUTPUT / "provenance/preview_hashes.csv", preview_hashes, list(preview_hashes[0]))
    result = {"status": "PASS", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "figures": len(figures), "byte_identical_input_copies": len(copies),
              "original_files_unchanged": len(snapshot), "source_value_reads_checked": len(plotted),
              "direct_value_ledger_checks": checked_ledger, "budget_queries_checked": len(budgets),
              "figure_hash_manifest_entries_checked": len(hash_rows),
              "limitations": ["Visual inspection is recorded separately in FIGURE_REVISION_REPORT.md.",
                              "Operational completion/coverage/score definitions cannot be resolved from the permitted package."]}
    write_json(OUTPUT / "review/validation_results.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
