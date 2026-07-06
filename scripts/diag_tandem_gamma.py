"""诊断: 叠层 γ 用 module_pmp(低 npts) 与 operating_point 差异是否源于 MPP 分辨率。"""
import sys
from pvsim.materials import CSI_EARLY, PEROVSKITE, TANDEM_2T
from pvsim.module import module_pmp
from pvsim.cell import operating_point
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def gam_modpmp(tech, npts):
    p25 = module_pmp(tech, 800, 25, npts=npts)
    p45 = module_pmp(tech, 800, 45, npts=npts)
    return (p45/p25 - 1)/20*100


def gam_op(tech):
    p25 = operating_point(tech, 800, 25, ns=tech.cells_in_series, npts=600).pmp
    p45 = operating_point(tech, 800, 45, ns=tech.cells_in_series, npts=600).pmp
    return (p45/p25 - 1)/20*100


print(f"{'tech':<10}{'lit':>6}{'modpmp_n60':>12}{'modpmp_n400':>13}{'op_n600':>10}")
for t, lit in [(CSI_EARLY, -0.45), (PEROVSKITE, -0.15), (TANDEM_2T, -0.30)]:
    print(f"{t.name:<10}{lit:>6}{gam_modpmp(t,60):>12.3f}"
          f"{gam_modpmp(t,400):>13.3f}{gam_op(t):>10.3f}")

op = operating_point(TANDEM_2T, 800, 25, ns=TANDEM_2T.cells_in_series, npts=600)
print(f"\ntandem @800/25: Voc={op.voc:.1f}V Vmp={op.vmp:.1f}V Pmp={op.pmp:.1f}W "
      f"-> npts=60 MPP 分辨率 {op.voc/60:.2f} V/点")
