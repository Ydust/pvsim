"""Main Fig 3 — efficiency is not yield (现代晶硅基准): 把"效率"翻成两种市场的"发电".

  (a) 相对现代晶硅(22%) 的 效率/每kWp/每m² 比值 + 31 省散点:
      钙钛矿 0.88× 效率却 1.03× 每kWp(温度), 0.90× 每m²; 叠层 1.29× 效率仅在每m²(1.30×)兑现.
  (b) 市场平面 (核心): 每省一点, x=每kWp比值(集中式), y=每m²比值(屋顶), 晶硅=(1,1).
      钙钛矿落"右下=只赢集中式"; 叠层落"上=赢屋顶". 62 点二维云, 含象限.
  (c) 优势是分布不是一个数: 钙钛矿每kWp优势在 365 个点(31省+334网格)上的直方, 标中位/10–90%.

运行: python -m scripts.fig_yield_segmentation
输出: outputs/figures/NEWFig3_segmentation.png (+ MainFig2 兼容名)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from pvsim import viz
from pvsim.provinces import PROVINCE_PV_2024_GW

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EN = {"晶硅": "c-Si (modern)", "钙钛矿": "Perovskite", "叠层": "Tandem"}
COL = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
ETA_STC = {"晶硅": 22.0, "钙钛矿": 19.3, "叠层": 28.3}


def national_weighted(df, col):
    tot = sum(PROVINCE_PV_2024_GW.values())
    return {t: sum(r[col] * PROVINCE_PV_2024_GW.get(r["province"], 0) / tot
                   for _, r in df[df["tech"] == t].iterrows())
            for t in ["晶硅", "钙钛矿", "叠层"]}


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    dfp = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    y_kwp = national_weighted(dfp, "yield_kwh_per_kwp")
    y_m2 = national_weighted(dfp, "yield_kwh_per_m2")
    piv_k = dfp.pivot(index="province", columns="tech", values="yield_kwh_per_kwp")
    piv_m = dfp.pivot(index="province", columns="tech", values="yield_kwh_per_m2")
    plot_techs = ["钙钛矿", "叠层"]

    fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.0), dpi=300)

    # ===== (a) 效率/每kWp/每m² 比值 + 省散点 =====
    ax = axes[0]
    x = np.arange(2); bw = 0.26
    eff_r = [ETA_STC[t]/ETA_STC["晶硅"] for t in plot_techs]
    kwp_r = [y_kwp[t]/y_kwp["晶硅"] for t in plot_techs]
    m2_r = [y_m2[t]/y_m2["晶硅"] for t in plot_techs]
    b1 = ax.bar(x-bw, eff_r, bw, color="#9a9a9a", label="STC efficiency")
    b2 = ax.bar(x, kwp_r, bw, color="#4393c3", label="Yield per kWp")
    b3 = ax.bar(x+bw, m2_r, bw, color="#d6604d", label="Yield per m$^2$")
    ax.axhline(1.0, color="black", lw=1.3, zorder=1)
    ax.text(1.30, 1.01, "modern c-Si = 1.00", va="bottom", fontsize=6.6,
            fontweight="bold", color="#222")
    rng = np.random.default_rng(0)
    for i, t in enumerate(plot_techs):
        rk = (piv_k[t]/piv_k["晶硅"]).dropna().values
        rm = (piv_m[t]/piv_m["晶硅"]).dropna().values
        ax.scatter(np.full(len(rk), x[i])+rng.uniform(-0.07, 0.07, len(rk)), rk,
                   s=6, color="#08306b", alpha=0.6, zorder=4)
        ax.scatter(np.full(len(rm), x[i]+bw)+rng.uniform(-0.07, 0.07, len(rm)), rm,
                   s=6, color="#67000d", alpha=0.6, zorder=4)
    for bars, vals in [(b1, eff_r), (b2, kwp_r), (b3, m2_r)]:
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, v+0.015, f"{v:.2f}x",
                    ha="center", fontsize=6.6)
    ax.set_xticks(x); ax.set_xticklabels(["Perovskite", "Tandem"], fontsize=9.5)
    ax.set_ylabel("Ratio to modern c-Si", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(a) Efficiency is not yield", fontsize=11, fontweight="bold",
                 loc="left", pad=3)
    ax.legend(fontsize=7.2, loc="upper left", frameon=False)
    ax.set_xlim(-0.55, 1.95); ax.set_ylim(0, 1.62)
    ax.text(0.5, -0.18, "dots = 31 provinces", transform=ax.transAxes, ha="center",
            fontsize=6.3, color="#666")

    # ===== (b) 换尺子→翻转 (交叉线) + 每kWp领先幅度的 31 省散布 (双轴) =====
    from matplotlib.patches import ConnectionPatch
    ax = axes[1]                       # 左轴 = STC 效率 (%)
    ax2 = ax.twinx()                   # 右轴 = 每kWp 相对 c-Si 的领先 (%)
    techs3 = ["叠层", "晶硅", "钙钛矿"]
    adv_prov = {t: ((piv_k[t]/piv_k["晶硅"]) - 1).dropna().values*100 for t in techs3}
    adv_med = {t: float(np.median(adv_prov[t])) for t in techs3}
    ax.set_ylim(17.5, 30.5); ax2.set_ylim(-0.5, 6.3); ax.set_xlim(-0.4, 1.85)
    ax2.axhline(0, color=COL["晶硅"], lw=1.0, ls=":", zorder=1)
    rng = np.random.default_rng(1)
    for t in techs3:
        ax.plot(0, ETA_STC[t], "o", color=COL[t], ms=12, markeredgecolor="white",
                markeredgewidth=1, zorder=6)
        ax.text(-0.07, ETA_STC[t], f"{EN[t]}\n{ETA_STC[t]:.1f}%", ha="right", va="center",
                fontsize=7, color=COL[t], fontweight="bold")
        if t != "晶硅":
            a = adv_prov[t]
            ax2.scatter(np.full(len(a), 1.0)+rng.uniform(-0.045, 0.045, len(a)), a,
                        s=9, color=COL[t], alpha=0.4, zorder=3)
        ax2.plot(1, adv_med[t], "o", color=COL[t], ms=12, markeredgecolor="white",
                 markeredgewidth=1, zorder=6)
        lab = (f"{EN[t]}\n+{adv_med[t]:.1f}% ({adv_prov[t].min():.1f}–{adv_prov[t].max():.1f})"
               if t != "晶硅" else f"{EN[t]}\nbaseline (0%)")
        ax2.text(1.08, adv_med[t], lab, ha="left", va="center", fontsize=6.6,
                 color=COL[t], fontweight="bold")
        con = ConnectionPatch(xyA=(0, ETA_STC[t]), coordsA=ax.transData,
                              xyB=(1, adv_med[t]), coordsB=ax2.transData,
                              color=COL[t], lw=2.6, alpha=0.9, zorder=4)
        con.set_clip_on(False); ax.add_artist(con)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["by EFFICIENCY\n(STC, lab spec)", "by ENERGY\n(per kWp)"], fontsize=8)
    ax.set_ylabel("STC efficiency (%)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    ax2.set_ylabel("Per-kWp advantage over c-Si (%)", fontsize=8.5, color="#444")
    ax2.tick_params(labelsize=7.5)
    ax.set_title("(b) Change the ruler, the podium flips", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.text(0.5, 0.98, "Perovskite: worst by efficiency, best by energy per kWp",
            transform=ax.transAxes, ha="center", va="top", fontsize=7,
            color="#7a1f12", fontweight="bold")
    perov_first = (piv_k[["晶硅", "钙钛矿", "叠层"]].idxmax(axis=1) == "钙钛矿").mean()*100
    ax.text(0.5, -0.18, "dots = 31 provinces · ranking fixed, margin varies",
            transform=ax.transAxes, ha="center", fontsize=6.3, color="#666")

    fig.suptitle("Fig 3 — A cell's efficiency rating mispredicts its energy: change the ruler "
                 "(per-kWp vs per-m$^2$) and the technology ranking flips",
                 fontsize=11.5, fontweight="bold", y=1.03)
    fig.tight_layout(w_pad=2.5)
    fig.savefig("outputs/figures/NEWFig3_segmentation.png", dpi=300, bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig2_yield_segmentation.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Fig 3 saved. eff {[round(v,2) for v in eff_r]}, kWp {[round(v,2) for v in kwp_r]}, "
          f"m2 {[round(v,2) for v in m2_r]} | perov #1 per-kWp in {perov_first:.0f}% prov")


if __name__ == "__main__":
    main()
