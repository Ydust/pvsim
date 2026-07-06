"""动画：全国光伏"新建 vs 报废"两股流的交替（逐年）。

绿(上)=当年新建, 红(下)=当年报废, 线=在运总容量。
情景: 基于 2024 年真实存量 366 GW(真实投产年分布), 退役即等量新建替换(维持容量)。
→ 前期纯新建(净容量爬升) → 后期新建=报废的持续换新交替。晶硅25年寿命为基准,
  叠钙钛矿15年报废线(橙虚)作对比:短寿命→报废更早更密、换新更频繁。
运行: python -m scripts.anim_build_retire   输出: outputs/animations/build_retire.gif (+ _peak.png)
"""

import os
import sys
import json

import numpy as np
import matplotlib.animation as animation

from pvsim import viz
from pvsim.viz import plt, color

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/animations/build_retire.gif"
Y0, Y1 = 2010, 2055


def num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def annual_install(years):
    with open(os.path.join(GEO, SOLAR), encoding="utf-8-sig") as f:
        feats = json.load(f)["features"]
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
    return orig


NB_FUTURE = 100.0   # 2025 起年新建(GW/年, 示意值; 接近中国近年装机节奏)


def retire_of(new, L):
    ret = np.zeros(len(new))
    for i in range(len(new)):
        if i - L >= 0:
            ret[i] = new[i - L]
    return ret


def main():
    viz.setup()
    years = np.arange(Y0, Y1 + 1)
    orig = annual_install(years)         # 2010-2024 真实新建
    new_c = orig.copy()
    new_c[years >= 2025] = NB_FUTURE     # 2025 起持续新建(示意)
    ret_c = retire_of(new_c, 25)         # 报废: 晶硅25年寿命
    ret_p = retire_of(new_c, 15)         # 报废: 钙钛矿15年寿命(对比)
    net = np.cumsum(new_c - ret_c)       # 在运容量
    ymax = max(new_c.max(), ret_c.max(), ret_p.max()) * 1.15

    fig, ax = plt.subplots(figsize=(12, 6))
    ax2 = ax.twinx()

    def update(i):
        ax.clear(); ax2.clear()
        yy = years[:i + 1]
        ax.bar(yy, new_c[:i + 1], color="#2ca02c", alpha=0.85, label="新建 (GW/年)")
        ax.bar(yy, -ret_c[:i + 1], color="#d62728", alpha=0.85, label="报废·晶硅25年 (GW/年)")
        ax.plot(yy, -ret_p[:i + 1], color=color("perovskite"), lw=1.8, ls="--",
                label="报废·钙钛矿15年(对比)")
        ax.axhline(0, color="#333", lw=0.8)
        ax.axvline(2024.5, color="gray", ls=":", lw=1)
        ax.set_xlim(Y0 - 0.5, Y1 + 0.5); ax.set_ylim(-ymax, ymax)
        ax.set_xlabel("年"); ax.set_ylabel("年新建(+) / 报废(−)  GW/年")
        ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
        ax2.plot(yy, net[:i + 1], color="#1f4e9b", lw=2.4)
        ax2.set_ylim(0, max(net) * 1.15); ax2.set_ylabel("在运总容量 (GW)", color="#1f4e9b")
        ax2.tick_params(axis="y", labelcolor="#1f4e9b")
        Y = years[i]
        phase = "真实新建期" if Y <= 2024 else "新建持续 + 报废渐起 → 交替期(示意)"
        ax.set_title(f"全国光伏 新建 vs 报废 · {Y} 年   [{phase}]\n"
                     f"当年 新建 {new_c[i]:.0f} / 报废 {ret_c[i]:.0f} GW · 在运 {net[i]:.0f} GW",
                     fontweight="bold")
        ax.grid(axis="y", alpha=0.25)
        return []

    anim = animation.FuncAnimation(fig, update, frames=len(years), interval=380, blit=False)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    anim.save(OUT, writer=animation.PillowWriter(fps=2.6))
    update(len(years) - 1)
    fig.tight_layout(); fig.savefig(OUT.replace(".gif", "_peak.png"), dpi=130)
    plt.close(fig)
    print(f"已生成 {OUT}  ({len(years)} 帧)")
    print(f"  2024 在运 {net[2024-Y0]:.0f} GW → {Y1} 在运 {net[-1]:.0f} GW (新建持续{NB_FUTURE:.0f}GW/年)")
    print(f"  报废显著起始: 晶硅~2035后 / 钙钛矿~2025后; 同等新建下钙钛矿报废线更早更高")


if __name__ == "__main__":
    main()
