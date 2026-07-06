"""Deep dig 3 — the geography of substitution timing under a real capex trajectory.

问题: 真实 capex 轨迹下 (钙钛矿学习更快 + 寿命随年改善, 晶硅成熟缓降),
每个省哪一年钙钛矿 LCOE 翻过晶硅? 高优势西南先翻盘, 薄优势西北后翻盘.
=> 替代不是全国同步, 而是一条**自西南向西北推进的翻盘锋**.

capex 轨迹 (外生 glide, 标定到全国中位翻盘 ~2032, 与 Fig4 蒙卡一致):
  c-Si:    0.55→0.40 $/W (成熟, 慢)
  钙钛矿:  0.95→0.40 $/W (学习快) ; 寿命 15→25yr、退化 3→1%/yr 在 2028-2034 改善
逐省差异只来自**物理 yield 优势**(温度驱动), 故翻盘年=优势的地理映射.

  (a) 翻盘年地图 (hex): 各省钙钛矿 LCOE 超晶硅之年.
  (b) 翻盘年 vs 优势: 梯度 (高优势→早翻).
  (c) 代表省 LCOE-时间曲线: 西南(早) vs 西北(晚).

运行: python -m scripts.fig_substitution_timing_geo
输出: outputs/figures/MainFig4y_substitution_timing_geo.png/.pdf
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

DISCOUNT, OPEX = 0.05, 0.015
YEARS = np.arange(2024, 2051)


PER_FLOOR, PER_TAU = 0.36, 6.5      # 中性情景: 钙钛矿略低于晶硅地板


def cap_csi(t):
    return 0.42 + 0.13*np.exp(-(t-2024)/8.0)          # 0.55→0.42 (成熟, 慢)


def cap_per(t, floor=PER_FLOOR, tau=PER_TAU):
    return floor + (0.95-floor)*np.exp(-(t-2024)/tau)  # 0.95→floor (学习快)


def per_life(t):
    f = np.clip((t-2027)/5.0, 0, 1)                   # 寿命突破 2027-2032
    return 15 + 10*f, 0.030 - 0.020*f, 0.10 - 0.05*f  # life, deg, burn


def lcoe(capex, y, life, deg, burn):
    yrs = np.arange(1, int(round(life))+1); df = (1+DISCOUNT)**-yrs
    yf = (1-burn)*(1-deg)**(yrs-1); yf[0] = (1-burn)
    return (capex*1000*(1+np.sum(OPEX*df))) / np.sum(y*yf*df)


def crossover_year(y_csi, y_per, floor=PER_FLOOR, tau=PER_TAU):
    for t in YEARS:
        lc_c = lcoe(cap_csi(t), y_csi, 25, 0.007, 0.02)
        life, deg, burn = per_life(t)
        lc_p = lcoe(cap_per(t, floor, tau), y_per, life, deg, burn)
        if lc_p < lc_c:
            return t
    return 9999


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = y[y.tech == "晶硅"].set_index("province")["yield_kwh_per_kwp"]
    per = y[y.tech == "钙钛矿"].set_index("province")["yield_kwh_per_kwp"]
    band = y[y.tech == "晶硅"].set_index("province")["res_band"]
    prov = [p for p in csi.index if p in per.index]
    adv = {p: (per[p]/csi[p]-1)*100 for p in prov}
    cross = {p: crossover_year(csi[p], per[p]) for p in prov}
    valid = [cross[p] for p in prov if cross[p] < 9999]
    print(f"crossover range {min(valid)}-{max(valid)}, median {int(np.median(valid))}, "
          f"never={sum(cross[p]>=9999 for p in prov)}")

    RES = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}
    fig = plt.figure(figsize=(17, 4.7), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.05, 1.05], wspace=0.26)

    # ===== (a) crossover-year hex map =====
    ax = fig.add_subplot(gs[0, 0])
    yrs_arr = np.array(valid)
    vmin, vmax = yrs_arr.min(), yrs_arr.max()
    cmap = plt.cm.RdYlGn_r            # 早=绿, 晚=红
    for p, (col, rowp) in HEX_LAYOUT.items():
        xx, yy = hex_xy(col, rowp)
        if p in cross and cross[p] < 9999:
            fc = cmap((cross[p]-vmin)/(vmax-vmin)); lbl = f"{cross[p]}"
        elif p in cross:
            fc = "#444444"; lbl = "never"
        else:
            fc = "#eeeeee"; lbl = ""
        ax.add_patch(RegularPolygon((xx, yy), numVertices=6, radius=0.5, orientation=0,
                                    facecolor=fc, edgecolor="black", linewidth=0.5))
        ax.text(xx, yy+0.12, PROVINCE_CODE.get(p, ""), ha="center", va="center",
                fontsize=5.0, fontweight="bold",
                color="white" if (p in cross and cross[p] >= 9999) else "black")
        ax.text(xx, yy-0.18, lbl, ha="center", va="center", fontsize=4.4,
                color="white" if (p in cross and cross[p] >= 9999) else "black")
    ax.set_aspect("equal"); ax.set_xlim(0.3, 8.7); ax.set_ylim(-8.7, 1.0); ax.axis("off")
    ax.set_title("(a) Year perovskite wins on LCOE", fontsize=10.5, fontweight="bold",
                 loc="left", pad=3)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
    cb = plt.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("crossover year", fontsize=7.5); cb.ax.tick_params(labelsize=6.5)
    ax.text(0.5, 0.02, "green = early (SW) · red = late (NW)", transform=ax.transAxes,
            ha="center", fontsize=7, color="#444", style="italic")

    # ===== (b) crossover year vs advantage =====
    ax = fig.add_subplot(gs[0, 1])
    for b in ["I", "II", "III", "IV"]:
        ps = [p for p in prov if band[p] == b and cross[p] < 9999]
        ax.scatter([adv[p] for p in ps], [cross[p] for p in ps], s=55, color=RES[b],
                   edgecolors="black", linewidth=0.4, zorder=3, label=f"Band {b}")
    av = np.array([adv[p] for p in prov if cross[p] < 9999])
    cv = np.array([cross[p] for p in prov if cross[p] < 9999])
    z = np.polyfit(av, cv, 1); xx = np.linspace(av.min(), av.max(), 20)
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.2)
    r = np.corrcoef(av, cv)[0, 1]
    for p in ["重庆", "四川", "新疆", "内蒙古"]:
        if p in adv and cross[p] < 9999:
            ax.annotate(PROVINCE_EN.get(p, p), (adv[p], cross[p]),
                        textcoords="offset points", xytext=(4, 3), fontsize=6.5)
    ax.text(0.05, 0.1, f"r = {r:.2f}", transform=ax.transAxes, fontsize=9,
            fontweight="bold")
    ax.set_xlabel("Perovskite per-kWp advantage (%)", fontsize=9)
    ax.set_ylabel("Crossover year", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(b) High-advantage SW flips first", fontsize=10.5, fontweight="bold",
                 loc="left", pad=3)
    ax.legend(fontsize=7, loc="upper right", frameon=False, ncol=2, columnspacing=0.7)
    ax.grid(alpha=0.25, lw=0.3)

    # ===== (c) front width is conditional on the cost margin (honest meta-finding) =====
    ax = fig.add_subplot(gs[0, 2])
    floors = np.linspace(0.30, 0.41, 12)
    spreads, medians, nevers = [], [], []
    for fl in floors:
        xs = [crossover_year(csi[p], per[p], floor=fl) for p in prov]
        v = [x for x in xs if x < 9999]
        spreads.append((max(v)-min(v)) if v else np.nan)
        medians.append(np.median(v) if v else np.nan)
        nevers.append(sum(x >= 9999 for x in xs))
    margin = 0.42 - floors        # 钙钛矿地板比晶硅低多少 ($/W); 大=成本决定性赢
    ax.plot(margin, spreads, "o-", color="#5a2d82", lw=2, ms=5)
    ax.axvline(0.42-PER_FLOOR, color="#1b7837", ls="--", lw=1.2)
    ax.text(0.42-PER_FLOOR+0.002, max(s for s in spreads if not np.isnan(s))*0.85,
            "central\nscenario", fontsize=7, color="#1b7837")
    ax.set_xlabel("Perovskite cost edge over c-Si ($/W)", fontsize=9)
    ax.set_ylabel("SW→NW timing spread (yr)", fontsize=9); ax.tick_params(labelsize=8)
    ax.invert_xaxis()   # 左=决定性便宜(同步), 右=平价(梯度宽)
    ax.set_title("(c) Timing geography is conditional", fontsize=10.5, fontweight="bold",
                 loc="left", pad=3)
    ax.grid(alpha=0.25, lw=0.3)
    ax.text(0.03, 0.93, "decisive cost win\n-> synchronous", transform=ax.transAxes,
            fontsize=7, color="#1b7837", va="top")
    ax.text(0.97, 0.5, "near parity\n-> SW leads by years\n(but late, some never)",
            transform=ax.transAxes, fontsize=7, color="#b2182b", ha="right")

    span = f"{min(valid)}-{max(valid)}"
    fig.suptitle("The geography of substitution timing — under central cost a modest "
                 f"SW→NW front ({span}); the spread is small because the 5%% advantage range "
                 "is dwarfed by the capex decline (timing geography is conditional, panel c)",
                 fontsize=11.8, fontweight="bold", y=1.02)
    fig.savefig("outputs/figures/MainFig4y_substitution_timing_geo.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig4y_substitution_timing_geo.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"saved. crossover {span}")


if __name__ == "__main__":
    main()
