"""I-V 迟滞（钙钛矿特有）。

钙钛矿因离子迁移/界面电容，正向扫描(Isc→Voc)与反向扫描(Voc→Isc)得到的 I-V 曲线
不同，反向扫常给出更高的表观效率。这带来两个运行/测量上的问题：
    1) 效率测量有歧义（依赖扫描方向/速率）——晶硅没有；
    2) 实际 MPPT 难以锁定真实最大功率点，造成等效发电损失。

简化建模：以基准 I-V 为中心，用 ±ΔRs（等效串联电阻扰动）生成正/反扫两条曲线，
标定使 (Pmax_rev − Pmax_fwd)/Pmax_rev = 技术的迟滞指数 HI。
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .materials import CellTechnology
from .cell import operating_point, OperatingPoint


@dataclass
class HysteresisResult:
    forward: OperatingPoint      # 正向扫描 (偏低)
    reverse: OperatingPoint      # 反向扫描 (偏高)
    stabilized_pmax: float       # 稳态(MPPT)可得功率 ~ 两者间
    hysteresis_index: float      # (Prev - Pfwd)/Prev
    mppt_loss: float             # 相对反向扫的等效发电损失


def hysteresis_curves(tech: CellTechnology, irradiance=1000.0, tcell_C=25.0,
                      ns=None, npts=400) -> HysteresisResult:
    """生成正/反扫 I-V 曲线并量化迟滞。c-Si (HI=0) 时两条曲线重合。"""
    if ns is None:
        ns = tech.cells_in_series
    hi = tech.hysteresis_index

    base = operating_point(tech, irradiance, tcell_C, ns=ns, npts=npts)
    if hi <= 0:
        return HysteresisResult(forward=base, reverse=base,
                                stabilized_pmax=base.pmp,
                                hysteresis_index=0.0, mppt_loss=0.0)

    # ±ΔRs 扰动：反向扫 Rs 略低(FF高), 正向扫 Rs 略高(FF低)
    # 用二分法找 delta 使功率差≈HI
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
    # 稳态 MPPT 实得功率近似取几何中点偏保守
    stabilized = float(np.sqrt(rev.pmp * fwd.pmp))
    mppt_loss = (rev.pmp - stabilized) / rev.pmp
    return HysteresisResult(forward=fwd, reverse=rev, stabilized_pmax=stabilized,
                            hysteresis_index=(rev.pmp - fwd.pmp) / rev.pmp,
                            mppt_loss=mppt_loss)
