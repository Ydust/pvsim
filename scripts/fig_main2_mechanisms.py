"""提议的新 Figure 2 — 两个机制, 各有物理驱动, 且相互独立 (2 栏版)。

  (a) 两个机制叠在一张图 (双 x 轴):
        红点=温度分量 vs 电池温度 (读下方红轴), r=+0.98;
        蓝点=光谱分量 vs 大气质量 (读上方蓝轴), r=-0.85.
  (b) 独立性 (时间): 31 省平均 + 10–90% 分布带 —— 温度优势只在夏季、光谱优势全年.

运行: python -m scripts.fig_main2_mechanisms
输出: outputs/figures/NEWFig2_mechanisms.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from pvsim import viz
from pvsim.materials import CSI_MODERN, PEROVSKITE
from pvsim.module import module_pmp
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

C_T, C_S = "#d6604d", "#2166ac"          # 温度=红, 光谱=蓝
C_TL, C_SL = "#f0b0a4", "#a8cbe2"        # 网格点淡色


def gamma(tech):
    return (module_pmp(tech, 800, 45, npts=60)/module_pmp(tech, 800, 25, npts=60) - 1)/20*100


def seasonal_profiles():
    """31 省逐月 温度/光谱优势 (POA 加权; 缓存到 outputs/seasonal_profiles.csv)。"""
    cache = "outputs/seasonal_profiles.csv"
    if os.path.exists(cache):
        return pd.read_csv(cache, encoding="utf-8-sig")
    from pvsim.provinces import PROVINCES
    dg = gamma(PEROVSKITE) - gamma(CSI_MODERN)
    cfg = SystemConfig(n_modules=20)
    rows = []
    for p in PROVINCES:
        w = wx.from_pvgis_tmy(p.lat, p.lon, altitude=p.alt, name=p.key)
        rc = simulate(CSI_MODERN, w, cfg, npts=45)
        rp = simulate(PEROVSKITE, w, cfg, npts=45)
        poa = rc["timeseries"]["poa_global"].to_numpy()
        tcell = rc["timeseries"]["tcell"].to_numpy()
        sfc = rc["timeseries"]["spectral_factor"].to_numpy()
        sfp = rp["timeseries"]["spectral_factor"].to_numpy()
        months = pd.to_datetime(w.index[:len(poa)]).month.to_numpy()
        m = poa > 80
        therm = dg*(tcell-25); spec = (sfp/np.maximum(sfc, 1e-9)-1)*100
        for k in range(1, 13):
            sel = m & (months == k)
            if sel.any():
                rows.append({"province": p.name, "month": k,
                             "temp": float(np.average(therm[sel], weights=poa[sel])),
                             "spec": float(np.average(spec[sel], weights=poa[sel]))})
    df = pd.DataFrame(rows)
    df.to_csv(cache, index=False, encoding="utf-8-sig")
    return df


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    d = pd.read_csv("outputs/advantage_drivers.csv", encoding="utf-8-sig")
    gpath = "outputs/advantage_drivers_grid.csv"
    dg = pd.read_csv(gpath, encoding="utf-8-sig") if os.path.exists(gpath) else None
    dall = pd.concat([d, dg]) if dg is not None else d

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0), dpi=300)

    # ===== (a) 两个机制叠加 (双 x 轴) =====
    ax = axes[0]
    # 机制 1: 温度 (红, 下方 x = 电池温度)
    r1 = np.corrcoef(dall["tcell"], dall["thermal"])[0, 1]
    if dg is not None:
        ax.scatter(dg["tcell"], dg["thermal"], s=10, color=C_TL, alpha=0.55,
                   edgecolors="none", zorder=2)
    ax.scatter(d["tcell"], d["thermal"], s=34, color=C_T, marker="o",
               edgecolors="black", linewidth=0.35, zorder=4)
    z1 = np.polyfit(dall["tcell"], dall["thermal"], 1)
    xx1 = np.linspace(dall["tcell"].min(), dall["tcell"].max(), 20)
    ax.plot(xx1, np.polyval(z1, xx1), "--", color=C_T, lw=1.4, zorder=5)
    ax.set_xlabel("Irradiance-weighted cell temperature (°C)", fontsize=9, color=C_T)
    ax.tick_params(axis="x", labelcolor=C_T, labelsize=8); ax.tick_params(axis="y", labelsize=8)
    ax.set_ylabel("Advantage component (%)", fontsize=9.5)
    ax.text(0.045, 0.95, f"temperature  r = {r1:+.2f}", transform=ax.transAxes,
            color=C_T, fontsize=9.5, fontweight="bold", va="top")

    # 机制 2: 光谱 (蓝, 上方 x = 大气质量, 反向)
    axt = ax.twiny()
    r2 = np.corrcoef(dall["airmass"], dall["spectral"])[0, 1]
    if dg is not None:
        axt.scatter(dg["airmass"], dg["spectral"], s=10, color=C_SL, alpha=0.55,
                    edgecolors="none", zorder=2)
    axt.scatter(d["airmass"], d["spectral"], s=34, color=C_S, marker="s",
                edgecolors="black", linewidth=0.35, zorder=4)
    z2 = np.polyfit(dall["airmass"], dall["spectral"], 1)
    xx2 = np.linspace(dall["airmass"].min(), dall["airmass"].max(), 20)
    axt.plot(xx2, np.polyval(z2, xx2), "--", color=C_S, lw=1.4, zorder=5)
    axt.invert_xaxis()
    axt.set_xlabel("Irradiance-weighted air mass  (← bluer spectrum)", fontsize=9, color=C_S)
    axt.tick_params(axis="x", labelcolor=C_S, labelsize=8)
    ax.text(0.955, 0.30, f"spectral  r = {r2:+.2f}", transform=ax.transAxes,
            color=C_S, fontsize=9.5, fontweight="bold", ha="right")

    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=C_T,
                      markeredgecolor="black", markersize=7, label="temperature  (read ↓ red axis)"),
               Line2D([0], [0], marker="s", color="none", markerfacecolor=C_S,
                      markeredgecolor="black", markersize=7, label="spectral  (read ↑ blue axis)")]
    ax.legend(handles=handles, fontsize=7.8, loc="lower right", frameon=True,
              framealpha=0.9, edgecolor="#ccc")
    ax.set_title("(a) Two mechanisms, two independent drivers", fontsize=10.5,
                 fontweight="bold", loc="left", pad=24)
    ax.grid(alpha=0.2, lw=0.3)

    # ===== (b) 独立性: 时间指纹 (31 省平均 + 10–90% 分布带) =====
    ax = axes[1]
    sp = seasonal_profiles()
    M = np.arange(1, 13)
    tmat = sp.pivot(index="province", columns="month", values="temp").reindex(columns=M)
    smat = sp.pivot(index="province", columns="month", values="spec").reindex(columns=M)
    ax.fill_between(M, tmat.quantile(0.1), tmat.quantile(0.9), color=C_T, alpha=0.15, lw=0)
    ax.fill_between(M, smat.quantile(0.1), smat.quantile(0.9), color=C_S, alpha=0.15, lw=0)
    tm, sm = tmat.mean().to_numpy(), smat.mean().to_numpy()
    ax.plot(M, tm, "o-", color=C_T, lw=2, ms=4, label="temperature")
    ax.plot(M, sm, "s-", color=C_S, lw=2, ms=4, label="spectral")
    ax.axhline(0, color="gray", lw=0.5)
    cvt = np.nanstd(tm)/abs(np.nanmean(tm)); cvs = np.nanstd(sm)/abs(np.nanmean(sm))
    ax.set_xticks([1, 4, 7, 10]); ax.set_xlabel("Month", fontsize=9)
    ax.set_ylabel("Advantage by mechanism (%)", fontsize=9.5); ax.tick_params(labelsize=8)
    ax.set_title("(b) Independent in time (31 provinces)", fontsize=10.5,
                 fontweight="bold", loc="left", pad=24)
    ax.legend(fontsize=8, loc="upper left", frameon=False); ax.grid(alpha=0.25, lw=0.3)
    ax.annotate("temperature:\nsummer only", xy=(7, tm.max()), xytext=(2.0, tm.max()*0.62),
                fontsize=7, color="#7a1f12",
                arrowprops=dict(arrowstyle="->", color=C_T, lw=0.7))
    ax.text(8.6, sm.min()-0.12, "spectral:\nall year", fontsize=7, color=C_S)
    ax.text(0.5, 0.03, "shaded = 10–90% across provinces", transform=ax.transAxes,
            fontsize=6.5, color="#888", ha="center")

    fig.suptitle("Fig 2 — The advantage is two physically independent mechanisms: a temperature "
                 "term and a spectral term, each with its own driver and time signature",
                 fontsize=11.5, fontweight="bold", y=1.04)
    for a in fig.axes:
        a.grid(False)
    fig.tight_layout()
    fig.savefig("outputs/figures/NEWFig2_mechanisms.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved NEWFig2 (2-panel). r_temp={r1:+.2f}, r_spec={r2:+.2f}, "
          f"n_grid={0 if dg is None else len(dg)}, CV temp={cvt:.2f} spec={cvs:.2f}")


if __name__ == "__main__":
    main()
