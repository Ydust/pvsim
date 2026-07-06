"""Deep dig — the two advantage mechanisms have distinct TEMPORAL fingerprints.

把 Fig3 的"双机制"在时间域再证 (独立性的第二证据). 用干净的解析指标, 避免弱光污染:
  温度层  = Δγ·(Tcell - 25)           (纯温度系数差, Δγ 由 module_pmp 斜率定)
  光谱层  = SF_perov / SF_csi - 1       (直接用逐时光谱失配因子, 纯 airmass 效应)
两者都直接来自孪生 timeseries.

  预期: 温度层随"热" → 盛夏午后峰 (且滞后正午, 因气温滞后辐照);
        光谱层随"低 airmass" → 正午峰, 全年都有, 季节性弱.
  => 时间指纹不同 (峰时刻 + 季节强度) => 机制独立, 与 Fig3 的 r=+0.95/-0.95 互证.

运行: python -m scripts.fig_temporal_fingerprint
输出: outputs/figures/MainFig3x_temporal_fingerprint.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.materials import CSI_MODERN, PEROVSKITE
from pvsim.module import module_pmp
from pvsim.cities import CITIES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

C_THERM, C_SPEC = "#d6604d", "#2166ac"


def gamma(tech):
    p25 = module_pmp(tech, 800, 25, npts=60); p45 = module_pmp(tech, 800, 45, npts=60)
    return (p45/p25 - 1)/20*100        # %/°C


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    city = next(c for c in CITIES if c.key == "wuhan")
    w = wx.from_pvgis_tmy(city.lat, city.lon, altitude=city.alt, name=city.key)
    cfg = SystemConfig(n_modules=20)
    rc = simulate(CSI_MODERN, w, cfg, npts=55)
    rp = simulate(PEROVSKITE, w, cfg, npts=55)
    ts_c, ts_p = rc["timeseries"], rp["timeseries"]

    poa = ts_c["poa_global"].to_numpy()
    tcell = ts_c["tcell"].to_numpy()
    sfc = ts_c["spectral_factor"].to_numpy()
    sfp = ts_p["spectral_factor"].to_numpy()
    dgamma = gamma(PEROVSKITE) - gamma(CSI_MODERN)     # +0.30 %/°C

    m = poa > 80
    thermal = np.where(m, dgamma*(tcell-25), np.nan)
    spectral = np.where(m, (sfp/np.maximum(sfc, 1e-9)-1)*100, np.nan)

    # PVGIS TMY 索引是 UTC; 由最小天顶角定太阳正午, 数据驱动地移到当地太阳时
    zen = w["solar_zenith"].to_numpy(float)
    hutc = np.arange(len(zen)) % 24
    noon = int(np.argmin([np.nanmean(zen[hutc == h]) for h in range(24)]))
    shift = (12 - noon) % 24

    def grid(a):
        g = np.full((24, 365), np.nan); n = min(len(a), 8760)
        g.T.flat[:n] = a[:n]
        return np.roll(g, shift, axis=0)            # 行=当地太阳时
    gth, gsp = grid(thermal), grid(spectral)

    hours = (np.arange(8760) + shift) % 24          # 当地太阳时
    idx = w.index[:8760]
    months = pd.to_datetime(idx).month.to_numpy() if len(w.index) >= 8760 \
        else np.clip(np.arange(len(thermal))//730+1, 1, 12)
    wgt = np.where(m, np.maximum(poa, 0), 0.0)[:8760]

    def wmean_by(key, val, K):
        val = val[:8760]; out = []
        for k in K:
            sel = (key == k) & np.isfinite(val) & (wgt > 0)
            out.append(np.average(val[sel], weights=wgt[sel]) if sel.any() else np.nan)
        return np.array(out)

    fig, axes = plt.subplots(1, 4, figsize=(19, 4.3), dpi=300)

    # (a)(b) heatmaps
    im0 = axes[0].imshow(gth, aspect="auto", origin="lower", cmap="RdBu_r",
                         vmin=-3, vmax=9, extent=[1, 365, 0, 24])
    im1 = axes[1].imshow(gsp, aspect="auto", origin="lower", cmap="RdBu_r",
                         vmin=-1.6, vmax=1.6, extent=[1, 365, 0, 24])
    for ax, im, ttl in [
            (axes[0], im0, "(a) Temperature layer: on in summer only"),
            (axes[1], im1, "(b) Spectral layer: persistent midday band")]:
        ax.set_xlabel("Day of year", fontsize=9); ax.set_ylabel("Hour", fontsize=9)
        ax.tick_params(labelsize=8)
        cb = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02); cb.ax.tick_params(labelsize=6.5)
        cb.set_label("advantage (%)", fontsize=7.5)
        ax.set_title(ttl, fontsize=10.5, fontweight="bold", loc="left", pad=3)

    # (c) diurnal fingerprint
    ax = axes[2]
    H = np.arange(5, 20)
    th_h, sp_h = wmean_by(hours, thermal, H), wmean_by(hours, spectral, H)
    ax.plot(H, th_h, "o-", color=C_THERM, lw=2, ms=4, label="temperature")
    ax.plot(H, sp_h, "s-", color=C_SPEC, lw=2, ms=4, label="spectral")
    hp_t, hp_s = H[np.nanargmax(th_h)], H[np.nanargmax(sp_h)]
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(hp_s, color=C_SPEC, ls=":", lw=0.9); ax.axvline(hp_t, color=C_THERM, ls=":", lw=0.9)
    ax.set_xlabel("Hour of day", fontsize=9); ax.set_ylabel("Advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(c) Diurnal: both peak at solar noon", fontsize=10.5,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=8, loc="upper right", frameon=False); ax.grid(alpha=0.25, lw=0.3)
    ax.text(0.5, 0.06, "shared timing diurnally\n=> distinction is seasonal (d)",
            transform=ax.transAxes, ha="center", fontsize=6.8, color="#555", style="italic")

    # (d) seasonal fingerprint
    ax = axes[3]
    M = np.arange(1, 13)
    th_m, sp_m = wmean_by(months, thermal, M), wmean_by(months, spectral, M)
    ax.plot(M, th_m, "o-", color=C_THERM, lw=2, ms=4, label="temperature")
    ax.plot(M, sp_m, "s-", color=C_SPEC, lw=2, ms=4, label="spectral")
    cv_t = np.nanstd(th_m)/abs(np.nanmean(th_m)); cv_s = np.nanstd(sp_m)/abs(np.nanmean(sp_m))
    ax.axhline(0, color="gray", lw=0.5)
    ax.set_xlabel("Month", fontsize=9); ax.set_ylabel("Advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8); ax.set_xticks([1, 4, 7, 10])
    ax.set_title(f"(d) Seasonal: temp swings (CV {cv_t:.2f}) vs spectral flat ({cv_s:.2f})",
                 fontsize=10.5, fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=8, loc="upper left", frameon=False); ax.grid(alpha=0.25, lw=0.3)
    ax.annotate("temperature switches OFF\nin winter (cold -> ~0)", xy=(1, th_m[0]),
                xytext=(2.6, np.nanmax(th_m)*0.5), fontsize=6.8, color="#7a1f12",
                arrowprops=dict(arrowstyle="->", color=C_THERM, lw=0.7))
    ax.annotate("spectral persists", xy=(11, sp_m[10]), xytext=(6.0, np.nanmin(th_m)+0.4),
                fontsize=6.8, color=C_SPEC,
                arrowprops=dict(arrowstyle="->", color=C_SPEC, lw=0.7))

    fig.suptitle("Temporally decoupled mechanisms — the temperature advantage is seasonal "
                 "(summer only), the spectral advantage persists year-round "
                 f"({city.key.capitalize()}; $\\Delta\\gamma$={dgamma:+.2f}%/°C)",
                 fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig3x_temporal_fingerprint.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig3x_temporal_fingerprint.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"saved. dgamma={dgamma:+.3f}; diurnal peaks spectral={hp_s}h thermal={hp_t}h; "
          f"seasonal CV thermal={cv_t:.2f} spectral={cv_s:.2f}")


if __name__ == "__main__":
    main()
