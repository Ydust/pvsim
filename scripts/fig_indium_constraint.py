"""Main Fig 4 (reframed) — Indium: a global multi-TW constraint, not a China-2030 cap.

[Audit correction] Earlier draft mis-assigned the total material demand
(30,170 t/TWp, Wagner Joule 2024) to indium alone (~15x too high). Corrected to
the authoritative indium intensity (Wagner Table S13: ITO-thickness dependent,
~1.9 kg/MW at 100 nm). The honest finding:

  (a) GLOBAL scale: at 1 TWp/yr and 100 nm ITO, indium demand reaches ~198% of
      world primary production -> a real long-horizon constraint, reducible by
      thinner ITO or indium-free TCO (AZO/FTO).
  (b) CHINA near-term: perovskite+tandem indium demand stays well below domestic
      production through 2050 (DPR < ~40%) -> NOT a near-term Chinese bottleneck.

So indium reframes from "hard cap on China's transition" to "forward-looking,
ITO-dependent global signal that motivates indium-free electrode R&D".

运行: python -m scripts.fig_indium_constraint
输出: outputs/figures/MainFig4_indium_constraint.png/.pdf
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.policy_data import (china_pv_target_gw, INDIUM_T_PER_TWP_BY_ITO,
                                GLOBAL_INDIUM_T_PER_YR,
                                critical_metal_supply_t_per_yr,
                                METAL_INTENSITY_KG_PER_MW)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

C_IN = "#7d3c98"


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), dpi=300)

    # ===== (a) GLOBAL: annual indium demand vs world production over time =====
    # 具体化为时间序列 (与 b 同轴): 若全球 PV 新增都走钙钛矿/叠层, 逐年铟需求 vs
    # 全球年产铟, 看"撞墙年"; 再叠一条薄 ITO 线显示电极设计这个杠杆.
    ax = axes[0]
    gyr = np.arange(2025, 2051)
    # 全球 PV 年新增 (GW/yr): BNEF/IEA 量级, 2024~450 → 2035~1100 → 2040+ ~1400
    g_new = np.interp(gyr, [2025, 2030, 2035, 2040, 2050],
                      [600, 850, 1100, 1400, 1400])
    g_perov = np.clip((gyr - 2026) * 0.09, 0, 0.55)
    g_tand = np.clip((gyr - 2029) * 0.05, 0, 0.32)
    in_per = METAL_INTENSITY_KG_PER_MW["钙钛矿25y"]["In"]   # 1.0 kg/MW @100nm
    in_tan = METAL_INTENSITY_KG_PER_MW["叠层"]["In"]        # 1.9 kg/MW @100nm
    g_demand_100 = g_new * (g_perov * in_per + g_tand * in_tan)        # t/yr @100nm
    g_demand_20 = g_demand_100 * (INDIUM_T_PER_TWP_BY_ITO[20] /
                                  INDIUM_T_PER_TWP_BY_ITO[100])        # 薄 ITO
    g_supply = np.interp(gyr, [2025, 2050], [GLOBAL_INDIUM_T_PER_YR, 1200])

    ax.fill_between(gyr, 0, g_supply, color="#dddddd", zorder=1,
                    label=f"world indium produced (~{GLOBAL_INDIUM_T_PER_YR:.0f}→1200 t/yr)")
    ax.plot(gyr, g_supply, color="#444444", lw=2, zorder=4)
    ax.plot(gyr, g_demand_100, color="#c0392b", lw=2.2, zorder=3,
            label="demand @100 nm ITO (today)")
    ax.plot(gyr, g_demand_20, color="#2a9d4a", lw=2.0, ls="--", zorder=3,
            label="demand @20 nm ITO / In-free path")
    # 撞墙年: demand_100 首次超过 supply
    cross = next((int(gyr[i]) for i in range(len(gyr))
                  if g_demand_100[i] > g_supply[i]), None)
    if cross:
        ci = list(gyr).index(cross)
        ax.scatter(cross, g_demand_100[ci], s=90, color="#c0392b", zorder=5,
                   edgecolors="black", linewidth=0.6)
        ax.annotate(f"wall ~{cross}\n(global demand > world supply)",
                    xy=(cross, g_supply[ci]), xytext=(2033, 2400),
                    fontsize=8, color="#c0392b", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1))
    ax.text(2045, g_demand_20[-1] + 250, "thinner ITO /\nIn-free TCO\nstays under supply",
            fontsize=7.8, color="#2a9d4a", style="italic", ha="center")
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("Indium (t/yr)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(a) Global: all-perovskite PV growth hits an indium wall",
                 fontsize=10, fontweight="bold", loc="left", pad=3)
    ax.set_xlim(2025, 2050); ax.set_ylim(0, 3200)
    ax.legend(fontsize=7.5, loc="upper left", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    # ===== (b) CHINA near-term: annual demand vs domestic supply (tonnes) =====
    ax = axes[1]
    yrs, target = china_pv_target_gw()
    new_gw = np.gradient(target)            # annual new build GW/yr
    yr_arr = yrs
    perov_share = np.clip((yr_arr - 2026) * 0.09, 0, 0.55)
    tand_share = np.clip((yr_arr - 2029) * 0.05, 0, 0.32)
    in_per = METAL_INTENSITY_KG_PER_MW["钙钛矿25y"]["In"]   # 1.0 kg/MW
    in_tan = METAL_INTENSITY_KG_PER_MW["叠层"]["In"]        # 1.9 kg/MW
    in_demand = new_gw * (perov_share * in_per + tand_share * in_tan)
    _, supply = critical_metal_supply_t_per_yr()
    cn_supply = supply["In"]                # China domestic indium t/yr

    ax.fill_between(yr_arr, 0, cn_supply, color="#dddddd", zorder=1,
                    label=f"China indium produced (~{cn_supply[5]:.0f} t/yr)")
    ax.plot(yr_arr, cn_supply, "-", color="#444444", lw=2, zorder=3)
    ax.fill_between(yr_arr, 0, in_demand, color=C_IN, alpha=0.75, zorder=2,
                    label="needed for China's perovskite+tandem build")
    peak_dpr = np.max(in_demand / cn_supply) * 100
    d2030 = in_demand[yrs.tolist().index(2030)]
    s2030 = cn_supply[yrs.tolist().index(2030)]
    ax.annotate(f"2030: {d2030:.0f} t needed\nof {s2030:.0f} t produced ({d2030/s2030*100:.0f}%)",
                xy=(2030, d2030), xytext=(2031, s2030*0.62),
                fontsize=8.2, color="#222222",
                arrowprops=dict(arrowstyle="->", color=C_IN, lw=0.9),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.text(2037, s2030*0.30, f"peak ever ~{peak_dpr:.0f}% of supply\n→ not binding for China",
            fontsize=8.2, color="#2a9d4a", fontweight="bold")
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("Indium (t/yr)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(b) China: its own build barely touches domestic indium",
                 fontsize=10, fontweight="bold", loc="left", pad=3)
    ax.set_xlim(2025, 2050); ax.set_ylim(0, max(cn_supply)*1.15)
    ax.legend(fontsize=7.8, loc="upper left", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    fig.suptitle("Fig 4 — Indium constrains the global TW-scale build, not China's "
                 "near-term transition (intensity: Wagner, Joule 2024)",
                 fontsize=11.5, fontweight="bold", y=1.02)
    # 兼容旧打印变量
    i100, dpr = 0, [INDIUM_T_PER_TWP_BY_ITO[100] / GLOBAL_INDIUM_T_PER_YR * 100]
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig4_indium_constraint.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig4_indium_constraint.pdf",
                bbox_inches="tight")
    plt.close(fig)
    print(f"Main Fig 4 saved.")
    print(f"  (a) 100nm ITO needs {INDIUM_T_PER_TWP_BY_ITO[100]:.0f} t/TWp "
          f"= {dpr[0]:.0f}% of world annual indium")
    print(f"  (b) China peak demand-production ratio = {peak_dpr:.0f}%")
    print(f"      China In demand 2030 = {in_demand[yrs.tolist().index(2030)]:.0f} t/yr "
          f"vs supply {cn_supply[yrs.tolist().index(2030)]:.0f} t/yr")


if __name__ == "__main__":
    main()
