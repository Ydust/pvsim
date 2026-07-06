"""物理引擎驱动的 CO2 减排分析 (C 路线 v3+, 任务 E).

把物理 yield (来自 portfolio_provinces) × 电网脱碳轨迹 (policy_data) ×
embodied carbon 数据 → 累计 GtCO2 减排, 三技 vs 反事实 (全 c-Si).

输出:
  Fig 45: 三技碳回收时间 (按省份, 物理 yield 驱动)
  Fig 46: 累计 GtCO2 avoided 2025-2050, 3 个部署情景对比
  Fig 47: 省级减排潜力地图 (用 PROVINCE_PV_2024_GW 加权)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.provinces import PROVINCES, PROVINCE_PV_2024_GW
from pvsim.policy_data import (china_pv_target_gw, china_grid_ef_kgco2_per_kwh,
                                 EMBODIED_KG_PER_WP)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

YEARS = np.arange(2025, 2051)
N = len(YEARS)
COLORS = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}

# embodied 碳 (kgCO2/kWp), mid 值
EMB = {
    "晶硅": EMBODIED_KG_PER_WP["晶硅25y"]["mid"] * 1000,    # 0.50 × 1000 = 500 kg/kWp
    "钙钛矿": EMBODIED_KG_PER_WP["钙钛矿25y"]["mid"] * 1000,  # 150 kg/kWp
    "叠层":  EMBODIED_KG_PER_WP["叠层"]["mid"] * 1000,       # 200 kg/kWp
}

# 寿命 (与 portfolio_physics.py 一致, 钙钛矿假设 2032 突破后 25y)
LIFE = {"晶硅": 25, "钙钛矿": 25, "叠层": 25}    # 含突破后假设
DEG = {"晶硅": 0.007, "钙钛矿": 0.010, "叠层": 0.007}
BURN = {"晶硅": 0.02, "钙钛矿": 0.05, "叠层": 0.04}


def load_province_physics():
    """读取 portfolio_provinces.py 输出的物理 yield 数据."""
    path = "outputs/province_physics_yield.csv"
    if not os.path.exists(path):
        print(f"未找到 {path}, 先运行 python -m scripts.portfolio_provinces", flush=True)
        sys.exit(1)
    return pd.read_csv(path, encoding="utf-8-sig")


def lifetime_offset(yield_kwh_per_kwp, install_year, life, deg, burn_in,
                    grid_ef_series, grid_ef_years):
    """给定一个 install_year 的 1 kWp 装机, 算其全寿命内累计 CO2 offset (kgCO2/kWp).

    yield(t) = yield_0 × (1-burn) (t=1) × (1-deg)^(t-1) (t>=2)
    grid_ef(t) 沿运行年线性内插
    offset = Σ yield(t) × grid_ef(install_year + t-1)
    """
    total = 0.0
    for t in range(1, int(life)+1):
        if t == 1:
            y = yield_kwh_per_kwp * (1 - burn_in)
        else:
            y = yield_kwh_per_kwp * (1 - burn_in) * (1 - deg)**(t-1)
        op_year = install_year + t - 1
        if op_year > 2050:
            op_year = 2050    # 假设后续电网保持 2050 水平 (深度脱碳已达)
        ef = float(np.interp(op_year, grid_ef_years, grid_ef_series))
        total += y * ef     # kWh/kWp × kgCO2/kWh = kgCO2/kWp
    return total


def carbon_payback_by_province(yield_df, grid_years, grid_ef):
    """每省 × 每技 的碳回收时间 (年) 在 2025 装机, 当年电网 EF."""
    rows = []
    for _, r in yield_df.iterrows():
        ef_2025 = float(np.interp(2025, grid_years, grid_ef))
        annual_offset = r["yield_kwh_per_kwp"] * (1 - BURN[r["tech"]]) * ef_2025
        payback = EMB[r["tech"]] / annual_offset    # 年
        rows.append({"province": r["province"], "tech": r["tech"],
                     "payback_yr": payback,
                     "yield_kwh_per_kwp": r["yield_kwh_per_kwp"],
                     "embodied_kg_per_kwp": EMB[r["tech"]],
                     "annual_offset_kg_per_kwp": annual_offset})
    return pd.DataFrame(rows)


def cumulative_avoided_by_scenario(yield_df, grid_years, grid_ef):
    """3 个部署情景 × 26 年 × 31 省 × 3 技, 累计 CO2 avoided (GtCO2)."""
    _, target = china_pv_target_gw()
    # 年新增 GW (2025-2050)
    yr_full = np.arange(2024, 2051)
    new_total = np.diff(target)       # 26 years
    # 三技每年份额 — 三个情景
    # 情景 1: all c-Si (反事实)
    sc1_share = {"晶硅": np.ones(N), "钙钛矿": np.zeros(N), "叠层": np.zeros(N)}
    # 情景 2: 自然替代 (与 portfolio_substitution v2 一致, 大致)
    sc2_share = {"晶硅": np.zeros(N), "钙钛矿": np.zeros(N), "叠层": np.zeros(N)}
    for i, yr in enumerate(YEARS):
        if yr < 2030:
            sc2_share["晶硅"][i] = max(0, 1 - (yr-2025) * 0.18)
            sc2_share["钙钛矿"][i] = min(0.6, (yr-2024) * 0.13)
            sc2_share["叠层"][i] = max(0, (yr-2028) * 0.07)
        elif yr < 2036:
            sc2_share["晶硅"][i] = 0.12 + (yr-2030)*0.015
            sc2_share["钙钛矿"][i] = 0.55 - (yr-2030)*0.025
            sc2_share["叠层"][i] = 0.33 + (yr-2030)*0.01
        else:
            sc2_share["晶硅"][i] = 0.21
            sc2_share["钙钛矿"][i] = 0.40
            sc2_share["叠层"][i] = 0.39
        # 归一
        s = sum(sc2_share[k][i] for k in sc2_share)
        for k in sc2_share: sc2_share[k][i] /= s
    # 情景 3: 钙钛矿激进 (政策强推 70%)
    sc3_share = {"晶硅": np.zeros(N), "钙钛矿": np.zeros(N), "叠层": np.zeros(N)}
    for i, yr in enumerate(YEARS):
        if yr < 2028:
            sc3_share["晶硅"][i] = max(0.1, 1 - (yr-2024)*0.25)
            sc3_share["钙钛矿"][i] = min(0.9, (yr-2024)*0.22)
            sc3_share["叠层"][i] = 0
        elif yr < 2035:
            sc3_share["晶硅"][i] = 0.08
            sc3_share["钙钛矿"][i] = 0.62
            sc3_share["叠层"][i] = 0.30
        else:
            sc3_share["晶硅"][i] = 0.05
            sc3_share["钙钛矿"][i] = 0.55
            sc3_share["叠层"][i] = 0.40
        s = sum(sc3_share[k][i] for k in sc3_share)
        for k in sc3_share: sc3_share[k][i] /= s

    scenarios = {"全晶硅(反事实)": sc1_share, "自然替代(基线)": sc2_share,
                  "钙钛矿激进": sc3_share}

    # 省级 yield 加权: 用 2024 装机存量做配额, 假设新增按比例分配
    csi = yield_df[yield_df["tech"] == "晶硅"].set_index("province")
    perov = yield_df[yield_df["tech"] == "钙钛矿"].set_index("province")
    tand = yield_df[yield_df["tech"] == "叠层"].set_index("province")
    yields = {"晶硅": csi, "钙钛矿": perov, "叠层": tand}
    total_2024 = sum(PROVINCE_PV_2024_GW.values())
    prov_share = {p: PROVINCE_PV_2024_GW.get(p, 0) / total_2024
                   for p in csi.index}

    results = {}
    for sc_name, shares in scenarios.items():
        cum_avoided_gtco2 = np.zeros(N)
        cum_embodied_gtco2 = np.zeros(N)
        # 对每个 install year × tech × province, 算全寿命 offset
        for i, yr in enumerate(YEARS):
            gw_new = float(new_total[i+1] if i+1 < len(new_total) else 25)
            for tech in ["晶硅", "钙钛矿", "叠层"]:
                gw_tech = gw_new * shares[tech][i]
                # 加权省级 yield (用 prov_share 加权平均)
                wy = sum(yields[tech].loc[p]["yield_kwh_per_kwp"] * prov_share[p]
                         for p in prov_share if p in yields[tech].index)
                # 全寿命 offset (kg/kWp)
                offset = lifetime_offset(wy, int(yr), LIFE[tech], DEG[tech],
                                          BURN[tech], grid_ef, grid_years)
                emb = EMB[tech]
                # 装机 GW → kWp ×1e6 → kg → Gt
                total_offset_gtco2 = gw_tech * 1e6 * offset / 1e12
                total_emb_gtco2 = gw_tech * 1e6 * emb / 1e12
                cum_avoided_gtco2[i] += total_offset_gtco2 - total_emb_gtco2
                cum_embodied_gtco2[i] += total_emb_gtco2
        results[sc_name] = {
            "annual_net_gtco2": cum_avoided_gtco2,
            "annual_embodied_gtco2": cum_embodied_gtco2,
            "cumulative_net_gtco2": np.cumsum(cum_avoided_gtco2),
            "shares": shares,
        }
    return results


def plot_fig45_payback(payback_df):
    """Fig 45: 三技碳回收时间分布."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    # (a) 31 省 × 3 技碳回收时间散点
    ax = axes[0]
    for tech in ["晶硅", "钙钛矿", "叠层"]:
        sub = payback_df[payback_df["tech"] == tech].sort_values("yield_kwh_per_kwp")
        ax.plot(sub["yield_kwh_per_kwp"], sub["payback_yr"], "o-",
                color=COLORS[tech], lw=1.5, ms=7, label=f"{tech} (embodied {EMB[tech]:.0f} kg/kWp)")
    ax.set_xlabel("年发电 (kWh/kWp, 物理 8760h)")
    ax.set_ylabel("碳回收时间 (年, 在 2025 装机, EF=0.55)")
    ax.set_title("(a) 物理 yield 决定的碳回收周期", fontweight="bold")
    ax.grid(alpha=0.3); ax.legend()

    # (b) 按省份碳回收时间排序条形
    ax = axes[1]
    p = payback_df.pivot(index="province", columns="tech", values="payback_yr")
    p = p.sort_values("晶硅", ascending=False)
    x = np.arange(len(p)); bw = 0.27
    ax.barh(x - bw, p["晶硅"], height=bw, color=COLORS["晶硅"], label="晶硅")
    ax.barh(x, p["钙钛矿"], height=bw, color=COLORS["钙钛矿"], label="钙钛矿")
    ax.barh(x + bw, p["叠层"], height=bw, color=COLORS["叠层"], label="叠层")
    ax.set_yticks(x); ax.set_yticklabels(p.index, fontsize=7)
    ax.set_xlabel("碳回收时间 (年)")
    ax.set_title("(b) 31 省碳回收时间排序 (短=好)", fontweight="bold")
    ax.legend(loc="lower right"); ax.grid(alpha=0.3, axis="x")
    fig.suptitle("CO2 回收时间: 钙钛矿 embodied 仅 c-Si 30% → 1-2 年回收",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/45_carbon_payback.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def plot_fig46_scenarios(results):
    """Fig 46: 3 部署情景 2025-2050 累计 CO2 avoided + 年度结构."""
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.5))
    # (a) 累计净 GtCO2 avoided
    ax = axes[0]
    for name, d in results.items():
        ls = "-" if name == "自然替代(基线)" else "--"
        lw = 2.4 if name == "自然替代(基线)" else 1.8
        ax.plot(YEARS, d["cumulative_net_gtco2"], ls=ls, lw=lw, label=name)
    ax.set_xlabel("年"); ax.set_ylabel("累计净 CO2 avoided (GtCO2)")
    ax.set_title("(a) 三情景累计净碳减排 (含 embodied 抵扣)", fontweight="bold")
    ax.grid(alpha=0.3); ax.legend(loc="upper left")

    # (b) 基线情景 vs 反事实差量 (政策有效性)
    ax = axes[1]
    baseline = results["自然替代(基线)"]["cumulative_net_gtco2"]
    counterf = results["全晶硅(反事实)"]["cumulative_net_gtco2"]
    aggr = results["钙钛矿激进"]["cumulative_net_gtco2"]
    ax.plot(YEARS, baseline - counterf, "o-", color="#1f6fb2", lw=2.4,
            label="自然替代 vs 全晶硅")
    ax.plot(YEARS, aggr - counterf, "s--", color="#e2641e", lw=2.0,
            label="激进路线 vs 全晶硅")
    ax.axhline(0, color="gray", lw=0.5)
    ax.set_xlabel("年"); ax.set_ylabel("替代方案相对反事实减排 (GtCO2)")
    ax.set_title("(b) 技术替代的额外减排贡献", fontweight="bold")
    ax.grid(alpha=0.3); ax.legend(loc="upper left")
    final_savings_2050 = (baseline[-1] - counterf[-1], aggr[-1] - counterf[-1])
    ax.text(2027, ax.get_ylim()[1]*0.6,
            f"2050 累计节省:\n  自然替代 +{final_savings_2050[0]:.1f} GtCO2\n"
            f"  激进路线 +{final_savings_2050[1]:.1f} GtCO2",
            fontsize=10, bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow"))

    fig.suptitle("中国 PV 部署 2025-2050 CO2 减排: 物理 yield × 电网脱碳轨迹",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/46_carbon_scenarios.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)


def plot_fig47_province_map(yield_df, grid_years, grid_ef):
    """Fig 47: 省级减排潜力地图 (基于物理 yield × 2024 装机比例)."""
    csi = yield_df[yield_df["tech"] == "晶硅"]
    perov = yield_df[yield_df["tech"] == "钙钛矿"]
    coords = {p.name: (p.lon, p.lat) for p in PROVINCES}
    rows = []
    for _, c in csi.iterrows():
        p = perov[perov["province"] == c["province"]].iloc[0]
        share = PROVINCE_PV_2024_GW.get(c["province"], 0) / sum(PROVINCE_PV_2024_GW.values())
        # 每省假设 2050 装机 = 2400 × share, 全替代 (perov 主导)
        gw_prov_2050 = 2400 * share
        # 简化: 假设该省 2050 装机全为 perov, 全寿命 (用 2030 中点 EF)
        ef_mid = float(np.interp(2030, grid_years, grid_ef))
        annual_offset_perov = p["yield_kwh_per_kwp"] * 0.95 * ef_mid    # 含 burn-in
        # 25y 累计 offset (kg/kWp)
        life_offset = sum(p["yield_kwh_per_kwp"] * (1-DEG["钙钛矿"])**t * 0.95 *
                          float(np.interp(min(2050, 2025+t), grid_years, grid_ef))
                          for t in range(25))
        # GtCO2 减排潜力 = GW × kWp/GW × kg/kWp / 1e12
        gt = gw_prov_2050 * 1e6 * life_offset / 1e12
        rows.append({"province": c["province"], "lon": coords.get(c["province"], (0,0))[0],
                     "lat": coords.get(c["province"], (0,0))[1],
                     "share": share, "gw_2050": gw_prov_2050,
                     "gtco2_25y": gt, "yield": p["yield_kwh_per_kwp"]})
    df = pd.DataFrame(rows)
    df.to_csv("outputs/province_carbon_potential.csv", index=False,
              encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(11, 7))
    sc = ax.scatter(df["lon"], df["lat"], c=df["gtco2_25y"],
                    s=df["gw_2050"]*4+30, cmap="YlOrRd",
                    edgecolors="black", linewidth=0.7, alpha=0.85, zorder=3)
    for _, r in df.iterrows():
        ax.annotate(f"{r['province']}\n{r['gtco2_25y']:.2f}",
                    (r["lon"], r["lat"]), textcoords="offset points",
                    xytext=(8, 4), fontsize=7.5, fontweight="bold")
    ax.set_xlabel("经度 (°E)"); ax.set_ylabel("纬度 (°N)")
    ax.set_title("31 省钙钛矿 2050 装机 25y 累计 CO2 减排潜力 (GtCO2)\n"
                 "气泡大小 ∝ 2050 装机量, 颜色 ∝ 累计减排",
                 fontweight="bold")
    ax.set_xlim(78, 135); ax.set_ylim(18, 50); ax.grid(alpha=0.3)
    plt.colorbar(sc, ax=ax, label="累计 CO2 减排 (GtCO2)")
    fig.tight_layout()
    fig.savefig("outputs/figures/47_province_carbon_map.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)

    return df


def main():
    viz.setup()
    os.makedirs("outputs/figures", exist_ok=True)

    print("[1/3] 加载 31 省物理 yield 数据...")
    yield_df = load_province_physics()
    print(f"  {len(yield_df)} 行 (3 技 × {len(yield_df)//3} 省)")

    grid_years, grid_ef = china_grid_ef_kgco2_per_kwh()
    print(f"\n[2/3] 碳回收时间 (省级 × 3 技)...")
    payback_df = carbon_payback_by_province(yield_df, grid_years, grid_ef)
    payback_df.to_csv("outputs/province_carbon_payback.csv", index=False,
                      encoding="utf-8-sig")
    print(f"  钙钛矿碳回收 中位: {payback_df[payback_df['tech']=='钙钛矿']['payback_yr'].median():.2f} 年")
    print(f"  晶硅碳回收 中位: {payback_df[payback_df['tech']=='晶硅']['payback_yr'].median():.2f} 年")
    print(f"  叠层碳回收 中位: {payback_df[payback_df['tech']=='叠层']['payback_yr'].median():.2f} 年")

    print(f"\n[3/3] 累计 GtCO2 减排 (3 部署情景)...")
    results = cumulative_avoided_by_scenario(yield_df, grid_years, grid_ef)
    for name, d in results.items():
        print(f"  {name:15s}: 2050 累计净 {d['cumulative_net_gtco2'][-1]:6.2f} GtCO2 "
              f"(含 embodied 抵扣 {d['annual_embodied_gtco2'].sum():.2f} GtCO2)")

    print("\n[4/4] 出图...")
    plot_fig45_payback(payback_df)
    plot_fig46_scenarios(results)
    province_carbon = plot_fig47_province_map(yield_df, grid_years, grid_ef)
    print(f"  Top 5 减排潜力省份 (25y kWh×EF):")
    for _, r in province_carbon.nlargest(5, "gtco2_25y").iterrows():
        print(f"    {r['province']:5s}: {r['gtco2_25y']:.2f} GtCO2 "
              f"(2050 装机 {r['gw_2050']:.0f} GW)")

    print("\n图: 45_payback / 46_scenarios / 47_province_map 已保存")


if __name__ == "__main__":
    main()
