"""Deep dig — the geography of lifetime risk: how much degradation each province absorbs.

问题: 在等 capex 下(隔离纯寿命风险), 每个省能容忍多高的钙钛矿年退化率, 钙钛矿才
仍以 LCOE 胜过晶硅? 优势越大(西南, 温度驱动)→ 容忍度越高(稳健);
优势越薄(西北, 高辐照低温)→ 容忍度越低(脆弱, 寿命一不达标就先翻车).
=> 寿命风险有地理分布: 政策最爱的西北恰是对退化最敏感的地方.

  (a) 敏感面: 省(按优势排序) × 退化率 → 钙钛矿 LCOE 相对晶硅溢价(%), 含平价等高线.
  (b) 容忍度地图(hex): 各省"最大可容忍退化率"(平价退化率).
  (c) 代表省 LCOE-退化曲线: 西南(稳健) vs 西北(脆弱) + 晶硅基线.

运行: python -m scripts.fig_degradation_risk
输出: outputs/figures/MainFig4x_degradation_risk.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon

from pvsim import viz
from pvsim.provinces import PROVINCE_EN, PROVINCE_CODE
from scripts.portfolio_hexmap import HEX_LAYOUT, hex_xy

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DISCOUNT, OPEX = 0.05, 0.015
CAPEX = 0.50           # 等 capex, 隔离纯寿命风险 ($/W)
LIFE = 25              # 等寿命设计 (post-breakthrough)
BURN = 0.03
DEG_CSI = 0.007


def lcoe(capex, y_kwp, life, deg, burn):
    yrs = np.arange(1, int(life)+1); df = (1+DISCOUNT)**-yrs
    yf = (1-burn)*(1-deg)**(yrs-1); yf[0] = (1-burn)
    return (capex*1000*(1+np.sum(OPEX*df))) / np.sum(y_kwp*yf*df)


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = y[y.tech == "晶硅"].set_index("province")["yield_kwh_per_kwp"]
    per = y[y.tech == "钙钛矿"].set_index("province")["yield_kwh_per_kwp"]
    prov = [p for p in csi.index if p in per.index]
    adv = {p: (per[p]/csi[p]-1)*100 for p in prov}

    degs = np.linspace(0.0, 0.05, 60)            # 0–5 %/yr
    # 溢价矩阵 premium[province, deg] = perov_lcoe/csi_lcoe - 1 (%)
    order = sorted(prov, key=lambda p: adv[p])    # 低优势在下
    prem = np.zeros((len(order), len(degs)))
    parity = {}
    for i, p in enumerate(order):
        lc_csi = lcoe(CAPEX, csi[p], LIFE, DEG_CSI, BURN)
        row = np.array([lcoe(CAPEX, per[p], LIFE, dg, BURN)/lc_csi-1 for dg in degs])*100
        prem[i] = row
        # 平价退化率: premium 穿 0 的退化率 (越高越稳健)
        sign = np.sign(row)
        cross = np.where(np.diff(sign) > 0)[0]
        parity[p] = degs[cross[0]]*100 if len(cross) else (degs[-1]*100 if row[-1] < 0 else 0.0)

    fig = plt.figure(figsize=(17, 4.6), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 1.0], wspace=0.28)

    # ===== (a) sensitivity surface =====
    ax = fig.add_subplot(gs[0, 0])
    im = ax.imshow(prem, aspect="auto", origin="lower", cmap="RdBu_r", vmin=-12, vmax=12,
                   extent=[0, 5, 0, len(order)])
    cs = ax.contour(np.linspace(0, 5, len(degs)), np.arange(len(order))+0.5, prem,
                    levels=[0], colors="black", linewidths=1.6)
    ax.clabel(cs, fmt="parity", fontsize=7)
    ax.set_yticks(np.arange(len(order))+0.5)
    ax.set_yticklabels([PROVINCE_CODE.get(p, p) for p in order], fontsize=4.6)
    ax.set_xlabel("Perovskite degradation rate (%/yr)", fontsize=9)
    ax.set_ylabel("Province (low → high advantage)", fontsize=9)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title("(a) LCOE premium surface vs c-Si", fontsize=10.5, fontweight="bold",
                 loc="left", pad=3)
    cb = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label("perovskite LCOE premium (%)", fontsize=7.5); cb.ax.tick_params(labelsize=6.5)
    ax.text(0.4, len(order)*0.92, "perovskite\nWINS", fontsize=7, color="#1b5e20",
            fontweight="bold")
    ax.text(3.6, len(order)*0.08, "perovskite\nLOSES", fontsize=7, color="#7a1f12",
            fontweight="bold")

    # ===== (b) tolerance hex map =====
    ax = fig.add_subplot(gs[0, 1])
    pv = np.array([parity[p] for p in prov])
    vmin, vmax = np.nanmin(pv), np.nanmax(pv)        # 收到实际范围, 放大 SW-NW 对比
    cmap = plt.cm.RdYlGn
    for p, (col, rowp) in HEX_LAYOUT.items():
        xx, yy = hex_xy(col, rowp)
        if p in parity:
            fc = cmap((parity[p]-vmin)/(vmax-vmin)); lbl = f"{parity[p]:.1f}"
        else:
            fc = "#eeeeee"; lbl = ""
        ax.add_patch(RegularPolygon((xx, yy), numVertices=6, radius=0.5, orientation=0,
                                    facecolor=fc, edgecolor="black", linewidth=0.5))
        ax.text(xx, yy+0.1, PROVINCE_CODE.get(p, ""), ha="center", va="center",
                fontsize=5.2, fontweight="bold")
        ax.text(xx, yy-0.17, lbl, ha="center", va="center", fontsize=4.6)
    ax.set_aspect("equal"); ax.set_xlim(0.3, 8.7); ax.set_ylim(-8.7, 1.0); ax.axis("off")
    ax.set_title("(b) Max tolerable degradation (%/yr)", fontsize=10.5, fontweight="bold",
                 loc="left", pad=3)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
    cb = plt.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("tolerance (%/yr)", fontsize=7.5); cb.ax.tick_params(labelsize=6.5)
    ax.text(0.5, 0.02, "green = robust (SW) · red = fragile (NW)", transform=ax.transAxes,
            ha="center", fontsize=7, color="#444", style="italic")

    # ===== (c) representative curves =====
    ax = fig.add_subplot(gs[0, 2])
    reps = [("重庆", "#b30000", "SW robust"), ("四川", "#e34a33", "SW"),
            ("新疆", "#3182bd", "NW fragile"), ("内蒙古", "#6baed6", "NW")]
    dd = np.linspace(0, 0.05, 40)
    for p, c, tag in reps:
        if p not in csi.index:
            continue
        lc_csi = lcoe(CAPEX, csi[p], LIFE, DEG_CSI, BURN)
        prem_c = np.array([lcoe(CAPEX, per[p], LIFE, g, BURN)/lc_csi-1 for g in dd])*100
        ax.plot(dd*100, prem_c, lw=2, color=c,
                label=f"{PROVINCE_EN.get(p,p)} ({tag}, ≤{parity[p]:.1f})")
    ax.axhline(0, color="black", lw=0.8, ls="--")
    ax.fill_between([0, 5], 0, 14, color="#fde0d9", alpha=0.5, zorder=0)
    ax.fill_between([0, 5], -10, 0, color="#e0f0e0", alpha=0.5, zorder=0)
    ax.set_xlabel("Perovskite degradation rate (%/yr)", fontsize=9)
    ax.set_ylabel("LCOE premium vs c-Si (%)", fontsize=9); ax.tick_params(labelsize=8)
    ax.set_xlim(0, 5); ax.set_ylim(-10, 14)
    ax.set_title("(c) SW absorbs more degradation than NW", fontsize=10.2,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7, loc="upper left", frameon=False); ax.grid(alpha=0.25, lw=0.3)
    ax.text(4.8, 11, "perovskite loses", ha="right", fontsize=7, color="#7a1f12")
    ax.text(4.8, -8, "perovskite wins", ha="right", fontsize=7, color="#1b5e20")

    pv_sw = np.mean([parity[p] for p in prov if adv[p] > np.median(list(adv.values()))])
    pv_nw = np.mean([parity[p] for p in prov if adv[p] <= np.median(list(adv.values()))])
    fig.suptitle("The geography of lifetime risk — high-advantage SW absorbs "
                 f"~{pv_sw:.1f}%/yr degradation, low-advantage NW only ~{pv_nw:.1f}%/yr "
                 "(at cost parity)", fontsize=12.5, fontweight="bold", y=1.02)
    fig.savefig("outputs/figures/MainFig4x_degradation_risk.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig4x_degradation_risk.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"saved. tolerance SW~{pv_sw:.2f}%/yr vs NW~{pv_nw:.2f}%/yr; "
          f"range {min(parity.values()):.2f}-{max(parity.values()):.2f}")


if __name__ == "__main__":
    main()
