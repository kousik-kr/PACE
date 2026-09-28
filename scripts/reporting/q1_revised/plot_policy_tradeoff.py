"""Successive bounded-policy runtime-quality trade-off, without point jitter."""
from pathlib import Path
from common import COLORS, clean, data, number, plt, save, style


def main():
    style()
    rows = sorted(data("bounded_policy_final_q1.csv"), key=lambda r: int(r["stage_index"]))
    x = [number(r, "runtime_s") for r in rows]
    y = [number(r, "relative_gap_pct") for r in rows]
    agreement = [number(r, "path_agreement_pct") for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    fig.subplots_adjust(left=.115, right=.975, bottom=.15, top=.84)
    ax.plot(x, y, color=COLORS["PACE-B"], linewidth=1.5, zorder=2)
    # Direction arrows convey cumulative introduction, including motion leftward.
    for i in (0, 1):
        start = (x[i] * .56 + x[i + 1] * .44, y[i] * .56 + y[i + 1] * .44)
        end = (x[i] * .44 + x[i + 1] * .56, y[i] * .44 + y[i + 1] * .56)
        ax.annotate("", xy=end, xytext=start,
                    arrowprops={"arrowstyle": "-|>", "color": COLORS["PACE-B"], "lw": 1.4})
    for xx, yy, marker in zip(x, y, ["s", "D", "^", "o"]):
        ax.plot(xx, yy, marker=marker, markersize=5.2, markeredgewidth=1.25,
                markerfacecolor="white", color=COLORS["PACE-B"], linestyle="none", zorder=4)
    positions = [(.073, 11), (.052, 11), (.044, 38), (.022, 52)]
    labels = ["1  Depth cap", "2  Top-$L$", "3  Single connector", r"4  $K_f$ retention"]
    for i, (label, location) in enumerate(zip(labels, positions)):
        ax.annotate(f"{label}\nMedian agreement {agreement[i]:.0f}%", xy=(x[i], y[i]), xytext=location,
                    ha="left" if i >= 2 else "center", va="center", fontsize=9.7,
                    linespacing=1.55, bbox={"facecolor": "white", "edgecolor": "none", "pad": 2},
                    arrowprops={"arrowstyle": "-", "color": COLORS["muted"], "lw": .75,
                                "shrinkA": 4, "shrinkB": 5})
    ax.text(.053, 25, "First observed median\nquality loss at stage 3", fontsize=9.2,
            color=COLORS["muted"], linespacing=1.35)
    ax.set(xlim=(.018, .083), ylim=(-4, 58), xticks=[.02, .03, .04, .05, .06, .07, .08],
           yticks=[0, 10, 20, 30, 40, 50], xlabel="Median query runtime (s)",
           ylabel="Median relative score gap (%)")
    clean(ax)
    ax.set_title("Successive bounded-policy trade-off", loc="left", pad=15, fontsize=11,
                 fontweight="semibold")
    save(fig, "fig04_successive_policy_tradeoff_v3", Path(__file__))


if __name__ == "__main__":
    main()
