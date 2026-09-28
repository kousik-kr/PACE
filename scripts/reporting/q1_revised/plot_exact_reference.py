"""Two-panel controlled exact-reference analysis; local frozen values only."""
from pathlib import Path
from common import COLORS, MARKERS, clean, data, line, number, panel, plt, save, style


def main():
    style()
    rows = data("exact_reference_final_q1.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.55))
    fig.subplots_adjust(left=.105, right=.975, bottom=.20, top=.81, wspace=.43)
    ax = axes[0]
    for method in ("PACE-X", "PACE-B"):
        subset = sorted((r for r in rows if r["method"] == method), key=lambda r: int(r["budget_B"]))
        x = [number(r, "budget_B") for r in subset]
        y = [number(r, "runtime_s") for r in subset]
        e = [number(r, "runtime_half_iqr_s") for r in subset]
        ax.errorbar(x, y, yerr=e, color=COLORS[method], marker=MARKERS[method],
                    markerfacecolor="white", markeredgewidth=1.25, capsize=2.2,
                    elinewidth=.8, label=method, zorder=3)
        for i, (xx, yy) in enumerate(zip(x, y)):
            offset = ((7 if i == 0 else -6 if i == 2 else 0), (22 if i == 0 else 12) if method == "PACE-X" else -7)
            ha = "left" if i == 0 else "right" if i == 2 else "center"
            ax.annotate(f"{yy:.4f}" if yy < 1 else f"{yy:.3f}", (xx, yy), xytext=offset,
                        textcoords="offset points", ha=ha, va="bottom" if method == "PACE-X" else "top",
                        fontsize=9.1, color=COLORS[method])
    ax.set(yscale="log", ylim=(.007, 55), xlim=(4, 16), xticks=[5, 10, 15],
           xlabel=r"Travel-time budget $B$ (min)", ylabel="Median query runtime (s)")
    ax.set_yticks([.01, .1, 1, 10], ["0.01", "0.1", "1", "10"])
    ax.minorticks_off()
    clean(ax)
    panel(ax, "a", "Runtime")
    gap_rows = sorted((r for r in rows if r["method"] == "PACE-B"), key=lambda r: int(r["budget_B"]))
    ax = axes[1]
    x = [number(r, "budget_B") for r in gap_rows]
    y = [number(r, "relative_gap_pct") for r in gap_rows]
    line(ax, x, y, COLORS["PACE-B"])
    for i, (xx, yy) in enumerate(zip(x, y)):
        ax.annotate(f"{yy:.1f}%", (xx, yy), xytext=((0 if i == 0 else -4 if i == 2 else 0), 18 if i == 0 else 10),
                    textcoords="offset points", ha="right" if i == 2 else "center", va="bottom",
                    fontsize=9.3, color=COLORS["PACE-B"])
    ax.set(xlim=(4, 16), ylim=(0, 90), xticks=[5, 10, 15], yticks=[0, 20, 40, 60, 80],
           xlabel=r"Travel-time budget $B$ (min)", ylabel="Median relative score gap (%)")
    agreements = [number(r, "path_agreement_pct") for r in gap_rows]
    assert len(set(agreements)) == 1
    ax.text(.05, .15, f"Median path agreement: {agreements[0]:.0f}%\nat each budget",
            transform=ax.transAxes, fontsize=9.1, va="center", color=COLORS["muted"])
    clean(ax)
    panel(ax, "b", "Bounded quality gap")
    fig.legend(*axes[0].get_legend_handles_labels(), ncol=2, frameon=False,
               loc="upper center", bbox_to_anchor=(.53, .985), handlelength=2)
    save(fig, "fig03_exact_reference_v3", Path(__file__))


if __name__ == "__main__":
    main()
