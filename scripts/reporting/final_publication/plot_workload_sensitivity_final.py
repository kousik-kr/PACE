#!/usr/bin/env python3
"""Render Figure E: workload sensitivity from measured points only."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_common import read_csv, save, set_style


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = ap.parse_args().root
    set_style()
    rows = read_csv(root / "plot_data/workload_sensitivity_final.csv")
    fig, axes = plt.subplots(2, 3, figsize=(7.15, 4.65), constrained_layout=True)
    specs = [
        ("window", "Departure window (min)", "rho", "Window"),
        ("rho", "Budget slack rho", "window_minutes", "Slack"),
        ("density", "Score-bearing-edge density", "density_label", "Density"),
    ]
    for col, (kind, xlabel, group_field, title) in enumerate(specs):
        rs = [r for r in rows if r["sensitivity"] == kind]
        groups = sorted({r[group_field] for r in rs}, key=float if kind != "density" else str)
        ax = axes[0, col]
        score_ax = axes[1, col]
        if kind == "density":
            # Density has only two measured x values, with no second grouping
            # dimension.  Plot both points on their actual shared x-axis so
            # the 5% and 40% labels remain explicit.
            gr = sorted(rs, key=lambda r: float(r["x_value"]))
            x = np.arange(len(gr))
            ax.plot(x, [float(r["runtime_s"]) for r in gr], marker="o", linewidth=1.25, markersize=3, label="measured density")
            score_ax.plot(x, [float(r["score"]) for r in gr], marker="o", linewidth=1.25, markersize=3, label="measured density")
            tick_labels = [r["x_label"] for r in gr]
        else:
            for group in groups:
                gr = [r for r in rs if r[group_field] == group]
                gr.sort(key=lambda r: float(r["x_value"]))
                x = np.arange(len(gr))
                label = f"{group_field}={group}"
                ax.plot(x, [float(r["runtime_s"]) for r in gr], marker="o", linewidth=1.25, markersize=3, label=label)
                score_ax.plot(x, [float(r["score"]) for r in gr], marker="o", linewidth=1.25, markersize=3, label=label)
            # Each column uses the natural sorted x values; groups share the same axis in the two measured grids.
            first = [r for r in rs if r[group_field] == groups[0]]
            first.sort(key=lambda r: float(r["x_value"]))
            tick_labels = [r["x_label"] for r in first]
            x = np.arange(len(first))
        ax.set_xticks(x, tick_labels)
        score_ax.set_xticks(x, tick_labels)
        ax.set_title(f"({chr(97 + col)}) {title}")
        ax.set_xlabel(xlabel)
        score_ax.set_xlabel(xlabel)
        ax.set_ylabel("Runtime (s)")
        score_ax.set_ylabel("Full-window score")
        if col == 0:
            ax.legend(frameon=False, fontsize=6.2, loc="upper left")
            score_ax.legend(frameon=False, fontsize=6.2, loc="upper left")
        ax.set_ylim(bottom=0)
        score_ax.set_ylim(bottom=0)
    axes[0, 2].text(0.04, 0.92, "Only 5% and 40%\nmeasured; 20% omitted", transform=axes[0, 2].transAxes, fontsize=6.7, va="top", bbox={"facecolor": "white", "edgecolor": "#bbbbbb", "pad": 2})
    fig.suptitle("Measured workload sensitivity; non-monotonic behavior is retained", fontsize=10)
    save(fig, root, "workload_sensitivity_final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
