"""Main Fig 1 — 物理引擎 vs 成本曲线: 替代叙事的三处质变.

立论图: 论证"为什么必须用物理一致的数字孪生, 而非成本曲线外推".
三个分镜揭示玩具 Wright 模型看不到、物理引擎才能看到的事实:

  (a) 每 kWp 的错觉: STC 效率 15/19/28% 差很大, 但每 kWp yield 几乎相同;
      叠层的效率优势只在"每 m²"(面积约束/rooftop)显现, 不在"每 kWp"(utility).
  (b) 寿命门槛: 钙钛矿在 15 年寿命下, 即使 capex 降到 floor, NPV LCOE 仍压不过晶硅;
      25 年寿命才翻盘 → 决定替代的是寿命突破, 不是成本下降.
  (c) 替代时机被改写: 成本曲线模型 (只看 capex/yield) 说 2025-26 钙钛矿就赢;
      物理 NPV (含退化/burn-in/折现) 说要等寿命突破 2030-36.

运行: python -m scripts.fig_physics_vs_cost
输出: outputs/figures/MainFig1_physics_vs_cost.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.provinces import PROVINCE_PV_2024_GW

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

COLORS = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
DISCOUNT = 0.05
OPEX = 0.015
ETA_STC = {"晶硅": 15.3, "钙钛矿": 19.3, "叠层": 28.3}   # 物理仿真 STC 效率


def national_weighted(col):
    df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    total = sum(PROVINCE_PV_2024_GW.values())
    out = {}
    for tech in ["晶硅", "钙钛矿", "叠层"]:
        sub = df[df["tech"] == tech]
        v = sum(r[col] * PROVINCE_PV_2024_GW.get(r["province"], 0) / total
                for _, r in sub.iterrows())
        out[tech] = v
    return out


def lcoe_npv(capex_per_w, yield_kwh_per_kwp, life, deg, burn):
    """全寿命 NPV 折现 LCOE ($/kWh)."""
    years = np.arange(1, int(life) + 1)
    df = (1 + DISCOUNT) ** -years
    yf = (1 - burn) * (1 - deg) ** (years - 1)
    yf[0] = (1 - burn)
    npv_yield = np.sum(yield_kwh_per_kwp * yf * df)
    npv_cost = capex_per_w * 1000 * (1 + np.sum(OPEX * df))
    return npv_cost / npv_yield


def lcoe_costcurve(capex_per_w, yield_kwh_per_kwp, life):
    """成本曲线模型: 只用 CRF, 不计退化/burn-in/逐年折现 (玩具版)."""
    crf = DISCOUNT * (1+DISCOUNT)**life / ((1+DISCOUNT)**life - 1)
    annual = yield_kwh_per_kwp / 1000.0
    return capex_per_w * (crf + OPEX) / annual


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    y_kwp = national_weighted("yield_kwh_per_kwp")
    y_m2 = national_weighted("yield_kwh_per_m2")
    print(f"per-kWp yield: {y_kwp}")
    print(f"per-m2 yield:  {y_m2}")
    EN = {"晶硅": "c-Si", "钙钛矿": "Perovskite", "叠层": "Tandem"}

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=300)

    # ===== (a) the per-kWp illusion =====
    ax = axes[0]
    techs = ["晶硅", "钙钛矿", "叠层"]
    x = np.arange(3); bw = 0.26
    # all normalised to c-Si = 1
    eff_ratio = [ETA_STC[t] / ETA_STC["晶硅"] for t in techs]
    kwp_ratio = [y_kwp[t] / y_kwp["晶硅"] for t in techs]
    m2_ratio = [y_m2[t] / y_m2["晶硅"] for t in techs]
    b1 = ax.bar(x - bw, eff_ratio, bw, color="#999999", label="STC efficiency")
    b2 = ax.bar(x, kwp_ratio, bw, color="#4393c3", label="Yield per kWp")
    b3 = ax.bar(x + bw, m2_ratio, bw, color="#d6604d", label="Yield per m$^2$")
    ax.axhline(1.0, color="black", lw=0.6, ls=":")
    for bars, vals in [(b1, eff_ratio), (b2, kwp_ratio), (b3, m2_ratio)]:
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, v + 0.02, f"{v:.2f}",
                    ha="center", fontsize=6.5)
    ax.set_xticks(x); ax.set_xticklabels([EN[t] for t in techs], fontsize=9)
    ax.set_ylabel("Ratio vs c-Si", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(a) The per-kWp illusion", fontsize=11, fontweight="bold",
                  loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="upper left", frameon=False)
    ax.set_ylim(0, 2.2)
    ax.annotate("Tandem 1.85$\\times$ in efficiency\nbut only 1.04$\\times$ per kWp\n"
                "$\\rightarrow$ gain is rooftop-only",
                xy=(2+bw, m2_ratio[2]), xytext=(0.55, 1.95),
                fontsize=6.8, color="#7a1f12",
                arrowprops=dict(arrowstyle="->", color="#d6604d", lw=0.7))

    # ===== (b) 同一块钙钛矿: 成本曲线核算 vs 物理 NPV 核算 =====
    # 沿同一 capex 下降轨迹, 比较两种"账法"下钙钛矿 LCOE 何时低于晶硅.
    ax = axes[1]
    yrs = np.arange(2025, 2051)
    cap_perov = np.maximum(0.40, 0.95 * 0.90 ** (yrs - 2025))
    cap_csi = np.maximum(0.40, 0.65 * 0.97 ** (yrs - 2025))
    yp, yc = y_kwp["钙钛矿"], y_kwp["晶硅"]

    def perov_life(t):   # 15→25 线性至 2032 突破
        f = np.clip((t - 2025) / (2032 - 2025), 0, 1)
        return 15 + f*10, 0.030 + f*(0.007-0.030), 0.10 + f*(0.03-0.10)

    lc_cost = np.array([lcoe_costcurve(cap_perov[i], yp, 25) * 100
                        for i in range(len(yrs))])           # 铭牌 25yr, 不计退化
    lc_phys = np.array([lcoe_npv(cap_perov[i], yp, *perov_life(yrs[i])) * 100
                        for i in range(len(yrs))])           # 真实寿命/退化/burn-in
    lc_csi = np.array([lcoe_npv(cap_csi[i], yc, 25, 0.007, 0.02) * 100
                       for i in range(len(yrs))])

    ax.fill_between(yrs, lc_cost, lc_phys, color="#f3d9c0", alpha=0.7, zorder=1)
    ax.plot(yrs, lc_cost, color="#999999", lw=2.2, ls="--", zorder=3,
            label="perovskite — cost-curve accounting")
    ax.plot(yrs, lc_phys, color=COLORS["钙钛矿"], lw=2.4, zorder=3,
            label="perovskite — physics NPV accounting")
    ax.plot(yrs, lc_csi, color=COLORS["晶硅"], lw=2.0, zorder=3,
            label="c-Si baseline")
    # 各账法下钙钛矿首次 < 晶硅 的年份
    for arr, col, lab in [(lc_cost, "#999999", "cost"), (lc_phys, COLORS["钙钛矿"], "phys")]:
        below = np.where(arr < lc_csi)[0]
        if len(below):
            yc_x = int(yrs[below[0]])
            ax.scatter(yc_x, arr[below[0]], s=55, color=col, edgecolors="black",
                       linewidth=0.5, zorder=5)
            ax.text(yc_x, arr[below[0]] - 0.5, f"{yc_x}", ha="center",
                    fontsize=7.5, fontweight="bold", color=col)
    ax.annotate("accounting gap:\nphysics keeps the same\nmodule more expensive",
                xy=(2034, (lc_cost[9]+lc_phys[9])/2), xytext=(2036, 6.2),
                fontsize=7.6, color="#7a3410",
                arrowprops=dict(arrowstyle="->", color="#c07a3a", lw=0.9))
    ax.set_xlabel("Year (capex falling to floor)", fontsize=9)
    ax.set_ylabel("LCOE (cents/kWh)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(b) Same module, two accountings", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.set_xlim(2025, 2050); ax.set_ylim(2, 9)
    ax.legend(fontsize=7.3, loc="upper right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 1 — Why physics, not cost curves: the per-kWp illusion and "
                 "the accounting that hides degradation",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig1_physics_vs_cost.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig1_physics_vs_cost.pdf",
                bbox_inches="tight")
    plt.close(fig)
    print("\nMain Fig 1 saved (2-panel).")
    cost_yr = int(yrs[np.where(lc_cost < lc_csi)[0][0]]) if np.any(lc_cost < lc_csi) else None
    phys_yr = int(yrs[np.where(lc_phys < lc_csi)[0][0]]) if np.any(lc_phys < lc_csi) else None
    print(f"  perovskite < c-Si: cost-curve accounting {cost_yr}, physics {phys_yr}")


if __name__ == "__main__":
    main()
