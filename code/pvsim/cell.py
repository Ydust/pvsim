"""Single-diode photovoltaic cell model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import lambertw

from .materials import CellTechnology, K_B, Q, T_REF, G_REF

K_EV = 8.617333262e-5


@dataclass
class DiodeParams:

    IL: float
    I0: float
    Rs: float
    Rsh: float
    nNsVth: float    # n * Ns * kT/q (V)


@dataclass
class OperatingPoint:

    isc: float
    voc: float
    imp: float
    vmp: float
    pmp: float
    ff: float
    efficiency: float
    v: np.ndarray = None
    i: np.ndarray = None


def thermal_voltage(n_ideality: float, ns: int, tcell_C: float) -> float:
    """n*Ns*kT/q (V)。"""
    tcell_K = tcell_C + 273.15
    return n_ideality * ns * K_B * tcell_K / Q


def translate_params(
    tech: CellTechnology,
    effective_irradiance: float,
    tcell_C: float,
    ns: int = 1,
) -> DiodeParams:

    geff = max(float(effective_irradiance), 1e-6)
    tcell_K = tcell_C + 273.15

    IL = (geff / G_REF) * (tech.I_L_ref + tech.alpha_sc * (tcell_K - T_REF))


    I0 = (tech.I_o_ref * (tcell_K / T_REF) ** 3
          * np.exp(tech.Ea_recomb / K_EV * (1.0 / T_REF - 1.0 / tcell_K)))
    Rsh = tech.R_sh_ref * (G_REF / geff)
    Rs = tech.R_s


    a_cell = thermal_voltage(tech.n_ideality, 1, tcell_C)
    return DiodeParams(
        IL=IL,
        I0=I0,
        Rs=Rs * ns,
        Rsh=Rsh * ns,
        nNsVth=a_cell * ns,
    )


def i_from_v(v: np.ndarray, p: DiodeParams) -> np.ndarray:

    v = np.asarray(v, dtype=float)
    Gsh = 1.0 / p.Rsh
    A = 1.0 + p.Rs * Gsh
    a = p.nNsVth

    c = p.Rs * p.I0 / (A * a)
    d = (p.Rs * (p.IL + p.I0) + v) / (A * a)

    arg = c * np.exp(np.clip(d, -700, 700))
    w = np.real(lambertw(arg))
    x = d - w
    u = a * x                      # u = V + I*Rs
    return (u - v) / p.Rs


def _find_voc(p: DiodeParams) -> float:

    voc_est = p.nNsVth * np.log(p.IL / p.I0 + 1.0)

    vv = np.linspace(0.0, 1.5 * voc_est, 600)
    ii = i_from_v(vv, p)
    sign = np.where(ii >= 0)[0]
    if len(sign) == 0:
        return 0.0
    k = sign[-1]
    if k + 1 >= len(vv):
        return float(vv[-1])

    v0, v1 = vv[k], vv[k + 1]
    i0, i1 = ii[k], ii[k + 1]
    return float(v0 - i0 * (v1 - v0) / (i1 - i0))


def operating_point(
    tech: CellTechnology,
    irradiance: float,
    tcell_C: float,
    effective_irradiance: float | None = None,
    ns: int = 1,
    npts: int = 400,
) -> OperatingPoint:

    if effective_irradiance is None:
        effective_irradiance = irradiance
    p = translate_params(tech, effective_irradiance, tcell_C, ns=ns)

    isc = float(i_from_v(np.array([0.0]), p)[0])
    voc = _find_voc(p)
    if voc <= 0 or isc <= 0:
        return OperatingPoint(0, 0, 0, 0, 0, 0, 0,
                              v=np.array([0.0]), i=np.array([0.0]))

    v = np.linspace(0.0, voc, npts)
    i = np.clip(i_from_v(v, p), 0.0, None)
    pwr = v * i
    kmax = int(np.argmax(pwr))

    if 0 < kmax < npts - 1:
        x0, x1, x2 = v[kmax - 1], v[kmax], v[kmax + 1]
        y0, y1, y2 = pwr[kmax - 1], pwr[kmax], pwr[kmax + 1]
        denom = (y0 - 2 * y1 + y2)
        vmp = x1 - 0.5 * (x2 - x0) * (y2 - y0) / denom / 2 if denom != 0 else x1
    else:
        vmp = v[kmax]
    imp = float(i_from_v(np.array([vmp]), p)[0])
    pmp = float(vmp * imp)
    ff = pmp / (voc * isc) if voc * isc > 0 else 0.0

    area_m2 = ns * tech.area_cm2 / 1e4
    efficiency = pmp / (area_m2 * irradiance) if irradiance > 0 else 0.0

    return OperatingPoint(
        isc=isc, voc=voc, imp=imp, vmp=float(vmp), pmp=pmp,
        ff=ff, efficiency=efficiency, v=v, i=i,
    )
