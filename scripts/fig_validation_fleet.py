"""#6 — 孪生 vs 真实机队地面验证 + 真实损失(弃光)反演地图。

孪生(干净物理: 温度/光谱/IAM/逆变器)应系统性高于真实"利用小时数"(=kWh/kWp/年),
差额 = 孪生不建模的真实系统损失(组串/积灰/可用率约 ~10% 基线 + 弃光 0-25% 因地而异)。

  (a) 验证: 孪生比发电 vs 各省利用小时数; 1:1 线 + 拟合; r 与平均系统损失.
  (b) 反演: 各省(1 − 机队/孪生)= 隐含真实损失 %; 西北高出基线的部分 ≈ 弃光.

数据: 孪生 outputs/province_physics_yield.csv(现代晶硅); 利用小时数读取自
data/source_tables/provincial_fleet_hours_2024.csv。

运行: python -m scripts.fig_validation_fleet
输出: outputs/figures/MainFigV_fleet_validation.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon

from pvsim import viz
from pvsim.provinces import PROVINCE_EN, PROVINCE_CODE, PROVINCE_PV_2024_GW
from pvsim.source_data import load_fleet_hours
from scripts.portfolio_hexmap import HEX_LAYOUT, hex_xy

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FLEET_HOURS = load_fleet_hours()
BASELINE_LOSS = 10.0   # 组串/积灰/可用率等非弃光基线损失 (%)


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    sy = y[y.tech == "晶硅"].set_index("province")["yield_kwh_per_kwp"]
    prov = [p for p in FLEET_HOURS if p in sy.index]
    twin = np.array([sy[p] for p in prov])
    fleet = np.array([float(FLEET_HOURS[p]) for p in prov])
    loss = (1 - fleet/twin)*100                      # 隐含真实系统损失 %
    meanloss = loss.mean()

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), dpi=300)

    # ===== (a) 验证散点 =====
    ax = axes[0]
    RES = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}
    band = y[y.tech == "晶硅"].set_index("province")["res_band"]
    for b in ["I", "II", "III", "IV"]:
        idx = [i for i, p in enumerate(prov) if band[p] == b]
        ax.scatter(twin[idx], fleet[idx], s=55, color=RES[b], edgecolors="black",
                   linewidth=0.4, zorder=3, label=f"Band {b}")
    lim = [850, 2050]
    ax.plot(lim, lim, "k--", lw=1, label="1:1 (no losses)")
    ax.plot(lim, [v*(1-meanloss/100) for v in lim], color="#888", ls=":", lw=1.2,
            label=f"−{meanloss:.0f}% (mean system loss)")
    r = np.corrcoef(twin, fleet)[0, 1]
    for p in ["甘肃", "新疆", "青海", "重庆", "四川"]:
        if p in prov:
            i = prov.index(p)
            ax.annotate(PROVINCE_EN.get(p, p), (twin[i], fleet[i]),
                        textcoords="offset points", xytext=(4, 3), fontsize=6.5)
    ax.text(0.05, 0.92, f"r = {r:.2f}\nmean implied loss = {meanloss:.0f}%",
            transform=ax.transAxes, fontsize=9, va="top", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.set_xlabel("Twin specific yield (kWh/kWp/yr, clean physics)", fontsize=9)
    ax.set_ylabel("Fleet utilisation hours (h/yr, NEA — real)", fontsize=9)
    ax.set_xlim(lim); ax.set_ylim(lim); ax.tick_params(labelsize=8)
    ax.set_title("(a) Fleet-anchored system check", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="lower right", frameon=False); ax.grid(alpha=0.25, lw=0.3)

    # ===== (b) 损失反演地图 =====
    ax = axes[1]
    lossd = {p: loss[i] for i, p in enumerate(prov)}
    vmin, vmax = 0, 28
    cmap = plt.cm.YlOrRd
    for p, (col, row) in HEX_LAYOUT.items():
        x, yy = hex_xy(col, row)
        if p in lossd:
            fc = cmap(np.clip((lossd[p]-vmin)/(vmax-vmin), 0, 1)); lbl = f"{lossd[p]:.0f}"
        else:
            fc = "#eeeeee"; lbl = ""
        ax.add_patch(RegularPolygon((x, yy), numVertices=6, radius=0.5, orientation=0,
                                    facecolor=fc, edgecolor="black", linewidth=0.5))
        ax.text(x, yy+0.12, PROVINCE_CODE.get(p, ""), ha="center", va="center",
                fontsize=5.2, fontweight="bold")
        ax.text(x, yy-0.17, lbl, ha="center", va="center", fontsize=4.8)
    ax.set_aspect("equal"); ax.set_xlim(0.3, 8.7); ax.set_ylim(-8.7, 1.0); ax.axis("off")
    ax.set_title("(b) Inferred real-world system loss (%)", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
    cb = plt.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("twin − fleet, as % of twin", fontsize=7.5); cb.ax.tick_params(labelsize=6.5)
    ax.text(0.5, 0.02, f"~{BASELINE_LOSS:.0f}% baseline (soiling/wiring/availability); "
            "excess in the NW ≈ curtailment", transform=ax.transAxes, ha="center",
            fontsize=7, color="#444", style="italic")

    fig.suptitle(f"Fleet-anchored system validation: clean-physics twin minus ~{meanloss:.0f}% real "
                 f"system loss lands on fleet hours (r={r:.2f}); residuals recover NW curtailment",
                 fontsize=12, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFigV_fleet_validation.png", dpi=300, bbox_inches="tight")
    fig.savefig("outputs/figures/MainFigV_fleet_validation.pdf", bbox_inches="tight")
    plt.close(fig)
    nw = np.mean([lossd[p] for p in ["甘肃", "新疆", "青海", "宁夏", "内蒙古"] if p in lossd])
    sw = np.mean([lossd[p] for p in ["重庆", "四川", "贵州", "湖南"] if p in lossd])
    print(f"saved. r={r:.2f}, mean loss {meanloss:.0f}%; NW loss ~{nw:.0f}% vs SW ~{sw:.0f}% "
          f"(excess NW ≈ curtailment)")


if __name__ == "__main__":
    main()
