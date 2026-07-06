"""Main Fig 3a (mechanism) — the inversion IS a temperature effect.

加固地理反转的因果机制 (回应"辐照只是代理/会不会伪相关"):
  (a) 器件级: 相对功率随电池温度的响应, c-Si 陡 (γ≈-0.45%/°C) vs 钙钛矿平
      (γ≈-0.15%/°C); 两线随温度发散 = 高温下钙钛矿赢的物理根源.
  (b) 地理级: 31 省钙钛矿优势 vs 辐照加权工作温度, r=0.93 (强正) —— 温度是真因;
      优势 vs 年辐照 r=-0.52 只是温度与辐照在中国地理上负相关的"投影".

运行: python -m scripts.fig_temperature_mechanism
输出: outputs/figures/MainFig3a_temperature_mechanism.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.module import module_pmp
from pvsim.provinces import PROVINCE_EN

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

C_CSI, C_PER = "#1f6fb2", "#e2641e"
RESOURCE_COLOR = {"I": "#d62728", "II": "#ff7f0e", "III": "#2ca02c", "IV": "#1f77b4"}


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)

    # ===== (a) device-level temperature response =====
    ax = axes[0]
    T = np.linspace(10, 65, 40)
    G = 800.0
    p_csi = np.array([module_pmp(CSI_EARLY, G, t, npts=60) for t in T])
    p_per = np.array([module_pmp(PEROVSKITE, G, t, npts=60) for t in T])
    # 归一到 25°C
    p_csi /= np.interp(25, T, p_csi); p_per /= np.interp(25, T, p_per)
    ax.plot(T, p_csi * 100, color=C_CSI, lw=2.2, label="c-Si  (γ ≈ −0.45%/°C)")
    ax.plot(T, p_per * 100, color=C_PER, lw=2.2, label="perovskite  (γ ≈ −0.15%/°C)")
    ax.axvline(25, color="gray", ls=":", lw=0.8)
    ax.fill_between(T, p_csi * 100, p_per * 100, where=(p_per >= p_csi),
                    color=C_PER, alpha=0.12)
    # 标注 50°C 处的差距
    i50 = np.argmin(np.abs(T - 55))
    gap = (p_per[i50] - p_csi[i50]) * 100
    ax.annotate(f"+{gap:.1f}% at 55°C\n(perovskite keeps more power)",
                xy=(55, p_per[i50]*100), xytext=(33, 88),
                fontsize=7.8, color="#7a3410",
                arrowprops=dict(arrowstyle="->", color=C_PER, lw=0.8))
    ax.set_xlabel("Cell operating temperature (°C)", fontsize=9)
    ax.set_ylabel("Relative power (% of value at 25°C)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(a) Device cause: the two temperature slopes", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=8, loc="lower left", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    # ===== (b) geographic consequence: advantage vs operating temperature =====
    ax = axes[1]
    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = y[y.tech == "晶硅"].set_index("province")
    per = y[y.tech == "钙钛矿"].set_index("province")
    prov = [p for p in csi.index if p in per.index]
    adv = np.array([(per.loc[p, "yield_kwh_per_kwp"] /
                     csi.loc[p, "yield_kwh_per_kwp"] - 1) * 100 for p in prov])
    tcell = np.array([csi.loc[p, "tcell_weighted"] for p in prov])
    ghi = np.array([csi.loc[p, "ghi_kwh_m2"] for p in prov])
    band = [csi.loc[p, "res_band"] for p in prov]
    r_t = np.corrcoef(tcell, adv)[0, 1]
    r_g = np.corrcoef(ghi, adv)[0, 1]
    for b in ["I", "II", "III", "IV"]:
        m = [i for i, bb in enumerate(band) if bb == b]
        ax.scatter(tcell[m], adv[m], s=55, color=RESOURCE_COLOR[b],
                   edgecolors="black", linewidth=0.4, zorder=3, label=f"Band {b}")
    z = np.polyfit(tcell, adv, 1)
    xx = np.linspace(tcell.min(), tcell.max(), 40)
    ax.plot(xx, np.polyval(z, xx), "k--", lw=1.3, zorder=2)
    # 标极值省
    for i in list(np.argsort(adv)[-2:]) + list(np.argsort(adv)[:2]):
        ax.annotate(PROVINCE_EN.get(prov[i], prov[i]), (tcell[i], adv[i]),
                    textcoords="offset points", xytext=(5, 3), fontsize=6.8)
    ax.text(0.04, 0.92, f"advantage vs operating T:  r = {r_t:.2f}\n"
            f"(vs irradiance: r = {r_g:.2f}, only a proxy)",
            transform=ax.transAxes, fontsize=8, va="top",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.set_xlabel("Irradiance-weighted cell temperature (°C)", fontsize=9)
    ax.set_ylabel("Perovskite yield advantage (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(b) Geographic effect: advantage is a temperature effect",
                 fontsize=11, fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="lower right", frameon=False, ncol=2,
              columnspacing=0.8)
    ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 3a — The geographic inversion is a temperature effect "
                 "(device cause → spatial consequence)",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig3a_temperature_mechanism.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig3a_temperature_mechanism.pdf",
                bbox_inches="tight")
    plt.close(fig)
    print(f"Main Fig 3a saved. adv-vs-Tcell r={r_t:.3f}, adv-vs-GHI r={r_g:.3f}")
    print(f"  device gap at 55°C: +{gap:.1f}%")


if __name__ == "__main__":
    main()
