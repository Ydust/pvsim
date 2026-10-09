from __future__ import annotations
from dataclasses import replace
import numpy as np
from pvsim.cell import operating_point
def _gamma_pmax(tech: CellTechnology) -> float:
    """Modelled Pmax temperature coefficient in percent per C."""
    temps = np.arange(15.0, 66.0, 5.0)
    pmp = np.array([
        operating_point(
            tech, 1000.0, float(temp), ns=tech.cells_in_series,
        ).pmp
        for temp in temps
    ])
    p25 = operating_point(
        tech, 1000.0, 25.0, ns=tech.cells_in_series,
    ).pmp
    slope = np.sum((temps - temps.mean()) * (pmp - pmp.mean()))
    slope /= np.sum((temps - temps.mean()) ** 2)
    return float(slope / p25 * 100.0)

def gamma_tech(name, gamma):
    from pvsim.materials import PEROVSKITE, TANDEM_2T
    
    tech = PEROVSKITE if name == "single" else TANDEM_2T
    if gamma == (-.15 if name == "single" else -.30):
        return tech
    low, high = .3, 2.2
    for _ in range(50):
        mid=(low+high)/2
        actual=_gamma_pmax(replace(tech,Ea_recomb=mid))
        if actual > gamma: low=mid
        else: high=mid
    result=replace(tech,Ea_recomb=(low+high)/2)
    assert abs(_gamma_pmax(result)-gamma)<1e-4
    return result
