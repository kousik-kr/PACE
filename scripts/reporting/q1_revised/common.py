"""Local-only data access, publication style, and verifiable render records."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1]
PACKAGE = OUTPUT.parent


def inside(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(PACKAGE):
        raise ValueError(f"Path is outside the permitted figure package: {path}")
    return resolved


def write_path(path: Path) -> Path:
    path = inside(path)
    if not path.is_relative_to(OUTPUT):
        raise ValueError(f"Outputs must remain in revised_figures_v3: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# Keep plotting caches inside the permitted output folder as well.
os.environ["MPLCONFIGDIR"] = str(write_path(OUTPUT / "review/.cache/matplotlib/config").parent)
os.environ["XDG_CACHE_HOME"] = str(write_path(OUTPUT / "review/.cache/config").parent)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text

COLORS = {"PACE-X": "#306E9A", "PACE-B": "#237C69", "iSCOPE-Profile": "#B96532",
          "ink": "#30353B", "muted": "#59616B", "grid": "#DCE0E3", "shade": "#F0F2F3"}
MARKERS = {"PACE-X": "s", "PACE-B": "o", "iSCOPE-Profile": "^"}
READS: list[dict] = []


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with inside(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def raw_csv(path: Path) -> list[dict]:
    with inside(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def data(name: str) -> list[dict]:
    path = inside(OUTPUT / "plot_data" / name)
    rows = raw_csv(path)
    for line, row in enumerate(rows, 2):
        row["__source"] = str(path.relative_to(OUTPUT))
        row["__line"] = line
    return rows


def number(row: dict, field: str) -> float:
    result = float(row[field])
    record = {"source": row["__source"], "csv_line": row["__line"],
              "field": field, "frozen_value": row[field], "used_value": result}
    if record not in READS:
        READS.append(record)
    return result


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with write_path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value) -> None:
    write_path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def style() -> None:
    READS.clear()
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.labelsize": 10.2, "axes.titlesize": 10.5,
        "xtick.labelsize": 9.2, "ytick.labelsize": 9.2, "legend.fontsize": 9.4,
        "text.color": COLORS["ink"], "axes.labelcolor": COLORS["ink"],
        "xtick.color": COLORS["ink"], "ytick.color": COLORS["ink"],
        "axes.edgecolor": COLORS["ink"], "axes.linewidth": .7,
        "lines.linewidth": 1.5, "lines.markersize": 5.5,
        "pdf.fonttype": 42, "ps.fonttype": 42, "mathtext.fontset": "dejavusans",
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "axes.axisbelow": True,
    })


def clean(ax, grid="y") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=3, width=.7, pad=4)
    if grid:
        ax.grid(axis=grid, color=COLORS["grid"], linewidth=.6)


def panel(ax, label: str, title="") -> None:
    ax.set_title(f"({label})" + (f"  {title}" if title else ""), loc="left", pad=11,
                 fontweight="semibold")


def line(ax, x, y, color, marker="o", **kwargs):
    return ax.plot(x, y, color=color, marker=marker, markerfacecolor="white",
                   markeredgewidth=1.25, markersize=5.5, linewidth=1.5, zorder=3, **kwargs)


def save(fig, stem: str, script: Path) -> None:
    # Fixed page size, without tight cropping that could hide overflowing text.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    page = fig.bbox
    text_items, overflows = [], []
    for item in fig.findobj(match=Text):
        if not item.get_visible() or not item.get_text().strip():
            continue
        box = item.get_window_extent(renderer)
        if box.width == 0 or box.height == 0:
            continue
        record = {"text": item.get_text(), "font_size_pt": item.get_fontsize(),
                  "bbox_px": list(box.extents)}
        text_items.append(record)
        if box.x0 < page.x0 - 1 or box.y0 < page.y0 - 1 or box.x1 > page.x1 + 1 or box.y1 > page.y1 + 1:
            overflows.append(record)
    if overflows:
        raise RuntimeError(f"{stem}: text extends beyond the page: {overflows}")
    pdf = write_path(OUTPUT / "figures" / f"{stem}.pdf")
    png = write_path(OUTPUT / "previews" / f"{stem}.png")
    fig.savefig(pdf, metadata={"Creator": "PACE frozen figure revision v3", "CreationDate": None, "ModDate": None})
    fig.savefig(png, dpi=600, metadata={"Software": "PACE frozen figure revision v3"})
    write_json(OUTPUT / "review" / f"{stem}_render.json", {
        "figure": stem, "script": str(inside(script).relative_to(OUTPUT)),
        "width_inches": fig.get_figwidth(), "height_inches": fig.get_figheight(),
        "png_dpi": 600, "text_overflows": overflows, "text_items": text_items,
        "used_values": list(READS),
    })
    plt.close(fig)
