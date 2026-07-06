"""标定叠层 Ea_recomb 使模型 γ_Pmax 命中文献 -0.30 %/°C。"""
import sys
from dataclasses import replace
from pvsim.materials import TANDEM_2T
from pvsim.cell import operating_point
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def gam(tech):
    p25 = operating_point(tech, 800, 25, ns=tech.cells_in_series, npts=600).pmp
    p45 = operating_point(tech, 800, 45, ns=tech.cells_in_series, npts=600).pmp
    return (p45/p25 - 1)/20*100


TARGET = -0.30
lo, hi = 0.95, 2.5
for _ in range(40):
    mid = (lo+hi)/2
    g = gam(replace(TANDEM_2T, Ea_recomb=mid))
    if g < TARGET:     # 太负 -> 降 Ea
        hi = mid
    else:
        lo = mid
ea = (lo+hi)/2
print(f"当前 Ea=0.95 -> γ={gam(TANDEM_2T):+.3f}")
print(f"标定 Ea={ea:.4f} -> γ={gam(replace(TANDEM_2T, Ea_recomb=ea)):+.3f} (目标 {TARGET})")
