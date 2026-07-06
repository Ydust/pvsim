"""深挖机理图墙 — 三张"挖到底"的机理/风险图拼一页, 作为主图 Fig3/Fig4 的 SI 支撑.

运行: python -m scripts.make_digs_wall
输出: outputs/figures/_OVERVIEW_deep_digs.png
"""

import os
import sys
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from pvsim import viz

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FIGDIR = "outputs/figures"
DIGS = [
    ("MainFig3x_temporal_fingerprint.png", "Dig 1 · supports Fig 3 (mechanism independence)",
     "Two mechanisms, two temporal fingerprints: temperature is seasonal\n"
     "(summer-only), spectral persists year-round -> they are decoupled in time"),
    ("MainFig3y_tandem_decomposition.png", "Dig 2 · supports Fig 2/5 (tandem = area play)",
     "Against modern silicon the tandem has ~no per-kWp edge (0.9%) and no spectral\n"
     "component (full-spectrum) -> its value is area (rooftop), not utility yield"),
    ("MainFig4x_degradation_risk.png", "Dig 3 · supports Fig 4 (lifetime gate)",
     "The geography of lifetime risk (vs modern c-Si): SW absorbs ~1.1%/yr degradation,\n"
     "policy-favoured NW only ~0.9%/yr -> the NW is the most fragile to lifetime shortfall"),
    ("MainFig4y_substitution_timing_geo.png", "Dig 4 · supports Fig 4 (timing)",
     "Substitution timing geography is conditional: advantage orders the crossover (r=-0.95)\n"
     "but the SW leads the NW by only ~2 yr under central cost (widens near parity)"),
]


def main():
    viz.setup_en()
    fig = plt.figure(figsize=(15, 18))
    gs = fig.add_gridspec(4, 1, hspace=0.22)
    for i, (fname, tag, cap) in enumerate(DIGS):
        ax = fig.add_subplot(gs[i, 0])
        path = os.path.join(FIGDIR, fname)
        if os.path.exists(path):
            ax.imshow(mpimg.imread(path))
        else:
            ax.text(0.5, 0.5, f"missing\n{fname}", ha="center", color="red", fontsize=14)
        ax.set_title(f"{tag}\n{cap}", fontsize=11, fontweight="bold", loc="left",
                     pad=5, color="#5a2d82")
        ax.axis("off")
    fig.suptitle("Deep digs — three mechanistic results that earn the machine "
                 "(SI cluster behind Fig 3 & Fig 4)\n"
                 "each dig tested a hypothesis; one was refuted (tandem), all reported honestly",
                 fontsize=14, fontweight="bold", y=0.997)
    fig.savefig(os.path.join(FIGDIR, "_OVERVIEW_deep_digs.png"), dpi=110,
                bbox_inches="tight")
    plt.close(fig)
    print("已保存: outputs/figures/_OVERVIEW_deep_digs.png")


if __name__ == "__main__":
    main()
