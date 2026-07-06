"""省级 LCOE 对比地图: 光照+温度组合, 哪些省该用钙钛矿/晶硅。

把 12 城实测年比发电量按 IDW 插值到 31 省会, 用 lcoe.py 算两种技术的 LCOE,
然后把所有真实光伏电站点按"赢家"上色: 蓝=晶硅便宜, 橙=钙钛矿便宜 (中值衰减情景)。
运行: python -m scripts.fig_lcoe_provinces   输出: outputs/figures/26_lcoe_provinces.png
"""

import os
import sys
import json
from collections import defaultdict

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
OUT = "outputs/figures/26_lcoe_provinces.png"
ASPECT = 1.0 / np.cos(np.radians(36))

# 省会经纬度 (简化, 主要省份)
PROV_CAP = {
    "新疆": (43.83, 87.62), "Xinjiang": (43.83, 87.62),
    "青海": (36.62, 101.78), "Qinghai": (36.62, 101.78),
    "山西": (37.87, 112.55), "Shanxi": (37.87, 112.55),
    "内蒙古": (40.84, 111.75), "Inner Mongolia": (40.84, 111.75),
    "山东": (36.65, 117.00), "Shandong": (36.65, 117.00),
    "宁夏": (38.49, 106.23), "Ningxia": (38.49, 106.23),
    "甘肃": (36.05, 103.83), "Gansu": (36.05, 103.83),
    "河北": (38.05, 114.50), "Hebei": (38.05, 114.50),
    "江苏": (32.06, 118.78), "Jiangsu": (32.06, 118.78),
    "陕西": (34.27, 108.95), "Shaanxi": (34.27, 108.95),
    "河南": (34.75, 113.62), "Henan": (34.75, 113.62),
    "安徽": (31.86, 117.28), "Anhui": (31.86, 117.28),
    "云南": (25.04, 102.71), "Yunnan": (25.04, 102.71),
    "四川": (30.67, 104.07), "Sichuan": (30.67, 104.07),
    "浙江": (30.27, 120.15), "Zhejiang": (30.27, 120.15),
    "湖北": (30.59, 114.30), "Hubei": (30.59, 114.30),
    "湖南": (28.23, 112.93), "Hunan": (28.23, 112.93),
    "广东": (23.13, 113.26), "Guangdong": (23.13, 113.26),
    "吉林": (43.82, 125.32), "Jilin": (43.82, 125.32),
    "黑龙江": (45.75, 126.63), "Heilongjiang": (45.75, 126.63),
    "辽宁": (41.80, 123.43), "Liaoning": (41.80, 123.43),
    "江西": (28.68, 115.89), "Jiangxi": (28.68, 115.89),
    "贵州": (26.65, 106.63), "Guizhou": (26.65, 106.63),
    "西藏": (29.65, 91.14), "Tibet": (29.65, 91.14), "Xizang": (29.65, 91.14),
    "广西": (22.82, 108.36), "Guangxi": (22.82, 108.36),
    "福建": (26.07, 119.30), "Fujian": (26.07, 119.30),
    "海南": (20.04, 110.32), "Hainan": (20.04, 110.32),
    "北京": (39.90, 116.41), "Beijing": (39.90, 116.41),
    "天津": (39.13, 117.20), "Tianjin": (39.13, 117.20),
    "上海": (31.23, 121.47), "Shanghai": (31.23, 121.47),
    "重庆": (29.56, 106.55), "Chongqing": (29.56, 106.55),
}


def num(x):
    try: return float(x)
    except Exception: return 0.0


def idw(target_lat, target_lon, ref_lats, ref_lons, ref_vals, p=2):
    d2 = (ref_lats - target_lat) ** 2 + (ref_lons - target_lon) ** 2 + 1e-6
    w = 1.0 / d2 ** (p / 2)
    return float(np.sum(w * ref_vals) / np.sum(w))


