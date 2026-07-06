"""三城"运行一整天"动画 (GIF)：用真实TMY代表日 + 与Unity一致的物理链路。

每城: 左=单组件功率随时间(晶硅/钙钛矿)+电池温度; 右=实时I-V曲线。
物理链路与 Unity 一致: 有效辐照 = POA × 光谱失配SF(随天顶角) × 入射角IAM(随aoi), 温度用Faiman。
运行: python -m scripts.animate_cities
输出: outputs/animations/city_<key>.gif (+ _peak.png)
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
from pvsim.optics import iam
from pvsim.spectral import spectral_factor_from_zenith
from pvsim.cities import CITIES
from pvsim import weather as wx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUTDIR = "outputs/animations"
# 选 3 个气候反差大的城市
PICK = ["harbin", "shanghai", "haikou"]
N_FRAMES = 44   # 插值到更多帧, 播放更顺


def representative_day(city):
    w = wx.from_pvgis_tmy(city.lat, city.lon, altitude=city.alt, name=city.key)
    wl = w.tz_convert("Asia/Shanghai")
    dates = wl.index.normalize()
    daily = wl.groupby(dates)["poa_global"].sum()
    summer = daily[(daily.index.month >= 5) & (daily.index.month <= 8)]
    best = (summer if len(summer) else daily).idxmax()
    day = wl[dates == best]
    day = day[day["poa_global"] > 5.0]
    return day


def precompute(city):
    day = representative_day(city)
    h = (day.index.hour + day.index.minute / 60.0).to_numpy()
    # 插值到细网格, 播放更平滑
    hf = np.linspace(h[0], h[-1], N_FRAMES)
    poa = np.interp(hf, h, day["poa_global"].to_numpy())
    tair = np.interp(hf, h, day["temp_air"].to_numpy())
    wind = np.interp(hf, h, day["wind_speed"].to_numpy())
    zen = np.interp(hf, h, day["solar_zenith"].to_numpy())
    aoi_d = np.interp(hf, h, day["aoi"].to_numpy())
    tcell = faiman(poa, tair, wind)

    frames = []
    for k in range(N_FRAMES):
        sfC = spectral_factor_from_zenith(CSI_EARLY, zen[k])
        sfP = spectral_factor_from_zenith(PEROVSKITE, zen[k])
        ia = float(iam(aoi_d[k]))
        recC = operating_point(CSI_EARLY, float(poa[k]), float(tcell[k]),
                               float(poa[k] * sfC * ia), ns=60, npts=120)
        recP = operating_point(PEROVSKITE, float(poa[k]), float(tcell[k]),
                               float(poa[k] * sfP * ia), ns=60, npts=120)
        frames.append({"hour": hf[k], "poa": poa[k], "tcell": tcell[k],
                       "c": recC, "p": recP})
    return hf, tcell, frames


def make_gif(city):
    hf, tcell, frames = precompute(city)
    pmpC = np.array([f["c"].pmp for f in frames])
    pmpP = np.array([f["p"].pmp for f in frames])
    vmax = max(max(f["c"].voc for f in frames), max(f["p"].voc for f in frames)) * 1.05
    imax = max(max(f["c"].isc for f in frames), max(f["p"].isc for f in frames)) * 1.1
    pmax = max(pmpC.max(), pmpP.max()) * 1.15
    cC, cP = color("c-Si"), color("perovskite")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    axT = ax1.twinx()
    ax1.plot(hf, pmpC, color=cC, alpha=0.18, lw=1)
    ax1.plot(hf, pmpP, color=cP, alpha=0.18, lw=1)
    lineC, = ax1.plot([], [], color=cC, lw=2.5, label="早期晶硅")
    lineP, = ax1.plot([], [], color=cP, lw=2.5, label="钙钛矿")
    dotC, = ax1.plot([], [], "o", color=cC, ms=8)
    dotP, = ax1.plot([], [], "o", color=cP, ms=8)
    lineT, = axT.plot([], [], color="firebrick", ls="--", lw=1.6, alpha=0.8, label="电池温度")
    vline = ax1.axvline(hf[0], color="gray", ls=":", lw=1)
    ax1.set_xlim(hf[0], hf[-1]); ax1.set_ylim(0, pmax)
    ax1.set_xlabel("时刻 (h)"); ax1.set_ylabel("单组件功率 Pmax (W)")
    axT.set_ylim(min(20, tcell.min() - 2), tcell.max() * 1.05 + 2)
    axT.set_ylabel("电池温度 (°C)", color="firebrick")
    ax1.set_title("功率随时间 (浅线=全天参照)")
    ax1.legend(loc="upper left"); axT.legend(loc="upper right")

    ivC, = ax2.plot([], [], color=cC, lw=2.5, label="早期晶硅")
    ivP, = ax2.plot([], [], color=cP, lw=2.5, label="钙钛矿")
    mppC, = ax2.plot([], [], "o", color=cC, ms=8)
    mppP, = ax2.plot([], [], "o", color=cP, ms=8)
    ax2.set_xlim(0, vmax); ax2.set_ylim(0, imax)
    ax2.set_xlabel("电压 (V)"); ax2.set_ylabel("电流 (A)")
    ax2.set_title("实时 I-V 曲线 (●=最大功率点)"); ax2.legend(loc="upper right")
    suptitle = fig.suptitle("", fontsize=14, fontweight="bold")

    def update(k):
        f = frames[k]
        lineC.set_data(hf[:k + 1], pmpC[:k + 1]); lineP.set_data(hf[:k + 1], pmpP[:k + 1])
        lineT.set_data(hf[:k + 1], tcell[:k + 1])
        dotC.set_data([hf[k]], [pmpC[k]]); dotP.set_data([hf[k]], [pmpP[k]])
        vline.set_xdata([hf[k], hf[k]])
        ivC.set_data(f["c"].v, f["c"].i); ivP.set_data(f["p"].v, f["p"].i)
        mppC.set_data([f["c"].vmp], [f["c"].imp]); mppP.set_data([f["p"].vmp], [f["p"].imp])
        gap = (pmpP[k] - pmpC[k]) / pmpC[k] * 100 if pmpC[k] > 1 else 0
        hh = int(f["hour"]); mm = int(round((f["hour"] - hh) * 60))
        suptitle.set_text(
            f"{city.name} ({city.note})  真实气象  {hh:02d}:{mm:02d}   "
            f"辐照 {f['poa']:.0f} W/m²   电池温度 {f['tcell']:.0f}°C\n"
            f"晶硅 {pmpC[k]:.0f} W   |   钙钛矿 {pmpP[k]:.0f} W   (钙钛矿领先 {gap:+.0f}%)")
        return (lineC, lineP, dotC, dotP, lineT, ivC, ivP, mppC, mppP, vline, suptitle)

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    anim = animation.FuncAnimation(fig, update, frames=N_FRAMES, interval=120, blit=False)
    gif = f"{OUTDIR}/city_{city.key}.gif"
    anim.save(gif, writer=animation.PillowWriter(fps=10))
    peak = int(np.argmax(pmpC + pmpP)); update(peak)
    fig.savefig(f"{OUTDIR}/city_{city.key}_peak.png", dpi=115)
    plt.close(fig)
    return gif, pmpC, pmpP


def main():
    viz.setup()
    os.makedirs(OUTDIR, exist_ok=True)
    by_key = {c.key: c for c in CITIES}
    for key in PICK:
        city = by_key[key]
        print(f"  渲染 {city.name} ...", flush=True)
        gif, pc, pp = make_gif(city)
        gap_peak = (pp.max() - pc.max()) / pc.max() * 100
        print(f"    {gif}  峰值: 晶硅{pc.max():.0f}W 钙钛矿{pp.max():.0f}W (+{gap_peak:.0f}%)")
    print("完成。")


if __name__ == "__main__":
    main()
