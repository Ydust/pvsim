"""各省电网碳强度(由煤电反推) + PV 年减排地图。

方法:
  per plant: intensity = Annual_CO2(Mt)×1e9 / (Cap_MW × CF × 8760×1e3)  → kg/kWh
  per province: sum_CO2 / sum_gen = 加权强度(kg/kWh)
  PV 年减排 = PV装机GW × 1300 kWh/kWp/yr × 该省强度 = Mt/yr
注意: 这是"煤电折算碳强度"(占中国电网~60%, 上限近似 PV 边际替代煤电); 全口径电网更低。
运行: python -m scripts.fig_pv_carbon_by_province  输出: figures/21_pv_carbon_by_province.png
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
COAL = "China_coal_power_plants_vJan2024_3__0__China_coal_power_plants_vJan2024_3.geojson"
OUT = "outputs/figures/21_pv_carbon_by_province.png"
ASPECT = 1.0 / np.cos(np.radians(36))

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


def province_coal_intensity():
    """每电厂强度 = HR(Btu/kWh) × EF(kg/TJ) × 1.0551e-9, 按容量加权聚合(CF字段全空, 不可用)。"""
    weighted, total_w = defaultdict(float), defaultdict(float)
    for ft in load(COAL)["features"]:
        p = ft["properties"]
        if p.get("Status") != "operating": continue
        cap = num(p.get("Capacity__MW_"))
        hr = num(p.get("Heat_rate__Btu_per_kWh_"))
        ef = num(p.get("Emission_factor__kg_of_CO2_per_"))   # kg/TJ 燃料
        prov = p.get("Subnational_unit__province__sta", "?")
        if cap <= 0 or hr <= 0 or ef <= 0: continue
        intens = hr * ef * 1.0551e-9       # kg/kWh
        weighted[prov] += intens * cap; total_w[prov] += cap
    return {p: weighted[p] / total_w[p] for p in weighted if total_w[p] > 0}


def province_pv_gw():
    out = defaultdict(float)
    for ft in load(SOLAR)["features"]:
        p = ft["properties"]
        if p.get("Status") != "operating": continue
        out[p.get("State_Province", "?")] += num(p.get("Capacity__MW_")) / 1000
    return out


def pv_points():
    lons, lats, caps, provs = [], [], [], []
    for ft in load(SOLAR)["features"]:
        p = ft["properties"]
        if p.get("Status") != "operating": continue
        g = ft.get("geometry") or {}
        if g.get("type") != "Point": continue
        lon, lat = g["coordinates"][:2]
        if not (70 < lon < 140 and 15 < lat < 55): continue
        lons.append(lon); lats.append(lat)
        caps.append(max(num(p.get("Capacity__MW_")), 0.1))
        provs.append(p.get("State_Province", "?"))
    return np.array(lons), np.array(lats), np.array(caps), provs


def main():
    viz.setup()
    intens = province_coal_intensity()
    pvcap = province_pv_gw()
    lons, lats, caps, provs = pv_points()
    # 各省年减排 (Mt/yr) = PV_GW × 1.3 TWh/GW × 强度 kg/kWh
    avoid = {p: pvcap[p] * 1.3 * intens.get(p, 0.6) for p in pvcap}
    # 每个PV点按所在省强度上色
    plant_intens = np.array([intens.get(p, 0.6) for p in provs])

    # 国界
    geom = load(ADM)["features"][0]["geometry"]
    polys = [np.array(p[0]) for p in (geom["coordinates"] if geom["type"] == "MultiPolygon"
                                      else [geom["coordinates"]])]

    fig = plt.figure(figsize=(13, 8.5))
    ax = fig.add_axes([0.06, 0.06, 0.60, 0.88])
    axb = fig.add_axes([0.70, 0.10, 0.27, 0.82])

    for ext in polys:
        ax.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b", lw=0.5, zorder=1)
    sc = ax.scatter(lons, lats, s=2 + 1.4 * np.sqrt(caps), c=plant_intens, cmap="YlOrRd",
                    vmin=0.5, vmax=1.1, alpha=0.7, edgecolors="none", zorder=2)
    cbar = fig.colorbar(sc, ax=ax, shrink=0.55, pad=0.01)
    cbar.set_label("所在省煤电折算碳强度 (kg CO2/kWh)")
    ax.set_aspect(ASPECT); ax.set_xlim(72, 136); ax.set_ylim(16, 54)
    ax.set_xlabel("经度 °E"); ax.set_ylabel("纬度 °N")
    ax.set_title("光伏电站按所在省电网碳强度着色（深=替代煤电避碳价值高）", fontweight="bold")
    ax.grid(alpha=0.2)

    # 右: top省年减排
    top = sorted(avoid.items(), key=lambda x: -x[1])[:15]
    names = [PROV_CN.get(k, k) for k, _ in top][::-1]
    vals = [v for _, v in top][::-1]
    ints = [intens.get(k, 0.6) for k, _ in top][::-1]
    axb.barh(range(len(names)), vals, color=plt.cm.YlOrRd(np.array(ints) / 1.1))
    axb.set_yticks(range(len(names))); axb.set_yticklabels(names, fontsize=9)
    axb.set_title("PV 年减排 Top15 省 (Mt CO2/yr)", fontsize=10)
    axb.tick_params(axis="x", labelsize=8); axb.grid(axis="x", alpha=0.3)
    for i, (v, it) in enumerate(zip(vals, ints)):
        axb.text(v, i, f" {v:.0f} ({it:.2f})", va="center", fontsize=8)
    axb.text(0.02, -0.06, "标注: 减排Mt (强度kg/kWh)", transform=axb.transAxes, fontsize=7, color="#666")

    total = sum(avoid.values())
    fig.suptitle(f"全国 PV 年减排 ≈ {total:.0f} Mt CO2/yr  (基于煤电折算省级碳强度)", fontweight="bold")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成 {OUT}")
    print(f"  全国 PV 年减排合计 {total:.0f} Mt/yr")
    for k, v in top[:8]:
        print(f"  {PROV_CN.get(k, k)}: {v:.0f} Mt/yr  (强度 {intens.get(k, 0.6):.2f} kg/kWh)")


if __name__ == "__main__":
    main()
