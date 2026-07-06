"""#2 可行性: 因地制宜的最优带隙 —— 钙钛矿带隙的年发电最优值是否随气候移动?

物理耦合 (单结钙钛矿, 随带隙 Eg):
  - 光谱截止 lambda_gap = 1240/Eg  (进入 EQE)
  - 光生电流 I_L ∝ ∫EQE·E·λ dλ (AM1.5G)  —— 带隙越宽吸的光子越少, 电流越低
  - 开路电压 Voc/cell = Eg - 0.44 V (经验电压亏损) → 由此定 I_o
不同地点的光谱(大气质量)与工作温度分布不同 → 年发电最优带隙可能不同。

运行: python -m scripts.feas_optimal_bandgap
输出: outputs/figures/feas_optimal_bandgap.png + 控制台最优带隙表
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import replace

import pvsim.materials as M
from pvsim.materials import PEROVSKITE, SpectralResponse
from pvsim.spectral import eqe, reference_am15g, _jph_weight
from pvsim.cities import CITIES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KB, Q, T0 = 1.380649e-23, 1.602176634e-19, 298.15
VTH = KB*T0/Q
WL_REF, E_REF = reference_am15g()
_BASE_JPH = _jph_weight(eqe(PEROVSKITE, WL_REF), E_REF, WL_REF)
EN = {"拉萨": "Lhasa(cool/plateau)", "乌鲁木齐": "Urumqi(cool/NW)",
      "成都": "Chengdu(hot/cloudy)", "海口": "Haikou(hot/tropical)",
      "广州": "Guangzhou(hot)"}


def voc_deficit(eg):
    """电压亏损随带隙增大 (宽带隙非辐射复合更重): 1.55eV→0.44V, 每宽 0.1eV 多 ~0.05V。"""
    return 0.44 + 0.5*(eg - 1.55)


def perovskite_at_eg(eg):
    """构造给定带隙的钙钛矿 (耦合 lambda_gap / I_L / I_o), 并注册供光谱查表。"""
    name = f"perov_eg{eg:.3f}"
    if name in M.TECHNOLOGIES:
        return M.TECHNOLOGIES[name]
    sr = replace(PEROVSKITE.spectral, lambda_gap=1240.0/eg)
    jph = _jph_weight(eqe(replace(PEROVSKITE, spectral=sr), WL_REF), E_REF, WL_REF)
    il = PEROVSKITE.I_L_ref * jph/_BASE_JPH
    voc_cell = eg - voc_deficit(eg)
    io = il / (np.exp(voc_cell/(PEROVSKITE.n_ideality*VTH)) - 1.0)
    tech = replace(PEROVSKITE, name=name, name_cn=f"钙钛矿{eg:.2f}",
                   spectral=sr, I_L_ref=il, I_o_ref=io, EgRef=eg)
    M.TECHNOLOGIES[name] = tech
    return tech


def main():
    egs = np.round(np.arange(1.25, 1.86, 0.03), 3)
    cities = ["lhasa", "urumqi", "chengdu", "haikou", "guangzhou"]
    cfg = SystemConfig(n_modules=20)
    area_m2 = 20 * PEROVSKITE.cells_in_series * PEROVSKITE.area_cm2 * 1e-4

    fig, ax = plt.subplots(figsize=(8.5, 5.2), dpi=130)
    print(f"{'city':<10}{'最优Eg':>8}{'峰值kWh/m2':>12}  climate")
    rows = []
    for key in cities:
        c = next(c for c in CITIES if c.key == key)
        w = wx.from_pvgis_tmy(c.lat, c.lon, altitude=c.alt, name=c.key)
        ys = []
        for eg in egs:
            r = simulate(perovskite_at_eg(float(eg)), w, cfg, npts=40)
            ys.append(r["energy_ac_kwh"] / area_m2)   # 每 m² 绝对发电 (=效率×辐照)
        ys = np.array(ys)
        ys_n = ys/ys.max()
        best = egs[np.argmax(ys)]
        ax.plot(egs, ys_n, "o-", ms=3, lw=1.6,
                label=f"{EN.get(c.name, c.key)} — opt {best:.2f} eV")
        ax.axvline(best, color=ax.lines[-1].get_color(), ls=":", lw=0.8, alpha=0.5)
        # 气候量
        ts = simulate(perovskite_at_eg(1.55), w, cfg, npts=40)["timeseries"]
        poa = ts["poa_global"].to_numpy(); tc = ts["tcell"].to_numpy()
        m = poa > 50
        tcw = np.average(tc[m], weights=poa[m])
        print(f"{c.name:<8}{best:>8.2f}{ys.max():>11.0f}   Tcell~{tcw:.0f}°C, alt {c.alt}m")
        rows.append((c.name, best, tcw, c.alt))

    ax.set_xlabel("Perovskite bandgap Eg (eV)")
    ax.set_ylabel("Annual specific yield (normalised to each city's max)")
    ax.set_title("#2 feasibility: does the yield-optimal perovskite bandgap shift by climate?",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8.5); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("outputs/figures/feas_optimal_bandgap.png", bbox_inches="tight")
    plt.close(fig)
    spread = max(r[1] for r in rows) - min(r[1] for r in rows)
    print(f"\n最优带隙城市间跨度: {spread:.2f} eV  "
          f"({'值得深挖' if spread >= 0.03 else '偏平, 需谨慎'})")


if __name__ == "__main__":
    main()
