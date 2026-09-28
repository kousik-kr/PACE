#!/usr/bin/env python3
"""Render Figure B: the bounded-policy transition."""

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
    rows = read_csv(root / "plot_data/bounded_policy_final.csv")
    rows = [r for r in rows if r["included_in_main_figure"] == "true"]
    labels = [r["display_stage"] for r in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.75), constrained_layout=True)
    gap = [float(r["relative_gap_pct"]) for r in rows]
    agree = [float(r["path_agreement_pct"]) for r in rows]
    bars = axes[0].bar(x, gap, color=["#777777", "#777777", "#b42318", "#b42318"], width=0.62)
    axes[0].set_title("(a) Quality transition")
    axes[0].set_ylabel("Relative score gap (%)")
    axes[0].set_xticks(x, labels, rotation=22, ha="right")
    axes[0].set_ylim(0, max(gap) * 1.28 if max(gap) else 1)
    for bar, value in zip(bars, gap):
        axes[0].text(bar.get_x() + bar.get_width() / 2, value, f"{value:.1f}", ha="center", va="bottom", fontsize=7)
    axes[1].plot(x, agree, marker="o", color="#b42318", linewidth=1.6, markersize=4)
    axes[1].set_title("(b) Agreement and runtime")
    axes[1].set_ylabel("Path agreement (%)")
    axes[1].set_xticks(x, labels, rotation=22, ha="right")
    axes[1].set_ylim(-5, 105)
    twin = axes[1].twinx()
    runtime = [float(r["runtime_s"]) for r in rows]
    twin.plot(x, runtime, marker="s", color=COLORS["PACE-B"], linewidth=1.3, markersize=3.5, label="Runtime")
    twin.set_ylabel("Median runtime (s)", color=COLORS["PACE-B"])
    twin.tick_params(axis="y", colors=COLORS["PACE-B"])
    twin.spines["right"].set_visible(True)
    twin.spines["right"].set_color(COLORS["PACE-B"])
    fig.suptitle("Controlled NY policy stages; +Mb is retained only in supplement/provenance", fontsize=10)
    save(fig, root, "bounded_policy_final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

