"""电池 → 组件 → 阵列 的功率缩放。

组件 = cells_in_series 个电池串联（已由 cell.operating_point 的 ns 处理）。
阵列 = n_modules 个组件，串并联后总直流功率按数量缩放（计入组件间失配损失）。
"""

from __future__ import annotations

import numpy as np

from .materials import CellTechnology
from .cell import operating_point


def module_pmp(tech: CellTechnology, irradiance: float, tcell_C: float,
               effective_irradiance: float | None = None, npts: int = 200) -> float:
    """单组件最大功率 (W)。"""
    op = operating_point(tech, irradiance, tcell_C,
                         effective_irradiance=effective_irradiance,
                         ns=tech.cells_in_series, npts=npts)
    return op.pmp


def module_stc_power(tech: CellTechnology) -> float:
    """单组件 STC 额定功率 Wp。"""
    return module_pmp(tech, 1000.0, 25.0, npts=400)


def array_dc_power(tech: CellTechnology, irradiance, tcell_C,
                   n_modules: int = 1, effective_irradiance=None,
                   mismatch_loss: float = 0.02, npts: int = 150):
    """阵列直流功率 (W)。支持标量或时间序列输入。

    mismatch_loss: 组件间失配/接线损失 (默认 2%)。
    """
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
