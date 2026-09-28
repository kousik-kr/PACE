"""Preserve every measured L/Kf/theta point and show effective depth separately."""
from pathlib import Path
from common import COLORS, clean, data, line, number, panel, plt, save, style
from matplotlib.transforms import blended_transform_factory


def main():
    style()
    rows = data("algorithm_sensitivity_final_q1.csv")
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.8))
    fig.subplots_adjust(left=.105, right=.98, bottom=.295, top=.85, wspace=.31, hspace=.55)
    specs = [("L", r"Selected pivots $L$"), ("K_f", r"Retained states $K_f$"),
             ("theta", r"Nominal pivot depth $\theta$")]
    for col, (parameter, heading) in enumerate(specs):
        subset = sorted([r for r in rows if r["parameter"] == parameter], key=lambda r: float(r["setting"]))
        x = [number(r, "setting") for r in subset]
        runtimes = [number(r, "runtime_s") for r in subset]
        completion = [number(r, "completion_pct") for r in subset]
        default = number(next(r for r in subset if r["canonical_default"] == "true"), "setting")
        top, bottom = axes[:, col]
        position = top.get_position()
        fig.text((position.x0 + position.x1) / 2, .94, heading, ha="center", fontsize=10.5, fontweight="semibold")
        for ax in (top, bottom):
            ax.axvline(default, linestyle=(0, (3, 3)), color=COLORS["muted"], lw=.8)
            ax.set_xticks(x, [r["setting_label"] for r in subset])
            ax.set_xlim((-.35, 3.35) if parameter == "theta" else (.45, 8.65))
            clean(ax)
        line(top, x, runtimes, COLORS["PACE-B"])
        line(bottom, x, completion, COLORS["iSCOPE-Profile"], marker="s")
        top.set(ylim=(0, 2.3), yticks=[0, 1, 2])
        bottom.set(ylim=(0, 113), yticks=[0, 50, 100], xlabel=heading)
        bottom.xaxis.labelpad = 8
        if col == 0:
            top.set_ylabel("Completed-query\nmedian runtime (s)")
            bottom.set_ylabel("Reported\ncompletion (%)")
        panel(top, chr(97 + col))
        panel(bottom, chr(100 + col))
        if parameter == "theta":
            for ax in (top, bottom):
                ax.axvspan(1, 3.35, color=COLORS["shade"], zorder=0)
            top.text(2, 1.7, "Effective depth = 1\nSource uses $L=1$", ha="center", va="center",
                     fontsize=9.1, linespacing=1.6, color=COLORS["muted"])
            depths = [number(r, "effective_depth") for r in subset]
            transform = blended_transform_factory(bottom.transData, fig.transFigure)
            bottom.text(-.20, .151, r"$\theta_{\mathrm{eff}}$:", transform=transform, ha="right",
                        va="center", fontsize=9.7, clip_on=False)
            for xx, depth in zip(x, depths):
                bottom.text(xx, .151, f"{depth:g}", transform=transform, ha="center",
                            va="center", fontsize=9.7, clip_on=False)
            selected = [0]
        else:
            selected = [x.index(default), len(x) - 1]
        for i in selected:
            bottom.annotate(f"{completion[i]:g}%", (x[i], completion[i]),
                            xytext=(8, -3) if parameter == "theta" else (0, -17),
                            textcoords="offset points", ha="left" if parameter == "theta" else "center",
                            va="center" if parameter == "theta" else "baseline", fontsize=9,
                            color=COLORS["iSCOPE-Profile"])
    save(fig, "fig06_algorithm_sensitivity_v3", Path(__file__))


if __name__ == "__main__":
    main()
