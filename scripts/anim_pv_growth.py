"""全国光伏装机"逐年增长"动画 (真实数据)：用每座电站真实投产年(Start_year)驱动。

2010→2024 全国光伏点逐年累积, 当年新增高亮(红), 已建为暖橙; 配累计容量曲线。
直观看中国光伏怎么一步步铺开(先东部分布式→后西北大基地)、装机如何指数增长。
运行: python -m scripts.anim_pv_growth   输出: outputs/animations/pv_growth.gif (+ _peak.png)
"""

import os
import sys
import json

import numpy as np
import matplotlib.animation as animation

from pvsim import viz
from pvsim.viz import plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
ADM = "CHN_adm_shp__0__CHN_adm_shp.geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/animations/pv_growth.gif"
Y0, Y1 = 2010, 2024
ASPECT = 1.0 / np.cos(np.radians(36))


def load(fn):
    with open(os.path.join(GEO, fn), encoding="utf-8-sig") as f:
        return json.load(f)


def num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def main():
    viz.setup()
    geom = load(ADM)["features"][0]["geometry"]
    polys = [np.array(p[0]) for p in (geom["coordinates"] if geom["type"] == "MultiPolygon"
                                      else [geom["coordinates"]])]
    lons, lats, caps, syr = [], [], [], []
    for ft in load(SOLAR)["features"]:
        p = ft["properties"]
        if p.get("Status") != "operating":
            continue
        g = ft.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        try:
            y = int(float(p.get("Start_year")))
        except Exception:
            continue
        lon, lat = g["coordinates"][:2]
        if not (70 < lon < 140 and 15 < lat < 55 and 1990 <= y <= 2025):
            continue
        lons.append(lon); lats.append(lat); caps.append(max(num(p.get("Capacity__MW_")), 0.1)); syr.append(y)
    lons, lats, caps, syr = map(np.array, (lons, lats, caps, syr))

    years = list(range(Y0, Y1 + 1))
    cum_gw = [caps[syr <= y].sum() / 1000 for y in years]

    fig, ax = plt.subplots(figsize=(11.5, 9))
    ax_in = fig.add_axes([0.60, 0.14, 0.26, 0.22])

    def update(i):
        Y = years[i]
        ax.clear()
        for ext in polys:
            ax.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b", lw=0.5, zorder=1)
        prev = syr < Y
        new = syr == Y
        ax.scatter(lons[prev], lats[prev], s=2 + 1.3 * np.sqrt(caps[prev]),
                   c="#ff9a3c", alpha=0.45, edgecolors="none", zorder=2)
        ax.scatter(lons[new], lats[new], s=6 + 2.2 * np.sqrt(caps[new]),
                   c="#d62728", alpha=0.9, edgecolors="white", linewidths=0.2, zorder=3)
        ax.set_aspect(ASPECT); ax.set_xlim(72, 136); ax.set_ylim(16, 54)
        ax.set_xlabel("经度 °E"); ax.set_ylabel("纬度 °N"); ax.grid(alpha=0.2)
        gw = caps[syr <= Y].sum() / 1000; n = int((syr <= Y).sum())
        ngw = caps[new].sum() / 1000; nn = int(new.sum())
        ax.set_title(f"中国光伏装机累积 · {Y} 年\n"
                     f"累计 {gw:.0f} GW · {n:,} 座    （红=当年新增 {ngw:.0f} GW / {nn:,} 座）",
                     fontweight="bold")
        # 累计曲线
        ax_in.clear()
        ax_in.plot(years[:i + 1], cum_gw[:i + 1], "-o", color="#d62728", ms=3)
        ax_in.set_xlim(Y0, Y1); ax_in.set_ylim(0, max(cum_gw) * 1.08)
        ax_in.set_title("累计装机 (GW)", fontsize=9)
        ax_in.tick_params(labelsize=7); ax_in.grid(alpha=0.3)
        ax_in.scatter([Y], [cum_gw[i]], color="#d62728", zorder=5)
        ax_in.text(Y0 + 0.3, max(cum_gw) * 0.9, f"{gw:.0f} GW", fontsize=10,
                   color="#d62728", fontweight="bold")
        return []

    anim = animation.FuncAnimation(fig, update, frames=len(years), interval=750, blit=False)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    anim.save(OUT, writer=animation.PillowWriter(fps=1.4))
    update(len(years) - 1)
    fig.savefig(OUT.replace(".gif", "_peak.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成 {OUT}  ({len(years)} 帧/年, ~0.7s/年)")
    for y, g in zip(years, cum_gw):
        print(f"  {y}: {g:.0f} GW")


if __name__ == "__main__":
    main()
