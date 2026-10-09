"""单二极管电池核心模型。

物理模型: 单二极管 5 参数 (De Soto et al. 2006)
    I = IL - I0*(exp((V+I*Rs)/(n*Ns*Vth)) - 1) - (V+I*Rs)/Rsh

随工况 (辐照 G、电池温度 T) 的参数平移采用 De Soto 标准定律：
    - IL ∝ 辐照，并含 Isc 温度系数
    - I0 ∝ T^3 * exp(...带隙...)        ← 温度系数差异的物理根源
    - Rsh ∝ 1/辐照                       ← 弱光性能差异的物理根源
钙钛矿的高带隙 + 高 Voc + 带隙随温升上升(dEgdT>0) 自然给出更小的温度系数，
高 Rsh 给出更好的弱光表现——无需人为设定，直接从物理量涌现。

I-V 方程对 I 的求解用 Lambert W 闭式解 (scipy.special.lambertw)，稳定且向量化。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import lambertw

from .materials import CellTechnology, K_B, Q, T_REF, G_REF

K_EV = 8.617333262e-5  # 玻尔兹曼常数 eV/K（用于带隙指数项）


@dataclass
class DiodeParams:
    """某一工况下的单二极管参数（已按串联电池数 ns 缩放到组件/电池级）。"""

    IL: float        # 光生电流 A
    I0: float        # 反向饱和电流 A
    Rs: float        # 串联电阻 Ω
    Rsh: float       # 并联电阻 Ω
    nNsVth: float    # n * Ns * kT/q (V)


@dataclass
class OperatingPoint:
    """某一工况下的电池/组件工作特性。"""

    isc: float       # 短路电流 A
    voc: float       # 开路电压 V
    imp: float       # 最大功率点电流 A
    vmp: float       # 最大功率点电压 V
    pmp: float       # 最大功率 W
    ff: float        # 填充因子
    efficiency: float  # 光电转换效率 (0-1)
    v: np.ndarray = None   # I-V 曲线电压数组
    i: np.ndarray = None   # I-V 曲线电流数组


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
    """De Soto 工况平移：把参考(STC)参数平移到给定辐照/温度，并按 ns 串联缩放。

    effective_irradiance: 有效辐照 W/m^2（已含光谱/入射角/污渍修正）。
    ns: 串联电池数（单电池=1，组件=cells_in_series）。
    """
    geff = max(float(effective_irradiance), 1e-6)
    tcell_K = tcell_C + 273.15

    IL = (geff / G_REF) * (tech.I_L_ref + tech.alpha_sc * (tcell_K - T_REF))
    # I0(T) 的温度激活能用复合激活能 Ea_recomb（与光学带隙解耦），
    # 这是 Voc 温度依赖、进而温度系数差异的物理根源。
    I0 = (tech.I_o_ref * (tcell_K / T_REF) ** 3
          * np.exp(tech.Ea_recomb / K_EV * (1.0 / T_REF - 1.0 / tcell_K)))
    Rsh = tech.R_sh_ref * (G_REF / geff)        # 弱光下 Rsh 增大
    Rs = tech.R_s

    # 串联缩放到 ns 片
    a_cell = thermal_voltage(tech.n_ideality, 1, tcell_C)
    return DiodeParams(
        IL=IL,
        I0=I0,
        Rs=Rs * ns,
        Rsh=Rsh * ns,
        nNsVth=a_cell * ns,
    )


def i_from_v(v: np.ndarray, p: DiodeParams) -> np.ndarray:
    """给定电压求电流，单二极管 Lambert W 闭式解。"""
    v = np.asarray(v, dtype=float)
    Gsh = 1.0 / p.Rsh
    A = 1.0 + p.Rs * Gsh
    a = p.nNsVth
    # x + c*exp(x) = d  =>  x = d - W(c*exp(d)),  其中 u = a*x = V + I*Rs
    c = p.Rs * p.I0 / (A * a)
    d = (p.Rs * (p.IL + p.I0) + v) / (A * a)
    # 防 exp 溢出：在我们关心的 V∈[0,Voc] 区间 d 不会过大
    arg = c * np.exp(np.clip(d, -700, 700))
    w = np.real(lambertw(arg))
    x = d - w
    u = a * x                      # u = V + I*Rs
    return (u - v) / p.Rs


def _find_voc(p: DiodeParams) -> float:
    """求开路电压（I=0 处）。"""
    voc_est = p.nNsVth * np.log(p.IL / p.I0 + 1.0)
    # 在 [0, 1.5*voc_est] 上用细网格 + 线性插值定位过零点
    vv = np.linspace(0.0, 1.5 * voc_est, 600)
    ii = i_from_v(vv, p)
    sign = np.where(ii >= 0)[0]
    if len(sign) == 0:
        return 0.0
    k = sign[-1]
    if k + 1 >= len(vv):
        return float(vv[-1])
    # 线性插值 I=0
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
    """计算给定工况下的工作特性 (Isc/Voc/Pmax/FF/效率) 与 I-V 曲线。

    irradiance: 入射(宽谱)POA 辐照 W/m^2，用于效率分母。
    effective_irradiance: 有效辐照（含光谱/AOI 修正），用于产生电流；缺省=irradiance。
    """
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
    # 抛物线精修最大功率点
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