def main():
    viz.setup()
    # 12 城实测年比发电
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

    # 各省 LCOE: 用省会插值 yield, 假设固定容量 4.48 kWp (跟之前 12 城一致)
    kwp = 4.48
    prov_lcoe = {}
    for pname, (lat, lon) in PROV_CAP.items():
        yc = idw(lat, lon, rlat, rlon, ryc)
        yp = idw(lat, lon, rlat, rlon, ryp)
        e1_c = yc * kwp; e1_p = yp * kwp
        lc = lcoe(CSI_EARLY, kwp, e1_c)["lcoe"] * 100  # 分/kWh
        lp = lcoe(PEROVSKITE, kwp, e1_p, "代表性")["lcoe"] * 100
        prov_lcoe[pname] = (lc, lp)

    # 国界
    with open(os.path.join(GEO, ADM), encoding="utf-8-sig") as f:
        geom = json.load(f)["features"][0]["geometry"]
    polys = [np.array(p[0]) for p in (geom["coordinates"] if geom["type"] == "MultiPolygon"
                                      else [geom["coordinates"]])]

    # 真实光伏点 + 各点所在省的 LCOE 差 (perovskite - csi, 负=钙钛矿便宜)
    lons, lats, caps, diffs = [], [], [], []
    with open(os.path.join(GEO, SOLAR), encoding="utf-8-sig") as f:
        for ft in json.load(f)["features"]:
            p = ft["properties"]
            if p.get("Status") != "operating": continue
            g = ft.get("geometry") or {}
            if g.get("type") != "Point": continue
            lon, lat = g["coordinates"][:2]
            if not (70 < lon < 140 and 15 < lat < 55): continue
            prov = p.get("State_Province", "?")
            if prov not in prov_lcoe: continue
            lc, lp = prov_lcoe[prov]
            lons.append(lon); lats.append(lat)
            caps.append(max(num(p.get("Capacity__MW_")), 0.1))
            diffs.append(lp - lc)
    lons = np.array(lons); lats = np.array(lats); caps = np.array(caps); diffs = np.array(diffs)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 7.2),
                                    gridspec_kw={"width_ratios": [2.2, 1]})
    # 国界 + 散点
    for ext in polys:
        ax1.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b", lw=0.5)
    vmax = max(abs(diffs.min()), abs(diffs.max()))
    sc = ax1.scatter(lons, lats, s=2 + 1.4 * np.sqrt(caps),
                     c=diffs, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                     alpha=0.7, edgecolors="none")
    cbar = fig.colorbar(sc, ax=ax1, shrink=0.55, pad=0.01)
    cbar.set_label("LCOE 差 (钙钛矿 − 晶硅, 分/kWh)\n负=钙钛矿便宜  正=晶硅便宜")
    ax1.set_aspect(ASPECT); ax1.set_xlim(72, 136); ax1.set_ylim(16, 54)
    ax1.set_xlabel("经度 °E"); ax1.set_ylabel("纬度 °N")
    ax1.set_title("真实光伏站点的 LCOE 赢家 (钙钛矿代表情景)", fontweight="bold")
    ax1.grid(alpha=0.2)

    # 右: 省级 LCOE 表(主要省份, 按差值排)
    used_prov = {p: prov_lcoe[p] for p in prov_lcoe if p in (
        "新疆 青海 山西 内蒙古 山东 宁夏 甘肃 河北 江苏 陕西 河南 安徽 "
        "云南 四川 浙江 湖北 湖南 广东 吉林 黑龙江 辽宁 江西 贵州 西藏 "
        "广西 福建 海南 北京 上海 重庆".split())}
    items = sorted(used_prov.items(), key=lambda x: x[1][1] - x[1][0])
    names = [n for n, _ in items]
    lcs = np.array([v[0] for _, v in items])
    lps = np.array([v[1] for _, v in items])
    y = np.arange(len(names))
    ax2.barh(y - 0.20, lcs, 0.4, color=color("c-Si"), label="晶硅 LCOE", alpha=0.85)
    ax2.barh(y + 0.20, lps, 0.4, color=color("perovskite"), label="钙钛矿 LCOE", alpha=0.85)
    ax2.set_yticks(y); ax2.set_yticklabels(names, fontsize=8)
    ax2.set_xlabel("LCOE (分/kWh)")
    ax2.set_title("各省 LCOE 对比 (按差距升序)", fontweight="bold")
    ax2.legend(fontsize=8); ax2.grid(axis="x", alpha=0.3)

    # 全国汇总
    csi_win = sum(1 for _, v in prov_lcoe.items() if v[0] < v[1])
    pero_win = sum(1 for _, v in prov_lcoe.items() if v[1] < v[0])
    fig.suptitle(
        f"省级 LCOE 对比 — 钙钛矿(代表情景)在哪些省划算? "
        f"晶硅赢: {csi_win} 省  /  钙钛矿赢: {pero_win} 省  "
        f"(衰减情景代表性, 含15yr寿命)", fontweight="bold", fontsize=12)
    fig.text(0.5, 0.01,
             "方法: 12城实测年比发电按 IDW 插值省会; LCOE 用各自寿命+衰减+capex (晶硅25yr/1$/Wp, "
             "钙钛矿15yr/0.8$/Wp 代表情景); 不含电网电价 (LCOE 是成本侧)。",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=[0, 0.03, 1, 0.93])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=120)
    plt.close(fig)
    print(f"已生成 {OUT}")
    print(f"  晶硅赢 {csi_win} 省, 钙钛矿赢 {pero_win} 省")
    print("  钙钛矿优势最大的 5 省:")
    pero_best = sorted(used_prov.items(), key=lambda x: x[1][1] - x[1][0])[:5]
    for n, (lc, lp) in pero_best:
        print(f"    {n}: 钙钛矿 {lp:.2f} vs 晶硅 {lc:.2f} (差 {lp-lc:+.2f})")


if __name__ == "__main__":
    main()
