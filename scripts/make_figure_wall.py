"""主图总览缩略图墙 — NEWFig1-5 (空间→机制→分段→时机→部署) + 主线框.

运行: python -m scripts.make_figure_wall
输出: outputs/figures/_OVERVIEW_main_figures.png
"""

import os
import sys
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from pvsim import viz

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FIGDIR = "outputs/figures"

# NEWFig1-5 主图 (从物理优势到部署决策)
MAIN_FIGS = [
    ("NEWFig1_inversion.png", "Fig 1 · Geographic inversion",
     "Perovskite gains most where sunlight is weakest\n0.1deg grid, r=-0.51, Southwest > Northwest"),
    ("NEWFig2_mechanisms.png", "Fig 2 · Mechanisms",
     "Two independent drivers: temperature r=+0.98\nand spectral/air-mass r=-0.85"),
    ("NEWFig3_segmentation.png", "Fig 3 · Market ruler",
     "Efficiency is not field energy: per-kWp vs per-m2\nflips the technology ranking"),
    ("NEWFig4_economics_timing.png", "Fig 4 · Lifetime gate",
     "Capex/lifetime/degradation dominate;\nscenario crossover P10/P50/P90 = 2030/2032/2039"),
    ("NEWFig5_deployment.png", "Fig 5 · Deployment mismatch",
     "Land-based utility decision plane: advantage x land penalty;\ntop advantage third holds only 24%"),
]


def _place(fig, slot, item):
    fname, tag, caption = item
    ax = fig.add_subplot(slot)
    path = os.path.join(FIGDIR, fname)
    if os.path.exists(path):
        ax.imshow(mpimg.imread(path))
    else:
        ax.text(0.5, 0.5, f"missing\n{fname}", ha="center", va="center",
                fontsize=14, color="red")
    ax.set_title(f"{tag}  —  {caption}", fontsize=12, fontweight="bold",
                 loc="left", pad=5, color="#b8360f")
    ax.axis("off")


def main():
    viz.setup_en()
    fig = plt.figure(figsize=(17, 19))
    gs = fig.add_gridspec(3, 2, hspace=0.16, wspace=0.06)

    _place(fig, gs[0, 0], MAIN_FIGS[0])   # Fig 1 foundation
    _place(fig, gs[0, 1], MAIN_FIGS[1])   # Fig 2 segmentation
    _place(fig, gs[1, 0], MAIN_FIGS[2])   # Fig 3 space (headline)
    _place(fig, gs[1, 1], MAIN_FIGS[3])   # Fig 4 time
    _place(fig, gs[2, 0], MAIN_FIGS[4])   # Fig 5 deployment

    # 主线框 (右下空格)
    axb = fig.add_subplot(gs[2, 1]); axb.axis("off")
    thesis = (
        "TITLE — Perovskite gains most where\n"
        "sunlight is weakest\n"
        "==========================================\n\n"
        "One benchmarked, fleet-anchored twin (pvlib\n"
        "0.0007%, fleet r=0.89) supports the Results spine:\n\n"
        "1) Fig 1-2  geographic inversion and its\n"
        "   two independent physical mechanisms\n"
        "2) Fig 3  efficiency ratings mispredict\n"
        "   field energy; markets need two rulers\n"
        "3) Fig 4  substitution is gated by lifetime,\n"
        "   degradation and capex, not yield alone\n"
        "4) Fig 5  deployment should follow physics:\n"
        "   SW/South land utility perovskite,\n"
        "   rooftops tandem, low-advantage\n"
        "   ground-mounted sites modern c-Si\n\n"
        "Main discipline: Fig 1 maps the advantage;\n"
        "Fig 5 tests whether capacity is deployed\n"
        "where that advantage is valuable."
    )
    axb.text(0.02, 0.99, thesis, ha="left", va="top", fontsize=11,
             linespacing=1.4,
             bbox=dict(boxstyle="round,pad=0.6", facecolor="#fdeee7",
                       edgecolor="#b8360f", linewidth=1.5))

    fig.suptitle("Perovskite gains most where sunlight is weakest: "
                 "NEWFig1-5 spine\n"
                 "geographic inversion (Fig 1) -> mechanisms (Fig 2) -> "
                 "market ruler (Fig 3) -> lifetime economics (Fig 4) -> "
                 "deployment mismatch (Fig 5)",
                 fontsize=14.5, fontweight="bold", y=0.998)
    fig.savefig(os.path.join(FIGDIR, "_OVERVIEW_main_figures.png"),
                dpi=110, bbox_inches="tight")
    plt.close(fig)
    print("已保存: outputs/figures/_OVERVIEW_main_figures.png")


if __name__ == "__main__":
    main()
