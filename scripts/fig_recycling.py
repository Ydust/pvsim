"""退役板的回收/废弃物量: 把 150 GW 钙钛矿 2030s 退役潮换算成
模组吨数 + 关键金属(银/铟/铅), 看回收行业需求。

文献代表系数 (t / GW = kg / MW):
  晶硅模组 ~60,000 t/GW 总质量(玻璃70%/铝17%/硅3%/EVA等), 银 ~10 t/GW
  钙钛矿模组 ~50,000 t/GW 总质量(玻璃80%/铝12%/聚合物), 银 ~3, 铟 ~30, 铅 ~1.5 t/GW
  来源: IEA PVPS 2023, Frischknecht 等 LCA, Leijtens 等 perovskite 回收综述
运行: python -m scripts.fig_recycling
输出: outputs/figures/24_recycling.png
"""

import os
import sys

import numpy as np
import matplotlib.cm as cm

from pvsim import viz
from pvsim.viz import plt, color

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = "outputs/figures/24_recycling.png"

# 单位: t/GW (= kg/MW)
MATERIALS = {
    "early-cSi": {
        "name": "早期晶硅", "color": color("c-Si"),
        "玻璃": 42000, "铝边框": 10000, "硅(电池片)": 1500,
        "EVA/封装": 3500, "铜线": 600,
        "_metals": {"银 Ag": 10, "铟 In": 0, "铅 Pb": 0},
    },
    "perovskite": {
        "name": "钙钛矿", "color": color("perovskite"),
        "玻璃": 40000, "铝边框": 6000, "聚合物/封装": 3000,
        "_metals": {"银 Ag": 3, "铟 In": 30, "铅 Pb": 1.5},
    },
}

# 情景: 150 GW 钙钛矿 2030s vs 366 GW 晶硅(全存量退完)
SCEN = {
    "钙钛矿\n(2030s 150GW)": ("perovskite", 150),
    "晶硅\n(2033-49 全366GW)": ("early-cSi", 366),
}


def main():
    viz.setup()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.8))

    # === 左: 模组吨数(分材料堆叠) ===
    bottoms = np.zeros(len(SCEN))
    mat_colors = cm.tab20.colors
    all_mats = ["玻璃", "铝边框", "硅(电池片)", "EVA/封装", "铜线", "聚合物/封装"]
    summary = []
    x = np.arange(len(SCEN))
    for mi, mat in enumerate(all_mats):
        vals = []
        for label, (tech, gw) in SCEN.items():
            t = MATERIALS[tech].get(mat, 0) * gw / 1e6  # t/GW × GW = t, /1e6 = Mt
            vals.append(t)
        vals = np.array(vals)
        if vals.sum() > 0.001:
            ax1.bar(x, vals, bottom=bottoms, color=mat_colors[mi], label=mat,
                    edgecolor="white", linewidth=0.5)
            bottoms += vals
    for i, (label, (tech, gw)) in enumerate(SCEN.items()):
        total = bottoms[i]
        ax1.text(i, total, f" {total:.1f} Mt", ha="center", va="bottom",
                 fontsize=11, fontweight="bold")
        summary.append((label.replace("\n", " "), tech, gw, total))
    ax1.set_xticks(x)
    ax1.set_xticklabels(list(SCEN.keys()))
    ax1.set_ylabel("模组废弃质量 (Mt)")
    ax1.set_title("模组吨数(按材料堆叠)")
    ax1.legend(loc="upper right", fontsize=8, ncol=2)
    ax1.grid(axis="y", alpha=0.3)

    # === 右: 关键金属 (银/铟/铅) ===
    metals = ["银 Ag", "铟 In", "铅 Pb"]
    metal_data = {}
    for label, (tech, gw) in SCEN.items():
        ms = MATERIALS[tech]["_metals"]
        metal_data[label] = {m: ms.get(m, 0) * gw for m in metals}  # t/GW × GW = t
    bw = 0.35
    for i, label in enumerate(SCEN):
        vals = [metal_data[label][m] for m in metals]
        tech = SCEN[label][0]
        col = MATERIALS[tech]["color"]
        bars = ax2.bar(np.arange(len(metals)) + (i - 0.5) * bw, vals, bw,
                       color=col, alpha=0.85 if i == 0 else 0.65,
                       edgecolor="white", label=label.replace("\n", " "))
        for j, v in enumerate(vals):
            if v > 0:
                ax2.text(j + (i - 0.5) * bw, v, f"{v:,.0f}",
                         ha="center", va="bottom", fontsize=9)
    ax2.set_xticks(range(len(metals)))
    ax2.set_xticklabels(metals)
    ax2.set_ylabel("关键金属 (吨)")
    ax2.set_title("关键金属可回收量(回收行业需求)")
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(axis="y", alpha=0.3)

    # 注解: 行业意义
    p_gw = SCEN["钙钛矿\n(2030s 150GW)"][1]
    p_total = summary[0][3]
    p_metals = metal_data["钙钛矿\n(2030s 150GW)"]
    fig.suptitle(
        f"光伏退役板的回收/废弃量\n"
        f"钙钛矿 150 GW 2030s 退役 → 模组 {p_total:.1f} Mt, 铟 {p_metals['铟 In']:,.0f} t, "
        f"铅 {p_metals['铅 Pb']:,.0f} t  (10年内集中处理→年均 {p_total/10:.1f} Mt/年)",
        fontweight="bold", fontsize=12)
    fig.text(0.5, 0.01,
             "因子: 晶硅 ~60t/MW(银10), 钙钛矿 ~50t/MW(银3/铟30/铅1.5) — IEA PVPS 2023 / "
             "Frischknecht LCA / Leijtens 综述, 代表值。", ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=[0, 0.04, 1, 0.92])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=125)
    plt.close(fig)
    print(f"已生成 {OUT}")
    for label, tech, gw, total in summary:
        ms = metal_data[label.replace(" ", "\n")] if label.replace(" ", "\n") in metal_data else metal_data[next(iter(SCEN))]
        print(f"  {label}: {gw} GW → 模组 {total:.1f} Mt", end="")
        if tech == "perovskite":
            print(f", 银 {ms['银 Ag']:.0f}t, 铟 {ms['铟 In']:.0f}t, 铅 {ms['铅 Pb']:.0f}t")
        else:
            print(f", 银 {ms['银 Ag']:.0f}t")


if __name__ == "__main__":
    main()
