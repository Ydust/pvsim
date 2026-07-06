"""省级退役压力对比: 晶硅25年 vs 钙钛矿15年, 看"换成钙钛矿"省级压力如何提前到2030s。

按真实投产年+寿命直接算每座电站的退役年, 按省份聚合三个十年窗口。简化(不含重建链)以聚焦"压力提前"。
运行: python -m scripts.fig_retirement_perovskite_vs_csi
输出: outputs/figures/23_retirement_perovskite_vs_csi.png
"""

import os
import sys
import json
from collections import defaultdict

import numpy as np
from pvsim import viz
from pvsim.viz import plt, color

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/figures/23_retirement_perovskite_vs_csi.png"
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


def num(x):
    try: return float(x)
    except Exception: return 0.0


def plants():
    out = []
    with open(os.path.join(GEO, SOLAR), encoding="utf-8-sig") as f:
        for ft in json.load(f)["features"]:
            p = ft["properties"]
            if p.get("Status") != "operating": continue
            try: y = int(float(p.get("Start_year")))
            except Exception: continue
            if not (2000 <= y <= 2024): continue
            out.append({"prov": p.get("State_Province", "?"),
                        "cap": max(num(p.get("Capacity__MW_")), 0.1) / 1000.0, "y": y})
    return out


def aggregate(plnts, life):
    pw = defaultdict(lambda: [0.0] * len(WINDOWS))
    tot = defaultdict(float)
    for p in plnts:
        ret = p["y"] + life
        tot[p["prov"]] += p["cap"]
        for j, (a, b, _) in enumerate(WINDOWS):
            if a <= ret <= b:
                pw[p["prov"]][j] += p["cap"]
    return pw, tot


def main():
    viz.setup()
    pl = plants()
    csi_pw, csi_tot = aggregate(pl, 25)
    per_pw, per_tot = aggregate(pl, 15)

    # 用两情景合计排序选 Top15(保证两侧同序、可比)
    combined = {k: csi_tot.get(k, 0) + per_tot.get(k, 0) for k in set(csi_tot) | set(per_tot)}
    top = sorted(combined.items(), key=lambda x: -x[1])[:15]
    keys = [k for k, _ in top][::-1]
    names = [PROV_CN.get(k, k) for k in keys]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 7.2), sharey=True)
    y = np.arange(len(keys))
    cols = ["#fdae6b", "#e6550d", "#7b1f10"]

    for ax, (pw, lab) in zip((ax1, ax2),
                             ((csi_pw, f"晶硅 25 年"), (per_pw, f"钙钛矿 15 年"))):
        cum = np.zeros(len(keys))
        for j, (_, _, wlab) in enumerate(WINDOWS):
            vals = np.array([pw[k][j] for k in keys])
            ax.barh(y, vals, left=cum, color=cols[j], label=wlab, edgecolor="white")
            cum += vals
        for i, t in enumerate(cum):
            ax.text(t, y[i], f" {t:.1f}", va="center", fontsize=8)
        ax.set_xlabel("退役量 (GW)"); ax.set_title(f"寿命 = {lab}", fontweight="bold")
        ax.grid(axis="x", alpha=0.3); ax.legend(loc="lower right", fontsize=8)
    ax1.set_yticks(y); ax1.set_yticklabels(names, fontsize=9)

    # 国家级 2030s 对比标题
    csi_30s = sum(csi_pw[k][0] for k in csi_pw)
    per_30s = sum(per_pw[k][0] for k in per_pw)
    csi_total = sum(csi_tot.values()); per_total = sum(per_tot.values())
    fig.suptitle(
        f"省级退役压力对比 — 换成钙钛矿(15yr)后 2030s 退役潮提前到来\n"
        f"2025–2034 全国: 晶硅 {csi_30s:.0f} GW vs 钙钛矿 {per_30s:.0f} GW   "
        f"(总盘约 {csi_total:.0f} GW, 钙钛矿大半压在 2030s)",
        fontweight="bold", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=125)
    plt.close(fig)
    print(f"已生成 {OUT}")
    print(f"  2025–2034 全国: 晶硅 {csi_30s:.1f} GW vs 钙钛矿 {per_30s:.1f} GW")
    print(f"  钙钛矿情景 2030s Top省:")
    top_per_30s = sorted([(k, per_pw[k][0]) for k in per_pw], key=lambda x: -x[1])[:8]
    for k, v in top_per_30s:
        print(f"    {PROV_CN.get(k, k)}: 2030s 退役 {v:.1f} GW")


if __name__ == "__main__":
    main()
