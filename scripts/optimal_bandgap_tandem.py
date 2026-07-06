"""#2 (真问题) — 2T 叠层顶电池最优带隙是否随气候移动?

2 端叠层串联 → 电流匹配: J_match = min(Jsc_top, Jsc_bot)。
顶(钙钛矿 Eg_top)吃 E>Eg_top, 底(Si 1.12)吃 1.12<E<Eg_top。
光谱越蓝(低大气质量)→ 顶电流偏多 → 最优 Eg_top 应更宽(把更多红光让给底)。
=> 最优 Eg_top 随光谱(=大气质量=地点)移动, 比单结敏感得多。

运行: python -m scripts.optimal_bandgap_tandem
"""

import sys
import numpy as np

from pvsim.materials import PEROVSKITE
from pvsim.cities import CITIES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate
from scripts.optimal_bandgap_db import (
    _spectrum_for_am, _j0, H, C, Q, KB, AM_NODES, T_NODES)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EG_BOT = 1.12
DV_TOP, DV_BOT = 0.15, 0.40
EG_TOPS = np.round(np.arange(1.50, 1.86, 0.02), 3)


def _flux(wl_nm, E):
    wl = wl_nm*1e-9
    eph = H*C/wl
    return wl, eph, (E*1e9)/eph        # 光子/m^2/s/m


def _band_currents(wl_nm, E, eg_top):
    """返回 (Jsc_top, Jsc_bot, Pin)。"""
    wl, eph, flux = _flux(wl_nm, E)
    top = eph > eg_top*Q
    bot = (eph > EG_BOT*Q) & (eph <= eg_top*Q)
    jt = Q*np.trapezoid(flux*top, wl)
    jb = Q*np.trapezoid(flux*bot, wl)
    pin = np.trapezoid(E*1e9, wl)
    return jt, jb, pin


def _voc(eg, tk, jph, dv):
    j0 = _j0(eg, tk)
    voc = (KB*tk/Q)*np.log(max(jph, 1e-6)/j0 + 1.0) - dv
    return max(voc, 0.0)


def _eta_tandem(jt, jb, pin, eg_top, tc_c):
    tk = tc_c + 273.15
    jm = min(jt, jb)                    # 电流匹配
    vt = _voc(eg_top, tk, jt, DV_TOP)
    vb = _voc(EG_BOT, tk, jb, DV_BOT)
    vtot = vt + vb
    if vtot <= 0 or pin <= 0:
        return 0.0
    v = Q*vtot/(2*KB*tk)               # 双结有效归一电压
    ff = (v - np.log(v + 0.72))/(v + 1.0)
    return jm*vtot*ff/pin


def build_grid():
    specs = [_spectrum_for_am(am) for am in AM_NODES]
    bc = np.array([[_band_currents(wl, E, eg) for (wl, E) in specs] for eg in EG_TOPS])
    grid = np.zeros((len(EG_TOPS), len(AM_NODES), len(T_NODES)))
    for ie, eg in enumerate(EG_TOPS):
        for ia in range(len(AM_NODES)):
            jt, jb, pin = bc[ie, ia]
            for it, tc in enumerate(T_NODES):
                grid[ie, ia, it] = _eta_tandem(jt, jb, pin, eg, tc)
    return grid


def main():
    print("  构建 2T 叠层 η[Eg_top×AM×T] 网格...")
    eta = build_grid()
    cities = ["lhasa", "urumqi", "dunhuang", "chengdu", "haikou", "guangzhou"]
    cfg = SystemConfig(n_modules=20)
    print(f"{'city':<9}{'最优Eg_top':>11}{'climate'}")
    rows = []
    for key in cities:
        c = next((c for c in CITIES if c.key == key), None)
        if c is None:
            continue
        w = wx.from_pvgis_tmy(c.lat, c.lon, altitude=c.alt, name=c.key)
        ts = simulate(PEROVSKITE, w, cfg, npts=40)["timeseries"]
        poa = ts["poa_global"].to_numpy(); tc = ts["tcell"].to_numpy()
        zen = w["solar_zenith"].to_numpy(float)
        am = 1.0/np.cos(np.radians(np.clip(zen, 0, 89)))
        m = poa > 30
        poa, am, tc = poa[m], np.clip(am[m], 1.0, 6.0), np.clip(tc[m], 5, 66)
        wgt = np.zeros((len(AM_NODES), len(T_NODES)))
        ia = np.clip(np.searchsorted(AM_NODES, am), 0, len(AM_NODES)-1)
        it = np.clip(np.searchsorted(T_NODES, tc), 0, len(T_NODES)-1)
        for k in range(len(poa)):
            wgt[ia[k], it[k]] += poa[k]
        energy = np.array([np.sum(eta[ie]*wgt) for ie in range(len(EG_TOPS))])
        best = EG_TOPS[np.argmax(energy)]
        amw = np.average(am, weights=poa); tcw = np.average(tc, weights=poa)
        print(f"{c.name:<7}{best:>11.2f}   AM~{amw:.2f}, Tcell~{tcw:.0f}°C, alt {c.alt}m")
        rows.append((c.name, best, amw, tcw))
    spread = max(r[1] for r in rows) - min(r[1] for r in rows)
    rail = min(r[1] for r in rows) <= EG_TOPS[1] or max(r[1] for r in rows) >= EG_TOPS[-2]
    print(f"\n最优 Eg_top 跨度 {spread:.2f} eV "
          f"({'有地理移动, 可深挖 ✓' if spread >= 0.03 else '偏平'}); "
          f"railing? {'是(需扩范围)' if rail else '否, 内部最优 ✓'}")


if __name__ == "__main__":
    main()
