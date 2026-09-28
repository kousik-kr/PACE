"""Large-network aggregate comparison; preserve local metric semantics."""
from pathlib import Path
from common import COLORS, MARKERS, clean, data, number, panel, plt, save, style
from matplotlib.lines import Line2D


def main():
    style()
    rows = data("scalability_final_q1.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.65))
    fig.subplots_adjust(left=.085, right=.975, bottom=.21, top=.785, wspace=.27)
    specs = [("runtime_s", "Median query\nruntime (s)", (0, 5.5), "Runtime"),
             ("fully_resolved_pct", "Fully resolved\nqueries (%)", (0, 110), "Reported resolution"),
             ("relative_utility_pct", "Median full-window score\n(% of PACE-B)", (0, 110), "Reported score")]
    for col, (field, label, limits, title) in enumerate(specs):
        ax = axes[col]
        for dataset, yy in [("NY", 2), ("FLA", 1), ("CAL", 0)]:
            methods = {r["method"]: r for r in rows if r["dataset"] == dataset}
            a, b = [number(methods[m], field) for m in ("PACE-B", "iSCOPE-Profile")]
            ax.plot([a, b], [yy, yy], color="#9CA3A8", lw=.9, zorder=1)
            for method, value, dy in [("PACE-B", a, 10), ("iSCOPE-Profile", b, -13)]:
                ax.plot(value, yy, marker=MARKERS[method], markersize=5.5, linestyle="none",
                        markerfacecolor="white", markeredgewidth=1.3, color=COLORS[method], zorder=3)
                annotation = f"{value:.3f}" if col == 0 else f"{value:g}%" if value == 100 else f"{value:.1f}%"
                ax.annotate(annotation, (value, yy), xytext=(0, dy), textcoords="offset points",
                            ha="right" if value >= limits[1] * .8 else "center", va="center",
                            fontsize=9.1, color=COLORS[method])
        ax.set(xlim=limits, ylim=(-.55, 2.55), xlabel=label)
        ax.set_yticks([2, 1, 0], ["NY", "FLA", "CAL"] if col == 0 else ["", "", ""])
        if col:
            ax.set_xticks([0, 50, 100])
            ax.tick_params(axis="y", length=0)
            ax.axvline(100, color="#A6ADB3", lw=.6, zorder=0)
        else:
            ax.set_xticks([0, 1, 2, 3, 4, 5])
            deadline = number(rows[0], "deadline_s")
            ax.axvline(deadline, ls=(0, (3, 3)), color=COLORS["muted"], lw=.85, zorder=0)
            ax.text(deadline, 2.49, f"iSCOPE-Profile {deadline:g}-s cutoff", ha="right", va="bottom",
                    fontsize=8.8, color=COLORS["muted"])
        clean(ax, None)
        panel(ax, chr(97 + col), title)
    handles = [Line2D([], [], linestyle="none", marker=MARKERS[m], color=COLORS[m],
                      markerfacecolor="white", markeredgewidth=1.3,
                      label=m if m == "PACE-B" else "iSCOPE-Profile (5-s capped)")
               for m in ("PACE-B", "iSCOPE-Profile")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.53, .985),
               ncol=2, frameon=False, handlelength=1.1, columnspacing=1.8)
    save(fig, "fig05_large_network_comparison_v3", Path(__file__))


if __name__ == "__main__":
    main()
