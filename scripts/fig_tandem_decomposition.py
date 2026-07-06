"""Deep dig — tandem's advantage is almost purely non-spectral (hypothesis refuted).

原假设: 叠层顶电池带隙更宽 → 光谱分量更大. 实测 **推翻**:
  叠层底电池(晶硅)吃红光, 整体仍吸收全光谱 → 对 c-Si 的光谱失配 ≈ 0.
  反而单结钙钛矿(只吃蓝光, 800nm 锐截止)才有大光谱优势.
=> 单结钙钛矿优势 = 温度 + 光谱 (双腿); 叠层优势 = 温度(+弱光), 光谱≈0 (单腿).
   含义: 叠层在多云/低 airmass 地区拿不到额外光谱红利, 它的地理优势纯由温度决定.

  (a) 全国均值 2 成分: 钙钛矿 vs 叠层 (光谱 vs 非光谱)
  (b) 光谱分量 vs 资源带: 钙钛矿随带增长, 叠层恒≈0
  (c) 光谱分量 vs airmass: 钙钛矿强负相关 (r), 叠层平贴 0

运行: python -m scripts.fig_tandem_decomposition
输出: outputs/figures/MainFig3y_tandem_decomposition.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib

from pvsim import viz
from pvsim.materials import CSI_MODERN, PEROVSKITE, TANDEM_2T
from pvsim.provinces import PROVINCES, PROVINCE_EN
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TANDEM_CACHE = "outputs/advantage_drivers_tandem.csv"
C_PER, C_TAN = "#e2641e", "#2a9d4a"


def compute_tandem_drivers():
    if os.path.exists(TANDEM_CACHE):
        return pd.read_csv(TANDEM_CACHE, encoding="utf-8-sig")
    print("  computing tandem decomposition (31 prov)...")
    rows = []
    for p in PROVINCES:
        w = wx.from_pvgis_tmy(p.lat, p.lon, altitude=p.alt, name=p.key)

        def adv(**kw):
            cfg = SystemConfig(n_modules=20, **kw)
            rc = simulate(CSI_MODERN, w, cfg, npts=45)
            rt = simulate(TANDEM_2T, w, cfg, npts=45)
            return (rt["specific_yield"]/rc["specific_yield"]-1)*100, rc
        full, rc = adv()
        no_spec, _ = adv(apply_spectral=False)
        ts = rc["timeseries"]; poa = ts["poa_global"].to_numpy(); tc = ts["tcell"].to_numpy()
        am = pvlib.atmosphere.get_relative_airmass(w["solar_zenith"].to_numpy(float))
        am = np.where(np.isfinite(am), am, 40.0); m = poa > 50
        rows.append({"province": p.name, "band": p.res_band,
                     "full": full, "spectral": full-no_spec, "nonspec": no_spec,
                     "tcell": float(np.average(tc[m], weights=poa[m])),
                     "airmass": float(np.average(np.clip(am, 1, 10)[m], weights=poa[m]))})
    df = pd.DataFrame(rows)
    df.to_csv(TANDEM_CACHE, index=False, encoding="utf-8-sig")
    return df


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    dt = compute_tandem_drivers()
    dp = pd.read_csv("outputs/advantage_drivers.csv", encoding="utf-8-sig")
    dp["nonspec"] = dp["full"] - dp["spectral"]      # 钙钛矿 非光谱 = 温度+弱光+iam
    bands = ["I", "II", "III", "IV"]
    blab = {"I": "I", "II": "II", "III": "III", "IV": "IV"}

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), dpi=300)

    # ===== (a) national-mean 2-component bars =====
    ax = axes[0]
    techs = [("Perovskite", dp, C_PER), ("Tandem", dt, C_TAN)]
    x = np.arange(2)
    ns = [d["nonspec"].mean() for _, d, _ in techs]
    sp = [d["spectral"].mean() for _, d, _ in techs]
    ax.bar(x, ns, 0.5, color=["#f4a582", "#a6dba0"], edgecolor="black", lw=0.5,
           label="non-spectral (temp + low-light)")
    ax.bar(x, sp, 0.5, bottom=ns, color=["#b2182b", "#1b7837"], edgecolor="black",
           lw=0.5, label="spectral")
    for xi in range(2):
        ax.text(xi, ns[xi]+sp[xi]+0.12, f"{ns[xi]+sp[xi]:.1f}%", ha="center",
                fontsize=8.5, fontweight="bold")
        ax.text(xi, ns[xi]+sp[xi]/2, f"spec\n{sp[xi]:.2f}%", ha="center", va="center",
                fontsize=7, color="white", fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(["Perovskite", "Tandem"], fontsize=9.5)
    ax.set_ylabel("Advantage over c-Si (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(a) Tandem's spectral leg ~ 0", fontsize=11, fontweight="bold",
                 loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="upper right", frameon=False)
    ax.annotate("full-spectrum absorber\n(bottom Si eats the red)\n-> spectrally like c-Si",
                xy=(1, ns[1]+sp[1]), xytext=(0.3, ns[1]*0.5), fontsize=7,
                color="#1b5e20", arrowprops=dict(arrowstyle="->", color=C_TAN, lw=0.8))

    # ===== (b) spectral component vs resource band =====
    ax = axes[1]
    sp_p = [dp[dp.band == b]["spectral"].mean() for b in bands]
    sp_t = [dt[dt.band == b]["spectral"].mean() for b in bands]
    ax.plot(range(4), sp_p, "o-", color=C_PER, lw=2, ms=6, label="Perovskite")
    ax.plot(range(4), sp_t, "s-", color=C_TAN, lw=2, ms=6, label="Tandem")
    ax.axhline(0, color="gray", lw=0.5)
    ax.set_xticks(range(4)); ax.set_xticklabels([blab[b] for b in bands], fontsize=9)
    ax.set_xlabel("Resource band (I plateau → IV SW)", fontsize=9)
    ax.set_ylabel("Spectral component (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_title("(b) Spectral leg grows for perovskite only", fontsize=10.5,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=8, loc="center left", frameon=False); ax.grid(alpha=0.25, lw=0.3)
    ax.text(2.0, 0.18, "tandem flat ~0.1%", fontsize=7.5, color=C_TAN, style="italic")

    # ===== (c) spectral vs airmass =====
    ax = axes[2]
    rp = np.corrcoef(dp["airmass"], dp["spectral"])[0, 1]
    rt = np.corrcoef(dt["airmass"], dt["spectral"])[0, 1]
    ax.scatter(dp["airmass"], dp["spectral"], s=34, color=C_PER, edgecolors="black",
               linewidth=0.3, label=f"Perovskite (r={rp:+.2f})", zorder=3)
    ax.scatter(dt["airmass"], dt["spectral"], s=34, color=C_TAN, edgecolors="black",
               linewidth=0.3, label="Tandem (flat ~0%)", zorder=3)
    z = np.polyfit(dp["airmass"], dp["spectral"], 1)
    xx = np.linspace(dp["airmass"].min(), dp["airmass"].max(), 20)
    ax.plot(xx, np.polyval(z, xx), "--", color=C_PER, lw=1.1)
    ax.axhline(0, color="gray", lw=0.5)
    ax.set_xlabel("Irradiance-weighted air mass", fontsize=9)
    ax.set_ylabel("Spectral component (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.invert_xaxis()
    ax.set_title("(c) Only perovskite tracks the spectrum", fontsize=10.5,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=8, loc="upper right", frameon=False); ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Against modern silicon the tandem has almost no per-kWp edge (0.9%) and no "
                 "spectral component — a full-spectrum absorber; its value is area, not utility yield",
                 fontsize=11.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig3y_tandem_decomposition.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig3y_tandem_decomposition.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"saved. perov spectral mean={dp['spectral'].mean():.2f}%, "
          f"tandem spectral mean={dt['spectral'].mean():.2f}%; "
          f"airmass r: perov={rp:+.2f} tandem={rt:+.2f}")


if __name__ == "__main__":
    main()
