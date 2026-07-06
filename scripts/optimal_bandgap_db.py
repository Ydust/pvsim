"""#2 — 因地制宜的最优带隙 (Shockley-Queisser 细致平衡版)。

用细致平衡而非"换 De Soto 参数"来定带隙→器件, 避免边界 railing:
  Jsc(Eg, 光谱) = q ∫_{E>Eg} 光子通量
  J0(Eg, T)     = q π ∫_{E>Eg} 黑体光子发射   (温度由此自然进入 → 温度系数)
  Voc = (kT/q) ln(Jsc/J0+1) − ΔV_nonrad      (ΔV_nonrad ~0.15V, 非辐射亏损)
  FF  = (v − ln(v+0.72))/(v+1),  v = qVoc/kT
  η   = Jsc·Voc·FF / Pin
年发电(每 m²) ∝ Σ_hour η(Eg, 光谱(大气质量h), Tcell h) × POA h。

各地大气质量分布(光谱)与工作温度不同 → 年发电最优带隙不同。
运行: python -m scripts.optimal_bandgap_db
"""

import sys
import numpy as np

from pvsim.materials import PEROVSKITE
from pvsim.spectral import generate_spectrum
from pvsim.cities import CITIES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

H, C, Q, KB = 6.62607015e-34, 2.99792458e8, 1.602176634e-19, 1.380649e-23
DV_NONRAD = 0.15
AM_NODES = np.array([1.0, 1.3, 1.7, 2.2, 3.0, 4.2, 6.0])
T_NODES = np.array([5.0, 18.0, 30.0, 42.0, 54.0, 66.0])   # °C
EGS = np.round(np.arange(1.05, 1.81, 0.025), 3)


def _spectrum_for_am(am):
    zen = float(np.degrees(np.arccos(np.clip(1.0/am, 0.02, 1.0))))
    wl, E = generate_spectrum(zen)
    return wl.astype(float), np.clip(E.astype(float), 0, None)


def _jsc_pin(wl_nm, E, eg):
    """给定光谱与带隙: 返回 (Jsc [A/m^2], Pin [W/m^2])。"""
    wl = wl_nm*1e-9
    E_si = E*1e9                              # W/m^2/m
    eph = H*C/wl                              # 每光子能量 J
    flux = E_si/eph                           # 光子/m^2/s/m
    mask = eph > eg*Q
    jsc = Q*np.trapezoid(flux*mask, wl)
    pin = np.trapezoid(E_si, wl)
    return jsc, pin


def _j0(eg, tk):
    """辐射饱和电流 (黑体 above Eg)。"""
    e = np.linspace(eg, eg+1.6, 500)*Q       # J
    bb = (2*np.pi/(H**3 * C**2)) * e**2 / (np.exp(e/(KB*tk)) - 1.0)
    return Q*np.trapezoid(bb, e)


def _eta(jsc, pin, eg, tc_c):
    tk = tc_c + 273.15
    j0 = _j0(eg, tk)
    voc = (KB*tk/Q)*np.log(jsc/j0 + 1.0) - DV_NONRAD
    if voc <= 0:
        return 0.0
    v = Q*voc/(KB*tk)
    ff = (v - np.log(v + 0.72))/(v + 1.0)
    return jsc*voc*ff/pin


def build_eta_grid():
    """η[Eg, AM, T] 网格。"""
    specs = [_spectrum_for_am(am) for am in AM_NODES]
    jsc_pin = np.array([[_jsc_pin(wl, E, eg) for (wl, E) in specs] for eg in EGS])  # [Eg,AM,2]
    grid = np.zeros((len(EGS), len(AM_NODES), len(T_NODES)))
    for ie, eg in enumerate(EGS):
        for ia in range(len(AM_NODES)):
            jsc, pin = jsc_pin[ie, ia]
            for it, tc in enumerate(T_NODES):
                grid[ie, ia, it] = _eta(jsc, pin, eg, tc)
    return grid


def main():
    print("  构建 η[Eg×AM×T] 细致平衡网格...")
    eta = build_eta_grid()
    cities = ["lhasa", "urumqi", "chengdu", "haikou", "guangzhou"]
    cfg = SystemConfig(n_modules=20)
    print(f"{'city':<9}{'最优Eg':>8}{'climate'}")
    rows = []
    for key in cities:
        c = next(c for c in CITIES if c.key == key)
        w = wx.from_pvgis_tmy(c.lat, c.lon, altitude=c.alt, name=c.key)
        ts = simulate(PEROVSKITE, w, cfg, npts=40)["timeseries"]
        poa = ts["poa_global"].to_numpy(); tc = ts["tcell"].to_numpy()
        zen = w["solar_zenith"].to_numpy(float)
        am = 1.0/np.cos(np.radians(np.clip(zen, 0, 89)))
        m = poa > 30
        poa, am, tc = poa[m], np.clip(am[m], 1.0, 6.0), np.clip(tc[m], 5, 66)
        # POA 加权 (AM,T) 占用矩阵
        wgt = np.zeros((len(AM_NODES), len(T_NODES)))
        ia = np.clip(np.searchsorted(AM_NODES, am), 0, len(AM_NODES)-1)
        it = np.clip(np.searchsorted(T_NODES, tc), 0, len(T_NODES)-1)
        for k in range(len(poa)):
            wgt[ia[k], it[k]] += poa[k]
        energy = np.array([np.sum(eta[ie]*wgt) for ie in range(len(EGS))])
        best = EGS[np.argmax(energy)]
        tcw = np.average(tc, weights=poa); amw = np.average(am, weights=poa)
        print(f"{c.name:<7}{best:>8.2f}   Tcell~{tcw:.0f}°C, AM~{amw:.1f}, alt {c.alt}m")
        rows.append((c.name, best, tcw, amw))
    spread = max(r[1] for r in rows) - min(r[1] for r in rows)
    print(f"\n最优带隙跨度 {spread:.2f} eV "
          f"({'有地理移动, 可深挖' if spread >= 0.03 else '偏平'}); "
          f"边界 railing? {'是(需扩范围)' if min(r[1] for r in rows)<=EGS[1] or max(r[1] for r in rows)>=EGS[-2] else '否, 内部最优 ✓'}")


if __name__ == "__main__":
    main()
