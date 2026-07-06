"""Main Fig 3 (depth) — geographic inversion decomposed into two independent drivers.

把深度显出来 + 挖到底:
  (a) 真·94k 格点 0.1° 中国连续优势地图 (研究级空间产品).
  (b) 物理分解 (按资源带): 温度分量 vs 光谱分量 —— 温度占比 59%(凉)→72%(热).
  (c) 驱动 1 (温度分量): vs 辐照加权工作温度, r=+0.95 (钙钛矿 γ 小).
  (d) 驱动 2 (光谱分量): vs 辐照加权 airmass, r=-0.95 (钙钛矿带隙宽, 低 airmass 蓝移谱受益).
  => 两个物理独立的机制, 都在低纬西南最大 —— 故反转强.

依赖: outputs/grid_inversion_era5.csv; 31 省分解+驱动现算并缓存.
运行: python -m scripts.fig_geographic_inversion_deep
输出: outputs/figures/MainFig3_geographic_inversion.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib

from pvsim import viz
from pvsim.materials import CSI_MODERN, PEROVSKITE
from pvsim.provinces import PROVINCES, PROVINCE_EN
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RESOURCE_COLOR = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}
DRIVERS_CACHE = "outputs/advantage_drivers.csv"


def _adv(w, **kw):
    cfg = SystemConfig(n_modules=20, **kw)
    rc = simulate(CSI_MODERN, w, cfg, npts=45)
    rp = simulate(PEROVSKITE, w, cfg, npts=45)
    return (rp["specific_yield"]/rc["specific_yield"]-1)*100, rc


def compute_drivers():
    """每省: 优势的温度/光谱分解 + 各自的物理驱动 (工作温度, airmass)。"""
    if os.path.exists(DRIVERS_CACHE):
        return pd.read_csv(DRIVERS_CACHE, encoding="utf-8-sig")
    print("  computing two-driver decomposition (31 prov)...")
    rows = []
    for p in PROVINCES:
        w = wx.from_pvgis_tmy(p.lat, p.lon, altitude=p.alt, name=p.key)
        full, rc = _adv(w)
        no_spec, _ = _adv(w, apply_spectral=False)
        no_spec_no_iam, _ = _adv(w, apply_spectral=False, apply_iam=False)
        ts = rc["timeseries"]; poa = ts["poa_global"].to_numpy(); tc = ts["tcell"].to_numpy()
        zen = w["solar_zenith"].to_numpy(float)
        am = pvlib.atmosphere.get_relative_airmass(zen)
        am = np.where(np.isfinite(am), am, 40.0)
        m = poa > 50
        rows.append({
            "province": p.name, "band": p.res_band, "lat": p.lat,
            "full": full, "thermal": no_spec_no_iam, "spectral": full-no_spec,
            "iam": no_spec-no_spec_no_iam,
            "tcell": float(np.average(tc[m], weights=poa[m])),
            "airmass": float(np.average(np.clip(am, 1, 10)[m], weights=poa[m]))})
    df = pd.DataFrame(rows)
    df.to_csv(DRIVERS_CACHE, index=False, encoding="utf-8-sig")
    return df


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    d = compute_drivers()
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.4), dpi=300)

    # ===== (a) real 94k-cell 0.1° map =====
    ax = axes[0]
    g = pd.read_csv("outputs/grid_inversion_era5.csv", encoding="utf-8-sig")
    sc = ax.scatter(g["lon"], g["lat"], c=g["adv"], s=1.3, cmap="RdYlBu_r",
                    vmin=1, vmax=8, marker="s", edgecolors="none")
    ax.set_xlabel("Longitude (°E)", fontsize=9); ax.set_ylabel("Latitude (°N)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"(a) Advantage at 0.1°, {round(len(g)/1000)}k cells", fontsize=10.5,
                 fontweight="bold", loc="left", pad=3)
    ax.set_xlim(73, 135); ax.set_ylim(17, 54)
    cb = plt.colorbar(sc, ax=ax, shrink=0.82, pad=0.02)
    cb.set_label("perovskite advantage (%)", fontsize=8); cb.ax.tick_params(labelsize=7)

    # ===== (b) decomposition by resource band =====
    ax = axes[1]
    bands = ["I", "II", "III", "IV"]
    blab = {"I": "I\nplateau", "II": "II\nNW", "III": "III\nmost", "IV": "IV\nSW"}
    therm = [d[d.band == b]["thermal"].mean() for b in bands]
    spec = [d[d.band == b]["spectral"].mean() for b in bands]
    iam = [d[d.band == b]["iam"].mean() for b in bands]
    x = np.arange(4)
    ax.bar(x, therm, color="#d6604d", label="temperature", edgecolor="black", lw=0.4)
    ax.bar(x, spec, bottom=therm, color="#f4a582", label="spectral", edgecolor="black", lw=0.4)
    ax.bar(x, iam, bottom=np.array(therm)+np.array(spec), color="#bbbbbb",
           label="IAM/optics", edgecolor="black", lw=0.4)
    for xi in range(4):
        tot = therm[xi]+spec[xi]+iam[xi]
        ax.text(xi, tot+0.1, f"{tot:.1f}%", ha="center", fontsize=7.5, fontweight="bold")
        ax.text(xi, therm[xi]/2, f"{therm[xi]/tot*100:.0f}%", ha="center", va="center",
                fontsize=7, color="white", fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([blab[b] for b in bands], fontsize=8)
    ax.set_ylabel("Advantage by source (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(b) Two components", fontsize=10.5, fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7, loc="upper left", frameon=False)
    ax.text(3, therm[3]+spec[3]+0.5, "temp 59→72%\nas it gets hotter", fontsize=6.6,
            ha="center", color="#7a1f12")

    # ===== (c) driver 1: temperature component vs operating temperature =====
    ax = axes[2]
    r1 = np.corrcoef(d["tcell"], d["thermal"])[0, 1]
    for b in bands:
        sub = d[d.band == b]
        ax.scatter(sub["tcell"], sub["thermal"], s=46, color=RESOURCE_COLOR[b],
                   edgecolors="black", linewidth=0.4, zorder=3, label=f"Band {b}")
    z = np.polyfit(d["tcell"], d["thermal"], 1)
    xx = np.linspace(d["tcell"].min(), d["tcell"].max(), 30)
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.2)
    ax.text(0.05, 0.92, f"r = {r1:+.2f}", transform=ax.transAxes, fontsize=9,
            va="top", fontweight="bold", color="#b2182b")
    ax.set_xlabel("Irradiance-weighted cell temp (°C)", fontsize=9)
    ax.set_ylabel("Temperature component (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(c) Driver 1: small $\\gamma$ x heat", fontsize=10.5,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=6.8, loc="lower right", frameon=False, ncol=2, columnspacing=0.7)
    ax.grid(alpha=0.25, lw=0.3)

    # ===== (d) driver 2: spectral component vs airmass =====
    ax = axes[3]
    r2 = np.corrcoef(d["airmass"], d["spectral"])[0, 1]
    for b in bands:
        sub = d[d.band == b]
        ax.scatter(sub["airmass"], sub["spectral"], s=46, color=RESOURCE_COLOR[b],
                   edgecolors="black", linewidth=0.4, zorder=3, label=f"Band {b}")
    z = np.polyfit(d["airmass"], d["spectral"], 1)
    xx = np.linspace(d["airmass"].min(), d["airmass"].max(), 30)
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.2)
    ax.text(0.05, 0.16, f"r = {r2:+.2f}", transform=ax.transAxes, fontsize=9,
            fontweight="bold", color="#2166ac")
    for _, row in pd.concat([d.nsmallest(1, "airmass"), d.nlargest(1, "airmass")]).iterrows():
        ax.annotate(PROVINCE_EN.get(row["province"], row["province"]),
                    (row["airmass"], row["spectral"]), textcoords="offset points",
                    xytext=(4, 3), fontsize=6.5)
    ax.set_xlabel("Irradiance-weighted air mass", fontsize=9)
    ax.set_ylabel("Spectral component (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(d) Driver 2: wide gap x blue light", fontsize=10.5,
                 fontweight="bold", loc="left", pad=3)
    ax.invert_xaxis()  # 低 airmass(高日照,蓝移)在右
    ax.text(0.97, 0.92, "lower air mass\n= bluer spectrum", transform=ax.transAxes,
            ha="right", va="top", fontsize=6.6, color="#2166ac", style="italic")
    ax.legend(fontsize=6.8, loc="lower left", frameon=False, ncol=2, columnspacing=0.7)
    ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 3 — Geographic inversion = two physically independent advantages "
                 "(temperature r=%.2f, spectral r=%.2f), both maximal in the low-latitude SW"
                 % (r1, r2), fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig3_geographic_inversion.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig3_geographic_inversion.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Main Fig 3 (two-driver) saved. thermal-vs-T r={r1:.2f}, spectral-vs-AM r={r2:.2f}")


if __name__ == "__main__":
    main()
