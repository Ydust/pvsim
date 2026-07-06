"""全国真实光伏布局 4 张主题图 (元素均来自真实 GeoJSON 数据)：
  14 PV + 输电网(按电压着色)        —— 大基地如何外送
  15 PV + 煤电厂                    —— 谁是绿电、谁是煤电(碳减排背景)
  16 集中式大基地 vs 分布式         —— 按真实容量分类
  17 钙钛矿优势(基于12城实测插值)   —— 真实站点上"哪里换钙钛矿最划算"
运行: python -m scripts.map_pv_layers   输出: outputs/figures/14..17_*.png
"""

import os
import sys
import json
from collections import defaultdict

import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

from pvsim import viz
from pvsim.viz import plt
from pvsim.cities import CITIES

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
FILES = {
    "adm": "CHN_adm_shp__0__CHN_adm_shp.geojson",
    "solar": "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson",
    "coal": "China_coal_power_plants_vJan2024_3__0__China_coal_power_plants_vJan2024_3.geojson",
    "trans": "China_PowerTransmission_2025_Figshare__0__PowerTransmission_2025_ExportFeatures.geojson",
}
ASPECT = 1.0 / np.cos(np.radians(36))


def load(key):
    with open(os.path.join(GEO, FILES[key]), encoding="utf-8-sig") as f:
        return json.load(f)["features"]


def num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def china_outline(ax):
    geom = load("adm")[0]["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        ext = np.array(poly[0])
        ax.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b", lw=0.5, zorder=1)


def setup_ax(ax, title):
    ax.set_aspect(ASPECT); ax.set_xlim(72, 136); ax.set_ylim(16, 54)
    ax.set_xlabel("经度 °E"); ax.set_ylabel("纬度 °N")
    ax.set_title(title, fontweight="bold"); ax.grid(alpha=0.2)


def pv_points(status="operating"):
    lons, lats, caps, provs = [], [], [], []
    for ft in load("solar"):
        p = ft["properties"]
        if status and p.get("Status") != status:
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
    return np.array(lons), np.array(lats), np.array(caps), provs


# ---------------------------------------------------------------- 14 输电网
def fig_transmission(pv):
    lons, lats, caps, _ = pv
    bands = {"特高压 ≥800kV": ([], "#d62728", 1.0),
             "500–765kV": ([], "#1f77b4", 0.5),
             "<500kV": ([], "#aab2bd", 0.25)}
    for ft in load("trans"):
        g = ft.get("geometry") or {}
        kv = num(ft["properties"].get("voltage")) / 1000.0
        key = "特高压 ≥800kV" if kv >= 800 else ("500–765kV" if kv >= 500 else "<500kV")
        if g.get("type") == "LineString":
            bands[key][0].append(np.array(g["coordinates"]))
        elif g.get("type") == "MultiLineString":
            for seg in g["coordinates"]:
                bands[key][0].append(np.array(seg))

    fig, ax = plt.subplots(figsize=(11.5, 9))
    china_outline(ax)
    for label, (segs, col, lw) in bands.items():
        if segs:
            ax.add_collection(LineCollection(segs, colors=col, linewidths=lw, alpha=0.7, zorder=2))
    ax.scatter(lons, lats, s=2 + 1.4 * np.sqrt(caps), c="#ff8c1a", alpha=0.55,
               edgecolors="none", zorder=3, label="光伏电站")
    setup_ax(ax, "真实光伏布局 + 输电网（按电压等级）")
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=c, lw=2, label=l) for l, (_, c, _) in bands.items()]
    handles.append(Line2D([0], [0], marker="o", color="w", markerfacecolor="#ff8c1a", markersize=8, label="光伏电站"))
    ax.legend(handles=handles, loc="lower left", framealpha=0.9)
    save(fig, "14_pv_transmission")


