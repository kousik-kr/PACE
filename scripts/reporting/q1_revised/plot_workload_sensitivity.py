"""Five measured workload panels; no interpolated density values or score panel."""
from pathlib import Path
from common import COLORS, clean, data, line, number, panel, plt, save, style


def main():
    style()
    rows = data("workload_sensitivity_final_q1.csv")
    fig, axd = plt.subplot_mosaic([["wr", "rr", "dr"], ["ws", "rs", "."]], figsize=(7.2, 4.55))
    fig.subplots_adjust(left=.105, right=.97, bottom=.155, top=.86, wspace=.45, hspace=.98)
    specs = [("wr", "window", "runtime_s", r"Window length $w$ (min)", (80, 400), "a", "Window length"),
             ("rr", "rho", "runtime_s", r"Budget slack $\rho$", (.05, .55), "b", "Budget slack"),
             ("dr", "density", "runtime_s", "Score-bearing-edge\ndensity (%)", (0, 45), "c", "Score density"),
             ("ws", "window", "score", r"Window length $w$ (min)", (80, 400), "d", "Window length"),
             ("rs", "rho", "score", r"Budget slack $\rho$", (.05, .55), "e", "Budget slack")]
    for key, parameter, field, xlabel, limits, letter, title in specs:
        subset = sorted([r for r in rows if r["parameter"] == parameter], key=lambda r: float(r["x_value"]))
        x = [number(r, "x_value") for r in subset]
        y = [number(r, field) for r in subset]
        ax = axd[key]
        runtime = field == "runtime_s"
        color = COLORS["PACE-B"] if runtime else COLORS["iSCOPE-Profile"]
        if parameter == "density":
            ax.plot(x, y, linestyle="none", marker="o", markersize=5.5,
                    color=color, markerfacecolor="white", markeredgewidth=1.25, zorder=3)
            ax.text(.05, .92, "Comparable measured\nsettings only", transform=ax.transAxes,
                    fontsize=9.1, va="top", color=COLORS["muted"])
        else:
            line(ax, x, y, color, marker="o" if runtime else "s")
        for i, (xx, yy) in enumerate(zip(x, y)):
            ax.annotate(f"{yy:.2f}" if runtime else f"{yy:.1f}", (xx, yy), xytext=(0, -15 if parameter == "density" else 9),
                        textcoords="offset points", ha="center", fontsize=8.9, color=color)
        ax.set(xlim=limits, ylim=(0, 4.5) if runtime else (0, 460), xlabel=xlabel)
        ax.set_xticks(x, [f"{xx:.2f}" if parameter == "rho" else f"{xx:g}" for xx in x])
        ax.set_yticks([0, 2, 4] if runtime else [0, 200, 400])
        ax.set_ylabel("Median runtime (s)" if runtime else "Reported score")
        clean(ax)
        panel(ax, letter, title)
    save(fig, "fig07_workload_sensitivity_v3", Path(__file__))


if __name__ == "__main__":
    main()
