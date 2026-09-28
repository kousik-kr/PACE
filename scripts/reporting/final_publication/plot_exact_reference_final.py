#!/usr/bin/env python3
"""Render Figure A: controlled exact-reference cost and quality behavior."""

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
    rows = read_csv(root / "plot_data/exact_reference_final.csv")
    budgets = sorted({float(r["budget_min"]) for r in rows})
    x = np.arange(len(budgets))
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.75), constrained_layout=True)

    for method in ("PACE-X", "PACE-B"):
        vals = [float(next(r for r in rows if float(r["budget_min"]) == b and r["method"] == method)["runtime_s"]) for b in budgets]
        axes[0].plot(x, vals, marker="o", linewidth=1.6, markersize=4.2, label=method, color=COLORS[method])
    axes[0].set_xticks(x, [f"{int(b)}" for b in budgets])
    axes[0].set_xlabel("Controlled budget B (min)")
    axes[0].set_ylabel("Median runtime (s)")
    axes[0].set_title("(a) Exact-reference cost")
    axes[0].legend(frameon=False, loc="upper left")

    gap = [float(next(r for r in rows if float(r["budget_min"]) == b and r["method"] == "PACE-B")["relative_gap_pct"]) for b in budgets]
    agree = [float(next(r for r in rows if float(r["budget_min"]) == b and r["method"] == "PACE-B")["path_agreement_pct"]) for b in budgets]
    bars = axes[1].bar(x, gap, color=COLORS["PACE-B"], alpha=0.88, width=0.56, label="Relative score gap")
    axes[1].set_xticks(x, [f"{int(b)}" for b in budgets])
    axes[1].set_xlabel("Controlled budget B (min)")
    axes[1].set_ylabel("PACE-B relative score gap (%)")
    axes[1].set_title("(b) Quality versus PACE-X")
    axes[1].set_ylim(0, max(gap) * 1.28)
    for bar, value in zip(bars, gap):
        axes[1].text(bar.get_x() + bar.get_width() / 2, value, f"{value:.1f}", ha="center", va="bottom", fontsize=7)
    twin = axes[1].twinx()
    twin.plot(x, agree, color="#b42318", marker="s", linewidth=1.3, markersize=3.5, label="Path agreement")
    twin.set_ylim(0, 105)
    twin.set_ylabel("Path agreement (%)", color="#b42318")
    twin.tick_params(axis="y", colors="#b42318")
    twin.spines["right"].set_visible(True)
    twin.spines["right"].set_color("#b42318")
    fig.suptitle("Controlled NY induced-subset reference; not a full-NY certification", fontsize=10)
    save(fig, root, "exact_reference_final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

