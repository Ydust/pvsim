"""Graphical abstract — 三方向(三 shift)版 (重建, 供对照).

旧主线: 物理改写替代叙事的三处质变 ——
  (1) 寿命门槛 (非成本)
  (2) 地理反转 (西南 > 西北)
  (3) 铟: 全球约束, 非中国卡口
收口: 综合替代 2030–2039 而非成本曲线的 ~2026.

运行: python -m scripts.graphical_abstract_3shift
输出: outputs/figures/Graphical_Abstract_3shift.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from pvsim import viz

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

C_CSI, C_PER, C_TAN = "#1f6fb2", "#e2641e", "#2a9d4a"
C_GEO, C_IN = "#c0392b", "#7d3c98"
DISCOUNT, OPEX = 0.05, 0.015


def lcoe_npv(capex, y_kwp, life, deg, burn):
    yrs = np.arange(1, int(life)+1)
    df = (1+DISCOUNT)**-yrs
    yf = (1-burn)*(1-deg)**(yrs-1); yf[0] = (1-burn)
    return (capex*1000*(1+np.sum(OPEX*df))) / np.sum(y_kwp*yf*df)


def card(bg, x, y, w, h, fc="#ffffff", ec="#cccccc", lw=1.3):
    bg.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.006,rounding_size=0.018",
                 facecolor=fc, edgecolor=ec, linewidth=lw, zorder=1,
                 mutation_aspect=0.6))


def arrow(bg, x0, y0, x1, y1, color="#888888", lw=2.2):
    bg.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=18, color=color, lw=lw, zorder=2))


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    fig = plt.figure(figsize=(12, 7.2), dpi=200)
    bg = fig.add_axes([0, 0, 1, 1]); bg.set_xlim(0, 1); bg.set_ylim(0, 1)
    bg.axis("off"); bg.patch.set_alpha(0)

    # Title (story line: whether -> where -> how far)
    bg.text(0.5, 0.965, "Whether, where, and how far perovskite replaces silicon "
            "is set by physics, not price",
            ha="center", fontsize=16.5, fontweight="bold")
    bg.text(0.5, 0.927, "Three stages of one question, resolved by an 8760-h "
            "physics-consistent twin of China's PV transition",
            ha="center", fontsize=10.5, color="#444444")

    # Engine card
    card(bg, 0.035, 0.60, 0.265, 0.27, fc="#eef4fa", ec=C_CSI, lw=1.7)
    bg.text(0.1675, 0.845, "Physics-consistent\ndigital twin", ha="center",
            va="top", fontsize=12.5, fontweight="bold", color=C_CSI)
    bg.text(0.052, 0.755,
            "-  De Soto single-diode, 8760 h\n"
            "-  31 provinces -> 95k cells (0.1 deg)\n"
            "-  c-Si / perovskite / tandem\n"
            "-  validated vs pvlib: 0.0007%\n"
            "-  learning backcast R2=0.887",
            ha="left", va="top", fontsize=9.0, color="#222222")
    arrow(bg, 0.305, 0.735, 0.355, 0.735)
    bg.text(0.33, 0.762, "replaces\ncost curves", ha="center", fontsize=7.8,
            style="italic", color="#666666")

    # 3 acts of one question: WHETHER -> WHERE -> HOW FAR
    cards = [(0.365, "1 . WHETHER it happens", "lifetime gate", C_PER),
             (0.575, "2 . WHERE it pays first", "geographic inversion (SW)", C_GEO),
             (0.785, "3 . HOW FAR it scales", "indium ceiling (global)", C_IN)]
    for x0, t, sub, col in cards:
        card(bg, x0, 0.565, 0.19, 0.305, ec=col, lw=1.7)
        bg.text(x0+0.095, 0.852, t, ha="center", fontsize=11, fontweight="bold",
                color=col)
        bg.text(x0+0.095, 0.829, sub, ha="center", fontsize=8.3, style="italic",
                color="#666666")
    # connective arrows between the three acts (progression, not a list)
    arrow(bg, 0.560, 0.717, 0.572, 0.717, color="#555555", lw=2.0)
    arrow(bg, 0.770, 0.717, 0.782, 0.717, color="#555555", lw=2.0)

    # (1) lifetime mini
    ax1 = fig.add_axes([0.388, 0.635, 0.145, 0.135], zorder=5)
    yk = 1554.0
    cap = np.linspace(0.95, 0.38, 40)
    lc15 = [lcoe_npv(c, yk, 15, 0.030, 0.10)*100 for c in cap]
    lc25 = [lcoe_npv(c, yk, 25, 0.007, 0.03)*100 for c in cap]
    csi = lcoe_npv(0.55, 1486, 25, 0.007, 0.02)*100
    ax1.plot(cap, lc15, "--", color=C_PER, lw=1.8)
    ax1.plot(cap, lc25, "-", color=C_PER, lw=1.8)
    ax1.axhline(csi, color=C_CSI, lw=1.4)
    ax1.invert_xaxis(); ax1.set_xticks([]); ax1.set_yticks([])
    ax1.text(0.92, lc15[3]+0.1, "15 yr", fontsize=7, color=C_PER, fontweight="bold")
    ax1.text(0.6, lc25[-1]-0.55, "25 yr", fontsize=7, color=C_PER, fontweight="bold")
    ax1.text(0.6, csi+0.18, "c-Si", fontsize=7, color=C_CSI)
    ax1.set_title("NPV LCOE  (capex -> floor)", fontsize=7, pad=2)
    bg.text(0.46, 0.585, "15 yr never beats c-Si;\nlifetime = 43% of cost cut",
            ha="center", fontsize=7.6, color="#333333")

    # (2) geographic mini
    ax2 = fig.add_axes([0.598, 0.635, 0.145, 0.135], zorder=5)
    r_grid = -0.54
    try:
        gdf = pd.read_csv("outputs/grid_inversion_era5.csv", encoding="utf-8-sig")
        r_grid = float(np.corrcoef(gdf["ghi_ann"], gdf["adv"])[0, 1])
        show = gdf.sample(min(6000, len(gdf)), random_state=0)
        ax2.scatter(show["ghi_ann"], show["adv"], s=2, c=show["adv"], cmap="RdYlBu_r",
                    vmin=1, vmax=8, alpha=0.5, edgecolors="none")
        z = np.polyfit(gdf["ghi_ann"], gdf["adv"], 1)
        xx = np.linspace(gdf["ghi_ann"].min(), gdf["ghi_ann"].max(), 30)
        ax2.plot(xx, np.polyval(z, xx), "k--", lw=1.5)
    except FileNotFoundError:
        pass
    ax2.set_xticks([]); ax2.set_yticks([])
    ax2.set_title("advantage vs irradiance", fontsize=7, pad=2)
    ax2.text(0.04, 0.08, f"r = {r_grid:.2f}\n(95k grid cells)",
             transform=ax2.transAxes, fontsize=8, fontweight="bold", color=C_GEO)
    bg.text(0.67, 0.585, "Gains most in cloudy SW,\nnot sunny NW",
            ha="center", fontsize=7.6, color="#333333")

    # (3) indium mini
    ax3 = fig.add_axes([0.808, 0.635, 0.145, 0.135], zorder=5)
    ax3.bar([0], [199], width=0.5, color=C_IN)
    ax3.bar([1], [10], width=0.5, color="#bbbbbb")
    ax3.axhline(100, color="#c0392b", ls="--", lw=1)
    ax3.set_xticks([0, 1]); ax3.set_xticklabels(["Global\n1 TWp/yr", "China\n2030"],
                                                 fontsize=6.5)
    ax3.set_yticks([])
    ax3.text(0, 199+8, "199%", ha="center", fontsize=7.5, fontweight="bold", color=C_IN)
    ax3.text(1, 10+8, "10%", ha="center", fontsize=7.5)
    ax3.set_title("indium demand-production %", fontsize=7, pad=2)
    ax3.set_ylim(0, 240)
    bg.text(0.88, 0.585, "Binds globally at TW scale,\nnot China; needs In-free TCO",
            ha="center", fontsize=7.6, color="#333333")

    for xc in [0.46, 0.67, 0.88]:
        arrow(bg, xc, 0.558, xc, 0.49, color="#999999", lw=1.8)

    # synthesis timeline (the three acts together → the actual timing)
    card(bg, 0.06, 0.10, 0.88, 0.37, fc="#fafafa", ec="#999999", lw=1.4)
    bg.text(0.5, 0.435, "Put the three together: when does it actually happen?",
            ha="center", fontsize=12.5, fontweight="bold")
    axt = fig.add_axes([0.10, 0.155, 0.80, 0.20], zorder=5)
    axt.set_xlim(2024.5, 2050.5); axt.set_ylim(0, 1); axt.axis("off")
    axt.annotate("", xy=(2050.3, 0.5), xytext=(2024.7, 0.5),
                 arrowprops=dict(arrowstyle="->", color="#444444", lw=1.5))
    for yr in range(2025, 2051, 5):
        axt.plot([yr, yr], [0.45, 0.55], color="#444444", lw=1)
        axt.text(yr, 0.30, str(yr), ha="center", fontsize=8.5, color="#444444")
    axt.scatter(2026, 0.5, s=130, color="#bbbbbb", edgecolors="black",
                linewidth=0.6, zorder=4)
    axt.text(2026, 0.74, "cost-curve model\nsays 2026", ha="center", fontsize=8.2,
             color="#777777")
    axt.add_patch(plt.Rectangle((2030, 0.42), 9, 0.16, facecolor=C_PER, alpha=0.25,
                                edgecolor=C_PER, linewidth=1.2, zorder=2))
    axt.scatter(2032, 0.5, s=150, color=C_PER, edgecolors="black", linewidth=0.7,
                zorder=5)
    axt.text(2034.5, 0.76, "physics + Monte Carlo: 2030-2039\n"
             "(median 2032; calibrated to multi->mono R2=0.83)",
             ha="center", fontsize=8.6, color=C_PER, fontweight="bold")
    axt.text(2046.5, 0.28, "2.1% of runs:\nnever substitutes\n(lifetime fails)",
             ha="center", fontsize=7.8, color=C_GEO)

    bg.text(0.5, 0.055,
            "Policy: shift R&D from cost to lifetime   .   site perovskite in the "
            "Southwest, not the Northwest   .   pursue indium-free electrodes for the TW endgame",
            ha="center", fontsize=10, fontweight="bold", color="#222222",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff7e6",
                      edgecolor="#e2a04e", linewidth=1))

    fig.savefig("outputs/figures/Graphical_Abstract_story.png", dpi=200,
                facecolor="white")
    fig.savefig("outputs/figures/Graphical_Abstract_story.pdf", facecolor="white")
    plt.close(fig)
    print("Graphical_Abstract_story saved (whether->where->how far story line).")


if __name__ == "__main__":
    main()
