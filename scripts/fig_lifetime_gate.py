"""Main Fig 2 — 寿命门槛: 替代的真正闸门 (质变一: 寿命 > 成本).

论证: 决定钙钛矿能否替代晶硅的是寿命突破, 不是成本下降.
即使在温度优势最大的海口 (+7.5% yield), 15 年寿命的钙钛矿 NPV LCOE
也永远压不过晶硅; 必须等寿命突破到 ~25 年才翻盘.

三分镜:
  (a) 海口钙钛矿 NPV LCOE 全寿命演化: 15yr 永远 > 晶硅, 25yr 才翻盘.
  (b) 替代交叉年 vs 寿命突破年 (单调灵敏度, 突破越晚替代越晚).
  (c) LCOE 三因子分解: 寿命 / 退化率 / burn-in 各自对 LCOE 的贡献.

运行: python -m scripts.fig_lifetime_gate
输出: outputs/figures/MainFig2_lifetime_gate.png/.pdf
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
CAPEX_0 = {"晶硅": 0.65, "钙钛矿": 0.95}
Q_0 = {"晶硅": 1500.0, "钙钛矿": 12.0}
LR = {"晶硅": 0.18, "钙钛矿": 0.27}
B = {k: -np.log2(1 - v) for k, v in LR.items()}
CAPEX_FLOOR = {"晶硅": 0.40, "钙钛矿": 0.40}
MAX_DROP = 0.12
YEARS = np.arange(2025, 2051)
N = len(YEARS)


def lcoe_npv(capex_per_w, y_kwp, life, deg, burn):
    years = np.arange(1, int(life) + 1)
    df = (1 + DISCOUNT) ** -years
    yf = (1 - burn) * (1 - deg) ** (years - 1)
    yf[0] = (1 - burn)
    npv_yield = np.sum(y_kwp * yf * df)
    npv_cost = capex_per_w * 1000 * (1 + np.sum(OPEX * df))
    return npv_cost / npv_yield


def get_yield(province, tech):
    df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    r = df[(df["province"] == province) & (df["tech"] == tech)]
    return float(r["yield_kwh_per_kwp"].values[0])


def capex_trajectory(tech, breakthrough=2032):
    """全局 capex 轨迹 (年降幅封顶)."""
    cum = Q_0[tech]; cap = CAPEX_0[tech]; path = np.zeros(N)
    # 简化的全国新建驱动累计
    new = {"晶硅": np.linspace(80, 30, N), "钙钛矿": np.minimum(np.arange(N)*4+5, 100)}[tech]
    for i in range(N):
        raw = max(CAPEX_FLOOR[tech], CAPEX_0[tech]*(max(cum,0.1)/Q_0[tech])**(-B[tech]))
        cap = raw if i == 0 else max(cap*(1-MAX_DROP), raw, CAPEX_FLOOR[tech])
        path[i] = cap
        cum += new[i] * 1.4
    return path


def perov_life_step(year, breakthrough):
    """阶跃门槛: 突破前固定 15yr (差), 突破年起跳到 25yr (好).

    这是"闸门"的正确抽象 —— 商业钙钛矿在寿命突破前后是两种产品.
    (主轨迹 Fig 5 用渐进插值; 此处灵敏度分析用阶跃, 直接展示门槛效应.)
    """
    if year >= breakthrough:
        return 25.0, 0.007, 0.03
    return 15.0, 0.030, 0.10


def crossover_year(breakthrough, y_csi, y_perov):
    cap_csi = capex_trajectory("晶硅")
    cap_perov = capex_trajectory("钙钛矿")
    for i, yr in enumerate(YEARS):
        life, deg, burn = perov_life_step(int(yr), breakthrough)
        lc_perov = lcoe_npv(cap_perov[i], y_perov, life, deg, burn)
        lc_csi = lcoe_npv(cap_csi[i], y_csi, 25, 0.007, 0.02)
        if lc_perov < lc_csi:
            return int(yr)
    return None


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    CITY = "海南"   # 海口 — 温度优势最大省
    y_csi = get_yield(CITY, "晶硅")
    y_perov = get_yield(CITY, "钙钛矿")
    print(f"{CITY}: 晶硅 {y_csi:.0f}, 钙钛矿 {y_perov:.0f} kWh/kWp "
          f"(+{(y_perov/y_csi-1)*100:.1f}%)")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), dpi=300)

    # ===== (a) 海口钙钛矿 NPV LCOE 全寿命演化 (15yr vs 25yr vs 晶硅) =====
    ax = axes[0]
    cap_csi = capex_trajectory("晶硅")
    cap_perov = capex_trajectory("钙钛矿")
    lc_csi = [lcoe_npv(cap_csi[i], y_csi, 25, 0.007, 0.02)*100 for i in range(N)]
    # 钙钛矿固定 15yr (无突破)
    lc_p15 = [lcoe_npv(cap_perov[i], y_perov, 15, 0.030, 0.10)*100 for i in range(N)]
    # 钙钛矿固定 25yr (已突破)
    lc_p25 = [lcoe_npv(cap_perov[i], y_perov, 25, 0.007, 0.03)*100 for i in range(N)]
    ax.plot(YEARS, lc_csi, color=COLORS["晶硅"], lw=1.8, label="c-Si (25 yr)")
    ax.plot(YEARS, lc_p15, color=COLORS["钙钛矿"], lw=1.8, ls="--",
            label="Perovskite 15 yr (no breakthrough)")
    ax.plot(YEARS, lc_p25, color=COLORS["钙钛矿"], lw=1.8,
            label="Perovskite 25 yr (post-breakthrough)")
    ax.fill_between(YEARS, lc_csi, lc_p15, where=np.array(lc_p15)>np.array(lc_csi),
                    color=COLORS["钙钛矿"], alpha=0.08)
    ax.annotate("15 yr stays > c-Si\n$\\rightarrow$ never substitutes",
                xy=(2045, lc_p15[20]),
                xytext=(2034, lc_p15[20]+0.9), fontsize=7, color="#7a1f12",
                arrowprops=dict(arrowstyle="->", color=COLORS["钙钛矿"], lw=0.7))
    ax.set_xlabel("Year", fontsize=9); ax.set_ylabel("NPV LCOE (cents/kWh)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(a) Haikou: lifetime decides", fontsize=11, fontweight="bold",
                 loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="upper right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3); ax.set_xlim(2025, 2050)

    # ===== (b) 替代交叉年 vs 寿命突破年 =====
    ax = axes[1]
    breakthroughs = np.arange(2027, 2046, 2)
    # 用全国加权 yield 算更代表性
    total = sum(PROVINCE_PV_2024_GW.values())
    df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    yw = {}
    for tech in ["晶硅", "钙钛矿"]:
        sub = df[df["tech"] == tech]
        yw[tech] = sum(r["yield_kwh_per_kwp"]*PROVINCE_PV_2024_GW.get(r["province"],0)/total
                       for _, r in sub.iterrows())
    cross = [crossover_year(int(by), yw["晶硅"], yw["钙钛矿"]) for by in breakthroughs]
    valid = [(by, cr) for by, cr in zip(breakthroughs, cross) if cr]
    bx = [v[0] for v in valid]; cy = [v[1] for v in valid]
    ax.plot(bx, cy, "o-", color=COLORS["钙钛矿"], lw=2, ms=8, zorder=3)
    ax.plot([2027, 2045], [2027, 2045], "k:", lw=0.8, alpha=0.6, label="y = x")
    for x, y in zip(bx, cy):
        ax.annotate(f"{y}", (x, y), textcoords="offset points", xytext=(5, 5),
                    fontsize=7, color="#7a1f12")
    ax.set_xlabel("Perovskite lifetime breakthrough year (reaches 25 yr)", fontsize=9)
    ax.set_ylabel("Perovskite-beats-c-Si crossover year", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(b) Later breakthrough, later substitution", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="upper left", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    # ===== (c) LCOE 三因子分解 (寿命/退化/burn-in) =====
    ax = axes[2]
    # 基准: 钙钛矿 15yr 差版本 (deg 3%, burn 10%, life 15) → 逐步改善到 25yr 好版本
    cap_floor = 0.40
    base = lcoe_npv(cap_floor, y_perov, 15, 0.030, 0.10) * 100      # 全差
    step_life = lcoe_npv(cap_floor, y_perov, 25, 0.030, 0.10) * 100  # 只改寿命
    step_deg = lcoe_npv(cap_floor, y_perov, 25, 0.007, 0.10) * 100   # +改退化
    step_burn = lcoe_npv(cap_floor, y_perov, 25, 0.007, 0.03) * 100  # +改burn-in
    csi_ref = lcoe_npv(0.55, y_csi, 25, 0.007, 0.02) * 100
    # 瀑布: base → 寿命 → 退化 → burn-in
    contrib = [
        ("start\n15yr/3%/10%", base, "#cccccc"),
        ("+lifetime\n->25yr", base - step_life, COLORS["钙钛矿"]),
        ("+degr.\n->0.7%", step_life - step_deg, "#f0a868"),
        ("+burn-in\n->3%", step_deg - step_burn, "#f6d2a9"),
    ]
    cum = base
    ax.bar(0, base, color="#cccccc", width=0.6)
    ax.text(0, base+0.1, f"{base:.1f}", ha="center", fontsize=7)
    for i, (lbl, delta, col) in enumerate(contrib[1:], start=1):
        ax.bar(i, -delta, bottom=cum, color=col, width=0.6)
        ax.plot([i-0.3, i+0.3], [cum, cum], "k-", lw=0.5)
        cum -= delta
        ax.text(i, cum-0.25, f"-{delta:.1f}", ha="center", fontsize=6.5,
                color="#7a1f12")
    ax.bar(4, cum, color=COLORS["钙钛矿"], width=0.6, alpha=0.9)
    ax.text(4, cum+0.1, f"{cum:.1f}", ha="center", fontsize=7, fontweight="bold")
    ax.axhline(csi_ref, color=COLORS["晶硅"], ls="--", lw=1.2,
               label=f"c-Si {csi_ref:.1f}")
    ax.set_xticks(range(5))
    ax.set_xticklabels(["start\n15 yr", "+life", "+degr.", "+burn", "end\n25 yr"],
                       fontsize=7)
    ax.set_ylabel("NPV LCOE (cents/kWh)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(c) Lifetime dominates cost reduction", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="upper right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3, axis="y")

    fig.suptitle("Fig 2 — Lifetime gate: what truly governs substitution "
                 "(lifetime > cost)", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig2_lifetime_gate.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig2_lifetime_gate.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"\nMain Fig 2 saved. (c) lifetime contributes {base-step_life:.2f} cents/kWh "
          f"({(base-step_life)/(base-step_burn)*100:.0f}% of total reduction)")


if __name__ == "__main__":
    main()
