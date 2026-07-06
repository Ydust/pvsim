"""模型校核：验证两种技术在 STC 下的输出特性，以及温度/弱光行为是否符合文献。

运行: python -m scripts.calibrate
"""

import sys
from dataclasses import replace

import numpy as np

from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cell import operating_point

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台默认 GBK，强制 UTF-8


def stc_summary(tech):
    ns = tech.cells_in_series
    op = operating_point(tech, irradiance=1000.0, tcell_C=25.0, ns=ns)
    area = ns * tech.area_cm2 / 1e4
    print(f"\n=== {tech.name_cn} ({tech.name}) 组件 STC 特性 (Ns={ns}, 面积={area:.3f} m²) ===")
    print(f"  Isc = {op.isc:7.3f} A")
    print(f"  Voc = {op.voc:7.3f} V")
    print(f"  Imp = {op.imp:7.3f} A")
    print(f"  Vmp = {op.vmp:7.3f} V")
    print(f"  Pmp = {op.pmp:7.2f} W")
    print(f"  FF  = {op.ff:7.4f}")
    print(f"  效率 = {op.efficiency*100:6.2f} %")
    return op


def temp_coefficients(tech):
    """在 G=1000 下扫温度，线性拟合 Pmax/Voc/Isc 的相对温度系数 (%/°C)。"""
    ns = tech.cells_in_series
    temps = np.arange(15.0, 66.0, 5.0)
    pmp, voc, isc = [], [], []
    for t in temps:
        op = operating_point(tech, 1000.0, float(t), ns=ns)
        pmp.append(op.pmp); voc.append(op.voc); isc.append(op.isc)
    pmp = np.array(pmp); voc = np.array(voc); isc = np.array(isc)
    op25 = operating_point(tech, 1000.0, 25.0, ns=ns)

    def linslope(x, y):
        # 闭式最小二乘斜率，避免依赖 LAPACK
        x = np.asarray(x, float); y = np.asarray(y, float)
        xm, ym = x.mean(), y.mean()
        return float(((x - xm) * (y - ym)).sum() / ((x - xm) ** 2).sum())

    def coeff(y, ref):
        return linslope(temps, y) / ref * 100.0  # %/°C

    g_pmax = coeff(pmp, op25.pmp)
    b_voc = coeff(voc, op25.voc)
    a_isc = coeff(isc, op25.isc)
    print(f"\n--- {tech.name_cn} 温度系数 (模型 vs 文献, %/°C) ---")
    print(f"  γ_Pmax: 模型 {g_pmax:+.3f}  | 文献 {tech.gamma_pmax_lit:+.2f}")
    print(f"  β_Voc : 模型 {b_voc:+.3f}  | 文献 {tech.beta_voc_lit:+.2f}")
    print(f"  α_Isc : 模型 {a_isc:+.3f}  | 文献 {tech.alpha_isc_lit:+.2f}")
    return g_pmax, b_voc, a_isc


def _gamma_pmax(tech):
    """给定技术参数，返回模型 γ_Pmax (%/°C)。"""
    ns = tech.cells_in_series
    temps = np.arange(15.0, 66.0, 5.0)
    pmp = np.array([operating_point(tech, 1000.0, float(t), ns=ns).pmp for t in temps])
    xm, ym = temps.mean(), pmp.mean()
    slope = ((temps - xm) * (pmp - ym)).sum() / ((temps - xm) ** 2).sum()
    return slope / operating_point(tech, 1000.0, 25.0, ns=ns).pmp * 100.0


def solve_Ea(tech, target_gamma, lo=0.4, hi=1.4, tol=1e-3):
    """二分法求复合激活能 Ea_recomb，使模型 γ_Pmax 命中文献目标值。"""
    def f(ea):
        return _gamma_pmax(replace(tech, Ea_recomb=ea)) - target_gamma
    # γ_Pmax 随 Ea 增大而更负，f 单调；确保区间端点异号
    flo, fhi = f(lo), f(hi)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if abs(fmid) < tol:
            return mid
        if (flo < 0) == (fmid < 0):
            lo, flo = mid, fmid
        else:
            hi, fhi = mid, fmid
    return 0.5 * (lo + hi)


def calibrate_all():
    print("=== 标定复合激活能 Ea_recomb (使 γ_Pmax 命中文献) ===")
    for tech in (CSI_EARLY, PEROVSKITE):
        ea = solve_Ea(tech, tech.gamma_pmax_lit)
        g = _gamma_pmax(replace(tech, Ea_recomb=ea))
        print(f"  {tech.name_cn}: Ea_recomb = {ea:.4f} eV  "
              f"→ γ_Pmax = {g:+.3f} %/°C (目标 {tech.gamma_pmax_lit:+.2f})  "
              f"[当前参数库值 {tech.Ea_recomb:.4f}]")


def lowlight(tech):
    """弱光相对效率：200 W/m² 效率相对 1000 W/m² 的比值。"""
    ns = tech.cells_in_series
    e1000 = operating_point(tech, 1000.0, 25.0, ns=ns).efficiency
    e200 = operating_point(tech, 200.0, 25.0, ns=ns).efficiency
    rel = e200 / e1000 * 100.0
    print(f"\n--- {tech.name_cn} 弱光表现 ---")
    print(f"  η(1000)={e1000*100:.2f}%  η(200)={e200*100:.2f}%  "
          f"相对效率(200/1000)={rel:.1f}%")
    return rel


if __name__ == "__main__":
    calibrate_all()
    for tech in (CSI_EARLY, PEROVSKITE):
        stc_summary(tech)
        temp_coefficients(tech)
        lowlight(tech)
    print("\n校核完成。")
