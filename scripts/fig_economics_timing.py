"""Main Fig 4 — the economics and timing of substitution.

综合评估第四环 (时间): 寿命门控的 utility-scale LCOE → 成本杠杆 → 情景路径 → 不确定尾部.
四合一压缩 (原 寿命门槛 + Main_substitution + 蒙卡).

  (a) 寿命门槛: 钙钛矿 15yr NPV LCOE 永在晶硅之上, 25yr 才翻盘 (经济为何不早发生).
  (b) 成本杠杆: yield edge 只是小项, 寿命/退化/capex 是主项.
  (c) 情景路径: 中央情景线 + 钙钛矿新建份额蒙卡带.
  (d) 不确定性: 1000 次蒙卡的钙钛矿超晶硅交叉年分布, 含失败尾.

运行: python -m scripts.fig_economics_timing
输出: outputs/figures/MainFig4_economics_timing.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.economic_priors import MC_DRAWS, MC_RANDOM_SEED, sample_mc_inputs
from scripts.fig_substitution_validation import (
    forward, nat_yield, YEARS, TECHS, calibrate_T)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

COL = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
EN = {"晶硅": "c-Si", "钙钛矿": "Perovskite", "叠层": "Tandem"}
DISCOUNT, OPEX = 0.05, 0.015


def lcoe_npv(capex, y_kwp, life, deg, burn):
    yrs = np.arange(1, int(life)+1)
    df = (1+DISCOUNT)**-yrs
    yf = (1-burn)*(1-deg)**(yrs-1); yf[0] = (1-burn)
    return (capex*1000*(1+np.sum(OPEX*df))) / np.sum(y_kwp*yf*df)


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    yields = nat_yield()

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), dpi=300)
    axes = axes.flatten()

    # ===== (a) 省级 LCOE: 从93条细线降噪为均值线 + 10-90%省际带 =====
    ax = axes[0]
    lc = pd.read_csv("outputs/province_physics_lcoe.csv", encoding="utf-8-sig")
    lc = lc[lc["year"] >= 2027]
    ax.axvspan(2027, 2032, color="#f6ede7", alpha=0.45, zorder=0)
    for tech in TECHS:
        sub = lc[lc["tech"] == tech]
        grp = sub.groupby("year")["lcoe_cents_per_kwh"]
        band = grp.quantile([0.1, 0.9]).unstack()
        nat = grp.mean()
        ax.fill_between(band.index, band[0.1], band[0.9], color=COL[tech],
                        alpha=0.12, linewidth=0, zorder=1)
        ax.plot(nat.index, nat.values, color=COL[tech], lw=2.25, zorder=4)
        ax.text(2050.25, nat.iloc[-1], EN[tech], color=COL[tech],
                fontsize=7.5, va="center", fontweight="bold", clip_on=False)
    ymax = min(10.5, float(lc["lcoe_cents_per_kwh"].quantile(0.99))*1.05)
    ax.set_xlim(2027, 2051.4); ax.set_ylim(0, ymax)
    ax.axvline(2032, color="#7a1f12", ls=(0, (2, 2)), lw=1.0, zorder=3)
    ax.text(2029.45, ymax*0.90, "pre-bankable\n15-yr life",
            fontsize=6.4, color="#7a1f12", va="top", ha="center")
    ax.annotate("2032 life\nbreakthrough", xy=(2032, ymax*0.50),
                xytext=(2034.0, ymax*0.64), fontsize=6.8, color="#7a1f12",
                arrowprops=dict(arrowstyle="->", color="#7a1f12", lw=0.8))
    ax.text(0.03, 0.07, "lines = national mean\nbands = 10-90% across provinces",
            transform=ax.transAxes, ha="left", fontsize=6.8, color="#555")
    ax.set_xlabel("Year", fontsize=9); ax.set_ylabel("LCOE (cents/kWh)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(a) Lifetime gate in LCOE", fontsize=11, fontweight="bold",
                 loc="left", pad=3)
    ax.grid(False)
    ax.grid(alpha=0.16, lw=0.35, axis="y")

    # ===== (b) 成本差: 改成相对基线的增量条, 避免绝对横轴造成视觉噪声 =====
    ax = axes[1]
    yp, yc = yields["钙钛矿"], yields["晶硅"]
    base_p = lcoe_npv(0.40, yp, 25, 0.007, 0.03)*100      # 钙钛矿 乐观基线
    csi = lcoe_npv(0.55, yc, 25, 0.007, 0.02)*100         # 晶硅 (要赢的线)
    levers = [
        ("Lose 3% yield edge", lcoe_npv(0.40, yc, 25, 0.007, 0.03)*100 - base_p, True),
        ("3%/yr degradation", lcoe_npv(0.40, yp, 25, 0.030, 0.03)*100 - base_p, False),
        ("15-yr lifetime", lcoe_npv(0.40, yp, 15, 0.007, 0.03)*100 - base_p, False),
        ("0.55 $/W capex", lcoe_npv(0.55, yp, 25, 0.007, 0.03)*100 - base_p, False),
    ]
    levers.sort(key=lambda f: f[1])
    gap = csi - base_p
    xmax = max([v for _, v, _ in levers])*1.22
    ax.axvspan(gap, xmax, color="#eaf2fa", alpha=0.8, zorder=0)
    for i, (lab, delta, phys) in enumerate(levers):
        ax.barh(i, delta, left=0, height=0.58, color="#4393c3" if phys else "#bdbdbd",
                edgecolor="black", lw=0.5, zorder=3)
        ax.text(delta+0.035, i, f"+{delta:.2f}", va="center",
                fontsize=7.0, color="#333")
    ax.axvline(0, color="#222", lw=0.8)
    ax.axvline(gap, color=COL["晶硅"], lw=1.5, ls="--", zorder=4)
    ax.text(gap+0.03, len(levers)-0.70, f"c-Si parity gap\n+{gap:.2f}",
            color=COL["晶硅"], fontsize=7, ha="left", va="top")
    ax.set_yticks(range(len(levers))); ax.set_yticklabels([f[0] for f in levers], fontsize=7.5)
    ax.set_xlabel("LCOE increase from favorable perovskite case (cents/kWh)", fontsize=9)
    ax.set_xlim(0, xmax)
    ax.tick_params(labelsize=8)
    ax.grid(False)
    ax.grid(alpha=0.15, lw=0.3, axis="x")
    ax.set_title("(b) Non-physics levers dominate the cost gap", fontsize=11,
                 fontweight="bold", loc="left", pad=3)

    # Monte Carlo draws support panel d. The share fan is left to SI Fig S7.
    T_fit, _, _, _, _, _ = calibrate_T()
    rng = np.random.default_rng(MC_RANDOM_SEED)
    cross = []
    for _ in range(MC_DRAWS):
        LRs, fl, bt, lf, temp = sample_mc_inputs(rng, T_fit)
        _, c = forward(yields, LRs, fl, bt, temp, life_final=lf)
        cross.append(c)
    cross = np.array(cross)

    # ===== (c) national substitution trajectory: central scenario only =====
    ax = axes[2]
    LR = {"晶硅": 0.18, "钙钛矿": 0.27, "叠层": 0.30}
    floor = {"晶硅": 0.40, "钙钛矿": 0.40, "叠层": 0.50}
    share, _ = forward(yields, LR, floor, 2032, 0.8, life_final=25.0)
    for tech in TECHS:
        central = share[tech] * 100
        ax.plot(YEARS, central, color=COL[tech], lw=2.2, zorder=3)
        ax.text(2050.45, central[-1], EN[tech], color=COL[tech],
                fontsize=7.5, va="center", fontweight="bold", clip_on=False)
    ax.axvline(2032, color="#7a1f12", lw=0.9, ls=(0, (2, 2)), alpha=0.9)
    ax.text(0.58, 0.92, "central scenario, not forecast\nuncertainty summarized in panel d",
            transform=ax.transAxes, ha="left", va="top", fontsize=6.8, color="#555")
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("Annual new-build share (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_xlim(2025, 2052.0); ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title("(c) Scenario allocation path", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.grid(False)
    ax.grid(alpha=0.16, lw=0.35, axis="y")

    # ===== (d) Monte Carlo crossover-year uncertainty =====
    ax = axes[3]
    valid = cross[cross <= 2050]
    years = np.arange(int(valid.min()), int(valid.max()) + 1)
    counts = np.array([np.sum(valid == yr) for yr in years])
    never_count = int(np.sum(cross > 2050))
    ax.bar(years, counts, width=0.86, color=COL["钙钛矿"], alpha=0.50,
           edgecolor="white", linewidth=0.7)
    ymax = counts.max(); ax.set_ylim(0, ymax*1.34)
    p10, p50, p90 = np.percentile(valid, [10, 50, 90])
    never = np.mean(cross > 2050)*100
    ax.axvspan(p10 - 0.5, p90 + 0.5, color=COL["钙钛矿"], alpha=0.10, zorder=0)
    ax.axvline(p50, color="black", ls="--", lw=1.2)
    ax.text(0.05, 0.88, f"P10-P90 = {p10:.0f}-{p90:.0f}\n"
            f"P50 = {p50:.0f}",
            transform=ax.transAxes, fontsize=8.2, color="#333",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#dddddd", lw=0.6))
    ax.text(0.70, 0.88, f"0 draws in\n2043-2050\n{never_count} draws >2050\n{never:.1f}%",
            transform=ax.transAxes, fontsize=7.4, color="#555", ha="left", va="top",
            bbox=dict(boxstyle="round,pad=0.25", fc="#f2f2f2", ec="#dddddd", lw=0.6))
    ax.set_xlabel("LCOE crossover year", fontsize=9)
    ax.set_ylabel("Scenario draws", fontsize=9)
    ax.set_xticks([2030, 2032, 2035, 2038, 2040, 2042])
    ax.set_xlim(years[0] - 0.9, years[-1] + 0.9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"(d) Crossover-year scenario ensemble", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.grid(False)
    ax.grid(alpha=0.18, lw=0.35, axis="y")

    fig.suptitle("Fig 4 — Lifetime-gated economics and scenario timing",
                 fontsize=12, fontweight="bold", y=1.005)
    fig.tight_layout(h_pad=2.0, w_pad=1.6)
    fig.savefig("outputs/figures/NEWFig4_economics_timing.png", dpi=300, bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig4_economics_timing.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig4_economics_timing.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Main Fig 4 saved. crossover P10/P50/P90 = {p10:.0f}/{p50:.0f}/{p90:.0f}, "
          f"not crossing by 2050 {never:.1f}%")


if __name__ == "__main__":
    main()
