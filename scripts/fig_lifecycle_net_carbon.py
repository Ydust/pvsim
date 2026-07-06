"""全生命周期净碳对比: 累计运行端避碳 - 累计制造端隐含碳。

每年: 在运容量(≈366GW 持续替换维持)× 年利用 × 电网EF = 年避碳; 当年新建容量 × 隐含碳因子 = 当年制造碳。
钙钛矿: 年利用×1.05 (全国平均~5%发电优势), 隐含碳因子 0.15 kgCO2eq/Wp, 寿命15年; 晶硅 25年/0.50。
运行: python -m scripts.fig_lifecycle_net_carbon   输出: figures/20_lifecycle_net_carbon.png
"""

import os
import sys
import json

import numpy as np
from pvsim import viz
from pvsim.viz import plt, color

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/figures/20_lifecycle_net_carbon.png"
Y0, Y1, PLOT0 = 2008, 2060, 2024
GRID_EF = 0.58      # tCO2/MWh
YIELD = 1300.0      # kWh/kWp/yr (晶硅)
PERO_YIELD_MULT = 1.05    # 钙钛矿全年发电优势 ~+5%
SCEN = {
    "early-cSi": {"life": 25, "ef": 0.50, "yield_mult": 1.0,
                  "name": "早期晶硅(寿命25/EF0.50)", "color": color("c-Si")},
    "perovskite": {"life": 15, "ef": 0.15, "yield_mult": PERO_YIELD_MULT,
                   "name": "钙钛矿(寿命15/EF0.15)", "color": color("perovskite")},
}


def num(x):
    try: return float(x)
    except Exception: return 0.0


def annual_install_gw():
    with open(os.path.join(GEO, SOLAR), encoding="utf-8-sig") as f:
        feats = json.load(f)["features"]
    yrs = np.arange(Y0, Y1 + 1); orig = np.zeros(len(yrs))
    for ft in feats:
        p = ft["properties"]
        if p.get("Status") != "operating": continue
        try: y = int(float(p.get("Start_year")))
        except Exception: continue
        if Y0 <= y <= 2024:
            orig[y - Y0] += num(p.get("Capacity__MW_")) / 1000.0
    return yrs, orig


def chain(orig, L):
    n = len(orig); rebuild = np.zeros(n); retire = np.zeros(n); operating = np.zeros(n)
    for i in range(n):
        if i - L >= 0:
            ret = orig[i - L] + rebuild[i - L]
            retire[i] = ret; rebuild[i] += ret
        operating[i] = orig[:i + 1].sum() + rebuild[:i + 1].sum() - retire[:i + 1].sum()
    new_built = orig + rebuild   # 当年新建(原始+替换)
    return operating, new_built


def main():
    viz.setup()
    yrs, orig = annual_install_gw()
    m = yrs >= PLOT0; yy = yrs[m]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.6))
    summary = {}
    for key, s in SCEN.items():
        oper, new = chain(orig, s["life"])
        ann_avoided = oper * YIELD * s["yield_mult"] * 1e3 * GRID_EF / 1e6   # Mt/yr
        cum_avoided = np.cumsum(ann_avoided)
        ann_embodied = new * s["ef"]                                          # Mt/yr (GW × kg/Wp → Mt)
        cum_embodied = np.cumsum(ann_embodied)
        cum_net = cum_avoided - cum_embodied
        col = s["color"]
        ax1.plot(yy, cum_net[m] / 1000, color=col, lw=2.4, label=s["name"])  # Gt
        ax1.plot(yy, cum_avoided[m] / 1000, color=col, lw=1, ls=":", alpha=0.6)
        ax1.fill_between(yy, 0, -cum_embodied[m] / 1000, color=col, alpha=0.18)
        summary[key] = {"avoided": cum_avoided[-1], "embodied": cum_embodied[-1],
                        "net": cum_net[-1], "color": col, "name": s["name"]}

    ax1.axhline(0, color="gray", lw=0.6)
    ax1.set_xlabel("年"); ax1.set_ylabel("累计 (Gt CO2eq)")
    ax1.set_title(f"全生命周期净碳轨迹 ({PLOT0}–{Y1})\n粗=净额(避碳−制造) · 点=累计避碳 · 阴影=制造碳(向下)")
    ax1.legend(loc="upper left"); ax1.grid(alpha=0.3)

    # 右: 2060 分解条
    keys = list(SCEN.keys()); x = np.arange(len(keys)); w = 0.5
    for i, k in enumerate(keys):
        s = summary[k]
        ax2.bar(x[i], s["avoided"] / 1000, w, color=s["color"], alpha=0.7, label="避碳" if i == 0 else None)
        ax2.bar(x[i], -s["embodied"] / 1000, w, color="#b03a2e", alpha=0.85, label="制造碳" if i == 0 else None)
        ax2.scatter(x[i], s["net"] / 1000, marker="D", s=80, color="black", zorder=5,
                    label="净额" if i == 0 else None)
        ax2.text(x[i], s["avoided"] / 1000, f" 避碳\n {s['avoided']/1000:.2f} Gt",
                 ha="center", va="bottom", fontsize=9)
        ax2.text(x[i], -s["embodied"] / 1000, f" 制造碳\n {s['embodied']:.0f} Mt",
                 ha="center", va="top", fontsize=9, color="#7b1f10")
        ax2.text(x[i] + 0.27, s["net"] / 1000, f"净 {s['net']/1000:.2f} Gt",
                 ha="left", va="center", fontsize=10, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels([summary[k]["name"] for k in keys], fontsize=9)
    ax2.axhline(0, color="gray", lw=0.6); ax2.set_ylabel("Gt CO2eq")
    ax2.set_title(f"到{Y1}累计分解 (避碳↑ / 制造碳↓ / 净额◆)")
    ax2.legend(loc="lower right"); ax2.grid(axis="y", alpha=0.3)

    net_c = summary["early-cSi"]["net"]; net_p = summary["perovskite"]["net"]
    delta = (net_p - net_c) / 1000
    fig.suptitle(f"全生命周期净碳：钙钛矿净额 {net_p/1000:.2f} Gt vs 晶硅 {net_c/1000:.2f} Gt → 钙钛矿多减 {delta:.2f} Gt ({(net_p/net_c-1)*100:+.1f}%)",
                 fontweight="bold", fontsize=12)
    fig.text(0.5, 0.01, "假设: 电网EF 0.58 tCO2/MWh, 晶硅年利用1300 kWh/kWp, 钙钛矿×1.05; "
                        "存量366GW持续替换维持; 不计退役回收碳。",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140)
    plt.close(fig)
    print(f"已生成 {OUT}")
    for k in keys:
        s = summary[k]
        print(f"  {s['name']}: 避碳{s['avoided']/1000:.2f}Gt − 制造{s['embodied']:.0f}Mt = 净{s['net']/1000:.2f}Gt")


if __name__ == "__main__":
    main()
