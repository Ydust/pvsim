"""全国真实光伏布局图：用 GEM 真实电站(坐标/容量/省份)落到中国版图。

数据: C:/Users/yuanq/new/geojson
  - CHN_adm_shp...        国界轮廓 (MultiPolygon)
  - China_Solar_Power_Plants_GEM_202406...  13489 座光伏电站(点, 含容量/省份/状态)
点大小∝真实容量, 颜色∝容量(对数), 附 top 省份装机条。
运行: python -m scripts.map_pv_china
输出: outputs/figures/13_pv_china_map.png
"""

import os
import sys
import json
from collections import defaultdict

import numpy as np
import matplotlib.cm as cm
from matplotlib.colors import LogNorm

from pvsim import viz
from pvsim.viz import plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
ADM = "CHN_adm_shp__0__CHN_adm_shp.geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/figures/13_pv_china_map.png"

PROV_CN = {
    "Xinjiang": "新疆", "Qinghai": "青海", "Shanxi": "山西", "Inner Mongolia": "内蒙古",
    "Shandong": "山东", "Ningxia": "宁夏", "Gansu": "甘肃", "Hebei": "河北",
    "Jiangsu": "江苏", "Shaanxi": "陕西", "Henan": "河南", "Anhui": "安徽",
    "Yunnan": "云南", "Sichuan": "四川", "Zhejiang": "浙江", "Hubei": "湖北",
    "Hunan": "湖南", "Guangdong": "广东", "Jilin": "吉林", "Heilongjiang": "黑龙江",
    "Liaoning": "辽宁", "Jiangxi": "江西", "Guizhou": "贵州", "Tibet": "西藏",
    "Xizang": "西藏", "Guangxi": "广西", "Fujian": "福建", "Hainan": "海南",
    "Tianjin": "天津", "Beijing": "北京", "Shanghai": "上海", "Chongqing": "重庆",
}


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
    adm = load(ADM)["features"][0]["geometry"]
    sol = load(SOLAR)["features"]

    lons, lats, caps, provs = [], [], [], []
    for ft in sol:
        p = ft["properties"]
        if p.get("Status") != "operating":
            continue
        g = ft.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][:2]
        if not (70 < lon < 140 and 15 < lat < 55):
            continue
        lons.append(lon); lats.append(lat)
        caps.append(max(num(p.get("Capacity__MW_")), 0.1))
        provs.append(p.get("State_Province", "?"))
    lons = np.array(lons); lats = np.array(lats); caps = np.array(caps)
    total_gw = caps.sum() / 1000.0

    by = defaultdict(float)
    for pr, c in zip(provs, caps):
        by[pr] += c
    top = sorted(by.items(), key=lambda x: -x[1])[:10]

    fig, ax = plt.subplots(figsize=(11.5, 9))

    # 国界
    polys = adm["coordinates"] if adm["type"] == "MultiPolygon" else [adm["coordinates"]]
    for poly in polys:
        ext = np.array(poly[0])
        ax.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b",
                lw=0.5, zorder=1)

    # 电站点: 大小∝√容量, 颜色∝容量(对数)
    order = np.argsort(caps)            # 小的先画, 大的在上
    sc = ax.scatter(lons[order], lats[order],
                    s=2 + 1.6 * np.sqrt(caps[order]),
                    c=caps[order], cmap="plasma", norm=LogNorm(vmin=1, vmax=2000),
                    alpha=0.62, edgecolors="none", zorder=2)
    cbar = fig.colorbar(sc, ax=ax, shrink=0.55, pad=0.01)
    cbar.set_label("单站容量 (MW, 对数)")

    ax.set_aspect(1.0 / np.cos(np.radians(36)))
    ax.set_xlim(72, 136); ax.set_ylim(16, 54)
    ax.set_xlabel("经度 °E"); ax.set_ylabel("纬度 °N")
    ax.set_title(f"中国光伏电站真实分布（GEM 2024·运营中）\n"
                 f"{len(lons):,} 座电站 · 合计 {total_gw:.0f} GW", fontweight="bold")
    ax.grid(alpha=0.2)

    # 容量大小图例
    for cap_ref in (50, 500, 2000):
        ax.scatter([], [], s=2 + 1.6 * np.sqrt(cap_ref), c="gray", alpha=0.6,
                   label=f"{cap_ref} MW")
    ax.legend(scatterpoints=1, labelspacing=1.1, title="装机规模", loc="lower left",
              framealpha=0.9)

    # top 省份装机条 (右下内嵌, 避开标题与版图)
    ax_in = fig.add_axes([0.60, 0.13, 0.22, 0.25])
    names = [PROV_CN.get(k, k) for k, _ in top][::-1]
    vals = [v / 1000 for _, v in top][::-1]
    ax_in.barh(range(len(names)), vals, color="#d2691e")
    ax_in.set_yticks(range(len(names))); ax_in.set_yticklabels(names, fontsize=8)
    ax_in.set_title("运营装机 Top10 省 (GW)", fontsize=9)
    ax_in.tick_params(axis="x", labelsize=7)
    for i, v in enumerate(vals):
        ax_in.text(v, i, f" {v:.0f}", va="center", fontsize=7)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成 {OUT}")
    print(f"  运营电站 {len(lons):,} 座, 合计 {total_gw:.0f} GW")
    print("  Top省(GW):", [(PROV_CN.get(k, k), round(v / 1000, 1)) for k, v in top])


if __name__ == "__main__":
    main()
