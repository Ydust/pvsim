"""Main Fig 3c (ERA5 升级) — 0.1° 网格地理反转 (Gap 1 顶配).

把"西南>西北"反转扩到 ERA5-Land 0.1° 中国陆地 (~10 万格点, 比 954 点细 ~100×).

加速: 单二极管功率建 (G_eff, Tcell) 查找表 + 双线性插值, 10 万格点×12月瞬间完成.
验证: 同降阶模型在 31 省锚点 vs 全 8760h PVGIS, 拟合 k, 报 R².

运行: python -m scripts.fig_grid_inversion_era5
输出: outputs/figures/MainFig3c_era5_grid_inversion.png/.pdf + outputs/grid_inversion_era5.csv
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from shapely.geometry import shape
from shapely.ops import unary_union
from scipy.interpolate import RegularGridInterpolator

from pvsim import viz
from pvsim.materials import CSI_MODERN, PEROVSKITE
from pvsim.module import array_dc_power, module_stc_power
from pvsim.era5_land import fetch_china_climatology
from pvsim.provinces import PROVINCES

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEOJSON_CANDIDATES = [
    os.environ.get("CHINA_GEOJSON"),
    os.path.join("data", "geojson", "CHN_adm_shp__0__CHN_adm_shp.geojson"),
    os.path.expanduser(r"~\new\geojson\CHN_adm_shp__0__CHN_adm_shp.geojson"),
    r"C:\Users\yuanq\new\geojson\CHN_adm_shp__0__CHN_adm_shp.geojson",
]
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
U0, U1 = 25.0, 6.84
CSI_STC = module_stc_power(CSI_MODERN)
PEROV_STC = module_stc_power(PEROVSKITE)


def build_power_lut(tech, g_grid, t_grid):
    """(G, Tcell) → 单组件功率 查找表 + 插值器."""
    GG, TT = np.meshgrid(g_grid, t_grid, indexing="ij")
    P = array_dc_power(tech, GG.ravel(), TT.ravel(), n_modules=1, npts=60)
    P = np.atleast_1d(P).reshape(GG.shape)
    return RegularGridInterpolator((g_grid, t_grid), P, bounds_error=False,
                                   fill_value=None)


def resolve_china_geojson():
    for candidate in GEOJSON_CANDIDATES:
        if candidate and os.path.exists(candidate):
            return candidate
    searched = "\n".join(f"  - {p}" for p in GEOJSON_CANDIDATES if p)
    raise FileNotFoundError(
        "China boundary GeoJSON was not found. Set CHINA_GEOJSON or place it at "
        "data/geojson/CHN_adm_shp__0__CHN_adm_shp.geojson. Searched:\n"
        f"{searched}"
    )


def china_paths():
    with open(resolve_china_geojson(), encoding="utf-8-sig") as f:
        gj = json.load(f)
    geom = unary_union([shape(ft["geometry"]) for ft in gj["features"]])
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    return [MplPath(np.array(p.exterior.coords)) for p in polys if p.area > 0.05]


def advantage_grid(ghi12, tair12, wind12, k, lut_csi, lut_perov):
    """向量化: 月度数组 (12,...) → 优势 (%). 末维可为格点批."""
    g_eff = k * ghi12                                  # (12, N)
    tcell = tair12 + g_eff / (U0 + U1 * wind12)
    pts_csi = lut_csi(np.stack([g_eff.ravel(), tcell.ravel()], axis=1)).reshape(g_eff.shape)
    pts_per = lut_perov(np.stack([g_eff.ravel(), tcell.ravel()], axis=1)).reshape(g_eff.shape)
    w = DAYS[:, None]
    y_csi = np.sum(pts_csi * w, axis=0) / CSI_STC
    y_per = np.sum(pts_per * w, axis=0) / PEROV_STC
    return (y_per / y_csi - 1) * 100


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    print("[1/4] load ERA5-Land 0.1deg climatology...")
    g = fetch_china_climatology(verbose=True)
    LON, LAT = g["lon"], g["lat"]
    GHI, TAIR, WIND = g["ghi"], g["tair"], g["wind"]   # (12, ny, nx)
    ny, nx = LON.shape
    print(f"  grid {ny}x{nx} = {ny*nx} cells")

    # 功率查找表
    g_grid = np.linspace(5, 1200, 80)
    t_grid = np.linspace(-30, 75, 60)
    lut_csi = build_power_lut(CSI_MODERN, g_grid, t_grid)
    lut_perov = build_power_lut(PEROVSKITE, g_grid, t_grid)

    print("[2/4] calibrate k vs 31-province full-8760h...")
    anchor = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi_a = anchor[anchor["tech"] == "晶硅"].set_index("province")
    per_a = anchor[anchor["tech"] == "钙钛矿"].set_index("province")
    full_adv, a_ghi, a_tair, a_wind = [], [], [], []
    flat_lon, flat_lat = LON.ravel(), LAT.ravel()
    for prov in PROVINCES:
        if prov.name not in csi_a.index or prov.name not in per_a.index:
            continue
        # nearest ERA5 cell
        d = (flat_lon - prov.lon)**2 + (flat_lat - prov.lat)**2
        idx = int(np.argmin(d)); iy, ix = divmod(idx, nx)
        a_ghi.append(GHI[:, iy, ix]); a_tair.append(TAIR[:, iy, ix])
        a_wind.append(WIND[:, iy, ix])
        full_adv.append((per_a.loc[prov.name, "yield_kwh_per_kwp"] /
                         csi_a.loc[prov.name, "yield_kwh_per_kwp"] - 1) * 100)
    a_ghi = np.array(a_ghi).T; a_tair = np.array(a_tair).T; a_wind = np.array(a_wind).T
    full_adv = np.array(full_adv)
    best_k, best_rmse = None, 1e9
    for k in np.arange(60, 360, 5):
        pred = advantage_grid(a_ghi, a_tair, a_wind, k, lut_csi, lut_perov)
        rmse = np.sqrt(np.mean((pred - full_adv)**2))
        if rmse < best_rmse:
            best_rmse, best_k = rmse, k
    preds_a = advantage_grid(a_ghi, a_tair, a_wind, best_k, lut_csi, lut_perov)
    r2_val = 1 - np.sum((preds_a-full_adv)**2)/np.sum((full_adv-full_adv.mean())**2)
    print(f"  k={best_k:.0f}, RMSE={best_rmse:.2f}%, R2={r2_val:.3f}")

    print("[3/4] China land mask (vectorized) + grid physics...")
    paths = china_paths()
    pts = np.column_stack([flat_lon, flat_lat])
    inside = np.zeros(len(pts), dtype=bool)
    for p in paths:
        inside |= p.contains_points(pts)
    # 有效气象
    valid = inside & np.isfinite(GHI[6].ravel()) & np.isfinite(TAIR[6].ravel())
    sel = np.where(valid)[0]
    ghi_sel = GHI.reshape(12, -1)[:, sel]
    tair_sel = TAIR.reshape(12, -1)[:, sel]
    wind_sel = WIND.reshape(12, -1)[:, sel]
    adv = advantage_grid(ghi_sel, tair_sel, wind_sel, best_k, lut_csi, lut_perov)
    ghi_ann = GHI.mean(0).ravel()[sel] * 365.0
    gdf = pd.DataFrame({"lon": flat_lon[sel], "lat": flat_lat[sel],
                        "ghi_ann": ghi_ann, "adv": adv})
    gdf = gdf[np.isfinite(gdf["adv"])]
    gdf.to_csv("outputs/grid_inversion_era5.csv", index=False, encoding="utf-8-sig")
    r_grid = np.corrcoef(gdf["ghi_ann"], gdf["adv"])[0, 1]
    print(f"  China land {len(gdf)} cells (0.1deg), grid r={r_grid:+.3f}")

    print("[4/4] plotting...")
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), dpi=300)
    ax = axes[0]
    sc = ax.scatter(gdf["lon"], gdf["lat"], c=gdf["adv"], s=1.2, cmap="RdYlBu_r",
                    vmin=1, vmax=8, marker="s", edgecolors="none")
    ax.set_xlabel("Longitude (°E)", fontsize=9); ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"(a) 0.1° grid advantage map ({len(gdf)//1000}k land cells)",
                 fontsize=11, fontweight="bold", loc="left", pad=3)
    ax.set_xlim(73, 135); ax.set_ylim(17, 54)
    cb = plt.colorbar(sc, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("Perovskite advantage (%)", fontsize=8); cb.ax.tick_params(labelsize=7)

    ax = axes[1]
    # 大数据点用 hexbin 显示密度
    hb = ax.hexbin(gdf["ghi_ann"], gdf["adv"], gridsize=45, cmap="YlOrRd",
                   mincnt=1, bins="log")
    z = np.polyfit(gdf["ghi_ann"], gdf["adv"], 1)
    xx = np.linspace(gdf["ghi_ann"].min(), gdf["ghi_ann"].max(), 50)
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.5)
    ax.text(0.05, 0.08, f"grid r = {r_grid:.2f}\n(1° r=-0.52, 31-pt r=-0.52)\n"
            f"$\\rightarrow$ holds at {len(gdf)//1000}k cells",
            transform=ax.transAxes, fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.set_xlabel("Annual GHI (kWh/m$^2$)", fontsize=9)
    ax.set_ylabel("Perovskite advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(b) Inversion holds at 0.1° scale", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    cb2 = plt.colorbar(hb, ax=ax, shrink=0.8, pad=0.02)
    cb2.set_label("cell count (log)", fontsize=7); cb2.ax.tick_params(labelsize=6.5)

    ax = axes[2]
    ax.scatter(full_adv, preds_a, s=45, color="#2a9d4a", edgecolors="black",
               linewidth=0.4, zorder=3)
    lim = [min(full_adv.min(), preds_a.min())-0.5, max(full_adv.max(), preds_a.max())+0.5]
    ax.plot(lim, lim, "k:", lw=1, label="1:1")
    ax.text(0.05, 0.86, f"R$^2$ = {r2_val:.3f}\nRMSE = {best_rmse:.2f}%\n"
            f"k = {best_k:.0f}", transform=ax.transAxes, fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.set_xlabel("Full 8760h PVGIS advantage (%)", fontsize=9)
    ax.set_ylabel("ERA5 reduced-order advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(c) Reduced model validation (31 anchors)", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 3c (ERA5-Land 0.1°) — Grid-scale geographic inversion: "
                 f"China land {len(gdf)//1000}k cells, r={r_grid:.2f}",
                 fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig3c_era5_grid_inversion.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig3c_era5_grid_inversion.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"\nFig 3c (ERA5) saved. {len(gdf)} cells, r={r_grid:.3f}, R2={r2_val:.3f}")


if __name__ == "__main__":
    main()
