"""Main Fig 5 — a segment- and region-resolved deployment map.

综合评估收口 (落点): 把前四环 (运行特性 + 分段 + 地理 + 经济) 合成一张可执行的
部署处方, 并对照现行装机的错配.

  (a) utility 错配: 现有装机 (x) vs 钙钛矿优势 (y); 高价值西南被低估, 低价值西北过载.
  (b) 处方矩阵: 市场(utility/rooftop) x 区域(西南/西北) -> 该用哪种技术.

运行: python -m scripts.fig_deployment_map
输出: outputs/figures/MainFig5_deployment_map.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from pvsim import viz
from pvsim.provinces import PROVINCE_PV_2024_GW, PROVINCE_EN, PROVINCE_CODE
from scripts.portfolio_hexmap import HEX_LAYOUT, hex_xy
from matplotlib.patches import RegularPolygon

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RESOURCE_COLOR = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}
C_CSI, C_PER, C_TAN = "#1f6fb2", "#e2641e", "#2a9d4a"


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = y[y.tech == "晶硅"].set_index("province")
    per = y[y.tech == "钙钛矿"].set_index("province")
    prov = [p for p in csi.index if p in per.index]
    adv = {p: (per.loc[p, "yield_kwh_per_kwp"]/csi.loc[p, "yield_kwh_per_kwp"]-1)*100
           for p in prov}
    band = {p: csi.loc[p, "res_band"] for p in prov}
    cap = {p: PROVINCE_PV_2024_GW.get(p, 0) for p in prov}

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.3), dpi=300)

    # ===== (a) utility mismatch scatter =====
    ax = axes[0]
    capv = np.array([cap[p] for p in prov]); advv = np.array([adv[p] for p in prov])
    for b in ["I", "II", "III", "IV"]:
        idx = [i for i, p in enumerate(prov) if band[p] == b]
        ax.scatter(capv[idx], advv[idx], s=70, color=RESOURCE_COLOR[b],
                   edgecolors="black", linewidth=0.4, zorder=3, label=f"Band {b}")
    ax.axvline(np.median(capv), color="gray", ls=":", lw=0.8)
    ax.axhline(np.median(advv), color="gray", ls=":", lw=0.8)
    ax.text(0.02, 0.96, "high value, LOW build\n(Southwest — underused)",
            transform=ax.transAxes, fontsize=8, va="top", color="#c0392b",
            fontweight="bold")
    ax.text(0.98, 0.05, "low value, HIGH build\n(NW/N — over-targeted)",
            transform=ax.transAxes, fontsize=8, va="bottom", ha="right",
            color=C_CSI, fontweight="bold")
    for p in ["重庆", "广西", "海南", "四川", "山东", "河北", "新疆", "内蒙古"]:
        if p in adv:
            ax.annotate(PROVINCE_EN.get(p, p), (cap[p], adv[p]),
                        textcoords="offset points", xytext=(5, 3), fontsize=6.8)
    order = sorted(prov, key=lambda p: -adv[p]); n3 = len(prov)//3
    top = sum(cap[p] for p in order[:n3])/sum(cap.values())*100
    ax.set_xlabel("2024 installed PV capacity (GW)", fontsize=9)
    ax.set_ylabel("Perovskite advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"(a) Utility today: built where it matters least\n"
                 f"(top-advantage provinces hold only {top:.0f}% of capacity)",
                 fontsize=10, fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="center right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    # ===== (b) data-driven utility decision map (per province) =====
    # 阈值: 对现代晶硅, 钙钛矿(更低效+寿命风险)需较大 yield 优势才划算; 取 ~4% 选炎热西南.
    THR = 4.0
    ax = axes[1]
    n_per = sum(1 for p in prov if adv[p] >= THR)
    gw_per = sum(cap[p] for p in prov if adv[p] >= THR)
    gw_csi = sum(cap[p] for p in prov if adv[p] < THR)
    for p, (col, row) in HEX_LAYOUT.items():
        x, yy = hex_xy(col, row)
        if p in adv:
            face = C_PER if adv[p] >= THR else C_CSI
            lbl = f"{adv[p]:.1f}"
        else:
            face = "#eeeeee"; lbl = ""
        ax.add_patch(RegularPolygon((x, yy), numVertices=6, radius=0.5,
                                    orientation=0, facecolor=face, alpha=0.55,
                                    edgecolor="black", linewidth=0.5))
        ax.text(x, yy+0.12, PROVINCE_CODE.get(p, ""), ha="center", va="center",
                fontsize=5.5, fontweight="bold")
        ax.text(x, yy-0.16, lbl, ha="center", va="center", fontsize=5)
    ax.set_aspect("equal"); ax.set_xlim(0.3, 8.7); ax.set_ylim(-8.7, 1.0)
    ax.axis("off")
    ax.set_title(f"(b) Utility decision map (threshold {THR}% advantage)",
                 fontsize=10, fontweight="bold", loc="left", pad=3)
    # legend + rooftop note
    ax.scatter([], [], marker="h", s=120, color=C_PER, alpha=0.55,
               edgecolors="black", label=f"Perovskite-favoured ({n_per} prov, {gw_per:.0f} GW)")
    ax.scatter([], [], marker="h", s=120, color=C_CSI, alpha=0.55,
               edgecolors="black", label=f"c-Si-favoured ({31-n_per} prov, {gw_csi:.0f} GW)")
    ax.legend(fontsize=7.5, loc="lower left", frameon=False)
    ax.text(0.99, 0.12, "Rooftop (all regions):\ntandem (1.30x energy/m$^2$)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5,
            color=C_TAN, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc="#eef6ee", ec=C_TAN, lw=0.6))

    # ===== (c) 占地 × 纬度: 集中式土地约束 (技术无关) =====
    ax = axes[2]
    lu = pd.read_csv("outputs/land_use_latitude.csv", encoding="utf-8-sig")
    bandmap = {p: csi.loc[p, "res_band"] for p in csi.index}
    lu["band"] = lu["province"].map(bandmap)
    for b in ["I", "II", "III", "IV"]:
        s = lu[lu.band == b]
        ax.scatter(s["lat"], s["shading_loss_pct"], s=55, color=RESOURCE_COLOR[b],
                   edgecolors="black", linewidth=0.4, zorder=3, label=f"Band {b}")
    z = np.polyfit(lu["lat"], lu["shading_loss_pct"], 1)
    xx = np.array([lu["lat"].min(), lu["lat"].max()])
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.2)
    r = np.corrcoef(lu["lat"], lu["shading_loss_pct"])[0, 1]
    ax.text(0.05, 0.93, f"r = {r:.2f}", transform=ax.transAxes, fontsize=11,
            fontweight="bold", color="#b2182b", va="top")
    for p in ["新疆", "内蒙古", "黑龙江", "四川", "海南"]:
        if p in set(lu["province"]):
            row = lu[lu.province == p].iloc[0]
            ax.annotate(PROVINCE_EN.get(p, p), (row["lat"], row["shading_loss_pct"]),
                        textcoords="offset points", xytext=(4, 3), fontsize=6.5)
    ax.set_xlabel("Latitude (°N)", fontsize=9)
    ax.set_ylabel("Utility land penalty: row-shading loss at GCR 0.4 (%)", fontsize=9)
    ax.tick_params(labelsize=8); ax.grid(alpha=0.25, lw=0.3)
    ax.set_title("(c) High-latitude utility pays a land penalty\n(tech-independent: row spacing)",
                 fontsize=10, fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7, loc="lower right", frameon=False)

    fig.suptitle("Fig 5 — Deploy by physics: tandem on rooftops, perovskite in the utility "
                 "Southwest, c-Si in the Northwest; high-latitude utility also pays a land penalty",
                 fontsize=11.5, fontweight="bold", y=1.0)
    fig.tight_layout(w_pad=2.0)
    fig.savefig("outputs/figures/NEWFig5_deployment.png", dpi=300, bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig5_deployment_map.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig5_deployment_map.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Main Fig 5 saved. top-advantage tercile holds {top:.0f}% of PV.")


if __name__ == "__main__":
    main()
