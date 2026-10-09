"""Shared economic prior definitions for substitution scenarios."""

from __future__ import annotations

from typing import Any

import numpy as np


TECH_CSI = "晶硅"
TECH_PEROVSKITE = "钙钛矿"
TECH_TANDEM = "叠层"

MC_RANDOM_SEED = 42
MC_DRAWS = 10_000

LEARNING_RATE_PRIORS = {
    TECH_CSI: (0.18, 0.04),
    TECH_PEROVSKITE: (0.27, 0.04),
    TECH_TANDEM: (0.30, 0.04),
}
LEARNING_RATE_CLIP = (0.08, 0.45)

CAPEX_FLOOR_PRIORS_USD_W = {
    TECH_CSI: (0.35, 0.45),
    TECH_PEROVSKITE: (0.32, 0.45),
    TECH_TANDEM: (0.42, 0.58),
}

PEROVSKITE_BREAKTHROUGH_YEAR_RANGE = (2028, 2042)
POST_BREAKTHROUGH_LIFETIME_RANGE_YR = (18.0, 25.0)

INITIAL_SYSTEM_CAPEX_USD_W = {
    TECH_CSI: 0.65,
    TECH_PEROVSKITE: 0.95,
    TECH_TANDEM: 1.13,
}
INITIAL_GLOBAL_DEPLOYMENT_GW = {
    # Effective learning-curve seeds, not an audited 2025 installed-capacity series.
    # In particular the emerging-technology 12/4 GW inputs are scenario assumptions.
    TECH_CSI: 1500.0,
    TECH_PEROVSKITE: 12.0,
    TECH_TANDEM: 4.0,
}
CENTRAL_LEARNING_RATES = {
    tech: prior[0] for tech, prior in LEARNING_RATE_PRIORS.items()
}
CENTRAL_CAPEX_FLOORS_USD_W = {
    tech: (bounds[0] + bounds[1]) / 2.0
    for tech, bounds in CAPEX_FLOOR_PRIORS_USD_W.items()
}
CENTRAL_BREAKTHROUGH_YEAR = int(round(
    sum(PEROVSKITE_BREAKTHROUGH_YEAR_RANGE) / 2.0
))
CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR = (
    sum(POST_BREAKTHROUGH_LIFETIME_RANGE_YR) / 2.0
)

