"""Perovskite hysteresis model."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .materials import CellTechnology
from .cell import operating_point, OperatingPoint


@dataclass
class HysteresisResult:
    forward: OperatingPoint
    reverse: OperatingPoint
    stabilized_pmax: float
    hysteresis_index: float      # (Prev - Pfwd)/Prev
    mppt_loss: float


def hysteresis_curves(tech: CellTechnology, irradiance=1000.0, tcell_C=25.0,
                      ns=None, npts=400) -> HysteresisResult:

    if ns is None:
        ns = tech.cells_in_series
    hi = tech.hysteresis_index

    base = operating_point(tech, irradiance, tcell_C, ns=ns, npts=npts)
    if hi <= 0:
        return HysteresisResult(forward=base, reverse=base,
                                stabilized_pmax=base.pmp,
                                hysteresis_index=0.0, mppt_loss=0.0)


    def pmax_with_rs_scale(scale):
        t = replace(tech, R_s=tech.R_s * scale)
        return operating_point(t, irradiance, tcell_C, ns=ns, npts=npts).pmp

    lo, hi_d = 0.0, 2.0
    for _ in range(40):
        d = 0.5 * (lo + hi_d)
        p_rev = pmax_with_rs_scale(1.0 - 0.5 * d)
        p_fwd = pmax_with_rs_scale(1.0 + 0.5 * d)
        cur_hi = (p_rev - p_fwd) / p_rev if p_rev > 0 else 0.0
        if abs(cur_hi - hi) < 1e-4:
            break
        if cur_hi < hi:
            lo = d
        else:
            hi_d = d

    rev = operating_point(replace(tech, R_s=tech.R_s * (1 - 0.5 * d)),
                          irradiance, tcell_C, ns=ns, npts=npts)
    fwd = operating_point(replace(tech, R_s=tech.R_s * (1 + 0.5 * d)),
                          irradiance, tcell_C, ns=ns, npts=npts)

    stabilized = float(np.sqrt(rev.pmp * fwd.pmp))
    mppt_loss = (rev.pmp - stabilized) / rev.pmp
    return HysteresisResult(forward=fwd, reverse=rev, stabilized_pmax=stabilized,
                            hysteresis_index=(rev.pmp - fwd.pmp) / rev.pmp,
                            mppt_loss=mppt_loss)
