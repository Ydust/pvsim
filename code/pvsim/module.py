"""Series and parallel photovoltaic module scaling."""

from __future__ import annotations

import numpy as np

from .materials import CellTechnology
from .cell import operating_point


def module_pmp(tech: CellTechnology, irradiance: float, tcell_C: float,
               effective_irradiance: float | None = None, npts: int = 200) -> float:

    op = operating_point(tech, irradiance, tcell_C,
                         effective_irradiance=effective_irradiance,
                         ns=tech.cells_in_series, npts=npts)
    return op.pmp


def module_stc_power(tech: CellTechnology) -> float:

    return module_pmp(tech, 1000.0, 25.0, npts=400)


def array_dc_power(tech: CellTechnology, irradiance, tcell_C,
                   n_modules: int = 1, effective_irradiance=None,
                   mismatch_loss: float = 0.02, npts: int = 150):

    irradiance = np.atleast_1d(np.asarray(irradiance, float))
    tcell_C = np.atleast_1d(np.asarray(tcell_C, float))
    if effective_irradiance is None:
        eff = irradiance
    else:
        eff = np.atleast_1d(np.asarray(effective_irradiance, float))
    eff = np.broadcast_to(eff, irradiance.shape)
    tcell_C = np.broadcast_to(tcell_C, irradiance.shape)

    pmp = np.empty_like(irradiance)
    for k in range(irradiance.size):
        if irradiance.flat[k] <= 1.0:
            pmp.flat[k] = 0.0
        else:
            pmp.flat[k] = module_pmp(tech, float(irradiance.flat[k]),
                                     float(tcell_C.flat[k]),
                                     float(eff.flat[k]), npts=npts)
    dc = n_modules * pmp * (1.0 - mismatch_loss)
    return dc if dc.size > 1 else float(dc[0])
