"""Shared discounted-LCOE and durability calculations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


DISCOUNT_RATE = 0.05
OPEX_FRACTION_OF_CAPEX = 0.015

PEROVSKITE_START_LIFETIME_YR = 15.0
PEROVSKITE_START_DEGRADATION = 0.030
PEROVSKITE_START_BURN_IN = 0.10
PEROVSKITE_FULL_LIFETIME_YR = 25.0
PEROVSKITE_FULL_DEGRADATION = 0.007
PEROVSKITE_FULL_BURN_IN = 0.05


@dataclass(frozen=True)
class DurabilityState:
    lifetime_years: float
    degradation_rate: float
    burn_in_loss: float


MODERN_CSI_DURABILITY = DurabilityState(25.0, 0.005, 0.01)
TANDEM_DURABILITY = DurabilityState(25.0, 0.012, 0.04)


def _discount_terms(
    lifetime_years: float,
    discount_rate: float,
) -> tuple[np.ndarray, np.ndarray]:
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    full_years = int(np.floor(lifetime_years))
    times = np.arange(1, full_years + 1, dtype=float)
    service_weights = np.ones(full_years, dtype=float)
    fractional_year = lifetime_years - full_years
    if fractional_year > 1e-9:
        times = np.append(times, lifetime_years)
        service_weights = np.append(service_weights, fractional_year)
    return times, service_weights


def discounted_energy(
    year1_yield: float,
    lifetime_years: float,
    degradation_rate: float,
    burn_in_loss: float,
    *,
    discount_rate: float = DISCOUNT_RATE,
) -> float:
    """Return discounted lifetime energy in the same capacity/area basis as input."""
    if year1_yield <= 0:
        raise ValueError("year1_yield must be positive")
    if not 0 <= degradation_rate < 1:
        raise ValueError("degradation_rate must be in [0, 1)")
    if not 0 <= burn_in_loss < 1:
        raise ValueError("burn_in_loss must be in [0, 1)")
    times, service_weights = _discount_terms(lifetime_years, discount_rate)
    discount = (1.0 + discount_rate) ** (-times)
    retention = (1.0 - burn_in_loss) * (
        (1.0 - degradation_rate) ** (times - 1.0)
    )
    return float(np.sum(
        year1_yield * retention * service_weights * discount
    ))


def discounted_cost_multiplier(
    lifetime_years: float,
    *,
    discount_rate: float = DISCOUNT_RATE,
    opex_fraction_of_capex: float = OPEX_FRACTION_OF_CAPEX,
) -> float:
    """Return the multiplier from upfront capex to discounted capex plus O&M."""
    times, service_weights = _discount_terms(lifetime_years, discount_rate)
    discount = (1.0 + discount_rate) ** (-times)
    return float(
        1.0 + np.sum(opex_fraction_of_capex * service_weights * discount)
    )


def area_constrained_lcoe(
    capex_per_w: float,
    capacity_density_w_per_m2: float,
    year1_yield_kwh_per_m2: float,
    durability: DurabilityState,
    *,
    incremental_area_cost_usd_per_m2: float = 0.0,
    discount_rate: float = DISCOUNT_RATE,
    opex_fraction_of_capex: float = OPEX_FRACTION_OF_CAPEX,
) -> float:
    """Return USD/kWh for one square metre under an incremental area cost.

    The technology capex path remains in USD/W. The optional area cost is a
    one-time site or roof opportunity cost common to candidate technologies; it
    is kept separate from recurring O&M so it can be interpreted as a scarcity
    threshold rather than as a second system-cost forecast.
    """
    if capex_per_w < 0:
        raise ValueError("capex_per_w must be non-negative")
    if capacity_density_w_per_m2 <= 0:
        raise ValueError("capacity_density_w_per_m2 must be positive")
    if incremental_area_cost_usd_per_m2 < 0:
        raise ValueError("incremental_area_cost_usd_per_m2 must be non-negative")
    discounted_generation = discounted_energy(
        year1_yield_kwh_per_m2,
        durability.lifetime_years,
        durability.degradation_rate,
        durability.burn_in_loss,
        discount_rate=discount_rate,
    )
    recurring_cost_factor = discounted_cost_multiplier(
        durability.lifetime_years,
        discount_rate=discount_rate,
        opex_fraction_of_capex=opex_fraction_of_capex,
    )
    technology_cost_per_m2 = capex_per_w * capacity_density_w_per_m2
    discounted_cost = (
        technology_cost_per_m2 * recurring_cost_factor
        + incremental_area_cost_usd_per_m2
    )
    return float(discounted_cost / discounted_generation)


def area_cost_parity_threshold(
    *,
    reference_capex_per_w: float,
    candidate_capex_per_w: float,
    reference_capacity_density_w_per_m2: float,
    candidate_capacity_density_w_per_m2: float,
    reference_year1_yield_kwh_per_m2: float,
    candidate_year1_yield_kwh_per_m2: float,
    reference_durability: DurabilityState,
    candidate_durability: DurabilityState,
    discount_rate: float = DISCOUNT_RATE,
    opex_fraction_of_capex: float = OPEX_FRACTION_OF_CAPEX,
) -> float:
    """Return the common incremental USD/m2 cost at candidate/reference parity.

    A positive value is the additional site-area cost required before the
    candidate's higher discounted energy density offsets its base LCOE gap.
    Negative values indicate that the candidate is already below the reference
    LCOE without an area-scarcity credit.
    """
    reference_energy = discounted_energy(
        reference_year1_yield_kwh_per_m2,
        reference_durability.lifetime_years,
        reference_durability.degradation_rate,
        reference_durability.burn_in_loss,
        discount_rate=discount_rate,
    )
    candidate_energy = discounted_energy(
        candidate_year1_yield_kwh_per_m2,
        candidate_durability.lifetime_years,
        candidate_durability.degradation_rate,
        candidate_durability.burn_in_loss,
        discount_rate=discount_rate,
    )
    if candidate_energy <= reference_energy:
        raise ValueError(
            "candidate discounted energy per m2 must exceed the reference"
        )
    reference_zero = area_constrained_lcoe(
        reference_capex_per_w,
        reference_capacity_density_w_per_m2,
        reference_year1_yield_kwh_per_m2,
        reference_durability,
        discount_rate=discount_rate,
        opex_fraction_of_capex=opex_fraction_of_capex,
    )
    candidate_zero = area_constrained_lcoe(
        candidate_capex_per_w,
        candidate_capacity_density_w_per_m2,
        candidate_year1_yield_kwh_per_m2,
        candidate_durability,
        discount_rate=discount_rate,
        opex_fraction_of_capex=opex_fraction_of_capex,
    )
    area_slope_difference = 1.0 / candidate_energy - 1.0 / reference_energy
    return float((reference_zero - candidate_zero) / area_slope_difference)


def discounted_lcoe(
    capex_per_w: float,
    year1_yield_kwh_per_kwp: float,
    lifetime_years: float,
    degradation_rate: float,
    burn_in_loss: float,
    *,
    discount_rate: float = DISCOUNT_RATE,
    opex_fraction_of_capex: float = OPEX_FRACTION_OF_CAPEX,
) -> float:
    """Return LCOE in USD per kWh using discounted annual cash and energy flows.

    A fractional final service year is retained instead of silently truncating
    an evolving lifetime to an integer year.
    """
    if capex_per_w < 0:
        raise ValueError("capex_per_w must be non-negative")
    if year1_yield_kwh_per_kwp <= 0:
        raise ValueError("year1_yield_kwh_per_kwp must be positive")
    capex_per_kwp = capex_per_w * 1000.0
    discounted_cost = capex_per_kwp * discounted_cost_multiplier(
        lifetime_years,
        discount_rate=discount_rate,
        opex_fraction_of_capex=opex_fraction_of_capex,
    )
    energy = discounted_energy(
        year1_yield_kwh_per_kwp,
        lifetime_years,
        degradation_rate,
        burn_in_loss,
        discount_rate=discount_rate,
    )
    return float(discounted_cost / energy)


def perovskite_durability(
    year: float,
    breakthrough_year: float,
    final_lifetime_years: float,
    *,
    start_year: float = 2025.0,
) -> DurabilityState:
    """Interpolate perovskite durability to a sampled endpoint.

    The sampled breakthrough year is the year in which the endpoint is reached,
    not an instantaneous step change. Degradation and burn-in endpoints are
    linked to the sampled lifetime so partial durability improvement remains
    internally consistent.
    """
    final_lifetime = float(np.clip(
        final_lifetime_years,
        PEROVSKITE_START_LIFETIME_YR,
        PEROVSKITE_FULL_LIFETIME_YR,
    ))
    endpoint_fraction = (
        (final_lifetime - PEROVSKITE_START_LIFETIME_YR)
        / (PEROVSKITE_FULL_LIFETIME_YR - PEROVSKITE_START_LIFETIME_YR)
    )
    final_degradation = PEROVSKITE_START_DEGRADATION + endpoint_fraction * (
        PEROVSKITE_FULL_DEGRADATION - PEROVSKITE_START_DEGRADATION
    )
    final_burn_in = PEROVSKITE_START_BURN_IN + endpoint_fraction * (
        PEROVSKITE_FULL_BURN_IN - PEROVSKITE_START_BURN_IN
    )
    progress = float(np.clip(
        (year - start_year) / max(breakthrough_year - start_year, 1.0),
        0.0,
        1.0,
    ))
    return DurabilityState(
        lifetime_years=(
            PEROVSKITE_START_LIFETIME_YR
            + progress * (final_lifetime - PEROVSKITE_START_LIFETIME_YR)
        ),
        degradation_rate=(
            PEROVSKITE_START_DEGRADATION
            + progress * (final_degradation - PEROVSKITE_START_DEGRADATION)
        ),
        burn_in_loss=(
            PEROVSKITE_START_BURN_IN
            + progress * (final_burn_in - PEROVSKITE_START_BURN_IN)
        ),
    )
