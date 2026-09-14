"""Two-terminal tandem current matching."""

from __future__ import annotations

from pvsim.labels import label as _text_label

from dataclasses import dataclass

import numpy as np

from .spectral import reference_am15g


_Q = 1.602176634e-19
_H = 6.62607015e-34
_C = 2.99792458e8


def _photon_flux(wl_nm, E):

    wl_m = wl_nm * 1e-9
    return E * wl_m / (_H * _C)


def jsc_in_band(lam_lo, lam_hi, eqe_plateau=0.90):

    wl, E = reference_am15g()
    mask = (wl >= lam_lo) & (wl <= lam_hi)
    flux = _photon_flux(wl[mask], E[mask])
    j_A_m2 = _Q * eqe_plateau * np.trapezoid(flux, wl[mask])  # A/m^2
    return j_A_m2 / 10.0  # → mA/cm^2


def eg_to_wavelength(eg_ev):

    return 1239.84 / eg_ev


@dataclass
class CellResult:
    name: str
    jsc: float       # mA/cm^2
    voc: float       # V
    ff: float
    efficiency: float  # %


def _single_cell(name, eg_top_band, voc, ff, eqe_plateau=0.90, lam_lo=300.0):

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

    lam_top = eg_to_wavelength(eg_top)
    lam_bot = eg_to_wavelength(eg_bottom)


    j_top = jsc_in_band(300.0, lam_top, eqe_plateau)
    j_bottom = jsc_in_band(lam_top, lam_bot, eqe_plateau)

    voc_top = eg_top - voc_deficit_top
    voc_bottom = eg_bottom - voc_deficit_bottom

    j_matched = min(j_top, j_bottom)
    voc_tandem = voc_top + voc_bottom
    eff = j_matched * voc_tandem * ff / 100.0 * 100.0
    mismatch = abs(j_top - j_bottom) / max(j_top, j_bottom)

    return TandemResult(
        j_top=j_top, j_bottom=j_bottom, j_matched=j_matched,
        current_mismatch=mismatch, voc=voc_tandem, ff=ff, efficiency=eff,
        top=CellResult(_text_label('perovskite_top_cell'), j_top, voc_top, ff, j_top * voc_top * ff / 100 * 100),
        bottom=CellResult(_text_label('silicon_bottom_cell'), j_bottom, voc_bottom, ff,
                          j_bottom * voc_bottom * ff / 100 * 100),
    )


def reference_single_junctions(ff=0.80, eqe_plateau=0.90):

    pero = _single_cell(_text_label('tandem_text'), 1.55, 1.55 - 0.44, ff, eqe_plateau)
    csi = _single_cell(_text_label('single_junction_csi'), 1.12, 1.12 - 0.42, ff, eqe_plateau)
    return pero, csi


def optimal_top_bandgap(eg_bottom=1.12, ff=0.80, eqe_plateau=0.90,
                        eg_range=(1.55, 1.85), n=31):

    egs = np.linspace(*eg_range, n)
    effs = np.array([tandem_perovskite_silicon(eg, eg_bottom, ff=ff,
                                               eqe_plateau=eqe_plateau).efficiency
                     for eg in egs])
    k = int(np.argmax(effs))
    return egs, effs, egs[k], effs[k]
