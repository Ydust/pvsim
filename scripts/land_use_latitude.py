"""占地 × 纬度: 地面电站行间遮挡损失随纬度的规律 (留给图 5 用)。

物理: 行阵列里前排在低太阳角时遮后排; 纬度越高、太阳越低 → 同样行距(GCR)遮挡越重。
用 pvlib infinite_sheds(无限长行)算正面有效辐照 vs 单排基准, 得年遮挡损失 %。
该效应跟电池技术无关(已验证 perov/cSi 比值变化 <0.2%), 故在 POA 层面算即可。

输出: outputs/land_use_latitude.csv + outputs/figures/diag_land_use_latitude.png
运行: python -m scripts.land_use_latitude
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.bifacial import infinite_sheds

from pvsim import viz
from pvsim.provinces import PROVINCES
from pvsim import weather as wx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GCR_STD = 0.40                       # 行业典型固定倾角行距
COLLECTOR_W = 2.0                    # 组件斜宽 (m), pitch = COLLECTOR_W/gcr
REGION_EN = {"华东": "East", "华北": "North", "华南": "South", "华中": "Central",
             "西北": "Northwest", "西南": "Southwest", "东北": "Northeast", "其他": "Other"}
REGION_COL = {"East": "#1f77b4", "North": "#ff7f0e", "South": "#2ca02c", "Central": "#d62728",
              "Northwest": "#9467bd", "Southwest": "#8c564b", "Northeast": "#e377c2",
              "Other": "#7f7f7f"}


def shading_loss(w, tilt, gcr=GCR_STD):
    """阵列正面有效辐照 vs 单排基准的年遮挡损失 (%)。"""
    z = w["solar_zenith"].to_numpy(float); az = w["solar_azimuth"].to_numpy(float)
    r = infinite_sheds.get_irradiance(
        surface_tilt=tilt, surface_azimuth=180.0, solar_zenith=z, solar_azimuth=az,
        gcr=gcr, height=1.0, pitch=COLLECTOR_W/gcr, ghi=w["ghi"].to_numpy(float),
        dhi=w["dhi"].to_numpy(float), dni=w["dni"].to_numpy(float), albedo=0.2)
    e_arr = float(np.nansum(np.clip(r["poa_front"], 0, None)))
    e0 = float(np.nansum(np.clip(w["poa_global"].to_numpy(float), 0, None)))
    return (1 - e_arr/e0) * 100


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    rows = []
    for i, p in enumerate(PROVINCES):
        w = wx.from_pvgis_tmy(p.lat, p.lon, altitude=p.alt, name=p.key)  # tilt=lat
        rows.append({"province": p.name, "region_en": REGION_EN.get(p.region, "Other"),
                     "lat": p.lat, "lon": p.lon,
                     "shading_loss_pct": shading_loss(w, p.lat)})
        if (i+1) % 8 == 0:
            print(f"  {i+1}/{len(PROVINCES)} 省完成...")
    df = pd.DataFrame(rows).sort_values("lat")
    df.to_csv("outputs/land_use_latitude.csv", index=False, encoding="utf-8-sig")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=300)
    # (a) 遮挡损失 vs 纬度
    ax = axes[0]
    for reg, g in df.groupby("region_en"):
        ax.scatter(g["lat"], g["shading_loss_pct"], s=36, color=REGION_COL.get(reg, "#777"),
                   edgecolors="black", linewidth=0.3, label=reg, zorder=3)
    z = np.polyfit(df["lat"], df["shading_loss_pct"], 1)
    xx = np.array([df["lat"].min(), df["lat"].max()])
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.2)
    r = np.corrcoef(df["lat"], df["shading_loss_pct"])[0, 1]
    ax.text(0.05, 0.93, f"r = {r:.2f}", transform=ax.transAxes, fontsize=12,
            fontweight="bold", color="#b2182b", va="top")
    ax.set_xlabel("Latitude (°N)", fontsize=9)
    ax.set_ylabel(f"Inter-row shading loss at GCR={GCR_STD} (%)", fontsize=9)
    ax.set_title("(a) Utility land penalty rises with latitude", fontsize=10.5,
                 fontweight="bold", loc="left")
    ax.legend(fontsize=6.8, ncol=2, frameon=False); ax.grid(alpha=0.25, lw=0.3)
    ax.tick_params(labelsize=8)
    # (b) 中国地图: 按遮挡损失着色
    ax = axes[1]
    sc = ax.scatter(df["lon"], df["lat"], s=90, c=df["shading_loss_pct"], cmap="YlOrRd",
                    edgecolors="black", linewidth=0.4, zorder=3, vmin=2, vmax=11)
    ax.set_xlim(73, 135); ax.set_ylim(17, 54)
    ax.set_xlabel("Longitude (°E)", fontsize=9); ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.set_title("(b) Same penalty, mapped (north = worse)", fontsize=10.5,
                 fontweight="bold", loc="left")
    cb = plt.colorbar(sc, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label("shading loss (%)", fontsize=8); cb.ax.tick_params(labelsize=7)
    ax.tick_params(labelsize=8); ax.grid(alpha=0.2, lw=0.3)

    fig.suptitle("Land use × latitude (tech-independent): high-latitude utility PV pays a "
                 "row-spacing penalty (~2% → ~11%)", fontsize=11, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig("outputs/figures/diag_land_use_latitude.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    lo, hi = df.iloc[0], df.iloc[-1]
    print(f"完成。遮挡损失 {lo['province']}({lo['lat']:.0f}°)={lo['shading_loss_pct']:.1f}% → "
          f"{hi['province']}({hi['lat']:.0f}°)={hi['shading_loss_pct']:.1f}% | r(lat,loss)={r:.2f}")


if __name__ == "__main__":
    main()
