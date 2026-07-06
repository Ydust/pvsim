"""提议的新 Figure 1 (Joule 式: 先把主结论摆出来)。

三分镜,一眼讲完整个主张:
  (a) 反转地图: 95k 格点, 钙钛矿对现代晶硅的优势 —— 西南红(大)、西北蓝(小).
  (b) "阳光最弱处优势最大": 优势 vs 年辐照, 一条下滑线 (r=-0.51) —— 把反常画实.
  (c) 优势来自两个独立机制: 温度 + 光谱 (按资源带).

运行: python -m scripts.fig_main1_inversion
输出: outputs/figures/NEWFig1_inversion.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RES = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    g = pd.read_csv("outputs/grid_inversion_era5.csv", encoding="utf-8-sig")
    d = pd.read_csv("outputs/advantage_drivers.csv", encoding="utf-8-sig")

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6), dpi=300)

    # ===== (a) 反转地图 =====
    ax = axes[0]
    sc = ax.scatter(g["lon"], g["lat"], c=g["adv"], s=1.3, cmap="RdYlBu_r",
                    vmin=1, vmax=7, marker="s", edgecolors="none")
    ax.set_xlabel("Longitude (°E)", fontsize=9); ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.set_xlim(73, 135); ax.set_ylim(17, 54); ax.tick_params(labelsize=8)
    ax.set_title(f"(a) Perovskite vs modern silicon\nadvantage, {len(g)//1000}k cells (0.1°)",
                 fontsize=10.5, fontweight="bold", loc="left", pad=3)
    cb = plt.colorbar(sc, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("advantage (%)", fontsize=8); cb.ax.tick_params(labelsize=7)
    ax.text(0.97, 0.05, "SW: largest\nNW: smallest", transform=ax.transAxes,
            ha="right", fontsize=8, fontweight="bold", color="#7a1f12")

    # ===== (b) 阳光最弱处优势最大 (优势 vs 辐照, 下滑线) =====
    ax = axes[1]
    ghi, adv = g["ghi_ann"].to_numpy(), g["adv"].to_numpy()
    hb = ax.hexbin(ghi, adv, gridsize=45, cmap="Greys", mincnt=1, linewidths=0)
    # 分箱中位线
    bins = np.linspace(np.percentile(ghi, 1), np.percentile(ghi, 99), 14)
    bc = 0.5*(bins[:-1]+bins[1:])
    med = [np.median(adv[(ghi >= bins[i]) & (ghi < bins[i+1])]) for i in range(len(bins)-1)]
    ax.plot(bc, med, "o-", color="#b2182b", lw=2.2, ms=4, zorder=5, label="binned median")
    r = np.corrcoef(ghi, adv)[0, 1]
    z = np.polyfit(ghi, adv, 1); xx = np.array([ghi.min(), ghi.max()])
    ax.plot(xx, np.polyval(z, xx), "--", color="#b2182b", lw=1.1, alpha=0.7)
    ax.text(0.95, 0.92, f"r = {r:.2f}", transform=ax.transAxes, ha="right", va="top",
            fontsize=11, fontweight="bold", color="#b2182b")
    ax.text(0.95, 0.80, "← weaker sun = bigger advantage", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, color="#7a1f12", style="italic")
    ax.set_xlabel("Annual irradiance (kWh m$^{-2}$ yr$^{-1}$)", fontsize=9)
    ax.set_ylabel("Perovskite advantage (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(b) Largest where sunlight is weakest", fontsize=10.5,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="lower left", frameon=False); ax.grid(alpha=0.2, lw=0.3)

    # ===== (c) 两个独立机制 =====
    ax = axes[2]
    bands = ["I", "II", "III", "IV"]
    blab = {"I": "I\nplateau", "II": "II\nNW", "III": "III\nmost", "IV": "IV\nSW"}
    therm = [d[d.band == b]["thermal"].mean() for b in bands]
    spec = [d[d.band == b]["spectral"].mean() for b in bands]
    x = np.arange(4)
    ax.bar(x, therm, color="#d6604d", label="temperature", edgecolor="black", lw=0.4)
    ax.bar(x, spec, bottom=therm, color="#4393c3", label="spectral", edgecolor="black", lw=0.4)
    for xi in range(4):
        ax.text(xi, therm[xi]+spec[xi]+0.08, f"{therm[xi]+spec[xi]:.1f}%", ha="center",
                fontsize=7.5, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([blab[b] for b in bands], fontsize=8)
    ax.set_ylabel("Advantage by mechanism (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(c) Two independent mechanisms", fontsize=10.5, fontweight="bold",
                 loc="left", pad=3)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    ax.text(3, therm[3]+spec[3]+0.55, "both peak in\nthe hot SW", ha="center",
            fontsize=6.8, color="#444")

    fig.suptitle("Fig 1 — Perovskite's advantage over modern silicon inverts geographically "
                 "(largest where sunlight is weakest) and is the sum of two mechanisms",
                 fontsize=12, fontweight="bold", y=1.02)
    for a in fig.axes:
        a.grid(False)
    fig.tight_layout()
    fig.savefig("outputs/figures/NEWFig1_inversion.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved NEWFig1_inversion. grid r(ghi,adv)={r:.2f}, "
          f"temp band I->IV {therm[0]:.1f}->{therm[3]:.1f}%")


if __name__ == "__main__":
    main()
