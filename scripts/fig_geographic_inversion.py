"""Legacy/SI Fig — 优势地理反转省级示意.

说明: 这是 NEWFig1 之前的省级六角图版本, 保留作历史/支撑材料候选。
当前主图使用 scripts/fig_grid_inversion_era5.py 生成的 NEWFig1_inversion。
若继续使用本图, 只应表述为省级空间排序与机制示意, 不作为 0.1° 格点逐点预测。

三分镜:
  (a) 资源带 vs 钙钛矿优势 boxplot.
  (b) 六角优势地图.
  (c) 辐照 vs 替代价值散点.

运行: python -m scripts.fig_geographic_inversion
输出: outputs/figures/MainFig3_geographic_inversion.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon

from pvsim import viz
from pvsim.provinces import PROVINCE_EN, PROVINCE_CODE
from scripts.portfolio_hexmap import HEX_LAYOUT, hex_xy

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RESOURCE_COLOR = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}
COLORS = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e"}


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = df[df["tech"] == "晶硅"]
    perov = df[df["tech"] == "钙钛矿"]
    m = csi.merge(perov, on="province", suffixes=("_csi", "_perov"))
    m["adv"] = (m["yield_kwh_per_kwp_perov"] / m["yield_kwh_per_kwp_csi"] - 1) * 100
    m["band"] = m["res_band_csi"]
    m["ghi"] = m["ghi_kwh_m2_csi"]
    m["yield_csi"] = m["yield_kwh_per_kwp_csi"]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), dpi=300)

    # ===== (a) 资源带 vs 钙钛矿优势 boxplot =====
    ax = axes[0]
    band_order = ["I", "II", "III", "IV"]
    band_label = {"I": "I\nPlateau/desert", "II": "II\nNorthwest",
                  "III": "III\nMost regions", "IV": "IV\nSW cloudy"}
    data = [m[m["band"] == b]["adv"].values for b in band_order]
    bp = ax.boxplot(data, tick_labels=[band_label[b] for b in band_order],
                    patch_artist=True, widths=0.62,
                    medianprops=dict(color="black", lw=1.2))
    for patch, b in zip(bp["boxes"], band_order):
        patch.set_facecolor(RESOURCE_COLOR[b]); patch.set_alpha(0.65)
    # trend arrow
    medians = [np.median(m[m["band"] == b]["adv"]) for b in band_order]
    ax.plot(range(1, 5), medians, "k--", lw=1, alpha=0.6, zorder=1)
    ax.annotate("", xy=(4, medians[3]+0.3), xytext=(1, medians[0]-0.3),
                arrowprops=dict(arrowstyle="->", color="dimgray", lw=1.5))
    ax.text(2.5, 6.8, "poorer resource\n= larger advantage", fontsize=8,
            ha="center", color="dimgray", style="italic")
    for b in band_order:
        n = len(m[m["band"] == b])
        ax.text(band_order.index(b)+1, 0.3, f"n={n}", ha="center",
                fontsize=7, color="gray")
    ax.set_ylabel("Perovskite temp. advantage (% vs c-Si)", fontsize=9)
    ax.tick_params(labelsize=7.5)
    ax.set_title("(a) Resource band vs advantage: inverse", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.grid(alpha=0.25, lw=0.3, axis="y")

    # ===== (b) 六角优势地图 =====
    ax = axes[1]
    adv_map = dict(zip(m["province"], m["adv"]))
    vmin, vmax = 1, 8
    cmap = plt.get_cmap("RdYlBu_r")
    for prov, (col, row) in HEX_LAYOUT.items():
        x, y = hex_xy(col, row)
        if prov in adv_map:
            t = (adv_map[prov] - vmin) / (vmax - vmin)
            face = cmap(max(0, min(1, t)))
            lbl = f"{adv_map[prov]:.1f}"
        else:
            face = "#f0f0f0"; lbl = "-"
        ax.add_patch(RegularPolygon((x, y), numVertices=6, radius=0.5,
                                     orientation=0, facecolor=face,
                                     edgecolor="black", linewidth=0.6))
        ax.text(x, y+0.12, PROVINCE_CODE.get(prov, prov), ha="center",
                va="center", fontsize=6, fontweight="bold")
        ax.text(x, y-0.16, lbl, ha="center", va="center", fontsize=5.5)
    ax.set_aspect("equal"); ax.set_xlim(0.5, 8.5); ax.set_ylim(-8.5, 0.8)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title("(b) Advantage map: SW red / NW blue", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    sm = plt.cm.ScalarMappable(norm=plt.Normalize(vmin, vmax), cmap=cmap)
    sm.set_array([])
    cb = plt.colorbar(sm, ax=ax, shrink=0.65, pad=0.02)
    cb.set_label("Advantage (%)", fontsize=8); cb.ax.tick_params(labelsize=6.5)

    # ===== (c) 辐照 vs 替代价值散点 =====
    ax = axes[2]
    for b in band_order:
        sub = m[m["band"] == b]
        ax.scatter(sub["ghi"], sub["adv"], s=55, color=RESOURCE_COLOR[b],
                   alpha=0.8, edgecolors="black", linewidth=0.4,
                   label=f"Band {b}", zorder=3)
    # regression line
    z = np.polyfit(m["ghi"], m["adv"], 1)
    xx = np.linspace(m["ghi"].min(), m["ghi"].max(), 50)
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.2,
            label=f"slope {z[0]*1000:.2f}%/(MWh/m$^2$)")
    r = np.corrcoef(m["ghi"], m["adv"])[0, 1]
    # annotate extreme provinces
    hi_adv = m.nlargest(2, "adv"); lo_adv = m.nsmallest(2, "adv")
    for _, row in pd.concat([hi_adv, lo_adv]).iterrows():
        ax.annotate(PROVINCE_EN.get(row["province"], row["province"]),
                    (row["ghi"], row["adv"]),
                    textcoords="offset points", xytext=(5, 3), fontsize=6.5)
    ax.text(0.05, 0.06, f"r = {r:.2f}\n(high irradiance $\\rightarrow$ low value)",
            transform=ax.transAxes, fontsize=8,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.set_xlabel("Annual GHI (kWh/m$^2$)", fontsize=9)
    ax.set_ylabel("Perovskite temp. advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(c) Irradiance vs substitution value", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=6.8, loc="upper right", frameon=False, ncol=2,
              columnspacing=0.8)
    ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 3 — Geographic inversion of advantage: deploy perovskite "
                 "in the Southwest, not the Northwest",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig3_geographic_inversion.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig3_geographic_inversion.pdf",
                bbox_inches="tight")
    plt.close(fig)
    print(f"Main Fig 3 saved. irradiance-advantage r = {r:.3f}")
    print(f"  Top advantage: {', '.join(PROVINCE_EN.get(p,p) for p in hi_adv['province'])}")
    print(f"  Low advantage: {', '.join(PROVINCE_EN.get(p,p) for p in lo_adv['province'])}")


if __name__ == "__main__":
    main()
