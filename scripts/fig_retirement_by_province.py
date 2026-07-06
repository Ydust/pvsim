"""按省份的退役潮压力地图: 哪些省 2030s/2040s 面临的报废潮最大。

寿命按晶硅 25年(真实在网主体)。按真实投产年逐省统计:
  retirement_year[plant] = install_year + 25
  按省份聚合到三个时段: 2025-2034 / 2035-2044 / 2045-2054, 看Top省压力。
另出一张PV点按"退役年"上色的地图。
运行: python -m scripts.fig_retirement_by_province  输出: figures/22_retirement_by_province.png
"""

import os
import sys
import json
from collections import defaultdict

import numpy as np
from pvsim import viz
from pvsim.viz import plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
ADM = "CHN_adm_shp__0__CHN_adm_shp.geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/figures/22_retirement_by_province.png"
LIFE = 25
ASPECT = 1.0 / np.cos(np.radians(36))
WINDOWS = [(2025, 2034, "2025–2034"), (2035, 2044, "2035–2044"), (2045, 2054, "2045–2054")]

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
    try: return float(x)
    except Exception: return 0.0


def main():
    viz.setup()
    plants = []
    for ft in load(SOLAR)["features"]:
        p = ft["properties"]
        if p.get("Status") != "operating": continue
        g = ft.get("geometry") or {}
        if g.get("type") != "Point": continue
        try: y = int(float(p.get("Start_year")))
        except Exception: continue
        lon, lat = g["coordinates"][:2]
        if not (70 < lon < 140 and 15 < lat < 55 and 2000 <= y <= 2024): continue
        plants.append({"lon": lon, "lat": lat,
                       "cap": max(num(p.get("Capacity__MW_")), 0.1) / 1000.0,  # GW
                       "prov": p.get("State_Province", "?"),
                       "y": y, "ret": y + LIFE})
    print(f"分析 {len(plants)} 座电站")

    # 各省 × 时段 (GW)
    by_prov_win = defaultdict(lambda: [0.0] * len(WINDOWS))
    by_prov_total = defaultdict(float)
    for pl in plants:
        by_prov_total[pl["prov"]] += pl["cap"]
        for j, (a, b, _) in enumerate(WINDOWS):
            if a <= pl["ret"] <= b:
                by_prov_win[pl["prov"]][j] += pl["cap"]
    # Top 15 省按"总退役"
    top = sorted(by_prov_total.items(), key=lambda x: -x[1])[:15]
    names = [PROV_CN.get(k, k) for k, _ in top][::-1]
    mat = np.array([by_prov_win[k] for k, _ in top])[::-1]   # rows=省, cols=时段

    fig = plt.figure(figsize=(14, 8.5))
    ax_map = fig.add_axes([0.04, 0.06, 0.56, 0.88])
    ax_bar = fig.add_axes([0.66, 0.10, 0.30, 0.82])

    # 国界
    geom = load(ADM)["features"][0]["geometry"]
    polys = [np.array(p[0]) for p in (geom["coordinates"] if geom["type"] == "MultiPolygon"
                                      else [geom["coordinates"]])]
    for ext in polys:
        ax_map.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b", lw=0.5, zorder=1)
    lons = np.array([pl["lon"] for pl in plants]); lats = np.array([pl["lat"] for pl in plants])
    caps = np.array([pl["cap"] * 1000 for pl in plants])    # 回到MW做大小
    rets = np.array([pl["ret"] for pl in plants])
    sc = ax_map.scatter(lons, lats, s=2 + 1.4 * np.sqrt(caps), c=rets, cmap="plasma",
                        vmin=2030, vmax=2050, alpha=0.7, edgecolors="none", zorder=2)
    cbar = fig.colorbar(sc, ax=ax_map, shrink=0.55, pad=0.01)
    cbar.set_label(f"退役年(=投产+{LIFE})")
    ax_map.set_aspect(ASPECT); ax_map.set_xlim(72, 136); ax_map.set_ylim(16, 54)
    ax_map.set_xlabel("经度 °E"); ax_map.set_ylabel("纬度 °N")
    ax_map.set_title(f"光伏电站按退役年着色 (晶硅寿命{LIFE}年; 暖色=早退役)", fontweight="bold")
    ax_map.grid(alpha=0.2)

    # 右: 堆叠条 (Top15省, 三时段)
    y = np.arange(len(names))
    cum = np.zeros(len(names))
    colors = ["#fdae6b", "#e6550d", "#7b1f10"]
    for j, (_, _, lab) in enumerate(WINDOWS):
        ax_bar.barh(y, mat[:, j], left=cum, color=colors[j], label=lab, edgecolor="white")
        cum += mat[:, j]
    ax_bar.set_yticks(y); ax_bar.set_yticklabels(names, fontsize=9)
    ax_bar.set_xlabel("退役量 (GW)")
    ax_bar.set_title("各省退役压力按时段 (Top15)", fontsize=11)
    ax_bar.legend(loc="lower right", fontsize=8); ax_bar.grid(axis="x", alpha=0.3)
    for i, t in enumerate(cum):
        ax_bar.text(t, y[i], f" {t:.1f}", va="center", fontsize=8)

    fig.suptitle(f"全国光伏退役潮压力地图 (晶硅寿命{LIFE}年外推) — 三个十年窗口",
                 fontweight="bold")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成 {OUT}")
    for k, v in top[:8]:
        wins = by_prov_win[k]
        print(f"  {PROV_CN.get(k, k)}: 总{v:.1f}GW  ({WINDOWS[0][2]}: {wins[0]:.1f}, {WINDOWS[1][2]}: {wins[1]:.1f}, {WINDOWS[2][2]}: {wins[2]:.1f})")


if __name__ == "__main__":
    main()
