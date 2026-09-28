#!/usr/bin/env python3
"""Render Figure C: bounded large-network execution."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_common import COLORS, read_csv, save, set_style


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = ap.parse_args().root
    set_style()
    rows = read_csv(root / "plot_data/scalability_final.csv")
    datasets = ["NY", "FLA", "CAL"]
    methods = ["PACE-B", "iSCOPE-Profile"]
    x = np.arange(len(datasets))
    width = 0.34
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.75), constrained_layout=True)
    for j, method in enumerate(methods):
        rs = [next(r for r in rows if r["dataset"] == d and r["method"] == method) for d in datasets]
        offset = (j - 0.5) * width
        vals_runtime = [float(r["median_runtime_s"]) for r in rs]
        vals_resolved = [float(r["fully_resolved_queries_pct"]) for r in rs]
        label = "PACE-B (24 workers)" if method == "PACE-B" else "iSCOPE-Profile (1 worker; 5 s cap)"
        color = COLORS[method]
        axes[0].bar(x + offset, vals_runtime, width, color=color, edgecolor="black", linewidth=0.35, hatch="//" if method != "PACE-B" else "", label=label)
        axes[1].bar(x + offset, vals_resolved, width, color=color, edgecolor="black", linewidth=0.35, hatch="//" if method != "PACE-B" else "")
        for xx, value in zip(x + offset, vals_runtime):
            axes[0].text(xx, value + 0.07, f"{value:.2f}", ha="center", va="bottom", fontsize=6.8, rotation=90 if value > 3.5 else 0)
        for xx, value in zip(x + offset, vals_resolved):
            axes[1].text(xx, value + 2, f"{value:.1f}", ha="center", va="bottom", fontsize=6.8)
    axes[0].set_title("(a) Median query runtime")
    axes[0].set_ylabel("Seconds")
    axes[0].set_xticks(x, datasets)
    axes[0].set_ylim(0, 5.3)
    axes[0].legend(frameon=False, loc="upper left", fontsize=6.6)
    axes[1].set_title("(b) Fully resolved logical queries")
    axes[1].set_ylabel("Queries fully resolved (%)")
    axes[1].set_xticks(x, datasets)
    axes[1].set_ylim(0, 110)
    fig.suptitle("Final W120/RHO030 slice; iSCOPE bars are time-capped anytime outputs", fontsize=10)
    save(fig, root, "scalability_final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

