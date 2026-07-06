"""提议的新 Fig 5 — 细颗粒度部署图。

  (a) 主图 (大): 省级陆上地面集中式部署决策平面(钙钛矿优势 × 高纬土地惩罚),
      点大小为 2024 装机。
      不再重复 Fig 1a 的 95k 优势场地图, 也不再和 (b) 重复做"优势 × 装机"统计。
  (b) 量化错配: 按优势分三档(高/中/低), 各档握有多少装机 —— 高优势档只占 ~24%。
  (c) 土地约束 (技术无关): 陆上地面集中式行间遮挡损失随纬度升 (r=0.98), 高纬度西北更费地。

运行: python -m scripts.fig_main5_deployment
输出: outputs/figures/NEWFig5_deployment.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from pvsim import viz
from pvsim.provinces import PROVINCES, PROVINCE_PV_2024_GW, PROVINCE_EN

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RES = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}
C_TAN = "#2a9d4a"


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = y[y.tech == "晶硅"].set_index("province")
    per = y[y.tech == "钙钛矿"].set_index("province")
    prov = [p for p in csi.index if p in per.index]
    adv = {p: (per.loc[p, "yield_kwh_per_kwp"]/csi.loc[p, "yield_kwh_per_kwp"]-1)*100
           for p in prov}
    bandmap = {p: csi.loc[p, "res_band"] for p in prov}
    cap = {p: PROVINCE_PV_2024_GW.get(p, 0) for p in prov}
    lu = pd.read_csv("outputs/land_use_latitude.csv", encoding="utf-8-sig")
    lu["band"] = lu["province"].map(bandmap)
    land = lu.set_index("province")["shading_loss_pct"].to_dict()

    fig, axd = plt.subplot_mosaic([["a", "b"], ["a", "c"]],
                                  figsize=(16, 7.4), width_ratios=[1.75, 1], dpi=300)

    # ===== 分组: 按优势分三档 =====
    order = sorted(prov, key=lambda p: -adv[p])
    t = len(order)//3
    groups = [order[:t], order[t:2*t], order[2*t:]]
    top_threshold = min(adv[p] for p in groups[0])

    # ===== (a) 决策平面: 优势 × 土地惩罚; 点大小=现有装机 =====
    ax = axd["a"]
    median_land = float(np.median([land[p] for p in prov if p in land]))
    ax.axvspan(top_threshold, max(adv.values())+0.6, color="#f6d6d2", alpha=0.35, zorder=0)
    ax.axhspan(min(land.values())-0.4, median_land, color="#e7f4e4", alpha=0.4, zorder=0)
    for b in ["I", "II", "III", "IV"]:
        ps = [p for p in prov if bandmap[p] == b and p in land]
        ax.scatter([adv[p] for p in ps], [land[p] for p in ps],
                   s=[38 + cap[p]*1.35 for p in ps], color=RES[b], alpha=0.84,
                   edgecolors="black", linewidth=0.45, label=f"Band {b}", zorder=3)
    ax.axvline(top_threshold, color="#b2182b", lw=1.1, ls="--")
    ax.axhline(median_land, color="#666", lw=0.9, ls=":")
    ax.text(top_threshold+0.04, max(land.values())+0.25, "top-third\nadvantage",
            color="#b2182b", fontsize=8, ha="left", va="top")
    ax.text(0.04, 0.92, "land utility caution:\nlow relative value\nor high land penalty",
            transform=ax.transAxes, fontsize=8.5, color="#0b3d63",
            fontweight="bold", ha="left", va="top")
    ax.text(0.64, 0.13, "land utility priority:\nhigh advantage,\nlower land penalty",
            transform=ax.transAxes, fontsize=8.5, color="#7a1f12",
            fontweight="bold", ha="left", va="bottom")
    for p in ["新疆", "内蒙古", "山东", "河北", "四川", "重庆", "云南", "广西"]:
        ax.annotate(PROVINCE_EN.get(p, p), (adv[p], land[p]), textcoords="offset points",
                    xytext=(5, 4), fontsize=6.4, zorder=5)
    ax.set_xlabel("Perovskite per-kWp advantage over modern c-Si (%)", fontsize=9)
    ax.set_ylabel("Ground-mounted land penalty (%)", fontsize=9)
    ax.set_xlim(min(adv.values())-0.35, max(adv.values())+0.45)
    ax.set_ylim(min(land.values())-0.4, max(land.values())+0.55)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.25, lw=0.35)
    ax.set_title("(a) Land-based utility decision plane: advantage vs land penalty (bubble = 2024 capacity)",
                 fontsize=11, fontweight="bold", loc="left", pad=4)
    band_handles, band_labels = ax.get_legend_handles_labels()
    size_handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor="#dddddd",
                           markeredgecolor="black", markersize=np.sqrt(38 + gw*1.35)/1.45,
                           label=f"{gw} GW") for gw in [20, 50, 100]]
    leg1 = ax.legend(band_handles, band_labels, fontsize=7, ncol=2, frameon=False,
                     loc="upper right")
    ax.add_artist(leg1)
    ax.legend(handles=size_handles, title="2024 capacity", title_fontsize=7, fontsize=7,
              frameon=True, framealpha=0.9, edgecolor="#ccc", loc="lower left")

    # ===== (b) 量化错配: 按优势分三档的装机 =====
    ax = axd["b"]
    glab = ["Top third\n(high adv)", "Middle", "Bottom third\n(low adv)"]
    gcol = [RES["I"], RES["III"], RES["IV"]]
    gcap = [sum(cap[p] for p in gg) for gg in groups]
    tot = sum(cap.values())
    bars = ax.bar(range(3), gcap, color=gcol, edgecolor="black", lw=0.5, alpha=0.85)
    for i, (b, c) in enumerate(zip(bars, gcap)):
        ax.text(b.get_x()+b.get_width()/2, c+8, f"{c:.0f} GW\n{c/tot*100:.0f}%",
                ha="center", fontsize=7.5, fontweight="bold")
    ax.set_xticks(range(3)); ax.set_xticklabels(glab, fontsize=7.5)
    ax.set_ylabel("2024 installed PV capacity (GW)", fontsize=8.5)
    ax.set_ylim(0, max(gcap)*1.25); ax.tick_params(labelsize=8)
    ax.set_title("(b) High-advantage regions hold the least capacity", fontsize=10,
                 fontweight="bold", loc="left", pad=3)
    advmean = sum(adv[p]*cap[p] for p in prov)/tot
    ax.text(0.5, -0.3, f"capacity-weighted advantage {advmean:.1f}%  (vs simple mean "
            f"{np.mean(list(adv.values())):.1f}%)", transform=ax.transAxes, ha="center",
            fontsize=6.5, color="#555")

    # ===== (c) 土地约束: 占地×纬度 (技术无关) =====
    ax = axd["c"]
    for b in ["I", "II", "III", "IV"]:
        s = lu[lu.band == b]
        ax.scatter(s["lat"], s["shading_loss_pct"], s=34, color=RES[b],
                   edgecolors="black", linewidth=0.3, zorder=3, label=f"Band {b}")
    z = np.polyfit(lu["lat"], lu["shading_loss_pct"], 1)
    xx = np.array([lu["lat"].min(), lu["lat"].max()])
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.1)
    r = np.corrcoef(lu["lat"], lu["shading_loss_pct"])[0, 1]
    ax.text(0.05, 0.92, f"r = {r:.2f}", transform=ax.transAxes, fontsize=10,
            fontweight="bold", color="#b2182b", va="top")
    ax.set_xlabel("Latitude (°N)", fontsize=8.5)
    ax.set_ylabel("Ground-mounted land penalty (%)", fontsize=8.5); ax.tick_params(labelsize=8)
    ax.set_title("(c) High-latitude ground-mounted PV: row-spacing penalty (tech-independent)",
                 fontsize=9, fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=6.5, ncol=2, frameon=False, loc="lower right"); ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 5 — Deploy by physics: steer land-utility perovskite to its high-advantage Southwest "
                 "(today under-built); tandem on rooftops; mind the high-latitude land penalty",
                 fontsize=11.5, fontweight="bold", y=1.0)
    fig.tight_layout(w_pad=1.5)
    fig.savefig("outputs/figures/NEWFig5_deployment.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"NEWFig5 saved. top-third adv holds {gcap[0]/tot*100:.0f}% of cap; "
          f"cap-weighted adv {advmean:.1f}%; land r={r:.2f}")


if __name__ == "__main__":
    main()
