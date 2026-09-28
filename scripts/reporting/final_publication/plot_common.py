#!/usr/bin/env python3
"""Shared deterministic plotting style for the final PACE figures."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


COLORS = {
    "PACE-X": "#333333",
    "PACE-B": "#1769aa",
    "iSCOPE-Profile": "#d97706",
    "PACE-B (fast-connector)": "#4c78a8",
}


def set_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.titlesize": 9.5,
        "axes.labelsize": 8.5,
        "legend.fontsize": 7.5,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
    })


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save(fig: Any, root: Path, stem: str) -> None:
    fig.savefig(root / "figures" / f"{stem}.png", dpi=300, metadata={"CreationDate": None})
    fig.savefig(root / "figures" / f"{stem}.pdf", metadata={"CreationDate": None})
    plt.close(fig)

