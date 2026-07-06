"""动画：钙钛矿"全年"发电领先晶硅的幅度，按城市排开 —— 直观看"越热差距越大"。

横条 = 各城钙钛矿全年比发电领先%(来自真实气象年, run_cities 结果);
按 冷→热 自下而上排, 颜色按辐照加权电池温度(冷蓝→热红), 条长与数字一起增长。
1.1%(哈尔滨) → 7.5%(海口) 是 ~7 倍差距, 一眼可见。
运行: python -m scripts.anim_advantage
输出: outputs/animations/advantage_by_city.gif (+ _peak.png)
"""

import sys

import numpy as np
import matplotlib.animation as animation
import matplotlib.cm as cm
from matplotlib.colors import Normalize

from pvsim import viz
from pvsim.viz import plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = "outputs/animations/advantage_by_city.gif"
GROW, HOLD = 38, 14


def main():
    viz.setup()
    import pandas as pd
    df = pd.read_csv("outputs/cities_comparison.csv").sort_values("钙钛矿优势%").reset_index(drop=True)
    cities = df["城市"].tolist()
    adv = df["钙钛矿优势%"].to_numpy()
    temp = df["加权电池温"].to_numpy()
    y = np.arange(len(cities))

    norm = Normalize(temp.min(), temp.max())
    colors = cm.coolwarm(norm(temp))

    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    bars = ax.barh(y, np.zeros_like(adv), color=colors, edgecolor="white", height=0.7)
    labels = [ax.text(0, yi, "", va="center", ha="left", fontsize=12, fontweight="bold")
              for yi in y]
    ax.set_yticks(y); ax.set_yticklabels([f"{c}" for c in cities])
    ax.set_xlim(0, adv.max() * 1.18)
    ax.set_xlabel("钙钛矿全年比发电 领先晶硅的幅度 (%)")
    ax.set_title("越热的城市，钙钛矿优势越大（全年真实气象）", fontweight="bold", fontsize=15)
    ax.grid(axis="x", alpha=0.3)

    # 温度色条
    sm = cm.ScalarMappable(norm=norm, cmap=cm.coolwarm); sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label("辐照加权平均电池温度 (°C)")

    # 趋势注释
    z = np.polyfit(temp, adv, 1)[0]
    ax.text(0.98, 0.04, f"温度每升 1°C，优势约 +{z:.2f}%",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=11,
            bbox=dict(boxstyle="round", fc="#fff3d6", ec="#caa"))

    def ease(p):
        return p * p * (3 - 2 * p)   # smoothstep

    def update(k):
        p = ease(min(k / GROW, 1.0))
        for i, b in enumerate(bars):
            w = adv[i] * p
            b.set_width(w)
            labels[i].set_position((w + adv.max() * 0.01, y[i]))
            labels[i].set_text(f"+{w:.1f}%   ({temp[i]:.0f}°C)")
        return list(bars) + labels

    frames = GROW + HOLD
    anim = animation.FuncAnimation(fig, update, frames=frames, interval=120, blit=False)
    fig.tight_layout()
    anim.save(OUT, writer=animation.PillowWriter(fps=12))
    update(frames)  # 末态
    fig.savefig(OUT.replace(".gif", "_peak.png"), dpi=120)
    plt.close(fig)
    print(f"已生成 {OUT}  ({frames}帧)")
    print("各城全年领先%:")
    for c, a, t in zip(cities, adv, temp):
        print(f"  {c:<5} {a:>4.1f}%  (电池温 {t:.0f}°C)")


if __name__ == "__main__":
    main()
