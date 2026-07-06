"""Shared economic prior definitions for substitution scenarios."""

from __future__ import annotations

from typing import Any

import numpy as np


TECH_CSI = "晶硅"
TECH_PEROVSKITE = "钙钛矿"
TECH_TANDEM = "叠层"

MC_RANDOM_SEED = 42
MC_DRAWS = 1000

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

SOFTMAX_T_MULTIPLIER_MEAN = 3.0
SOFTMAX_T_MULTIPLIER_SD = 1.5
SOFTMAX_T_CLIP_CENTS_KWH = (0.15, 2.0)


def sample_mc_inputs(
    rng: np.random.Generator, t_fit_cents_kwh: float
) -> tuple[dict[str, float], dict[str, float], int, float, float]:
    learning_rates = {
        tech: float(np.clip(rng.normal(mean, sd), *LEARNING_RATE_CLIP))
        for tech, (mean, sd) in LEARNING_RATE_PRIORS.items()
    }
    capex_floors = {
        tech: float(rng.uniform(low, high))
        for tech, (low, high) in CAPEX_FLOOR_PRIORS_USD_W.items()
    }
    breakthrough_year = int(
        rng.integers(
            PEROVSKITE_BREAKTHROUGH_YEAR_RANGE[0],
            PEROVSKITE_BREAKTHROUGH_YEAR_RANGE[1] + 1,
        )
    )
    lifetime_final = float(rng.uniform(*POST_BREAKTHROUGH_LIFETIME_RANGE_YR))
    softmax_t = float(
        np.clip(
            rng.normal(
                t_fit_cents_kwh * SOFTMAX_T_MULTIPLIER_MEAN,
                t_fit_cents_kwh * SOFTMAX_T_MULTIPLIER_SD,
            ),
            *SOFTMAX_T_CLIP_CENTS_KWH,
        )
    )
    return learning_rates, capex_floors, breakthrough_year, lifetime_final, softmax_t


def mc_parameter_rows(t_fit_cents_kwh: float) -> list[dict[str, Any]]:
    return [
        {
            "parameter": "c-Si learning rate",
            "distribution_or_value": "Normal mean 0.18 and SD 0.04; clipped to 0.08-0.45",
            "source_or_anchor": "2015-2024 PV price backcast plus ITRPV and BNEF cost history",
            "prior_reason": "Mature incumbent still has residual cost decline and manufacturing uncertainty",
            "stress_test_role": "Tests whether silicon cost decline delays perovskite substitution",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "perovskite learning rate",
            "distribution_or_value": "Normal mean 0.27 and SD 0.04; clipped to 0.08-0.45",
            "source_or_anchor": "Scenario prior because bankable perovskite deployment history does not yet exist",
            "prior_reason": "Allows faster early learning without assuming guaranteed commercial dominance",
            "stress_test_role": "Tests whether high learning can overcome the lifetime gate",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "tandem learning rate",
            "distribution_or_value": "Normal mean 0.30 and SD 0.04; clipped to 0.08-0.45",
            "source_or_anchor": "NREL tandem TEA baseline plus emerging PV learning envelope",
            "prior_reason": "Represents immature two-terminal tandem manufacturing uncertainty",
            "stress_test_role": "Tests whether area efficiency can compensate for higher capex",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "c-Si capex floor",
            "distribution_or_value": "Uniform 0.35-0.45 USD per W",
            "source_or_anchor": "Observed 2024 module price floor and long-run system floor envelope",
            "prior_reason": "Prevents mature silicon from declining without a physical and supply-chain floor",
            "stress_test_role": "Sets the incumbent cost threshold",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "perovskite capex floor",
            "distribution_or_value": "Uniform 0.32-0.45 USD per W",
            "source_or_anchor": "Scenario process floor; no bankable market price series exists",
            "prior_reason": "Allows low-cost manufacturing while retaining parity and underperformance cases",
            "stress_test_role": "Separates cost-led substitution from yield-led substitution",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "tandem capex floor",
            "distribution_or_value": "Uniform 0.42-0.58 USD per W",
            "source_or_anchor": "NREL Cordell 2025 tandem TEA and floor uncertainty",
            "prior_reason": "Retains higher process complexity for tandem manufacturing",
            "stress_test_role": "Tests whether tandem remains area-driven rather than yield-driven",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "perovskite breakthrough year",
            "distribution_or_value": "Discrete uniform integer years 2028-2042",
            "source_or_anchor": "Durability-transition scenario bracket",
            "prior_reason": "Does not assume that bankable lifetime arrives on a fixed schedule",
            "stress_test_role": "Controls whether substitution starts early or remains blocked",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "post-breakthrough perovskite lifetime",
            "distribution_or_value": "Uniform 18-25 years",
            "source_or_anchor": "Scenario range from partial bankability to full silicon-like lifetime",
            "prior_reason": "Keeps incomplete lifetime improvement visible in the economics",
            "stress_test_role": "Controls never-substitute tail risk",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "softmax allocation temperature",
            "distribution_or_value": (
                f"Normal mean {t_fit_cents_kwh * SOFTMAX_T_MULTIPLIER_MEAN:.2f} "
                f"and SD {t_fit_cents_kwh * SOFTMAX_T_MULTIPLIER_SD:.2f}; "
                "clipped to 0.15-2.0 cents per kWh"
            ),
            "source_or_anchor": "2015-2023 multi-to-mono calibration expanded threefold",
            "prior_reason": "Avoids overconfident winner-take-all adoption from a short historical analogue",
            "stress_test_role": "Controls coexistence and inertia in new-build share allocation",
            "used_in": "Main Fig 4 MC",
        },
        {
            "parameter": "number of draws",
            "distribution_or_value": f"{MC_DRAWS} draws with random seed {MC_RANDOM_SEED}",
            "source_or_anchor": "Reproducibility setting",
            "prior_reason": "Keeps uncertainty summaries deterministic across reruns",
            "stress_test_role": "Defines Monte Carlo precision",
            "used_in": "Main Fig 4 MC",
        },
    ]
