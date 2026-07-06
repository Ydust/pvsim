"""平准化度电成本 (LCOE)。

LCOE 把"初装成本 + 逐年运维"折现，再除以"逐年发电量(含衰减)的折现和"，
是综合反映两种技术运行经济性的总结性指标。钙钛矿可能更便宜(材料/低温工艺)，
但寿命短、衰减快会推高 LCOE——LCOE 正好把"便宜"与"短命"放在同一杆秤上。

    LCOE = (CapEx + Σ_t OpEx_t/(1+r)^t) / Σ_t E_t/(1+r)^t
"""

from __future__ import annotations

import numpy as np

from .materials import CellTechnology
from .degradation import lifetime_energy


def lcoe(tech: CellTechnology, kwp: float, year1_energy_kwh: float,
         scenario: str | None = None, discount_rate: float = 0.05,
         opex_per_kwp_year: float = 12.0, horizon_years=None) -> dict:
    """计算 LCOE ($/kWh)。

    capex 由 tech.capex_per_wp × 容量(Wp) 得到；opex 按 $/kWp/年。
    """
    horizon = int(np.ceil(horizon_years if horizon_years else tech.lifetime_years))
    capex = tech.capex_per_wp * kwp * 1000.0          # $/Wp × Wp
    le = lifetime_energy(tech, year1_energy_kwh, scenario, horizon)

    years = le["years"]
    discount = (1.0 + discount_rate) ** years
    opex_pv = np.sum(opex_per_kwp_year * kwp / discount)
    energy_pv = np.sum(le["yearly_kwh"] / discount)

    lcoe_val = (capex + opex_pv) / energy_pv if energy_pv > 0 else float("inf")
    return {
        "lcoe": lcoe_val,                       # $/kWh
        "capex": capex,
        "opex_pv": opex_pv,
        "energy_pv": energy_pv,
        "lifetime_energy_kwh": float(le["cumulative_kwh"][-1]),
        "t80_year": le["t80_year"],
        "horizon_years": horizon,
        "detail": le,
    }