# ---------------------------------------------------------------- 15 煤电
def fig_coal(pv):
    lons, lats, caps, _ = pv
    clon, clat, ccap = [], [], []
    for ft in load("coal"):
        p = ft["properties"]
        if p.get("Status") != "operating":
            continue
        clon.append(num(p.get("Longitude"))); clat.append(num(p.get("Latitude")))
        ccap.append(max(num(p.get("Capacity__MW_")), 1))
    clon, clat, ccap = np.array(clon), np.array(clat), np.array(ccap)

    fig, ax = plt.subplots(figsize=(11.5, 9))
    china_outline(ax)
    ax.scatter(lons, lats, s=2 + 1.2 * np.sqrt(caps), c="#2ca02c", alpha=0.5,
               edgecolors="none", zorder=2, label=f"光伏 {len(lons):,}座/{caps.sum()/1000:.0f}GW")
    ax.scatter(clon, clat, s=3 + 1.2 * np.sqrt(ccap), c="#5a3a2a", alpha=0.6,
               edgecolors="none", zorder=3, label=f"煤电 {len(clon):,}座/{ccap.sum()/1000:.0f}GW")
    setup_ax(ax, "真实光伏(绿) vs 煤电(褐) 分布 —— 碳减排背景")
    ax.legend(loc="lower left", framealpha=0.9, markerscale=1.5)
    save(fig, "15_pv_coal")


# ---------------------------------------------------------------- 16 集中式 vs 分布式
def fig_utility_distributed(pv):
    lons, lats, caps, _ = pv
    cats = [("大型基地 ≥100MW", caps >= 100, "#d62728"),
            ("集中式 10–100MW", (caps >= 10) & (caps < 100), "#ff7f0e"),
            ("分布式 <10MW", caps < 10, "#2ca02c")]
    fig, ax = plt.subplots(figsize=(11.5, 9))
    china_outline(ax)
    for label, mask, col in cats:
        n = int(mask.sum()); gw = caps[mask].sum() / 1000
        ax.scatter(lons[mask], lats[mask], s=2 + 1.5 * np.sqrt(caps[mask]), c=col,
                   alpha=0.55, edgecolors="none", zorder=2,
                   label=f"{label}: {n:,}座 / {gw:.0f}GW")
    setup_ax(ax, "真实光伏：集中式大基地 vs 分布式")
    ax.legend(loc="lower left", framealpha=0.9, markerscale=1.3)
    save(fig, "16_pv_utility_vs_distributed")


# ---------------------------------------------------------------- 17 钙钛矿优势
def fig_perovskite(pv):
    lons, lats, caps, _ = pv
    df = pd.read_csv("outputs/cities_comparison.csv")
    by_name = {c.name: c for c in CITIES}
    ref = [(by_name[r["城市"]].lat, by_name[r["城市"]].lon, r["钙钛矿优势%"])
           for _, r in df.iterrows() if r["城市"] in by_name]
    rlat = np.array([a for a, _, _ in ref]); rlon = np.array([b for _, b, _ in ref])
    radv = np.array([c for _, _, c in ref])

    # 反距离加权插值 (IDW, 幂2)
    adv = np.empty(len(lons))
    for i in range(len(lons)):
        d2 = (rlat - lats[i]) ** 2 + (rlon - lons[i]) ** 2 + 1e-6
        w = 1.0 / d2 ** 1.0
        adv[i] = np.sum(w * radv) / np.sum(w)

    fig, ax = plt.subplots(figsize=(11.5, 9))
    china_outline(ax)
    sc = ax.scatter(lons, lats, s=2 + 1.5 * np.sqrt(caps), c=adv, cmap="YlOrRd",
                    vmin=float(radv.min()), vmax=float(radv.max()),
                    alpha=0.72, edgecolors="none", zorder=2)
    # 参考城市
    ax.scatter(rlon, rlat, s=60, facecolors="none", edgecolors="black", linewidths=1.3, zorder=4)
    for a, b, c in ref:
        ax.text(b, a, f"{c:.1f}", fontsize=7, zorder=5, ha="center", va="bottom")
    cbar = fig.colorbar(sc, ax=ax, shrink=0.55, pad=0.01)
    cbar.set_label("钙钛矿全年比发电领先晶硅 (%)")
    setup_ax(ax, "真实光伏站点：钙钛矿越往南/热越划算（基于12城实测插值）")
    save(fig, "17_pv_perovskite_advantage")


def save(fig, name):
    out = f"outputs/figures/{name}.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("已生成", out)


def main():
    viz.setup()
    os.makedirs("outputs/figures", exist_ok=True)
    pv = pv_points("operating")
    print(f"运营光伏: {len(pv[0]):,} 座 / {pv[2].sum()/1000:.0f} GW")
    fig_transmission(pv)
    fig_coal(pv)
    fig_utility_distributed(pv)
    fig_perovskite(pv)
    print("完成。")


if __name__ == "__main__":
    main()
