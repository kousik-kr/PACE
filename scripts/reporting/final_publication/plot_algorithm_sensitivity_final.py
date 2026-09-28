#!/usr/bin/env python3
"""Render Figure D: parameter sensitivity with effective theta depth."""

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
    rows = read_csv(root / "plot_data/algorithm_sensitivity_final.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.75), constrained_layout=True)
    panels = [("L", "Top-L pivots", "Top-L pivot limit"), ("theta", "Effective pivot depth", "Requested theta; theta_eff annotation"), ("Kf", "Retained states", "K_f")]
    for ax, (axis, title, xlabel) in zip(axes, panels):
        rs = [r for r in rows if r["axis"] == axis]
        rs.sort(key=lambda r: float(r["value"]))
        x = np.arange(len(rs))
        runtime = [float(r["runtime_s"]) for r in rs]
        completion = [float(r["completion_pct"]) for r in rs]
        ax.plot(x, runtime, marker="o", color="#1769aa", linewidth=1.45, markersize=3.8, label="Runtime")
        ax.set_ylabel("Median runtime (s)" if axis == "L" else "Runtime (s)")
        ax.set_xticks(x, [r["value_display"] for r in rs])
        ax.set_xlabel(xlabel)
        ax.set_title(title)
        ax2 = ax.twinx()
        ax2.plot(x, completion, marker="s", color="#b42318", linestyle="--", linewidth=1.1, markersize=3, label="Fully completed")
        ax2.set_ylim(0, 110)
        ax2.set_ylabel("Completed queries (%)", color="#b42318")
        ax2.tick_params(axis="y", colors="#b42318")
        ax2.spines["right"].set_visible(True)
        ax2.spines["right"].set_color("#b42318")
        if axis == "theta":
            ax.text(0.98, 0.93, "theta=1,2,3\nall theta_eff=1\n(L=1)", transform=ax.transAxes, ha="right", va="top", fontsize=6.8, bbox={"facecolor": "white", "edgecolor": "#bbbbbb", "pad": 2.0})
    axes[0].legend(frameon=False, loc="upper left", fontsize=6.5)
    fig.suptitle("Measured parameter sensitivity; source configurations and caveats are audited", fontsize=10)
    save(fig, root, "algorithm_sensitivity_final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

