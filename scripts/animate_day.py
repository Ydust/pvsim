"""动画：晶硅 vs 钙钛矿 "运行一整天" 对比 (输出 GIF)。

左图：单组件功率随时间累积曲线 + 电池温度(右轴, 虚线), 带移动时间线。
右图：当前时刻的实时 I-V 曲线 + 最大功率点。
标题：当前时刻 / 辐照 / 电池温度 / 两者 Pmax / 差距。

运行: python -m scripts.animate_day
输出: outputs/animations/day_cycle.gif
"""

import os
import sys

import numpy as np
import matplotlib.animation as animation

from pvsim import viz
from pvsim.viz import plt, color
from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cell import operating_point
from pvsim.temperature import faiman
from pvsim import weather as wx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = "outputs/animations/day_cycle.gif"


def precompute():
    loc = wx.get_location()
    day = wx.clear_sky_day("2023-06-21", loc, freq="15min", tmean=32.0)
    mask = day["poa_global"].to_numpy() > 10.0      # 只取白天
    day = day[mask]
    hours = (day.index.hour + day.index.minute / 60.0).to_numpy()
    poa = day["poa_global"].to_numpy()
    tair = day["temp_air"].to_numpy()
    wind = day["wind_speed"].to_numpy()
    tcell = faiman(poa, tair, wind)

    frames = []
    for k in range(len(hours)):
        rec = {"hour": hours[k], "poa": poa[k], "tair": tair[k], "tcell": tcell[k]}
        for tech, key in ((CSI_EARLY, "c"), (PEROVSKITE, "p")):
            op = operating_point(tech, float(poa[k]), float(tcell[k]),
                                 ns=tech.cells_in_series, npts=140)
            rec[key] = op
        frames.append(rec)
    return loc, hours, tcell, frames


def main():
    viz.setup()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    loc, hours, tcell, frames = precompute()

    pmpC = np.array([f["c"].pmp for f in frames])
    pmpP = np.array([f["p"].pmp for f in frames])
    vmax = max(max(f["c"].voc for f in frames), max(f["p"].voc for f in frames)) * 1.05
    imax = max(max(f["c"].isc for f in frames), max(f["p"].isc for f in frames)) * 1.1
    pmax = max(pmpC.max(), pmpP.max()) * 1.12
    cC, cP = color("c-Si"), color("perovskite")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    axT = ax1.twinx()

    # 左图静态背景：整日功率(浅色) 作参照
    ax1.plot(hours, pmpC, color=cC, alpha=0.18, lw=1)
    ax1.plot(hours, pmpP, color=cP, alpha=0.18, lw=1)
    lineC, = ax1.plot([], [], color=cC, lw=2.5, label="早期晶硅")
    lineP, = ax1.plot([], [], color=cP, lw=2.5, label="钙钛矿")
    dotC, = ax1.plot([], [], "o", color=cC, ms=8)
    dotP, = ax1.plot([], [], "o", color=cP, ms=8)
    lineT, = axT.plot([], [], color="firebrick", ls="--", lw=1.6, alpha=0.8, label="电池温度")
    vline = ax1.axvline(hours[0], color="gray", ls=":", lw=1)
    ax1.set_xlim(hours[0], hours[-1]); ax1.set_ylim(0, pmax)
    ax1.set_xlabel("时刻 (h)"); ax1.set_ylabel("单组件功率 Pmax (W)")
    axT.set_ylim(20, max(tcell) * 1.05); axT.set_ylabel("电池温度 (°C)", color="firebrick")
    ax1.set_title("功率随时间 (浅线=全天参照)")
    ax1.legend(loc="upper left"); axT.legend(loc="upper right")

    ivC, = ax2.plot([], [], color=cC, lw=2.5, label="早期晶硅")
    ivP, = ax2.plot([], [], color=cP, lw=2.5, label="钙钛矿")
    mppC, = ax2.plot([], [], "o", color=cC, ms=8)
    mppP, = ax2.plot([], [], "o", color=cP, ms=8)
    ax2.set_xlim(0, vmax); ax2.set_ylim(0, imax)
    ax2.set_xlabel("电压 (V)"); ax2.set_ylabel("电流 (A)")
    ax2.set_title("实时 I-V 曲线 (●=最大功率点)")
    ax2.legend(loc="upper right")

    suptitle = fig.suptitle("", fontsize=14, fontweight="bold")

    def init():
        for ln in (lineC, lineP, dotC, dotP, lineT, ivC, ivP, mppC, mppP):
            ln.set_data([], [])
        return lineC, lineP, dotC, dotP, lineT, ivC, ivP, mppC, mppP, vline, suptitle

    def update(k):
        f = frames[k]
        lineC.set_data(hours[:k + 1], pmpC[:k + 1])
        lineP.set_data(hours[:k + 1], pmpP[:k + 1])
        lineT.set_data(hours[:k + 1], tcell[:k + 1])
        dotC.set_data([hours[k]], [pmpC[k]])
        dotP.set_data([hours[k]], [pmpP[k]])
        vline.set_xdata([hours[k], hours[k]])
        ivC.set_data(f["c"].v, f["c"].i)
        ivP.set_data(f["p"].v, f["p"].i)
        mppC.set_data([f["c"].vmp], [f["c"].imp])
        mppP.set_data([f["p"].vmp], [f["p"].imp])
        gap = (pmpP[k] - pmpC[k]) / pmpC[k] * 100 if pmpC[k] > 1 else 0
        h = int(f["hour"]); m = int(round((f["hour"] - h) * 60))
        suptitle.set_text(
            f"{loc.name} 夏至晴天  {h:02d}:{m:02d}   辐照 {f['poa']:.0f} W/m²   "
            f"电池温度 {f['tcell']:.0f}°C\n"
            f"晶硅 {pmpC[k]:.0f} W   |   钙钛矿 {pmpP[k]:.0f} W   "
            f"(钙钛矿领先 {gap:+.0f}%)")
        return lineC, lineP, dotC, dotP, lineT, ivC, ivP, mppC, mppP, vline, suptitle

    fig.tight_layout(rect=[0, 0, 1, 0.92])
    anim = animation.FuncAnimation(fig, update, init_func=init,
                                   frames=len(frames), interval=120, blit=False)
    anim.save(OUT, writer=animation.PillowWriter(fps=10))

    # 额外存一张"正午峰值"静态图作预览
    peak_k = int(np.argmax(pmpC + pmpP))
    update(peak_k)
    still = OUT.replace(".gif", "_peak.png")
    fig.savefig(still, dpi=120)
    plt.close(fig)
    print(f"已生成动画: {OUT}  ({len(frames)} 帧)")
    print(f"已生成峰值预览: {still}")


if __name__ == "__main__":
    main()
