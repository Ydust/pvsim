"""Main Fig 3c — 网格尺度地理反转 (Gap 1: 从 31 点到 ~1200 网格点).

把"西南>西北"反转从 31 省代表点扩展到 NASA POWER 1° 网格 (中国陆地 ~1200 格点),
回应 Joule 审稿人"单点代表全省"的质疑.

方法 (月度降阶物理, 经全 8760h 验证):
  1. POWER 1° 月度气候态 GHI/Tair/wind, shapely 中国陆地掩膜.
  2. 每格点 12 个月: 电池温度 Tcell=Tair + k·GHI/(u0+u1·wind),
     单二极管算各技月度功率, 能量加权得年优势 = yield_perov/yield_csi - 1.
  3. 验证: 同模型在 31 省锚点 vs 全 8760h PVGIS 结果, 拟合标度 k, 报 R².
  4. 网格尺度重算辐照-优势相关 r, 与 31 点 r=-0.52 对比.

运行: python -m scripts.fig_grid_inversion
输出: outputs/figures/MainFig3c_grid_inversion.png/.pdf + outputs/grid_inversion.csv
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from shapely.prepared import prep
from scipy.spatial import cKDTree

from pvsim import viz
from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.module import array_dc_power, module_stc_power
from pvsim.nasa_power import fetch_china_grid, MONTHS
from pvsim.provinces import PROVINCES

CSI_STC = module_stc_power(CSI_EARLY)       # 单组件 STC Wp
PEROV_STC = module_stc_power(PEROVSKITE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHINA_GEOJSON = r"C:\Users\yuanq\new\geojson\CHN_adm_shp__0__CHN_adm_shp.geojson"
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
U0, U1 = 25.0, 6.84   # 开放支架 Faiman


def china_mask():
    with open(CHINA_GEOJSON, encoding="utf-8-sig") as f:
        gj = json.load(f)
    geom = unary_union([shape(ft["geometry"]) for ft in gj["features"]])
    return prep(geom)


def cell_advantage(ghi_m, tair_m, wind_m, k):
    """单格点: 月度数组 → 钙钛矿年优势 (%).

    ghi_m: 月度 GHI (kWh/m^2/day)[12]; tair_m: 月均温[12]; wind_m: 月均风[12].
    """
    g_eff = k * np.asarray(ghi_m)               # 等效运行辐照 W/m^2
    tcell = np.asarray(tair_m) + g_eff / (U0 + U1 * np.asarray(wind_m))
    # 单二极管月度功率 (一次性向量调用)
    p_csi = np.atleast_1d(array_dc_power(CSI_EARLY, g_eff, tcell, n_modules=1, npts=60))
    p_perov = np.atleast_1d(array_dc_power(PEROVSKITE, g_eff, tcell, n_modules=1, npts=60))
    # 各技按 STC 额定归一 → 比发电量 (kWh/kWp 等价), 消除效率水平差, 只留温度/弱光响应
    y_csi = np.sum(p_csi * DAYS) / CSI_STC
    y_perov = np.sum(p_perov * DAYS) / PEROV_STC
    w = DAYS * np.asarray(ghi_m)
    return (y_perov / y_csi - 1) * 100, float(np.average(tcell, weights=w))


def split_param_grids(grid):
    """POWER 太阳(CERES 1°)与气温/风(MERRA-2 0.5°)网格不对齐.
    拆成各参数独立 {coord: monthly[12]}, 用 KD-tree 最近邻重采样到 GHI 网格."""
    out = {"ghi": {}, "tair": {}, "wind": {}}
    for (lon, lat), rec in grid.items():
        for pk in ("ghi", "tair", "wind"):
            if pk in rec and all(rec[pk].get(m) is not None for m in MONTHS):
                out[pk][(lon, lat)] = ([rec[pk][m] for m in MONTHS], rec[pk]["ANN"])
    return out


def build_resampler(param_grid):
    coords = np.array(list(param_grid.keys()))
    tree = cKDTree(coords)
    vals = [param_grid[tuple(c)][0] for c in coords]
    anns = [param_grid[tuple(c)][1] for c in coords]
    return tree, np.array(vals), np.array(anns), coords


def monthly_at(lon, lat, tree, vals):
    _, idx = tree.query([lon, lat])
    return vals[idx]


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    print("[1/4] 加载 POWER 网格 (缓存)...")
    grid = fetch_china_grid(verbose=False)
    pg = split_param_grids(grid)
    print(f"  bbox {len(grid)} | ghi {len(pg['ghi'])} tair {len(pg['tair'])} "
          f"wind {len(pg['wind'])} (网格不对齐, KD-tree 重采样)")
    tair_tree, tair_vals, _, _ = build_resampler(pg["tair"])
    wind_tree, wind_vals, _, _ = build_resampler(pg["wind"])

    def cell_at(lon, lat, ghi_monthly):
        t = monthly_at(lon, lat, tair_tree, tair_vals)
        w = monthly_at(lon, lat, wind_tree, wind_vals)
        return ghi_monthly, t, w

    print("[2/4] 标定降阶模型 k (vs 31 省全 8760h)...")
    anchor = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi_a = anchor[anchor["tech"] == "晶硅"].set_index("province")
    per_a = anchor[anchor["tech"] == "钙钛矿"].set_index("province")
    full_adv = {}
    for p in csi_a.index:
        if p in per_a.index:
            full_adv[p] = (per_a.loc[p, "yield_kwh_per_kwp"] /
                           csi_a.loc[p, "yield_kwh_per_kwp"] - 1) * 100
    ghi_tree, ghi_vals, _, _ = build_resampler(pg["ghi"])
    anchor_monthly = {}
    for prov in PROVINCES:
        gm = monthly_at(prov.lon, prov.lat, ghi_tree, ghi_vals)
        anchor_monthly[prov.name] = cell_at(prov.lon, prov.lat, gm)

    best_k, best_rmse = None, 1e9
    for k in np.arange(60, 320, 5):
        preds, truths = [], []
        for p, (g, t, w) in anchor_monthly.items():
            if p in full_adv:
                adv, _ = cell_advantage(g, t, w, k)
                preds.append(adv); truths.append(full_adv[p])
        rmse = np.sqrt(np.mean((np.array(preds) - np.array(truths)) ** 2))
        if rmse < best_rmse:
            best_rmse, best_k = rmse, k
    preds, truths = [], []
    for p, (g, t, w) in anchor_monthly.items():
        if p in full_adv:
            adv, _ = cell_advantage(g, t, w, best_k)
            preds.append(adv); truths.append(full_adv[p])
    preds, truths = np.array(preds), np.array(truths)
    r2_val = 1 - np.sum((preds-truths)**2) / np.sum((truths-truths.mean())**2)
    r_val = np.corrcoef(preds, truths)[0, 1]
    print(f"  最优 k={best_k:.0f}, RMSE={best_rmse:.2f}%, R²={r2_val:.3f}, r={r_val:.3f}")

    print("[3/4] 中国陆地掩膜 + 网格物理...")
    mask = china_mask()
    rows = []
    for (lon, lat), (gm, ann) in pg["ghi"].items():
        if not mask.contains(Point(lon, lat)):
            continue
        g, t, w = cell_at(lon, lat, gm)
        adv, tcell = cell_advantage(g, t, w, best_k)
        ghi_ann = ann * 365.0   # kWh/m^2/yr
        rows.append({"lon": lon, "lat": lat, "ghi_ann": ghi_ann,
                     "adv": adv, "tcell": tcell})
    gdf = pd.DataFrame(rows)
    gdf.to_csv("outputs/grid_inversion.csv", index=False, encoding="utf-8-sig")
    r_grid = np.corrcoef(gdf["ghi_ann"], gdf["adv"])[0, 1]
    print(f"  China land {len(gdf)} cells, grid-scale r(GHI,adv)={r_grid:+.3f}")

    print("[4/4] plotting...")
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), dpi=300)

    # (a) grid advantage map
    ax = axes[0]
    sc = ax.scatter(gdf["lon"], gdf["lat"], c=gdf["adv"], s=11, cmap="RdYlBu_r",
                    vmin=1, vmax=8, marker="s", edgecolors="none")
    ax.set_xlabel("Longitude (°E)", fontsize=9); ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"(a) Grid advantage map ({len(gdf)} land cells)", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.set_xlim(73, 135); ax.set_ylim(17, 54)
    cb = plt.colorbar(sc, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("Perovskite advantage (%)", fontsize=8); cb.ax.tick_params(labelsize=7)

    # (b) grid-scale scatter r
    ax = axes[1]
    sc = ax.scatter(gdf["ghi_ann"], gdf["adv"], c=gdf["adv"], s=8,
                    cmap="RdYlBu_r", vmin=1, vmax=8, alpha=0.6, edgecolors="none")
    z = np.polyfit(gdf["ghi_ann"], gdf["adv"], 1)
    xx = np.linspace(gdf["ghi_ann"].min(), gdf["ghi_ann"].max(), 50)
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.3)
    ax.text(0.05, 0.08, f"grid r = {r_grid:.2f}\n(31-pt r = -0.52)\n"
            f"$\\rightarrow$ holds at {len(gdf)} cells",
            transform=ax.transAxes, fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.set_xlabel("Annual GHI (kWh/m$^2$)", fontsize=9)
    ax.set_ylabel("Perovskite advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(b) Inversion holds at grid scale", fontsize=11, fontweight="bold",
                 loc="left", pad=3)
    ax.grid(alpha=0.25, lw=0.3)

    # (c) reduced-order model validation (vs full 8760h)
    ax = axes[2]
    ax.scatter(truths, preds, s=45, color="#2a9d4a", edgecolors="black",
               linewidth=0.4, zorder=3)
    lim = [min(truths.min(), preds.min())-0.5, max(truths.max(), preds.max())+0.5]
    ax.plot(lim, lim, "k:", lw=1, label="1:1")
    ax.text(0.05, 0.88, f"R$^2$ = {r2_val:.3f}\nRMSE = {best_rmse:.2f}%\n"
            f"k = {best_k:.0f} W/(kWh/d)",
            transform=ax.transAxes, fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.set_xlabel("Full 8760h PVGIS advantage (%)", fontsize=9)
    ax.set_ylabel("Monthly reduced-order advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(c) Reduced model validation (31 anchors)", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 3c — Grid-scale geographic inversion: NASA POWER 1° China land, "
                 f"{len(gdf)} cells, r={r_grid:.2f} (vs 31-pt -0.52)",
                 fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig3c_grid_inversion.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig3c_grid_inversion.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"\nMain Fig 3c saved. grid {len(gdf)} cells r={r_grid:.3f}, validation R2={r2_val:.3f}")


if __name__ == "__main__":
    main()
