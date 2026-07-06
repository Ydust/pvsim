"""31 省物理引擎驱动的替代分析 (C 路线 v3+).

扩展 portfolio_physics.py 从 12 城到 31 省:
  - 复用 12 个已缓存的 PVGIS TMY
  - 自动拉取剩余 19 省 (首次联网, 之后用本地缓存)
  - 重做 Fig 40 的地理地图: 31 点 + 资源带着色
  - 输出 31 省 × 3 技 × 26 年 LCOE 矩阵, 供 CO2 减排分析使用 (portfolio_carbon.py)

运行: python -m scripts.portfolio_provinces
输出: outputs/province_physics_*.csv + outputs/figures/42-44_province_*.png
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.materials import CSI_MODERN, PEROVSKITE, TANDEM_2T
from pvsim.provinces import PROVINCES, PROVINCE_PV_2024_GW
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

# 复用 portfolio_physics 的参数 (统一 capex/LCOE 配置)
from scripts.portfolio_physics import (
    CAPEX_0, Q_0, CAPEX_FLOOR, B, MAX_DROP, DISCOUNT, OPEX,
    LIFE_0, DEG_0, BURN_0, BREAKTHROUGH_YEAR,
    tech_year_params, capex_path_global, lcoe_npv, COLORS,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

YEARS = np.arange(2025, 2051)
N = len(YEARS)
TECHS = [("c-Si", "晶硅", CSI_MODERN), ("perovskite", "钙钛矿", PEROVSKITE),
         ("tandem", "叠层", TANDEM_2T)]
RESOURCE_COLOR = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}


def fetch_or_load_tmy(prov):
    """从 PVGIS 拉取或加载缓存的 TMY."""
    cache_path = f"data/tmy_cache/{prov.key}.csv"
    if os.path.exists(cache_path):
        return wx.from_pvgis_tmy(prov.lat, prov.lon, altitude=prov.alt,
                                  name=prov.key)
    print(f"  [PVGIS 拉取] {prov.name} ({prov.city})...", flush=True)
    t0 = time.time()
    try:
        w = wx.from_pvgis_tmy(prov.lat, prov.lon, altitude=prov.alt,
                               name=prov.key)
        print(f"    ✓ {time.time()-t0:.1f}s", flush=True)
        return w
    except Exception as e:
        print(f"    ✗ 拉取失败 {prov.name}: {e}", flush=True)
        return None


def yield_all_provinces():
    """31 省 × 3 技 物理仿真."""
    print(f"[1/4] 31 省物理仿真 (PVGIS TMY × De Soto × 温度 × 光谱 × 退化)...")
    cfg = SystemConfig(n_modules=20)
    results = []
    for prov in PROVINCES:
        w = fetch_or_load_tmy(prov)
        if w is None:
            continue
        tair_mean = float(w["temp_air"].mean())
        ghi_total = float(w["ghi"].sum() / 1000.0)
        for code, name, tech in TECHS:
            r = simulate(tech, w, cfg, npts=60)
            ts = r["timeseries"]
            poa = ts["poa_global"].to_numpy(); tcell = ts["tcell"].to_numpy()
            sf = ts["spectral_factor"].to_numpy()
            m = poa > 50
            tcell_w = float(np.average(tcell[m], weights=poa[m])) if m.any() else np.nan
            sf_w = float(np.average(sf[m], weights=poa[m])) if m.any() else np.nan
            area_m2 = 20 * tech.cells_in_series * tech.area_cm2 * 1e-4
            results.append({
                "province": prov.name, "city": prov.city, "key": prov.key,
                "lat": prov.lat, "lon": prov.lon, "alt": prov.alt,
                "region": prov.region, "res_band": prov.res_band,
                "tech": name, "code": code,
                "kwp": r["kwp"],
                "yield_kwh_per_kwp": r["specific_yield"],
                "yield_kwh_per_m2": r["energy_ac_kwh"] / area_m2,
                "PR": r["performance_ratio"],
                "tcell_weighted": tcell_w,
                "spectral_factor_w": sf_w,
                "ghi_kwh_m2": ghi_total,
                "tair_mean": tair_mean,
                "pv_2024_gw": PROVINCE_PV_2024_GW.get(prov.name, 0),
            })
        n = len(results) // 3
        if n % 5 == 0 or n == len(PROVINCES):
            print(f"  完成 {n}/{len(PROVINCES)} 省", flush=True)
    return pd.DataFrame(results)


def build_province_lcoe(yield_df):
    print(f"\n[2/4] 省级 LCOE 矩阵 (31 省 × 3 技 × 26 年)...")
    base_dep = {"晶硅": np.linspace(80, 30, N) + np.linspace(0, 20, N),
                "钙钛矿": np.minimum(np.arange(N) * 4 + 5, 100),
                "叠层": np.maximum(0, np.minimum(np.arange(N) * 3 - 12, 80))}
    cap_path = capex_path_global(base_dep)
    rows = []
    for _, r in yield_df.iterrows():
        for i, yr in enumerate(YEARS):
            cap = cap_path[r["tech"]][i]
            life, deg, burn = tech_year_params(r["tech"], int(yr))
            lc = lcoe_npv(cap, r["yield_kwh_per_kwp"], life, deg, burn)
            rows.append({
                "province": r["province"], "tech": r["tech"], "year": int(yr),
                "capex_usd_per_w": cap,
                "lcoe_cents_per_kwh": lc * 100,
                "yield_kwh_per_kwp": r["yield_kwh_per_kwp"],
                "tcell_weighted": r["tcell_weighted"],
            })
    return pd.DataFrame(rows), cap_path


def plot_fig42_province_yield_map(yield_df):
    """Fig 42: 31 省晶硅 yield 地图 + 资源带."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
    csi = yield_df[yield_df["tech"] == "晶硅"]

    # (a) yield 地理景观
    ax = axes[0]
    sc = ax.scatter(csi["lon"], csi["lat"], c=csi["yield_kwh_per_kwp"],
                    s=180, cmap="viridis", vmin=1000, vmax=2100,
                    edgecolors="black", linewidth=0.7, zorder=3)
    for _, r in csi.iterrows():
        ax.annotate(f"{r['province']}\n{r['yield_kwh_per_kwp']:.0f}",
                    (r["lon"], r["lat"]), textcoords="offset points",
                    xytext=(6, 4), fontsize=7.5)
    ax.set_xlabel("经度 (°E)"); ax.set_ylabel("纬度 (°N)")
    ax.set_title("(a) 31 省晶硅年发电 (物理 8760h, kWh/kWp)",
                 fontweight="bold")
    ax.set_xlim(78, 135); ax.set_ylim(18, 50); ax.grid(alpha=0.3)
    plt.colorbar(sc, ax=ax, label="kWh/kWp")

    # (b) 钙钛矿温度优势
    ax = axes[1]
    perov_adv = []
    for _, r in csi.iterrows():
        p = yield_df[(yield_df["province"] == r["province"]) &
                      (yield_df["tech"] == "钙钛矿")].iloc[0]
        perov_adv.append((p["yield_kwh_per_kwp"] / r["yield_kwh_per_kwp"] - 1) * 100)
    perov_adv = np.array(perov_adv)
    sc = ax.scatter(csi["lon"], csi["lat"], c=perov_adv, s=180,
                    cmap="RdYlBu_r", vmin=0, vmax=10,
                    edgecolors="black", linewidth=0.7, zorder=3)
    for _, r, adv in zip(range(len(csi)), csi.iterrows(), perov_adv):
        prov, row = r[1]["province"], r[1]
        ax.annotate(f"{prov}\n+{adv:.1f}%",
                    (row["lon"], row["lat"]), textcoords="offset points",
                    xytext=(6, 4), fontsize=7.5)
    ax.set_xlabel("经度 (°E)"); ax.set_ylabel("纬度 (°N)")
    ax.set_title("(b) 钙钛矿温度优势 (yield vs 晶硅, %)", fontweight="bold")
    ax.set_xlim(78, 135); ax.set_ylim(18, 50); ax.grid(alpha=0.3)
    plt.colorbar(sc, ax=ax, label="优势 (%)")

    fig.suptitle("31 省物理 yield 景观: 资源带 + 钙钛矿温度优势分布",
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig("outputs/figures/42_provinces_yield_map.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)


def plot_fig43_province_2050_landscape(lcoe_df, yield_df):
    """Fig 43: 31 省 2050 LCOE 景观 + 最便宜技术分布."""
    d2050 = lcoe_df[lcoe_df["year"] == 2050].pivot(
        index="province", columns="tech", values="lcoe_cents_per_kwh")
    d2050["best_lcoe"] = d2050.min(axis=1)
    d2050["best_tech"] = d2050[["晶硅", "钙钛矿", "叠层"]].idxmin(axis=1)
    d2050["saving_pct"] = (d2050["晶硅"] - d2050["best_lcoe"]) / d2050["晶硅"] * 100
    d2050 = d2050.reset_index()
    coords = {p.name: (p.lon, p.lat) for p in PROVINCES}
    d2050["lon"] = d2050["province"].map(lambda c: coords.get(c, (0,0))[0])
    d2050["lat"] = d2050["province"].map(lambda c: coords.get(c, (0,0))[1])

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
    # (a) 最优 LCOE 2050
    ax = axes[0]
    sc = ax.scatter(d2050["lon"], d2050["lat"], c=d2050["best_lcoe"],
                    s=210, cmap="viridis_r", vmin=1.8, vmax=4.0,
                    edgecolors="black", linewidth=0.8, zorder=3)
    for _, r in d2050.iterrows():
        ax.annotate(f"{r['province']}\n{r['best_lcoe']:.2f}",
                    (r["lon"], r["lat"]), textcoords="offset points",
                    xytext=(6, 4), fontsize=7.5)
    ax.set_xlabel("经度 (°E)"); ax.set_ylabel("纬度 (°N)")
    ax.set_title("(a) 31 省 2050 最优 LCOE (分/kWh)", fontweight="bold")
    ax.set_xlim(78, 135); ax.set_ylim(18, 50); ax.grid(alpha=0.3)
    plt.colorbar(sc, ax=ax, label="LCOE (分/kWh)")

    # (b) 钙钛矿相对节省 (%)
    ax = axes[1]
    sc = ax.scatter(d2050["lon"], d2050["lat"], c=d2050["saving_pct"],
                    s=210, cmap="RdYlGn", vmin=20, vmax=50,
                    edgecolors="black", linewidth=0.8, zorder=3)
    for _, r in d2050.iterrows():
        ax.annotate(f"{r['province']}\n-{r['saving_pct']:.0f}%",
                    (r["lon"], r["lat"]), textcoords="offset points",
                    xytext=(6, 4), fontsize=7.5)
    ax.set_xlabel("经度 (°E)"); ax.set_ylabel("纬度 (°N)")
    ax.set_title("(b) 钙钛矿相对晶硅 LCOE 节省幅度 (%)", fontweight="bold")
    ax.set_xlim(78, 135); ax.set_ylim(18, 50); ax.grid(alpha=0.3)
    plt.colorbar(sc, ax=ax, label="LCOE 节省 (%)")

    fig.suptitle("2050 终态地理: LCOE 水平 + 替代价值的省级异质性",
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig("outputs/figures/43_provinces_2050_landscape.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)


def plot_fig44_resource_bands(yield_df):
    """Fig 44: 按太阳能资源带 (I/II/III/IV) 分组的 yield + 温度优势 boxplot."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    csi = yield_df[yield_df["tech"] == "晶硅"]
    perov = yield_df[yield_df["tech"] == "钙钛矿"]

    # (a) c-Si yield 按资源带分布
    ax = axes[0]
    band_order = ["I", "II", "III", "IV"]
    data = [csi[csi["res_band"] == b]["yield_kwh_per_kwp"].values for b in band_order]
    bp = ax.boxplot(data, tick_labels=band_order, patch_artist=True, widths=0.6)
    for patch, b in zip(bp["boxes"], band_order):
        patch.set_facecolor(RESOURCE_COLOR[b]); patch.set_alpha(0.7)
    ax.set_xlabel("太阳能资源带"); ax.set_ylabel("年发电 (kWh/kWp)")
    ax.set_title("(a) 资源带 vs c-Si 年发电", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")
    for b in band_order:
        n = len(csi[csi["res_band"] == b])
        ax.text(band_order.index(b)+1, ax.get_ylim()[0]+50, f"n={n}",
                ha="center", fontsize=9, color="gray")

    # (b) 钙钛矿优势按资源带
    ax = axes[1]
    pairs = csi.merge(perov, on="province", suffixes=("_csi", "_perov"))
    pairs["adv"] = (pairs["yield_kwh_per_kwp_perov"] /
                    pairs["yield_kwh_per_kwp_csi"] - 1) * 100
    data2 = [pairs[pairs["res_band_csi"] == b]["adv"].values for b in band_order]
    bp = ax.boxplot(data2, tick_labels=band_order, patch_artist=True, widths=0.6)
    for patch, b in zip(bp["boxes"], band_order):
        patch.set_facecolor(RESOURCE_COLOR[b]); patch.set_alpha(0.7)
    ax.set_xlabel("太阳能资源带")
    ax.set_ylabel("钙钛矿温度优势 (% vs c-Si)")
    ax.set_title("(b) 资源带 vs 钙钛矿温度优势", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")
    fig.suptitle("国网资源带分类: I 高原戈壁/II 西北/III 大部/IV 西南雾雨",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/44_provinces_resource_bands.png", dpi=130,
                bbox_inches="tight")
    plt.close(fig)


def main():
    viz.setup()
    os.makedirs("outputs/figures", exist_ok=True)

    yield_df = yield_all_provinces()
    yield_df.to_csv("outputs/province_physics_yield.csv", index=False,
                    encoding="utf-8-sig")
    print(f"  生成 {len(yield_df)} 行 (3 技 × {len(yield_df)//3} 省)")

    lcoe_df, cap_path = build_province_lcoe(yield_df)
    lcoe_df.to_csv("outputs/province_physics_lcoe.csv", index=False,
                   encoding="utf-8-sig")
    print(f"  生成 {len(lcoe_df)} 行 LCOE 矩阵")

    print("\n[3/4] 出 31 省地图...")
    plot_fig42_province_yield_map(yield_df)
    plot_fig43_province_2050_landscape(lcoe_df, yield_df)
    plot_fig44_resource_bands(yield_df)

    # 总结
    print("\n===== 31 省物理替代分析结果 =====")
    csi = yield_df[yield_df["tech"] == "晶硅"].sort_values("yield_kwh_per_kwp",
                                                            ascending=False)
    print(f"\n年发电 Top 5 / Bottom 5 (c-Si):")
    for _, r in csi.head(5).iterrows():
        print(f"  {r['province']:5s} ({r['city']:6s}): {r['yield_kwh_per_kwp']:.0f}"
              f" kWh/kWp, T_cell={r['tcell_weighted']:.1f}°C, band {r['res_band']}")
    print("  ...")
    for _, r in csi.tail(5).iterrows():
        print(f"  {r['province']:5s} ({r['city']:6s}): {r['yield_kwh_per_kwp']:.0f}"
              f" kWh/kWp, T_cell={r['tcell_weighted']:.1f}°C, band {r['res_band']}")

    perov_adv = []
    for _, r in csi.iterrows():
        p = yield_df[(yield_df["province"] == r["province"]) &
                      (yield_df["tech"] == "钙钛矿")].iloc[0]
        perov_adv.append((r["province"], (p["yield_kwh_per_kwp"] /
                          r["yield_kwh_per_kwp"] - 1) * 100, r["tcell_weighted"]))
    perov_adv.sort(key=lambda x: x[1], reverse=True)
    print(f"\n钙钛矿温度优势 Top 5 / Bottom 5:")
    for prov, adv, t in perov_adv[:5]:
        print(f"  {prov:5s}: +{adv:.2f}% (T_cell={t:.1f}°C)")
    print("  ...")
    for prov, adv, t in perov_adv[-5:]:
        print(f"  {prov:5s}: +{adv:.2f}% (T_cell={t:.1f}°C)")
    print("\n图: 42_yield_map / 43_2050_landscape / 44_resource_bands 已保存")


if __name__ == "__main__":
    main()
