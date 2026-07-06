"""物理引擎驱动的技术替代分析 (C 路线 v3)。

跟 portfolio_substitution.py (玩具 Wright + 软最大熵) 的区别:
  - 玩具版用全国均值 YIELD, 假设 tandem 每 kWp 高产 → 错!
  - 本版用 pvsim 全栈物理: De Soto + Faiman 温度 + 光谱失配 + 退化 + 滞回,
    在 12 个真实城市 TMY 上跑 8760 小时仿真.

关键暴露的物理事实 (玩具 Wright 看不到):
  1. 同 kWp 下 tandem 跟 c-Si 收益几乎一样 (单位 kW/m² 决定 kWp)
  2. tandem 真正优势在 rooftop (面积约束): kWh/m² 1.87× c-Si
  3. perov 温度优势在热带 (γ=-0.15 vs c-Si -0.45): 海口 +7.5% yield
  4. 替代地理: 南方钙钛矿 (温度赢) 早, tandem 在 rooftop 段早, c-Si 北方持续

运行: python -m scripts.portfolio_physics
输出: outputs/figures/37_*..41_*.png + outputs/portfolio_physics_results.csv
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.materials import CSI_EARLY, PEROVSKITE, TANDEM_2T
from pvsim.cities import CITIES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TECHS = [("c-Si", "晶硅", CSI_EARLY), ("perovskite", "钙钛矿", PEROVSKITE),
         ("tandem", "叠层", TANDEM_2T)]
COLORS = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
YEARS = np.arange(2025, 2051)
N = len(YEARS)

# Wright 学习曲线参数 (与 portfolio_substitution.py 一致)
LR = {"晶硅": 0.18, "钙钛矿": 0.22, "叠层": 0.24}
B = {k: -np.log2(1 - v) for k, v in LR.items()}
CAPEX_0 = {"晶硅": 0.65, "钙钛矿": 0.95, "叠层": 1.13}    # $/W 系统
Q_0 = {"晶硅": 1500.0, "钙钛矿": 5.0, "叠层": 1.0}      # GW 全球
CAPEX_FLOOR = {"晶硅": 0.40, "钙钛矿": 0.40, "叠层": 0.50}
MAX_DROP = 0.12
DISCOUNT = 0.05
OPEX = 0.015

# 退化率 (取自材料定义) — 钙钛矿随研发突破线性演化
DEG_0 = {"晶硅": CSI_EARLY.degradation_rate,
         "钙钛矿": PEROVSKITE.degradation_rate,      # 3%/yr 起步
         "叠层": TANDEM_2T.degradation_rate}
DEG_FINAL_PEROV = 0.007                              # 突破后接近 c-Si
BURN_0 = {"晶硅": CSI_EARLY.burn_in_loss,
          "钙钛矿": PEROVSKITE.burn_in_loss,         # 10% 起步
          "叠层": TANDEM_2T.burn_in_loss}
BURN_FINAL_PEROV = 0.03                              # 突破后封装改善
LIFE_0 = {"晶硅": 25.0, "钙钛矿": 15.0, "叠层": 25.0}
LIFE_FINAL_PEROV = 25.0
BREAKTHROUGH_YEAR = 2032                             # 钙钛矿寿命/衰减突破达成


def perov_evolve(year, breakthrough_year=BREAKTHROUGH_YEAR):
    """钙钛矿寿命/衰减/burn-in 随研发突破年线性演化."""
    if year >= breakthrough_year:
        f = 1.0
    elif year <= 2025:
        f = 0.0
    else:
        f = (year - 2025) / (breakthrough_year - 2025)
    return {
        "life": LIFE_0["钙钛矿"] + f * (LIFE_FINAL_PEROV - LIFE_0["钙钛矿"]),
        "deg": DEG_0["钙钛矿"] + f * (DEG_FINAL_PEROV - DEG_0["钙钛矿"]),
        "burn": BURN_0["钙钛矿"] + f * (BURN_FINAL_PEROV - BURN_0["钙钛矿"]),
    }


def tech_year_params(tech, year):
    """给定技 + 年, 返回 (life, deg, burn)."""
    if tech == "钙钛矿":
        e = perov_evolve(year)
        return e["life"], e["deg"], e["burn"]
    return LIFE_0[tech], DEG_0[tech], BURN_0[tech]


def yield_physics_year0():
    """对 12 个城市 × 3 技, 用 pvsim 全栈物理跑 8760h, 得到第 0 年的 kWp/yield/cell-T."""
    print("[1/4] 物理仿真: 12 城 × 3 技 × 8760h...")
    cfg = SystemConfig(n_modules=20)
    results = []
    for city in CITIES:
        w = wx.from_pvgis_tmy(city.lat, city.lon, altitude=city.alt, name=city.key)
        tair_mean = float(w["temp_air"].mean())
        ghi_total = float(w["ghi"].sum() / 1000.0)    # kWh/m²
        for code, name, tech in TECHS:
            r = simulate(tech, w, cfg, npts=60)
            ts = r["timeseries"]
            poa = ts["poa_global"].to_numpy(); tcell = ts["tcell"].to_numpy()
            sf = ts["spectral_factor"].to_numpy()
            m = poa > 50
            tcell_w = float(np.average(tcell[m], weights=poa[m])) if m.any() else np.nan
            sf_w = float(np.average(sf[m], weights=poa[m])) if m.any() else np.nan
            # 每 m² 年发电 (kWh/m²/yr) — 用于面积约束应用 (rooftop)
            area_m2 = 20 * tech.cells_in_series * tech.area_cm2 * 1e-4  # 20 modules
            kwh_per_m2 = r["energy_ac_kwh"] / area_m2
            results.append({
                "city": city.name, "key": city.key, "lat": city.lat, "alt": city.alt,
                "tech": name, "code": code,
                "kwp": r["kwp"],
                "yield_kwh_per_kwp": r["specific_yield"],
                "yield_kwh_per_m2": kwh_per_m2,
                "PR": r["performance_ratio"],
                "tcell_weighted": tcell_w,
                "spectral_factor_w": sf_w,
                "ghi_kwh_m2": ghi_total,
                "tair_mean": tair_mean,
            })
        print(f"  {city.name:5s}: c-Si {results[-3]['yield_kwh_per_kwp']:.0f} | "
              f"perov {results[-2]['yield_kwh_per_kwp']:.0f} | "
              f"tandem {results[-1]['yield_kwh_per_kwp']:.0f} kWh/kWp")
    return pd.DataFrame(results)


def capex_path_global(deployment):
    """Wright + 年降幅封顶, 返回 26 年 capex 轨迹.

    deployment: dict {tech: array(N) of GW/yr China deploy} — 此处用简化恒定增长.
    """
    cum = {k: Q_0[k] for k in CAPEX_0}
    cap_eff = {k: CAPEX_0[k] for k in CAPEX_0}
    path = {k: np.zeros(N) for k in CAPEX_0}
    for i in range(N):
        for k in CAPEX_0:
            raw = max(CAPEX_FLOOR[k],
                      CAPEX_0[k] * (max(cum[k], 0.1) / Q_0[k]) ** (-B[k]))
            if i == 0:
                cap_eff[k] = raw
            else:
                min_allowed = cap_eff[k] * (1 - MAX_DROP)
                cap_eff[k] = max(min_allowed, raw, CAPEX_FLOOR[k])
            path[k][i] = cap_eff[k]
            cum[k] += deployment.get(k, np.zeros(N))[i] * 1.4   # +ROW factor
    return path


def lcoe_npv(capex_per_w, yield_kwh_per_kwp, life, deg_rate, burn_in):
    """真实 NPV 折现的 LCOE (用全寿命年度发电流, 非线性退化).

    Y(t) = Y_0 × (1 - burn_in if t==1) × (1-deg)^t
    LCOE = (capex + Σ opex × capex / (1+r)^t) / Σ Y(t) / (1+r)^t
    """
    years = np.arange(1, int(life) + 1)
    df = (1 + DISCOUNT) ** -years
    yield_factor = (1 - burn_in) * (1 - deg_rate) ** (years - 1)
    yield_factor[0] = (1 - burn_in)    # 第 1 年只扣 burn-in
    yields = yield_kwh_per_kwp * yield_factor    # kWh/kWp/yr
    npv_yield = np.sum(yields * df)   # kWh/kWp NPV
    npv_cost = capex_per_w * 1000 + np.sum(capex_per_w * 1000 * OPEX * df)  # $/kWp
    return npv_cost / npv_yield      # $/kWh


def build_city_year_lcoe(yield_df):
    """每城市 × 每技 × 26 年 LCOE 矩阵 (utility-scale, kWp-based)."""
    print("\n[2/4] LCOE 矩阵 (12 城 × 3 技 × 26 年)...")
    # 部署轨迹 (估算, 实际可耦合到 portfolio_substitution)
    base_dep = {"晶硅": np.linspace(80, 30, N) + np.linspace(0, 20, N),
                "钙钛矿": np.minimum(np.arange(N) * 4 + 5, 100),
                "叠层": np.maximum(0, np.minimum(np.arange(N) * 3 - 12, 80))}
    cap_path = capex_path_global(base_dep)

    rows = []
    for _, row in yield_df.iterrows():
        for i, yr in enumerate(YEARS):
            cap = cap_path[row["tech"]][i]
            life, deg, burn = tech_year_params(row["tech"], int(yr))
            lc = lcoe_npv(cap, row["yield_kwh_per_kwp"], life, deg, burn)
            # rooftop 模式: 把 yield 改成 kWh/m² → 等价于 capex/m²
            cap_per_m2 = cap * 1000 * (row["kwp"] / (20 * row["tech_area_m2"] if "tech_area_m2" in row else 1))
            rows.append({
                "city": row["city"], "key": row["key"], "tech": row["tech"],
                "year": int(yr), "capex_usd_per_w": cap,
                "lcoe_utility_cents_per_kwh": lc * 100,
                "yield_kwh_per_kwp_year0": row["yield_kwh_per_kwp"],
                "yield_kwh_per_m2_year0": row["yield_kwh_per_m2"],
                "tcell_weighted": row["tcell_weighted"],
            })
    df = pd.DataFrame(rows)
    print(f"  生成 {len(df)} 行 (12×3×26)")
    return df, cap_path


def find_substitution_year(lcoe_df):
    """每城市 × 'src→dst' 替代年: dst LCOE 首次低于 src 的年份."""
    print("\n[3/4] 替代年逐城判定...")
    out = []
    for city in lcoe_df["city"].unique():
        d = lcoe_df[lcoe_df["city"] == city].pivot(index="year", columns="tech",
                                                    values="lcoe_utility_cents_per_kwh")
        crosses = {}
        for src, dst in [("晶硅", "钙钛矿"), ("晶硅", "叠层"), ("钙钛矿", "叠层")]:
            mask = d[dst] < d[src]
            if mask.any():
                crosses[f"{dst}超{src}"] = int(d.index[mask][0])
            else:
                crosses[f"{dst}超{src}"] = None
        row = {"city": city}; row.update(crosses)
        out.append(row)
    return pd.DataFrame(out)


def plot_fig37_temperature_advantage(yield_df):
    """Fig 37: 物理引擎驱动的'温度优势地图'."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8))
    pivot_y = yield_df.pivot(index="city", columns="tech", values="yield_kwh_per_kwp")
    pivot_t = yield_df.pivot(index="city", columns="tech", values="tcell_weighted")
    pivot_y = pivot_y.reindex(yield_df.groupby("city")["tcell_weighted"].first().sort_values().index)
    pivot_t = pivot_t.loc[pivot_y.index]

    # (a) yield 差: 钙钛矿/叠层 vs c-Si, 随平均工作温度
    ax = axes[0]
    tc = pivot_t["晶硅"].values
    perov_adv = (pivot_y["钙钛矿"] / pivot_y["晶硅"] - 1) * 100
    tand_adv = (pivot_y["叠层"] / pivot_y["晶硅"] - 1) * 100
    ax.scatter(tc, perov_adv, s=110, color=COLORS["钙钛矿"], label="钙钛矿 vs 晶硅", zorder=3)
    ax.scatter(tc, tand_adv, s=110, color=COLORS["叠层"], label="叠层 vs 晶硅", zorder=3, marker="s")
    for city, x, y in zip(pivot_y.index, tc, perov_adv):
        ax.annotate(city, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    # 趋势线
    for advs, col in [(perov_adv.values, COLORS["钙钛矿"]),
                       (tand_adv.values, COLORS["叠层"])]:
        z = np.polyfit(tc, advs, 1)
        xx = np.linspace(tc.min(), tc.max(), 50)
        ax.plot(xx, np.polyval(z, xx), "--", color=col, alpha=0.6,
                label=f"  斜率 {z[0]:+.3f}%/°C")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("辐照加权电池温度 (°C)")
    ax.set_ylabel("yield 优势 vs 晶硅 (%)")
    ax.set_title("(a) 温度系数差导致的 yield 优势 (物理 8760h 模拟)", fontweight="bold")
    ax.grid(alpha=0.3); ax.legend(loc="upper left", fontsize=9)

    # (b) yield per m² (面积约束 / rooftop): tandem 真正优势
    ax = axes[1]
    pivot_m2 = yield_df.pivot(index="city", columns="tech",
                               values="yield_kwh_per_m2").loc[pivot_y.index]
    x = np.arange(len(pivot_m2)); bw = 0.27
    ax.bar(x - bw, pivot_m2["晶硅"], width=bw, color=COLORS["晶硅"], label="晶硅 (η=15.3%)")
    ax.bar(x, pivot_m2["钙钛矿"], width=bw, color=COLORS["钙钛矿"], label="钙钛矿 (η=19.3%)")
    ax.bar(x + bw, pivot_m2["叠层"], width=bw, color=COLORS["叠层"], label="叠层 (η=28.3%)")
    ax.set_xticks(x); ax.set_xticklabels(pivot_m2.index, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("年发电 (kWh/m²)")
    ax.set_title("(b) 面积归一: rooftop 场景叠层真正优势 (1.87× c-Si)",
                 fontweight="bold")
    ax.legend(loc="upper left", fontsize=9); ax.grid(alpha=0.3, axis="y")

    fig.suptitle("物理引擎揭示: utility 与 rooftop 替代逻辑不同",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/37_physics_temperature_advantage.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)


def plot_fig38_spectral_mismatch(yield_df):
    """Fig 38: 光谱失配因子地图 — 三技在各城市的光谱响应损失."""
    fig, ax = plt.subplots(figsize=(13, 5.5))
    pivot = yield_df.pivot(index="city", columns="tech", values="spectral_factor_w")
    pivot_t = yield_df.pivot(index="city", columns="tech", values="tcell_weighted")
    order = pivot_t["晶硅"].sort_values().index
    pivot = pivot.loc[order]
    x = np.arange(len(pivot)); bw = 0.27
    ax.bar(x - bw, pivot["晶硅"], width=bw, color=COLORS["晶硅"], label="晶硅 (350-1110nm)")
    ax.bar(x, pivot["钙钛矿"], width=bw, color=COLORS["钙钛矿"], label="钙钛矿 (350-800nm, 窄)")
    ax.bar(x + bw, pivot["叠层"], width=bw, color=COLORS["叠层"], label="叠层 (350-1110nm, 串)")
    ax.axhline(1.0, color="gray", ls=":", lw=1, alpha=0.7, label="STC 基准 (AM1.5G)")
    ax.set_xticks(x); ax.set_xticklabels(pivot.index, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("辐照加权光谱因子 (实际光谱 / AM1.5G)")
    ax.set_title("光谱失配地图: 钙钛矿窄带隙在偏蓝光谱中得益, 叠层串联约束损失互补",
                 fontweight="bold")
    ax.set_ylim(pivot.values.min() * 0.99, pivot.values.max() * 1.01)
    ax.legend(loc="lower right", fontsize=9); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig("outputs/figures/38_physics_spectral.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def plot_fig39_city_lcoe_evolution(lcoe_df):
    """Fig 39: 6 个代表城市 LCOE 时间演化 (utility-scale)."""
    sel = ["拉萨", "敦煌", "北京", "上海", "广州", "海口"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), sharey=True)
    axes = axes.flatten()
    for ax, city in zip(axes, sel):
        d = lcoe_df[lcoe_df["city"] == city]
        for tech in ["晶硅", "钙钛矿", "叠层"]:
            sub = d[d["tech"] == tech].sort_values("year")
            ax.plot(sub["year"], sub["lcoe_utility_cents_per_kwh"],
                    lw=2.2, color=COLORS[tech], label=tech)
        ax.set_title(city, fontweight="bold")
        ax.grid(alpha=0.3); ax.set_xlim(2025, 2050)
        ax.set_xlabel("年"); ax.set_ylabel("LCOE 分/kWh")
    axes[0].legend(loc="upper right", fontsize=9)
    fig.suptitle("城市级 LCOE 演化 (物理引擎 yield + Wright capex + NPV 折现)",
                 fontweight="bold", y=1.00)
    fig.tight_layout()
    fig.savefig("outputs/figures/39_physics_city_lcoe.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def plot_fig40_substitution_map(cross_df, yield_df, lcoe_df):
    """Fig 40: 2050 LCOE 地理分布 + 各年代最便宜技术地图 (12 城)."""
    coords = {c.name: (c.lon, c.lat) for c in CITIES}

    # 2050 LCOE 数据
    d2050 = lcoe_df[lcoe_df["year"] == 2050].pivot(
        index="city", columns="tech", values="lcoe_utility_cents_per_kwh")
    d2050["best_lcoe"] = d2050.min(axis=1)
    d2050["best_tech"] = d2050[["晶硅", "钙钛矿", "叠层"]].idxmin(axis=1)
    d2050 = d2050.reset_index()
    d2050["lon"] = d2050["city"].map(lambda c: coords[c][0])
    d2050["lat"] = d2050["city"].map(lambda c: coords[c][1])

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # (a) 2050 LCOE 最低值 (颜色) — 显示地理 LCOE 景观
    ax = axes[0]
    sc = ax.scatter(d2050["lon"], d2050["lat"], c=d2050["best_lcoe"],
                    s=300, cmap="viridis_r", vmin=1.8, vmax=4.0,
                    edgecolors="black", linewidth=0.9, zorder=3)
    for _, r in d2050.iterrows():
        ax.annotate(f"{r['city']}\n{r['best_lcoe']:.2f}¢",
                    (r["lon"], r["lat"]), textcoords="offset points",
                    xytext=(8, 5), fontsize=9, fontweight="bold")
    ax.set_xlabel("经度 (°E)"); ax.set_ylabel("纬度 (°N)")
    ax.set_title("(a) 2050 最优 LCOE 地理分布 (分/kWh)", fontweight="bold")
    ax.set_xlim(80, 135); ax.set_ylim(18, 50); ax.grid(alpha=0.3)
    plt.colorbar(sc, ax=ax, label="LCOE (分/kWh)")

    # (b) 2050 最便宜技术 — 显示终态主导技术
    ax = axes[1]
    tech_color = {"晶硅": COLORS["晶硅"], "钙钛矿": COLORS["钙钛矿"], "叠层": COLORS["叠层"]}
    for tech in ["晶硅", "钙钛矿", "叠层"]:
        sub = d2050[d2050["best_tech"] == tech]
        if len(sub) > 0:
            ax.scatter(sub["lon"], sub["lat"], c=tech_color[tech], s=350,
                       edgecolors="black", linewidth=0.9, zorder=3,
                       label=f"{tech} 最优 ({len(sub)} 城)")
    for _, r in d2050.iterrows():
        margin = (r["晶硅"] - r["best_lcoe"]) / r["best_lcoe"] * 100
        ax.annotate(f"{r['city']}\n{r['best_tech']}\n(-{margin:.0f}% vs 晶硅)",
                    (r["lon"], r["lat"]), textcoords="offset points",
                    xytext=(8, 5), fontsize=8, fontweight="bold")
    ax.set_xlabel("经度 (°E)"); ax.set_ylabel("纬度 (°N)")
    ax.set_title("(b) 2050 各城市最便宜技术 (utility-scale)", fontweight="bold")
    ax.set_xlim(80, 135); ax.set_ylim(18, 50); ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    fig.suptitle("2050 终态: 物理 LCOE 地理景观 + 最优技术分布",
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig("outputs/figures/40_physics_2050_landscape.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)


def plot_fig41_rooftop_vs_utility(yield_df, lcoe_df):
    """Fig 41: rooftop (area-priced) vs utility (kWp-priced) 替代逻辑对比."""
    # rooftop LCOE: capex × area / yield_per_m²
    # 简化: 用同 area, capex_per_m² ∝ capex_per_W × η × 1000 W/m²
    # → 即 LCOE_rooftop = capex_per_W × CRF / yield_kwh_per_kwp × 1 (相同 per_kWp scale)
    # 但当成本归算到 per-m² (土地/屋顶约束), 叠层因为效率高 → 同 capex 更多电
    # 真实: rooftop LCOE = (cap_per_m² × CRF + opex × cap_per_m²) / yield_per_m²
    # cap_per_m² = capex_per_W × η_STC × 1000 (η 高 → 同 m² 更高额定)
    # 实际钱: capex_per_kWp 不变, 但单位 m² 装机量增加 → 单位面积总 capex 增加
    # rooftop 实际是按 m² 算建造成本约束 → tandem 在该域真正赢

    cfg = SystemConfig(n_modules=20)
    # 取代表城市
    sel_cities = ["拉萨", "海口"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    for ax, city in zip(axes, sel_cities):
        # 提取每技 LCOE 演化 (utility 和 rooftop)
        for tech_name in ["晶硅", "钙钛矿", "叠层"]:
            tech_data = yield_df[(yield_df["city"] == city) &
                                 (yield_df["tech"] == tech_name)].iloc[0]
            lc_data = lcoe_df[(lcoe_df["city"] == city) &
                              (lcoe_df["tech"] == tech_name)].sort_values("year")
            cap_path = lc_data["capex_usd_per_w"].values

            util_lcoe = lc_data["lcoe_utility_cents_per_kwh"].values
            # rooftop: scale capex by η ratio (实际同面积更高总 capex)
            #   cap_per_m² = cap_per_W × η_STC × 1000 (W/m²)
            #   yield_per_m² 已物理算出
            eta_rel = {"晶硅": 0.153, "钙钛矿": 0.193, "叠层": 0.283}[tech_name]
            cap_per_m2 = cap_path * eta_rel * 1000   # $/m²
            life_t, deg_t, _ = tech_year_params(tech_name, 2040)   # 用中点
            crf = DISCOUNT * (1 + DISCOUNT) ** life_t / \
                  ((1 + DISCOUNT) ** life_t - 1)
            yield_m2 = tech_data["yield_kwh_per_m2"] * \
                       (1 - life_t * deg_t / 2)
            roof_lcoe = cap_per_m2 * (crf + OPEX) / yield_m2 * 100  # cents/kWh
            ax.plot(lc_data["year"], util_lcoe, "-", color=COLORS[tech_name], lw=2,
                    label=f"{tech_name} utility")
            ax.plot(lc_data["year"], roof_lcoe, "--", color=COLORS[tech_name], lw=2,
                    alpha=0.7, label=f"{tech_name} rooftop")
        ax.set_title(f"{city}", fontweight="bold")
        ax.set_xlabel("年"); ax.set_ylabel("LCOE (分/kWh)")
        ax.grid(alpha=0.3); ax.legend(loc="upper right", fontsize=8)

    fig.suptitle("rooftop (面积约束) vs utility (kWp 约束): 替代逻辑不同",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/41_physics_rooftop_vs_utility.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)


def main():
    viz.setup()
    os.makedirs("outputs/figures", exist_ok=True)

    yield_df = yield_physics_year0()
    yield_df.to_csv("outputs/portfolio_physics_yield.csv", index=False,
                    encoding="utf-8-sig")

    lcoe_df, cap_path = build_city_year_lcoe(yield_df)
    lcoe_df.to_csv("outputs/portfolio_physics_lcoe.csv", index=False,
                   encoding="utf-8-sig")

    cross_df = find_substitution_year(lcoe_df)
    cross_df.to_csv("outputs/portfolio_physics_crossover.csv", index=False,
                    encoding="utf-8-sig")

    print("\n[4/4] 出图...")
    plot_fig37_temperature_advantage(yield_df)
    plot_fig38_spectral_mismatch(yield_df)
    plot_fig39_city_lcoe_evolution(lcoe_df)
    plot_fig40_substitution_map(cross_df, yield_df, lcoe_df)
    plot_fig41_rooftop_vs_utility(yield_df, lcoe_df)

    # 总结
    print("\n===== 物理引擎驱动替代分析结果 =====")
    print(f"\n年均工作温度排序 (晶硅模块):")
    t_order = yield_df[yield_df["tech"] == "晶硅"].sort_values("tcell_weighted")
    for _, r in t_order.iterrows():
        print(f"  {r['city']:5s} : Tcell={r['tcell_weighted']:.1f}°C, "
              f"yield={r['yield_kwh_per_kwp']:.0f} kWh/kWp")
    print(f"\n钙钛矿温度优势 (yield 相对 c-Si):")
    for _, r in t_order.iterrows():
        p = yield_df[(yield_df["city"] == r["city"]) &
                     (yield_df["tech"] == "钙钛矿")].iloc[0]
        adv = (p["yield_kwh_per_kwp"] / r["yield_kwh_per_kwp"] - 1) * 100
        print(f"  {r['city']:5s} : +{adv:>4.1f}%")
    print(f"\n替代年 (城市级 LCOE 自然交叉):")
    for _, r in cross_df.iterrows():
        v1 = r["钙钛矿超晶硅"]; v2 = r["叠层超晶硅"]
        print(f"  {r['city']:5s} : 钙钛矿→晶硅 {v1 if v1 else '无'} | "
              f"叠层→晶硅 {v2 if v2 else '无'}")
    print("\n图: 37/38/39/40/41 已保存到 outputs/figures/")


if __name__ == "__main__":
    main()
