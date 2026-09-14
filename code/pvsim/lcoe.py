"""Levelized cost of electricity."""

from __future__ import annotations

import numpy as np

from .materials import CellTechnology
from .degradation import lifetime_energy


def lcoe(tech: CellTechnology, kwp: float, year1_energy_kwh: float,
         scenario: str | None = None, discount_rate: float = 0.05,
         opex_per_kwp_year: float = 12.0, horizon_years=None) -> dict:

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
