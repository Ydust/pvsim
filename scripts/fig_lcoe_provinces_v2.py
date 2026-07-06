"""省级 LCOE 四技术对比: 晶硅 vs 钙钛矿(代表/乐观) vs 钙钛矿/晶硅叠层。

参数对齐:
  晶硅:         $1.0/Wp, 25yr, 0.7%/yr 衰减, 2% burn-in
  钙钛矿代表:   $0.8/Wp, 15yr, 3.0%/yr,    10% burn-in
  钙钛矿乐观:   $0.8/Wp, **25yr** (寿命达标), 1.0%/yr, 5% burn-in
  叠层钙钛矿/Si: $1.5/Wp, 25yr, 0.7%/yr,    5% burn-in, 发电量+8% (叠层效率红利)
运行: python -m scripts.fig_lcoe_provinces_v2
输出: outputs/figures/27_lcoe_4tech.png
"""

import os
import sys
import json
from dataclasses import replace

import numpy as np
import pandas as pd
from pvsim import viz
from pvsim.viz import plt, color
from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cities import CITIES
from pvsim.lcoe import lcoe

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
ADM = "CHN_adm_shp__0__CHN_adm_shp.geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/figures/27_lcoe_4tech.png"
ASPECT = 1.0 / np.cos(np.radians(36))
TANDEM_YIELD_BONUS = 1.08    # 叠层效率红利 (相对钙钛矿)

# 用 replace 构造钙钛矿乐观(寿命25年) 和 叠层
PERO_OPT = replace(PEROVSKITE, lifetime_years=25, degradation_rate=0.010, burn_in_loss=0.05)
TANDEM = replace(PEROVSKITE, name="tandem", name_cn="叠层",
                 lifetime_years=25, degradation_rate=0.007, burn_in_loss=0.05,
                 capex_per_wp=1.5)

PROV_CAP = {
    "新疆": (43.83, 87.62), "青海": (36.62, 101.78), "山西": (37.87, 112.55),
    "内蒙古": (40.84, 111.75), "山东": (36.65, 117.00), "宁夏": (38.49, 106.23),
    "甘肃": (36.05, 103.83), "河北": (38.05, 114.50), "江苏": (32.06, 118.78),
    "陕西": (34.27, 108.95), "河南": (34.75, 113.62), "安徽": (31.86, 117.28),
    "云南": (25.04, 102.71), "四川": (30.67, 104.07), "浙江": (30.27, 120.15),
    "湖北": (30.59, 114.30), "湖南": (28.23, 112.93), "广东": (23.13, 113.26),
    "吉林": (43.82, 125.32), "黑龙江": (45.75, 126.63), "辽宁": (41.80, 123.43),
    "江西": (28.68, 115.89), "贵州": (26.65, 106.63), "西藏": (29.65, 91.14),
    "广西": (22.82, 108.36), "福建": (26.07, 119.30), "海南": (20.04, 110.32),
    "北京": (39.90, 116.41), "天津": (39.13, 117.20), "上海": (31.23, 121.47),
    "重庆": (29.56, 106.55),
}
# 中文 -> 英文 (用于光伏点匹配)
CN2EN = {
    "新疆": "Xinjiang", "青海": "Qinghai", "山西": "Shanxi", "内蒙古": "Inner Mongolia",
    "山东": "Shandong", "宁夏": "Ningxia", "甘肃": "Gansu", "河北": "Hebei",
    "江苏": "Jiangsu", "陕西": "Shaanxi", "河南": "Henan", "安徽": "Anhui",
    "云南": "Yunnan", "四川": "Sichuan", "浙江": "Zhejiang", "湖北": "Hubei",
    "湖南": "Hunan", "广东": "Guangdong", "吉林": "Jilin", "黑龙江": "Heilongjiang",
    "辽宁": "Liaoning", "江西": "Jiangxi", "贵州": "Guizhou", "西藏": "Tibet",
    "广西": "Guangxi", "福建": "Fujian", "海南": "Hainan", "北京": "Beijing",
    "天津": "Tianjin", "上海": "Shanghai", "重庆": "Chongqing",
}
EN2CN = {v: k for k, v in CN2EN.items()}
EN2CN["Xizang"] = "西藏"

TECHS = [
    ("晶硅", "csi", color("c-Si")),
    ("钙钛矿\n(代表)", "pero_rep", color("perovskite")),
    ("钙钛矿\n(乐观25yr)", "pero_opt", "#f7b27e"),
    ("叠层", "tandem", color("tandem")),
]


def num(x):
    try: return float(x)
    except Exception: return 0.0


def idw(lat, lon, ref_lats, ref_lons, vals, p=2):
    d2 = (ref_lats - lat) ** 2 + (ref_lons - lon) ** 2 + 1e-6
    w = 1.0 / d2 ** (p / 2)
    return float(np.sum(w * vals) / np.sum(w))


