"""钙钛矿/晶硅两端叠层电池。

钙钛矿最大的潜力不是单独替代晶硅，而是作为**宽带隙顶电池**叠在晶硅上：
顶电池吃可见光、晶硅吃透过的近红外，串联后电压相加，突破单结效率极限(~33%)，
已有实验室记录 >33%。本模块用 AM1.5G 光子通量按带隙拆分、做电流匹配来量化这一协同。

两端(2-terminal)串联约束：子电池电流必须相等 → 叠层电流 = min(顶, 底)；电压相加。
故"电流匹配"(选合适的顶电池带隙)是设计关键。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .spectral import reference_am15g

# 物理常数
_Q = 1.602176634e-19
_H = 6.62607015e-34
_C = 2.99792458e8


def _photon_flux(wl_nm, E):
    """由光谱辐照 E[W/m^2/nm] 得光子通量 [photons/m^2/s/nm]。"""
    wl_m = wl_nm * 1e-9
    return E * wl_m / (_H * _C)


def jsc_in_band(lam_lo, lam_hi, eqe_plateau=0.90):
    """在 [lam_lo, lam_hi] nm 波段内、平台 EQE 下的短路电流密度 (mA/cm^2)。"""
    wl, E = reference_am15g()
    mask = (wl >= lam_lo) & (wl <= lam_hi)
    flux = _photon_flux(wl[mask], E[mask])
    j_A_m2 = _Q * eqe_plateau * np.trapezoid(flux, wl[mask])  # A/m^2
    return j_A_m2 / 10.0  # → mA/cm^2


def eg_to_wavelength(eg_ev):
    """带隙(eV) → 截止波长(nm)。"""
    return 1239.84 / eg_ev


@dataclass
class CellResult:
    name: str
    jsc: float       # mA/cm^2
    voc: float       # V
    ff: float
    efficiency: float  # %


def _single_cell(name, eg_top_band, voc, ff, eqe_plateau=0.90, lam_lo=300.0):
    """单结电池：吸收 lam_lo..带隙波长，效率按 AM1.5G(100mW/cm^2) 归一。"""
    lam_hi = eg_to_wavelength(eg_top_band)
    jsc = jsc_in_band(lam_lo, lam_hi, eqe_plateau)
    eff = jsc * voc * ff / 100.0 * 100.0  # P[mW/cm^2]/100 ×100%
    return CellResult(name, jsc, voc, ff, eff)


@dataclass
class TandemResult:
    j_top: float
    j_bottom: float
    j_matched: float
    current_mismatch: float    # |Jtop-Jbot|/max
    voc: float
    ff: float
    efficiency: float          # %
    top: CellResult
    bottom: CellResult


def tandem_perovskite_silicon(eg_top=1.68, eg_bottom=1.12,
                              voc_deficit_top=0.45, voc_deficit_bottom=0.42,
                              ff=0.80, eqe_plateau=0.90) -> TandemResult:
    """钙钛矿(顶)/晶硅(底) 两端叠层。

    eg_top: 顶电池(钙钛矿)带隙, 叠层最优约 1.68-1.72 eV。
    voc_deficit: 带隙与 Voc 的差(辐射+非辐射复合损失), 取代表性值。
    """
    lam_top = eg_to_wavelength(eg_top)        # 顶电池截止
    lam_bot = eg_to_wavelength(eg_bottom)     # 底电池截止

    # 顶电池吸收 300..lam_top；底电池吸收顶电池透过的 lam_top..lam_bot
    j_top = jsc_in_band(300.0, lam_top, eqe_plateau)
    j_bottom = jsc_in_band(lam_top, lam_bot, eqe_plateau)

    voc_top = eg_top - voc_deficit_top
    voc_bottom = eg_bottom - voc_deficit_bottom

    j_matched = min(j_top, j_bottom)          # 串联电流匹配
    voc_tandem = voc_top + voc_bottom
    eff = j_matched * voc_tandem * ff / 100.0 * 100.0
    mismatch = abs(j_top - j_bottom) / max(j_top, j_bottom)

    return TandemResult(
        j_top=j_top, j_bottom=j_bottom, j_matched=j_matched,
        current_mismatch=mismatch, voc=voc_tandem, ff=ff, efficiency=eff,
        top=CellResult("钙钛矿顶电池", j_top, voc_top, ff, j_top * voc_top * ff / 100 * 100),
        bottom=CellResult("晶硅底电池", j_bottom, voc_bottom, ff,
                          j_bottom * voc_bottom * ff / 100 * 100),
    )


def reference_single_junctions(ff=0.80, eqe_plateau=0.90):
    """单结参考：钙钛矿(1.55) 与 晶硅(1.12)，用同一方法以便公平比较。"""
    pero = _single_cell("单结钙钛矿", 1.55, 1.55 - 0.44, ff, eqe_plateau)
    csi = _single_cell("单结晶硅", 1.12, 1.12 - 0.42, ff, eqe_plateau)
    return pero, csi


def optimal_top_bandgap(eg_bottom=1.12, ff=0.80, eqe_plateau=0.90,
                        eg_range=(1.55, 1.85), n=31):
    """扫描顶电池带隙，找电流匹配点附近效率最高的带隙。"""
    egs = np.linspace(*eg_range, n)
    effs = np.array([tandem_perovskite_silicon(eg, eg_bottom, ff=ff,
                                               eqe_plateau=eqe_plateau).efficiency
                     for eg in egs])
    k = int(np.argmax(effs))
    return egs, effs, egs[k], effs[k]
