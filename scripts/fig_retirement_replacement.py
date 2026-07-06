"""退役潮专题图：报废量 + 替换需求（晶硅25年 vs 钙钛矿15年寿命）。

基于真实 2024 存量(366 GW, 按真实投产年分布), 外推"重建链":
  某年退役量 = L 年前投产(含此前替换件)的容量; 退役即等量替换, 替换件到期再退役…
→ 钙钛矿短寿命 → 退役更早 + 反复重建 → 累计替换需求远高于晶硅。
运行: python -m scripts.fig_retirement_replacement
输出: outputs/figures/18_retirement_replacement.png
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
OUT = "outputs/figures/18_retirement_replacement.png"
Y0, Y1 = 2008, 2060          # 建模区间
PLOT0 = 2024                 # 展示从 2024(存量基准)起
LIVES = [("早期晶硅 (25年)", 25, color("c-Si")),
         ("钙钛矿 (15年)", 15, color("perovskite"))]


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
            orig[y - Y0] += num(p.get("Capacity__MW_")) / 1000.0   # GW
    return years, orig


def replacement_chain(orig, L):
    """重建链: 返回每年退役量(=替换需求, GW)。退役即等量重建, 重建件 L 年后再退役。"""
    n = len(orig)
    rebuild = np.zeros(n)
    retire = np.zeros(n)
    for i in range(n):
        src = i - L
        if src >= 0:
            ret = orig[src] + rebuild[src]
            retire[i] = ret
            rebuild[i] += ret      # 当年等量替换(将于 i+L 再退役)
    return retire


def main():
    viz.setup()
    years, orig = annual_install_gw()
    mask = years >= PLOT0
    yy = years[mask]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))
    summary = []
    for label, L, col in LIVES:
        retire = replacement_chain(orig, L)
        cum = np.cumsum(retire)
        ax1.plot(yy, retire[mask], color=col, lw=2.2, label=label)
        ax2.plot(yy, cum[mask], color=col, lw=2.4, label=label)
        end = cum[mask][-1]
        ax2.annotate(f"{end:.0f} GW", (yy[-1], end), color=col, fontsize=11,
                     fontweight="bold", ha="right", va="bottom")
        summary.append((label, end))

    ax1.set_title("年报废量 / 替换需求 (GW/年)")
    ax1.set_xlabel("年"); ax1.set_ylabel("GW / 年"); ax1.legend(); ax1.grid(alpha=0.3)
    ax1.axvspan(PLOT0, 2024.5, color="gray", alpha=0.08)

    ax2.set_title("累计替换需求 (GW)")
    ax2.set_xlabel("年"); ax2.set_ylabel("累计 GW"); ax2.legend(loc="upper left"); ax2.grid(alpha=0.3)

    ratio = summary[1][1] / summary[0][1] if summary[0][1] > 0 else 0
    fig.suptitle(f"光伏退役潮与替换需求：钙钛矿(15年)累计替换需求约为晶硅(25年)的 {ratio:.1f} 倍\n"
                 f"（基于 2024 年真实存量 366 GW 外推, 退役即等量重建）",
                 fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140)
    plt.close(fig)
    print(f"已生成 {OUT}")
    for label, end in summary:
        print(f"  {label}: 到{Y1}累计替换需求 {end:.0f} GW")
    print(f"  钙钛矿/晶硅 替换需求比 = {ratio:.2f}")


if __name__ == "__main__":
    main()
