"""现实增长情景: 2025-2050 持续新建(替换"冻结"假设), 看两种寿命的总制造/废弃量。

情景设置:
  新建年装机: 2025起 200 GW/年, 按 CAGR 0% / 5% / 8% 三档增长(中国近年实际更高)。
  + 重建链(退役即等量替换). 比较 晶硅25yr vs 钙钛矿15yr 累计制造 + 累计废弃(到 2050)。
运行: python -m scripts.fig_growth_scenarios   输出: outputs/figures/25_growth.png
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
OUT = "outputs/figures/25_growth.png"
Y0, Y1 = 2008, 2050
INITIAL_2025_NEW = 200      # GW/yr 起点 (2024 中国实际 ~270, 取保守)
CAGRS = [0.00, 0.05, 0.08]
LIVES = [("晶硅 25年", 25, color("c-Si")),
         ("钙钛矿 15年", 15, color("perovskite"))]


def num(x):
    try: return float(x)
    except Exception: return 0.0


def install_history():
    with open(os.path.join(GEO, SOLAR), encoding="utf-8-sig") as f:
        feats = json.load(f)["features"]
    years = np.arange(Y0, Y1 + 1)
    orig = np.zeros(len(years))
    for ft in feats:
        p = ft["properties"]
        if p.get("Status") != "operating": continue
        try: y = int(float(p.get("Start_year")))
        except Exception: continue
        if Y0 <= y <= 2024:
            orig[y - Y0] += num(p.get("Capacity__MW_")) / 1000.0
    return years, orig


def project_new(orig, cagr):
    """把 2025 起的新增按 CAGR 加到原序列上(不含重建)。"""
    arr = orig.copy()
    rate = INITIAL_2025_NEW
    for i, y in enumerate(np.arange(Y0, Y1 + 1)):
        if y >= 2025:
            arr[i] += rate
            rate *= (1 + cagr)
    return arr


def simulate_chain(new_install_orig, L):
    """given new_install per year (含真实 + 未来新建, 不含重建), 加重建链.
    返回 (年退役 GW, 年总新建 GW=新+重建). 累计制造 = 累计总新建; 累计废弃 = 累计退役。"""
    n = len(new_install_orig)
    rebuild = np.zeros(n)
    retire = np.zeros(n)
    for i in range(n):
        if i - L >= 0:
            ret = new_install_orig[i - L] + rebuild[i - L]
            retire[i] = ret
            rebuild[i] += ret
    total_build = new_install_orig + rebuild
    return retire, total_build


def main():
    viz.setup()
    years, orig = install_history()
    mask = years >= 2025
    yy = years[mask]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8.6), sharey="row")

    results = {}
    for c_idx, cagr in enumerate(CAGRS):
        new_orig = project_new(orig, cagr)
        for life_name, L, col in LIVES:
            retire, total_build = simulate_chain(new_orig, L)
            cum_build = np.cumsum(total_build)
            cum_waste = np.cumsum(retire)

            ax_b = axes[0, c_idx]
            ax_w = axes[1, c_idx]
            ax_b.plot(yy, cum_build[mask] / 1000, color=col, lw=2.2, label=life_name)
            ax_w.plot(yy, cum_waste[mask] / 1000, color=col, lw=2.2, label=life_name)
            results[(cagr, L)] = (cum_build[-1], cum_waste[-1])

        for ax, title in [(axes[0, c_idx], f"CAGR = {cagr*100:.0f}%/年   累计制造"),
                          (axes[1, c_idx], f"CAGR = {cagr*100:.0f}%/年   累计废弃")]:
            ax.set_xlim(2025, Y1); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")
            ax.set_xlabel("年")
            ax.set_title(title, fontsize=11)
            if c_idx == 0:
                ax.set_ylabel("累计 (TW)" if "制造" in title else "累计废弃 (TW)")

    # 标题: 中等情景结论
    mid = CAGRS[1]
    bc, wc = results[(mid, 25)]; bp, wp = results[(mid, 15)]
    fig.suptitle(
        f"现实情景下的总制造/废弃量 (2025–{Y1}, 新建从200GW/年按CAGR增长 + 重建链)\n"
        f"中等 CAGR={mid*100:.0f}%: 累计制造 晶硅 {bc/1000:.1f} TW / 钙钛矿 {bp/1000:.1f} TW   "
        f"|   累计废弃 晶硅 {wc/1000:.1f} TW / 钙钛矿 {wp/1000:.1f} TW   "
        f"(钙钛矿都 ~{bp/bc:.1f}×)", fontweight="bold", fontsize=11)
    fig.text(0.5, 0.01,
             "假设: 2025起年新建200 GW, 按 CAGR 0/5/8% 复合增长; 退役即等量重建(维持容量); "
             "存量366GW按真实投产年. 中国 2024 实际新增~270 GW,故此处偏保守。",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=120)
    plt.close(fig)
    print(f"已生成 {OUT}")
    for cagr in CAGRS:
        for ln, L, _ in LIVES:
            b, w = results[(cagr, L)]
            print(f"  CAGR {cagr*100:.0f}% / {ln}: 累计制造 {b/1000:.2f} TW, 累计废弃 {w/1000:.2f} TW")


if __name__ == "__main__":
    main()
