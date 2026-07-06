"""Main Fig 4 (policy) — where silicon is built vs where perovskite is worth most.

地理反转的政策落点: 现行装机按辐照集中在西北/华北, 但钙钛矿优势在西南最大 ——
两者错配. 把"该布西南、不该只盯西北"画实.

  (a) 散点: 各省 2024 装机 (x) vs 钙钛矿优势 (y), 象限标注 ——
      高价值-低装机(西南)被低估, 大装机-中低价值(华北/西北)被高估.
  (b) 六角图: 颜色=优势(西南红), 大小=2024 装机 —— 最大的方块不是最红的.

运行: python -m scripts.fig_policy_mismatch
输出: outputs/figures/MainFig4_policy_mismatch.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon

from pvsim import viz
from pvsim.provinces import PROVINCE_PV_2024_GW, PROVINCE_EN, PROVINCE_CODE
from scripts.portfolio_hexmap import HEX_LAYOUT, hex_xy

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RESOURCE_COLOR = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = y[y.tech == "晶硅"].set_index("province")
    per = y[y.tech == "钙钛矿"].set_index("province")
    prov = [p for p in csi.index if p in per.index]
    adv = {p: (per.loc[p, "yield_kwh_per_kwp"] /
               csi.loc[p, "yield_kwh_per_kwp"] - 1) * 100 for p in prov}
    band = {p: csi.loc[p, "res_band"] for p in prov}
    cap = {p: PROVINCE_PV_2024_GW.get(p, 0) for p in prov}

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), dpi=300)

    # ===== (a) capacity vs advantage scatter =====
    ax = axes[0]
    capv = np.array([cap[p] for p in prov])
    advv = np.array([adv[p] for p in prov])
    cap_med, adv_med = np.median(capv), np.median(advv)
    for b in ["I", "II", "III", "IV"]:
        idx = [i for i, p in enumerate(prov) if band[p] == b]
        ax.scatter(capv[idx], advv[idx], s=70, color=RESOURCE_COLOR[b],
                   edgecolors="black", linewidth=0.4, zorder=3, label=f"Band {b}")
    ax.axvline(cap_med, color="gray", ls=":", lw=0.8)
    ax.axhline(adv_med, color="gray", ls=":", lw=0.8)
    # 象限标注
    ax.text(0.02, 0.96, "high value · LOW build\n(Southwest — underused)",
            transform=ax.transAxes, fontsize=8, va="top", color="#c0392b",
            fontweight="bold")
    ax.text(0.98, 0.06, "low value · HIGH build\n(NW/N — over-targeted)",
            transform=ax.transAxes, fontsize=8, va="bottom", ha="right",
            color="#1f6fb2", fontweight="bold")
    # 标注关键省
    for p in ["重庆", "广西", "海南", "四川", "山东", "河北", "新疆", "内蒙古"]:
        if p in adv:
            ax.annotate(PROVINCE_EN.get(p, p), (cap[p], adv[p]),
                        textcoords="offset points", xytext=(5, 3), fontsize=6.8)
    ax.set_xlabel("2024 installed PV capacity (GW)", fontsize=9)
    ax.set_ylabel("Perovskite yield advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(a) Built where it matters least", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="center right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    # ===== (b) hex map: color=advantage, size=capacity =====
    ax = axes[1]
    vmin, vmax = 1, 8
    cmap = plt.get_cmap("RdYlBu_r")
    cmax = max(cap.values())
    for p, (col, row) in HEX_LAYOUT.items():
        x, yy = hex_xy(col, row)
        if p in adv:
            t = (adv[p] - vmin) / (vmax - vmin)
            face = cmap(max(0, min(1, t)))
            rad = 0.16 + 0.34 * (cap[p] / cmax)      # size ∝ capacity
        else:
            face = "#f0f0f0"; rad = 0.16
        ax.add_patch(RegularPolygon((x, yy), numVertices=6, radius=rad,
                                    orientation=0, facecolor=face,
                                    edgecolor="black", linewidth=0.5))
        ax.text(x, yy, PROVINCE_CODE.get(p, ""), ha="center", va="center",
                fontsize=5, fontweight="bold")
    ax.set_aspect("equal"); ax.set_xlim(0.3, 8.7); ax.set_ylim(-8.7, 1.0)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title("(b) Hex size = capacity, colour = advantage\n"
                 "(biggest cells are not the reddest)", fontsize=10,
                 fontweight="bold", loc="left", pad=3)
    sm = plt.cm.ScalarMappable(norm=plt.Normalize(vmin, vmax), cmap=cmap)
    sm.set_array([])
    cb = plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cb.set_label("Perovskite advantage (%)", fontsize=8)
    cb.ax.tick_params(labelsize=6.5)

    # headline stat: 优势 top 三分位省占装机比例
    order = sorted(prov, key=lambda p: -adv[p])
    n3 = len(prov) // 3
    top_adv_cap = sum(cap[p] for p in order[:n3])
    bot_adv_cap = sum(cap[p] for p in order[-n3:])
    tot = sum(cap.values())
    fig.suptitle("Fig 4 — Policy mismatch: top-advantage provinces hold "
                 f"{top_adv_cap/tot*100:.0f}% of PV, lowest-advantage hold "
                 f"{bot_adv_cap/tot*100:.0f}%",
                 fontsize=12, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig4_policy_mismatch.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig4_policy_mismatch.pdf",
                bbox_inches="tight")
    plt.close(fig)
    print(f"Main Fig 4 (policy mismatch) saved.")
    print(f"  top-advantage tercile holds {top_adv_cap/tot*100:.0f}% of PV "
          f"({top_adv_cap:.0f}/{tot:.0f} GW)")
    print(f"  bottom-advantage tercile holds {bot_adv_cap/tot*100:.0f}% "
          f"({bot_adv_cap:.0f} GW)")


if __name__ == "__main__":
    main()
