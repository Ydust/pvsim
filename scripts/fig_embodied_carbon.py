"""存量替换的全国累计制造/隐含碳: 钙钛矿单瓦碳低 vs 替换翻倍, 谁赢。

把"年替换需求 GW"× 隐含碳因子(kgCO2eq/Wp) → 年新建带来的制造碳; 累计到 2060。
两种技术各给低/中/高三档隐含碳(文献代表范围), 既看中位线对比, 也看不确定带。

文献代表值 (kgCO2eq/Wp):
  晶硅:   低 0.40 / 中 0.50 / 高 0.65  (Fraunhofer ISE, IPCC AR6 范围)
  钙钛矿: 低 0.10 / 中 0.15 / 高 0.25  (Leijtens 等, 单结溶液工艺)
运行: python -m scripts.fig_embodied_carbon
输出: outputs/figures/19_embodied_carbon.png
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
OUT = "outputs/figures/19_embodied_carbon.png"
Y0, Y1, PLOT0 = 2008, 2060, 2024
SCEN = {
    "early-cSi": {"life": 25, "ef": {"低": 0.40, "中": 0.50, "高": 0.65},
                  "name": "早期晶硅", "color": color("c-Si")},
    "perovskite": {"life": 15, "ef": {"低": 0.10, "中": 0.15, "高": 0.25},
                   "name": "钙钛矿", "color": color("perovskite")},
}


def num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def annual_install_gw():
    with open(os.path.join(GEO, SOLAR), encoding="utf-8-sig") as f:
        feats = json.load(f)["features"]
    years = np.arange(Y0, Y1 + 1)
    orig = np.zeros(len(years))
    for ft in feats:
        p = ft["properties"]
        if p.get("Status") != "operating":
            continue
        try:
            y = int(float(p.get("Start_year")))
        except Exception:
            continue
        if Y0 <= y <= 2024:
            orig[y - Y0] += num(p.get("Capacity__MW_")) / 1000.0
    return years, orig


def replacement_chain(orig, L):
    n = len(orig); rebuild = np.zeros(n); retire = np.zeros(n)
    for i in range(n):
        if i - L >= 0:
            ret = orig[i - L] + rebuild[i - L]
            retire[i] = ret
            rebuild[i] += ret
    return retire   # GW / 年新建(=替换)


def main():
    viz.setup()
    years, orig = annual_install_gw()
    mask = years >= PLOT0
    yy = years[mask]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    summary = {}
    for key, s in SCEN.items():
        retire = replacement_chain(orig, s["life"])
        cum_gw = np.cumsum(retire)
        # 累计制造碳 (Mt) = 累计 GW × EF(kg/Wp) (因 1 GW × 1 kg/W = 1 Mt)
        cum_mt = {tag: cum_gw * ef for tag, ef in s["ef"].items()}
        ax1.fill_between(yy, cum_mt["低"][mask], cum_mt["高"][mask],
                         color=s["color"], alpha=0.18)
        ax1.plot(yy, cum_mt["中"][mask], color=s["color"], lw=2.3,
                 label=f"{s['name']} (寿命{s['life']}年, 中值)")
        end_mt = {tag: float(cum_mt[tag][-1]) for tag in cum_mt}
        end_gw = float(cum_gw[-1])
        summary[key] = {"end_gw": end_gw, "end_mt": end_mt, "color": s["color"], "name": s["name"]}

    ax1.set_title(f"累计存量替换的制造/隐含碳 (Mt CO2eq)  {PLOT0}–{Y1}")
    ax1.set_xlabel("年"); ax1.set_ylabel("Mt CO2eq")
    ax1.grid(alpha=0.3); ax1.legend(loc="upper left")

    # 右: 2060 累计对比 (低/中/高)
    keys = list(SCEN.keys()); x = np.arange(len(keys))
    w = 0.25
    for i, tag in enumerate(("低", "中", "高")):
        vals = [summary[k]["end_mt"][tag] for k in keys]
        ax2.bar(x + (i - 1) * w, vals, w,
                color=[summary[k]["color"] for k in keys],
                alpha=[0.55, 0.95, 0.75][i],
                edgecolor="white", label=f"{tag}值")
        for j, v in enumerate(vals):
            ax2.text(x[j] + (i - 1) * w, v, f"{v:.0f}", ha="center", va="bottom", fontsize=8)
    ax2.set_xticks(x); ax2.set_xticklabels([summary[k]["name"] for k in keys])
    ax2.set_ylabel("Mt CO2eq  (到 2060 累计)")
    ax2.set_title("不同隐含碳因子下的 2060 累计对比")
    ax2.legend(title="EF档", loc="upper right"); ax2.grid(axis="y", alpha=0.3)

    # 中值结论
    c_mid = summary["early-cSi"]["end_mt"]["中"]
    p_mid = summary["perovskite"]["end_mt"]["中"]
    ratio = p_mid / c_mid
    delta = c_mid - p_mid
    pct = (1 - ratio) * 100
    c_gw = summary["early-cSi"]["end_gw"]
    p_gw = summary["perovskite"]["end_gw"]
    fig.suptitle(
        f"全国存量替换的制造/隐含碳：钙钛矿替换量{p_gw:.0f} GW(晶硅{c_gw:.0f}的{p_gw/c_gw:.1f}×)，"
        f"但单瓦碳低 → 中值下累计{p_mid:.0f} Mt vs 晶硅{c_mid:.0f} Mt，钙钛矿仍低 {pct:.0f}%",
        fontweight="bold", fontsize=12)
    fig.text(0.5, 0.01,
             "假设: 隐含碳因子取文献代表范围 (晶硅 0.40/0.50/0.65, 钙钛矿 0.10/0.15/0.25 kgCO2eq/Wp); "
             "存量366 GW按真实投产年, 退役即等量重建; 不计运行端避碳。",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140)
    plt.close(fig)
    print(f"已生成 {OUT}")
    for k in keys:
        s = summary[k]
        print(f"  {s['name']}: 累计替换{s['end_gw']:.0f} GW, 制造碳 低{s['end_mt']['低']:.0f}/"
              f"中{s['end_mt']['中']:.0f}/高{s['end_mt']['高']:.0f} Mt")
    print(f"  中值比 钙钛矿/晶硅 = {ratio:.2f}  (钙钛矿低 {pct:.0f}%)")


if __name__ == "__main__":
    main()
