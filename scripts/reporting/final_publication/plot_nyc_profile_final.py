#!/usr/bin/env python3
"""Render the representative NYC temporal profile example."""

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
    rows = read_csv(root / "plot_data/nyc_profile_final.csv")
    rows.sort(key=lambda r: (int(r["start"]), int(r["end"])))
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.15, 2.9), constrained_layout=True)
    scores = [float(r["average_score"]) for r in rows]
    ax.step(x, scores, where="mid", color="#1769aa", linewidth=1.8, label="PACE-B cell score")
    ax.scatter(x, scores, color="#1769aa", s=18, zorder=3)
    for xx, r in zip(x, rows):
        ax.axvline(xx - 0.5, color="#cccccc", linewidth=0.45, zorder=0)
        ax.text(xx, scores[xx] + 1.8, r["path_rank"], ha="center", va="bottom", fontsize=6.2, color="#b42318")
    ax.set_xticks(x, [f"{r['start']}–{r['end']}" for r in rows], rotation=55, ha="right")
    ax.set_xlabel("Measured departure interval (minutes); red labels = stable path rank")
    ax.set_ylabel("Average selected score")
    ax.set_title("NYC-Q012-MORNING-R20: 8 serialized intervals, 5 distinct winning paths (summary count: 12)")
    ax.set_ylim(0, max(scores) * 1.22)
    ax.text(0.01, 0.97, "30 s diagnostic cap; complete profile", transform=ax.transAxes, ha="left", va="top", fontsize=7, bbox={"facecolor": "white", "edgecolor": "#bbbbbb", "pad": 2})
    save(fig, root, "nyc_profile_final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