def main():
    viz.setup()
    df = pd.read_csv("outputs/cities_comparison.csv")
    by_name = {c.name: c for c in CITIES}
    rlat, rlon, ryc, ryp = [], [], [], []
    for _, r in df.iterrows():
        if r["城市"] in by_name:
            c = by_name[r["城市"]]
            rlat.append(c.lat); rlon.append(c.lon)
            ryc.append(r["晶硅比发电"]); ryp.append(r["钙钛矿比发电"])
    rlat = np.array(rlat); rlon = np.array(rlon)
    ryc = np.array(ryc); ryp = np.array(ryp)

    kwp = 4.48
    prov_lcoe = {}
    for pname, (lat, lon) in PROV_CAP.items():
        yc = idw(lat, lon, rlat, rlon, ryc)
        yp = idw(lat, lon, rlat, rlon, ryp)
        e_csi = yc * kwp; e_pero = yp * kwp; e_tan = yp * kwp * TANDEM_YIELD_BONUS
        L = {
            "csi": lcoe(CSI_EARLY, kwp, e_csi)["lcoe"] * 100,
            "pero_rep": lcoe(PEROVSKITE, kwp, e_pero, "代表性")["lcoe"] * 100,
            "pero_opt": lcoe(PERO_OPT, kwp, e_pero)["lcoe"] * 100,
            "tandem": lcoe(TANDEM, kwp, e_tan)["lcoe"] * 100,
        }
        prov_lcoe[pname] = L

    # 国界
    with open(os.path.join(GEO, ADM), encoding="utf-8-sig") as f:
        geom = json.load(f)["features"][0]["geometry"]
    polys = [np.array(p[0]) for p in (geom["coordinates"] if geom["type"] == "MultiPolygon"
                                      else [geom["coordinates"]])]

    # 真实光伏点 + 该省赢家技术 idx
    lons, lats, caps, wins = [], [], [], []
    with open(os.path.join(GEO, SOLAR), encoding="utf-8-sig") as f:
        for ft in json.load(f)["features"]:
            p = ft["properties"]
            if p.get("Status") != "operating": continue
            g = ft.get("geometry") or {}
            if g.get("type") != "Point": continue
            lon, lat = g["coordinates"][:2]
            if not (70 < lon < 140 and 15 < lat < 55): continue
            en = p.get("State_Province", "?")
            cn = EN2CN.get(en, "")
            if cn not in prov_lcoe: continue
            L = prov_lcoe[cn]
            keys = ["csi", "pero_rep", "pero_opt", "tandem"]
            wi = int(np.argmin([L[k] for k in keys]))
            lons.append(lon); lats.append(lat)
            caps.append(max(num(p.get("Capacity__MW_")), 0.1))
            wins.append(wi)
    lons = np.array(lons); lats = np.array(lats); caps = np.array(caps); wins = np.array(wins)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7.5),
                                    gridspec_kw={"width_ratios": [2.0, 1.0]})
    for ext in polys:
        ax1.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b", lw=0.5)
    for tech_i, (tech_name, _, col) in enumerate(TECHS):
        m = wins == tech_i
        if m.any():
            ax1.scatter(lons[m], lats[m], s=2 + 1.4 * np.sqrt(caps[m]),
                        c=col, alpha=0.65, edgecolors="none",
                        label=f"{tech_name.replace(chr(10), '')} ({int(m.sum()):,})")
    ax1.set_aspect(ASPECT); ax1.set_xlim(72, 136); ax1.set_ylim(16, 54)
    ax1.set_xlabel("经度 °E"); ax1.set_ylabel("纬度 °N")
    ax1.set_title("真实站点的 LCOE 赢家技术", fontweight="bold")
    ax1.legend(loc="lower left", fontsize=9, framealpha=0.9)
    ax1.grid(alpha=0.2)

    # 右: 主要省份分组柱
    show_prov = ["新疆", "青海", "甘肃", "宁夏", "内蒙古", "山西", "陕西", "河北",
                 "山东", "江苏", "浙江", "云南", "四川", "广东", "海南", "西藏"]
    bw = 0.20; xs = np.arange(len(show_prov))
    for ti, (tname, key, col) in enumerate(TECHS):
        vals = [prov_lcoe[p][key] for p in show_prov]
        ax2.bar(xs + (ti - 1.5) * bw, vals, bw, color=col,
                label=tname.replace("\n", " "), edgecolor="white", lw=0.3)
    ax2.set_xticks(xs); ax2.set_xticklabels(show_prov, rotation=45, ha="right", fontsize=8)
    ax2.set_ylabel("LCOE (分/kWh)")
    ax2.set_title("主要省份 LCOE 四技术对比", fontweight="bold")
    ax2.legend(fontsize=7, loc="upper left", ncol=2)
    ax2.grid(axis="y", alpha=0.3)

    # 全国汇总
    counts = {k: 0 for k in ["csi", "pero_rep", "pero_opt", "tandem"]}
    for L in prov_lcoe.values():
        counts[min(L, key=L.get)] += 1
    fig.suptitle(
        f"省级 LCOE 四技术比拼 (31 省) — 胜出: 晶硅 {counts['csi']} / 钙钛矿代表 {counts['pero_rep']} / "
        f"钙钛矿乐观 {counts['pero_opt']} / 叠层 {counts['tandem']}",
        fontweight="bold", fontsize=12)
    fig.text(0.5, 0.01,
             "参数: 晶硅 1.0/25yr/0.7%衰减; 钙钛矿代表 0.8/15yr/3%; 钙钛矿乐观 0.8/25yr/1%; "
             "叠层 1.5/25yr/0.7%+发电量+8% (capex单位 USD/Wp)。 12城实测IDW插值省会。",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=[0, 0.03, 1, 0.94])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=120)
    plt.close(fig)
    print(f"已生成 {OUT}")
    for k in counts:
        print(f"  {k}: {counts[k]} 省")
    print("\n各技术全国最低 LCOE 省:")
    for ti, (tname, key, _) in enumerate(TECHS):
        best = min(prov_lcoe.items(), key=lambda x: x[1][key])
        print(f"  {tname.replace(chr(10), ' ')}: {best[0]} {best[1][key]:.2f} 分/kWh")


if __name__ == "__main__":
    main()
