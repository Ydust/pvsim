"""Joule 规格技术替代主图 v2 — 注入分析空间.

v1 的问题: 单一确定性轨迹, 没有政策杠杆/不确定性可分析.
v2 改进: 3 情景包络 (保守/基线/激进) + panel (d) 替换为政策灵敏度热图.

4 子图:
  (a) Wright capex 三技, 基线 + 保守/激进 band
  (b) LCOE 三技 + 3 情景交叉年标尺
  (c) 替代 S 曲线 (钙钛矿份额), 三情景包络
  (d) 钙钛矿超晶硅年 vs (突破年 × LR) 热图 — 政策决策可读

数据: 同样以 30 省 PVGIS yield 物理加权.
运行: python -m scripts.portfolio_main_fig
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.provinces import PROVINCE_PV_2024_GW, PROVINCE_EN
from pvsim.policy_data import china_pv_target_gw

TECH_EN = {"晶硅": "c-Si", "钙钛矿": "Perovskite", "叠层": "Tandem"}
SC_EN = {"保守": "Conservative", "基线": "Baseline", "激进": "Aggressive"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

YEARS = np.arange(2025, 2051)
N = len(YEARS)
TECHS = ["晶硅", "钙钛矿", "叠层"]
COLORS = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
DISCOUNT = 0.05
OPEX = 0.015
MAX_DROP = 0.12
INIT_FLEET = 887.0
ROW_FACTOR = 0.4

# 三情景参数
SCENARIOS = {
    "保守": {
        "LR": {"晶硅": 0.15, "钙钛矿": 0.20, "叠层": 0.22},
        "CAPEX_FLOOR": {"晶硅": 0.45, "钙钛矿": 0.35, "叠层": 0.55},
        "BREAKTHROUGH": 2038,
    },
    "基线": {
        "LR": {"晶硅": 0.18, "钙钛矿": 0.27, "叠层": 0.30},
        "CAPEX_FLOOR": {"晶硅": 0.40, "钙钛矿": 0.40, "叠层": 0.50},
        "BREAKTHROUGH": 2032,
    },
    "激进": {
        "LR": {"晶硅": 0.22, "钙钛矿": 0.35, "叠层": 0.38},
        "CAPEX_FLOOR": {"晶硅": 0.35, "钙钛矿": 0.30, "叠层": 0.45},
        "BREAKTHROUGH": 2028,
    },
}
CAPEX_0 = {"晶硅": 0.65, "钙钛矿": 0.95, "叠层": 1.13}
Q_0 = {"晶硅": 1500.0, "钙钛矿": 12.0, "叠层": 4.0}
LIFE_0 = {"晶硅": 25.0, "钙钛矿": 15.0, "叠层": 25.0}
DEG_0 = {"晶硅": 0.007, "钙钛矿": 0.030, "叠层": 0.012}
BURN_0 = {"晶硅": 0.02, "钙钛矿": 0.10, "叠层": 0.04}


def perov_evolve(year, breakthrough, deg_final=0.007):
    """钙钛矿寿命/衰减/burn-in 在 2025 → breakthrough 年间线性演化."""
    if year >= breakthrough: f = 1.0
    elif year <= 2025: f = 0.0
    else: f = (year - 2025) / (breakthrough - 2025)
    return (15 + f * 10, 0.030 + f * (deg_final - 0.030),
            0.10 + f * (0.03 - 0.10))


def tech_year_params(tech, year, breakthrough, deg_final=0.007):
    if tech == "钙钛矿":
        return perov_evolve(year, breakthrough, deg_final)
    return LIFE_0[tech], DEG_0[tech], BURN_0[tech]


def max_new(tech, year):
    if tech == "晶硅": return 350
    if tech == "钙钛矿": return max(0, min(120, (year - 2024) * 12))
    if tech == "叠层": return max(0, min(180, (year - 2028) * 18))
    return 0


def init_present(year):
    if year < 2043: return INIT_FLEET
    if year > 2049: return 0.0
    return INIT_FLEET * (1 - (year - 2043) / 6)


def national_weighted_yield():
    df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    total = sum(PROVINCE_PV_2024_GW.values())
    yields = {}
    for tech in TECHS:
        sub = df[df["tech"] == tech]
        y = 0.0
        for _, r in sub.iterrows():
            w = PROVINCE_PV_2024_GW.get(r["province"], 0) / total
            y += r["yield_kwh_per_kwp"] * w
        yields[tech] = y
    return yields


def simulate_scenario(LR, CAPEX_FLOOR, BREAKTHROUGH, yields, deg_final_perov=0.007):
    B = {k: -np.log2(1 - v) for k, v in LR.items()}
    _, target = china_pv_target_gw(); target = target[1:]

    deploy = {k: np.zeros(N) for k in TECHS}
    capex_path = {k: np.zeros(N) for k in TECHS}
    lcoe_path = {k: np.zeros(N) for k in TECHS}
    cum_global = {k: Q_0[k] for k in TECHS}
    cap_eff = {k: CAPEX_0[k] for k in TECHS}

    for i, yr in enumerate(YEARS):
        for k in TECHS:
            raw = max(CAPEX_FLOOR[k],
                      CAPEX_0[k] * (max(cum_global[k], 0.1) / Q_0[k]) ** (-B[k]))
            if i == 0:
                cap_eff[k] = raw
            else:
                cap_eff[k] = max(cap_eff[k] * (1 - MAX_DROP), raw, CAPEX_FLOOR[k])
            capex_path[k][i] = cap_eff[k]

        for k in TECHS:
            life, deg, burn = tech_year_params(k, int(yr), BREAKTHROUGH,
                                                 deg_final_perov)
            crf = DISCOUNT * (1+DISCOUNT)**life / ((1+DISCOUNT)**life - 1)
            annual_yield = yields[k] * (1 - life*deg/2) / 1000.0
            lcoe_path[k][i] = cap_eff[k] * (crf + OPEX) / annual_yield

        op = {k: 0.0 for k in TECHS}
        for k in TECHS:
            for j in range(i):
                inst_yr = YEARS[j]
                L = tech_year_params(k, int(inst_yr), BREAKTHROUGH,
                                       deg_final_perov)[0]
                if yr - inst_yr < L:
                    op[k] += deploy[k][j]
        current_op_total = sum(op.values()) + init_present(yr)
        needed = max(0, target[i] - current_op_total)

        T = 0.8
        weights = {k: np.exp(-lcoe_path[k][i]*100 / T) for k in TECHS
                    if max_new(k, yr) > 0}
        wsum = sum(weights.values())
        targets = {k: needed * weights[k] / wsum for k in weights}
        leftover = 0.0
        for k in TECHS:
            cap_max = min(targets.get(k, 0) + leftover, max_new(k, yr))
            deploy[k][i] = cap_max
            leftover += targets.get(k, 0) - cap_max
        for k in TECHS:
            if leftover > 0.5 and deploy[k][i] < max_new(k, yr):
                extra = min(leftover, max_new(k, yr) - deploy[k][i])
                deploy[k][i] += extra; leftover -= extra
        for k in TECHS:
            cum_global[k] += deploy[k][i] * (1 + ROW_FACTOR)

    operating = {k: np.zeros(N) for k in TECHS}
    for k in TECHS:
        for i in range(N):
            for j in range(i + 1):
                inst_yr = YEARS[j]
                L = tech_year_params(k, int(inst_yr), BREAKTHROUGH,
                                       deg_final_perov)[0]
                if YEARS[i] - inst_yr < L:
                    operating[k][i] += deploy[k][j]

    # 交叉年
    cross_perov = next((int(YEARS[i]) for i in range(N)
                         if lcoe_path["钙钛矿"][i] < lcoe_path["晶硅"][i]), None)
    cross_tand = next((int(YEARS[i]) for i in range(N)
                        if (lcoe_path["叠层"][i] < lcoe_path["晶硅"][i]
                            and max_new("叠层", YEARS[i]) > 0)), None)
    return {
        "capex": capex_path, "lcoe": lcoe_path,
        "deploy": deploy, "operating": operating,
        "cross_perov": cross_perov, "cross_tand": cross_tand,
    }


def sensitivity_heatmap(yields):
    """钙钛矿超晶硅年 vs (突破年 × 钙钛矿突破后衰减率) 物理参数热图.

    衰减率是真实物理参数 (封装质量决定), 不是经济参数.
    范围 0.3-2.0%/yr 覆盖文献区间 (Oxford PV 0.5%/yr, IEC 61215 ~1%/yr 上限).
    """
    breakthrough_grid = np.arange(2026, 2043, 2)         # 9 值
    deg_grid = np.arange(0.003, 0.021, 0.002)             # 9 值 (0.3% → 2.0%/yr)
    Z = np.full((len(deg_grid), len(breakthrough_grid)), np.nan)
    base_lr = {"晶硅": 0.18, "钙钛矿": 0.27, "叠层": 0.30}
    base_floor = {"晶硅": 0.40, "钙钛矿": 0.40, "叠层": 0.50}
    for i, by in enumerate(breakthrough_grid):
        for j, deg in enumerate(deg_grid):
            res = simulate_scenario(base_lr, base_floor, int(by), yields,
                                     deg_final_perov=float(deg))
            Z[j, i] = res["cross_perov"] if res["cross_perov"] else 2051
    return breakthrough_grid, deg_grid, Z


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    yields = national_weighted_yield()
    print(f"  加权全国 yield (kWh/kWp): "
          f"晶硅 {yields['晶硅']:.0f} / 钙钛矿 {yields['钙钛矿']:.0f} "
          f"/ 叠层 {yields['叠层']:.0f}")

    print("\n[1/3] 跑 3 情景前向模拟...")
    results = {}
    for name, sc in SCENARIOS.items():
        results[name] = simulate_scenario(sc["LR"], sc["CAPEX_FLOOR"],
                                           sc["BREAKTHROUGH"], yields)
        r = results[name]
        tot50 = sum(r["operating"][k][-1] for k in TECHS) + init_present(2050)
        print(f"  {name}: 交叉 钙{r['cross_perov']}/叠{r['cross_tand']}, "
              f"2050 份额 (晶/钙/叠) "
              f"{r['operating']['晶硅'][-1]/tot50*100:.0f}/"
              f"{r['operating']['钙钛矿'][-1]/tot50*100:.0f}/"
              f"{r['operating']['叠层'][-1]/tot50*100:.0f}%")

    print("\n[2/3] 跑灵敏度热图 9 × 11 = 99 次...")
    by_grid, lr_grid, Z = sensitivity_heatmap(yields)
    print(f"  钙钛矿超晶硅年范围: {np.nanmin(Z):.0f} - {np.nanmax(Z):.0f}")

    print("\n[3/3] 出 Joule 主图 v2 (5×4 inch, 300 dpi)...")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), dpi=300)

    # ===== (a) Capex Wright + 情景 band =====
    ax = axes[0, 0]
    for k in TECHS:
        cons = results["保守"]["capex"][k]
        base = results["基线"]["capex"][k]
        aggr = results["激进"]["capex"][k]
        lo = np.minimum(cons, aggr); hi = np.maximum(cons, aggr)
        ax.fill_between(YEARS, lo, hi, color=COLORS[k], alpha=0.18, linewidth=0)
        ax.plot(YEARS, base, color=COLORS[k], lw=1.4, label=TECH_EN[k])
        ax.plot(YEARS, cons, color=COLORS[k], lw=0.6, ls=":", alpha=0.7)
        ax.plot(YEARS, aggr, color=COLORS[k], lw=0.6, ls=":", alpha=0.7)
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("System capex (US$/W)", fontsize=9)
    ax.tick_params(labelsize=8, length=3)
    ax.set_title("(a) Wright curve + scenario band", fontsize=10, fontweight="bold",
                  loc="left", pad=2)
    ax.legend(fontsize=7.5, loc="upper right", frameon=False, handlelength=1.5,
               labelspacing=0.3)
    ax.grid(alpha=0.25, lw=0.3); ax.set_xticks([2025, 2035, 2045])
    ax.set_xlim(2025, 2050)

    # ===== (b) LCOE 国家均线 + 30 省物理云 =====
    ax = axes[0, 1]
    # 加载省级物理 LCOE (来自 portfolio_physics 30 省 × De Soto × 8760h)
    province_lcoe = pd.read_csv("outputs/province_physics_lcoe.csv",
                                  encoding="utf-8-sig")
    # 30 省淡线 (物理异质性)
    for tech in TECHS:
        sub = province_lcoe[province_lcoe["tech"] == tech]
        for prov in sub["province"].unique():
            ps = sub[sub["province"] == prov].sort_values("year")
            ys = ps["lcoe_cents_per_kwh"].values
            if tech == "叠层":
                mask = np.array([max_new(tech, yr) > 0 for yr in ps["year"]])
                ys = np.where(mask, ys, np.nan)
            ax.plot(ps["year"], ys, color=COLORS[tech],
                    alpha=0.10, lw=0.35, zorder=2)
    # 基线国家均线 (粗) 叠在上面
    for k in TECHS:
        base = results["基线"]["lcoe"][k] * 100
        if k == "叠层":
            mask = np.array([max_new(k, yr) > 0 for yr in YEARS])
            base = np.where(mask, base, np.nan)
        ax.plot(YEARS, base, color=COLORS[k], lw=1.4, label=TECH_EN[k], zorder=4)
    # annotate lowest/highest 3 provinces by 2050 perovskite LCOE (physical extremes)
    p2050 = province_lcoe[(province_lcoe["tech"] == "钙钛矿") &
                           (province_lcoe["year"] == 2050)].copy()
    p2050 = p2050.sort_values("lcoe_cents_per_kwh")
    lo3 = p2050.head(3)    # cheapest (high-irradiance west)
    hi3 = p2050.tail(3)    # priciest (SW cloudy)
    # staggered ladders to avoid label overlap (values are close within each group)
    for (_, r), ytxt in zip(hi3.iterrows(), [5.0, 4.4, 3.8]):
        ax.annotate(f"{PROVINCE_EN.get(r['province'], r['province'])} {r['lcoe_cents_per_kwh']:.1f}",
                     xy=(2050, r["lcoe_cents_per_kwh"]),
                     xytext=(2040.5, ytxt),
                     fontsize=5.5, color="#7a3410", ha="left",
                     arrowprops=dict(arrowstyle="-", color="#e2641e",
                                      lw=0.35, alpha=0.7))
    for (_, r), ytxt in zip(lo3.iterrows(), [1.05, 0.62, 0.2]):
        ax.annotate(f"{PROVINCE_EN.get(r['province'], r['province'])} {r['lcoe_cents_per_kwh']:.1f}",
                     xy=(2050, r["lcoe_cents_per_kwh"]),
                     xytext=(2040.5, ytxt),
                     fontsize=5.5, color="#7a3410", ha="left",
                     arrowprops=dict(arrowstyle="-", color="#e2641e",
                                      lw=0.35, alpha=0.7))
    # three-scenario perovskite-beats-c-Si crossover ruler (compact, upper-middle)
    cyears = {name: results[name]["cross_perov"] for name in ("保守", "基线", "激进")}
    xs = [cyears[n] for n in ("激进", "基线", "保守") if cyears[n]]
    if xs:
        yr_line = 8.5
        ax.plot([min(xs)-0.4, max(xs)+0.4], [yr_line, yr_line],
                color="#999999", lw=0.8, zorder=4)
        for name, mk in [("激进", "^"), ("基线", "o"), ("保守", "v")]:
            if cyears[name]:
                ax.scatter(cyears[name], yr_line, marker=mk, s=20,
                           color=COLORS["钙钛矿"], edgecolors="black",
                           linewidth=0.4, zorder=5)
        xc = (min(xs) + max(xs)) / 2
        ax.text(xc, yr_line + 0.45, "Perovskite beats c-Si", fontsize=6,
                ha="center", fontweight="bold", color=COLORS["钙钛矿"])
        ax.text(xc, yr_line - 0.62,
                f"Aggr {cyears['激进']} · Base {cyears['基线']} · Cons {cyears['保守']}",
                fontsize=5.5, ha="center", color="#555555")
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("LCOE (cents/kWh)", fontsize=9)
    ax.tick_params(labelsize=8, length=3)
    ax.set_title("(b) LCOE: 30-province physics cloud + national mean", fontsize=8,
                  fontweight="bold", loc="left", pad=2)
    ax.legend(fontsize=7, loc="upper right", frameon=False, handlelength=1.3,
               labelspacing=0.25)
    ax.grid(alpha=0.25, lw=0.3); ax.set_xticks([2025, 2035, 2045])
    ax.set_xlim(2025, 2050); ax.set_ylim(0, 9.5)

    # ===== (c) 钙钛矿份额 S 曲线 (三情景包络) =====
    ax = axes[1, 0]
    for k in TECHS:
        for name, ls, lw in [("保守", ":", 0.7), ("基线", "-", 1.4),
                              ("激进", "-.", 0.9)]:
            d = results[name]["deploy"]
            total = sum(d[t] for t in TECHS)
            share = np.where(total > 0, d[k] / np.maximum(total, 1e-9), 0) * 100
            ax.plot(YEARS, share, color=COLORS[k], lw=lw, ls=ls,
                    label=TECH_EN[k] if name == "基线" else None)
    # line-style legend box
    ax.text(2026, 90, "solid = Baseline\ndotted = Conservative\ndash-dot = Aggressive",
            fontsize=5, va="top", color="dimgray",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="lightgray",
                       lw=0.4, alpha=0.85))
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("Annual new-build share (%)", fontsize=9)
    ax.tick_params(labelsize=8, length=3)
    ax.set_title("(c) Substitution share S-curves", fontsize=8,
                  fontweight="bold", loc="left", pad=2)
    ax.legend(fontsize=7.5, loc="center right", frameon=False,
               handlelength=1.5, labelspacing=0.3)
    ax.set_xticks([2025, 2035, 2045]); ax.set_xlim(2025, 2050)
    ax.set_ylim(0, 100); ax.grid(alpha=0.25, lw=0.3)

    # ===== (d) 钙→晶替代年 vs (突破年 × 钙钛矿物理衰减率) 热图 =====
    ax = axes[1, 1]
    by_grid, deg_grid, Zphys = by_grid, lr_grid, Z   # alias from above
    Zm = np.where(Zphys >= 2051, np.nan, Zphys)
    deg_pct = deg_grid * 100   # 0.3%-2.0%/yr
    im = ax.imshow(Zm, aspect="auto", origin="lower", cmap="RdYlGn_r",
                    extent=[by_grid[0]-1, by_grid[-1]+1,
                            deg_pct[0]-0.1, deg_pct[-1]+0.1],
                    vmin=2026, vmax=2045)
    BY, DEG_g = np.meshgrid(by_grid, deg_pct)
    cs = ax.contour(BY, DEG_g, Zm, levels=[2028, 2032, 2036, 2040],
                     colors="black", linewidths=0.5, alpha=0.75)
    ax.clabel(cs, inline=True, fontsize=6, fmt="%d")
    # 文献参考线: Oxford PV 0.5%/yr, IEC 61215 上限 ~1%/yr
    ax.axhline(0.5, color="white", ls="-", lw=0.7, alpha=0.7)
    ax.text(2041, 0.55, "Oxford PV 0.5%/yr", fontsize=6, color="white",
            ha="right", style="italic")
    ax.axhline(1.0, color="white", ls=":", lw=0.6, alpha=0.6)
    ax.text(2041, 1.05, "IEC 61215 ~1%/yr", fontsize=6, color="white",
            ha="right", style="italic")
    # mark 3 scenario positions (baseline deg = 0.7%/yr)
    for name, mk in [("保守", "v"), ("基线", "o"), ("激进", "^")]:
        sc = SCENARIOS[name]
        ax.scatter(sc["BREAKTHROUGH"], 0.7,
                    marker=mk, s=35, color="white", edgecolors="black",
                    linewidth=0.6, zorder=4)
        ax.annotate(SC_EN[name], (sc["BREAKTHROUGH"], 0.7),
                     textcoords="offset points", xytext=(4, 4), fontsize=6,
                     color="black", fontweight="bold")
    ax.set_xlabel("Perovskite lifetime breakthrough year", fontsize=9)
    ax.set_ylabel("Post-breakthrough degradation (%/yr)", fontsize=9)
    ax.tick_params(labelsize=8, length=3)
    ax.set_title("(d) Crossover year vs physical params", fontsize=10,
                  fontweight="bold", loc="left", pad=2)
    cb = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label("Perovskite-beats-c-Si year", fontsize=8); cb.ax.tick_params(labelsize=6.5)

    fig.tight_layout(pad=0.6, w_pad=1.0, h_pad=0.8)
    fig.savefig("outputs/figures/Main_substitution.png", dpi=300,
                 bbox_inches="tight")
    fig.savefig("outputs/figures/Main_substitution.pdf",
                 bbox_inches="tight")
    plt.close(fig)
    print("  → Main_substitution.png (5×4 inch, 300 dpi)")
    print("  → Main_substitution.pdf (vector)")


if __name__ == "__main__":
    main()
