"""Polish the existing budget distribution; no runtime-bucket measurements exist."""
from pathlib import Path
from common import COLORS, clean, data, number, plt, save, style
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


def main():
    style()
    observations = data("scalability_budget_audit.csv")
    summary = data("scalability_budget_summary.csv")
    fig, ax = plt.subplots(figsize=(7.2, 3.35))
    fig.subplots_adjust(left=.19, right=.975, bottom=.20, top=.78)
    tick_labels = []
    for dataset, yy in [("NY", 2), ("FLA", 1), ("CAL", 0)]:
        row = next(r for r in summary if r["dataset"] == dataset)
        n = number(row, "n_queries")
        values = [number(r, "budget_min") for r in observations if r["dataset"] == dataset]
        assert len(values) == n
        low, q1, med, q3, high = [number(row, field) for field in (
            "min_budget_min", "q1_budget_min", "median_budget_min", "q3_budget_min", "max_budget_min")]
        tick_labels.append(f"{dataset}  (n={n:.0f})")
        ax.scatter(values, [yy] * len(values), color=COLORS["PACE-B"], alpha=.17, s=9, edgecolors="none", zorder=2)
        ax.plot([low, high], [yy, yy], color=COLORS["muted"], lw=1, zorder=3)
        ax.vlines([low, high], yy - .12, yy + .12, color=COLORS["muted"], lw=.9, zorder=3)
        ax.add_patch(Rectangle((q1, yy - .12), q3 - q1, .24,
                               facecolor=COLORS["PACE-B"], edgecolor=COLORS["PACE-B"], alpha=.55, zorder=4))
        ax.plot(med, yy, marker="D", color=COLORS["PACE-B"], markerfacecolor="white", markersize=5.5,
                markeredgewidth=1.25, zorder=5)
        ax.annotate(f"{med:.2f}", (med, yy), xytext=(0, 13), textcoords="offset points", ha="center", fontsize=9.1)
        for val, align in [(low, "left"), (high, "right")]:
            ax.annotate(f"{val:.2f}", (val, yy), xytext=(0, -15), textcoords="offset points",
                        ha=align, fontsize=8.9, color=COLORS["muted"])
    ax.set(xlim=(0, 320), ylim=(-.5, 2.6), xlabel=r"Travel-time budget $B$ (min)")
    ax.set_yticks([2, 1, 0], tick_labels)
    ax.set_xticks([0, 50, 100, 150, 200, 250, 300])
    clean(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [Line2D([], [], color=COLORS["muted"], lw=1, label="Min–max"),
               Rectangle((0, 0), 1, 1, facecolor=COLORS["PACE-B"], alpha=.55, label="IQR"),
               Line2D([], [], linestyle="none", marker="D", color=COLORS["PACE-B"],
                      markerfacecolor="white", label="Median")]
    fig.legend(handles=handles, ncol=3, frameon=False, loc="upper right", bbox_to_anchor=(.985, .98),
               columnspacing=1.3, handlelength=1.7)
    w, rho = number(observations[0], "window_min"), number(observations[0], "rho")
    fig.text(.19, .866, f"$w={w:g}$ min; $\\rho={rho:.2f}$", fontsize=9.7)
    save(fig, "figS1_budget_distribution_v3", Path(__file__))


if __name__ == "__main__":
    main()
