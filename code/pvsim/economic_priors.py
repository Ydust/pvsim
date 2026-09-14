"""Shared economic prior definitions for substitution scenarios."""

from __future__ import annotations

from pvsim.labels import label as _text_label

from typing import Any

import numpy as np


TECH_CSI = _text_label('tech_csi')
TECH_PEROVSKITE = _text_label('tech_perovskite')
TECH_TANDEM = _text_label('tech_tandem')

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

SOFTMAX_T_MULTIPLIER_MEAN = 3.0
SOFTMAX_T_MULTIPLIER_SD = 1.5
SOFTMAX_T_CLIP_CENTS_KWH = (0.15, 2.0)


def _sample_cost_durability_inputs(
    rng: np.random.Generator,
    active_technologies: tuple[str, ...],
) -> tuple[dict[str, float], dict[str, float], int, float]:
    learning_rates = dict(CENTRAL_LEARNING_RATES)
    capex_floors = dict(CENTRAL_CAPEX_FLOORS_USD_W)
    for tech in active_technologies:
        mean, sd = LEARNING_RATE_PRIORS[tech]
        learning_rates[tech] = float(np.clip(
            rng.normal(mean, sd), *LEARNING_RATE_CLIP,
        ))
        low, high = CAPEX_FLOOR_PRIORS_USD_W[tech]
        capex_floors[tech] = float(rng.uniform(low, high))
    breakthrough_year = int(
        rng.integers(
            PEROVSKITE_BREAKTHROUGH_YEAR_RANGE[0],
            PEROVSKITE_BREAKTHROUGH_YEAR_RANGE[1] + 1,
        )
    )
    lifetime_final = float(rng.uniform(*POST_BREAKTHROUGH_LIFETIME_RANGE_YR))
    return learning_rates, capex_floors, breakthrough_year, lifetime_final


def sample_cost_durability_inputs(
    rng: np.random.Generator,
) -> tuple[dict[str, float], dict[str, float], int, float]:
    return _sample_cost_durability_inputs(rng, tuple(LEARNING_RATE_PRIORS))


def sample_crossover_inputs(
    rng: np.random.Generator,
) -> tuple[dict[str, float], dict[str, float], int, float]:
    """Sample only inputs active in the perovskite versus c-Si crossover."""
    return _sample_cost_durability_inputs(rng, (TECH_CSI, TECH_PEROVSKITE))


def sample_mc_inputs(
    rng: np.random.Generator, t_fit_cents_kwh: float
) -> tuple[dict[str, float], dict[str, float], int, float, float]:
    learning_rates, capex_floors, breakthrough_year, lifetime_final = (
        sample_cost_durability_inputs(rng)
    )
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
            "source_or_anchor": "Author learning prior informed by PV cost-history literature; mean and SD are not a documented empirical fit",
            "prior_reason": "Mature incumbent still has residual cost decline and manufacturing uncertainty",
            "stress_test_role": "Tests whether silicon cost decline delays perovskite substitution",
            "used_in": "Main Fig 4c crossover and new-build share scenarios",
        },
        {
            "parameter": "perovskite learning rate",
            "distribution_or_value": "Normal mean 0.27 and SD 0.04; clipped to 0.08-0.45",
            "source_or_anchor": "Scenario prior because bankable perovskite deployment history does not yet exist",
            "prior_reason": "Allows faster early learning without assuming guaranteed commercial dominance",
            "stress_test_role": "Tests whether high learning can overcome the lifetime gate",
            "used_in": "Main Fig 4c crossover and new-build share scenarios",
        },
        {
            "parameter": "tandem learning rate",
            "distribution_or_value": "Normal mean 0.30 and SD 0.04; clipped to 0.08-0.45",
            "source_or_anchor": "Author learning prior; tandem module TEA provides cost context, not a measured 30% learning rate",
            "prior_reason": "Represents immature two-terminal tandem manufacturing uncertainty",
            "stress_test_role": "Tests whether area efficiency can compensate for higher capex",
            "used_in": "New-build share scenarios; held at the prior centre in Main Fig 4c",
        },
        {
            "parameter": "c-Si capex floor",
            "distribution_or_value": "Uniform 0.35-0.45 USD per W",
            "source_or_anchor": "Author system-capex floor scenario; module prices are not direct evidence for a system-cost floor",
            "prior_reason": "Prevents mature silicon from declining without a physical and supply-chain floor",
            "stress_test_role": "Sets the incumbent cost threshold",
            "used_in": "Main Fig 4c crossover and new-build share scenarios",
        },
        {
            "parameter": "perovskite capex floor",
            "distribution_or_value": "Uniform 0.32-0.45 USD per W",
            "source_or_anchor": "Scenario process floor; no bankable market price series exists",
            "prior_reason": "Allows low-cost manufacturing while retaining parity and underperformance cases",
            "stress_test_role": "Separates cost-led substitution from yield-led substitution",
            "used_in": "Main Fig 4c crossover and new-build share scenarios",
        },
        {
            "parameter": "tandem capex floor",
            "distribution_or_value": "Uniform 0.42-0.58 USD per W",
            "source_or_anchor": "Author system-capex floor scenario; Cordell models US module MSP, not this installed-system floor range",
            "prior_reason": "Retains higher process complexity for tandem manufacturing",
            "stress_test_role": "Tests whether tandem remains area-driven rather than yield-driven",
            "used_in": "New-build share scenarios; held at the prior centre in Main Fig 4c",
        },
        {
            "parameter": "perovskite durability-endpoint year",
            "distribution_or_value": "Discrete uniform integer years 2028-2042",
            "source_or_anchor": "Durability-transition scenario bracket",
            "prior_reason": "Does not assume that durability improvement finishes on a fixed schedule",
            "stress_test_role": "Controls how quickly lifetime, degradation and burn-in improve",
            "used_in": "Main Fig 4c crossover and new-build share scenarios",
        },
        {
            "parameter": "perovskite endpoint lifetime",
            "distribution_or_value": "Uniform 18-25 years",
            "source_or_anchor": "Scenario range from partial durability improvement to silicon-like lifetime",
            "prior_reason": "Keeps incomplete lifetime improvement visible in the economics",
            "stress_test_role": "Controls never-substitute tail risk",
            "used_in": "Main Fig 4c crossover and new-build share scenarios",
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
            "used_in": "New-build share scenarios; excluded from Main Fig 4c crossover",
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
