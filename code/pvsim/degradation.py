"""Photovoltaic degradation and durability models."""

from __future__ import annotations

from pvsim.labels import label as _text_label

from dataclasses import dataclass

import numpy as np

from .materials import CellTechnology


PEROVSKITE_SCENARIOS = {
    _text_label('degradation_text'): dict(burn_in_loss=0.05, degradation_rate=0.010),
    _text_label('degradation_text_2'): dict(burn_in_loss=0.10, degradation_rate=0.030),
    _text_label('degradation_text_3'): dict(burn_in_loss=0.15, degradation_rate=0.060),
}


@dataclass
class DegradationProfile:
    burn_in_loss: float
    burn_in_years: float
    degradation_rate: float
    lifetime_years: float


def profile_for(tech: CellTechnology, scenario: str | None = None) -> DegradationProfile:

    burn = tech.burn_in_loss
    rate = tech.degradation_rate
    if scenario and tech.name == "perovskite":
        s = PEROVSKITE_SCENARIOS[scenario]
        burn, rate = s["burn_in_loss"], s["degradation_rate"]
    return DegradationProfile(burn, tech.burn_in_years, rate, tech.lifetime_years)


def retention(prof: DegradationProfile, t_years) -> np.ndarray:

    t = np.asarray(t_years, float)
    by = max(prof.burn_in_years, 1e-9)

    burn = 1.0 - prof.burn_in_loss * np.clip(t / by, 0.0, 1.0)

    after = np.where(t > prof.burn_in_years,
                     prof.degradation_rate * (t - prof.burn_in_years), 0.0)
    return np.clip(burn - after, 0.0, 1.0)


def annual_retention_series(prof: DegradationProfile, horizon_years=None):

    n = int(np.ceil(horizon_years if horizon_years else prof.lifetime_years))
    mid = np.arange(n) + 0.5
    return retention(prof, mid)


def lifetime_energy(tech: CellTechnology, year1_energy_kwh: float,
                    scenario: str | None = None, horizon_years=None):

    prof = profile_for(tech, scenario)
    n = int(np.ceil(horizon_years if horizon_years else prof.lifetime_years))
    ret = annual_retention_series(prof, n)

    yearly = year1_energy_kwh * ret / ret[0]
    cumulative = np.cumsum(yearly)

    fine_t = np.linspace(0, n, n * 12 + 1)
    fine_r = retention(prof, fine_t)
    below = np.where(fine_r < 0.80)[0]
    t80 = float(fine_t[below[0]]) if len(below) else float("inf")
    return {
        "years": np.arange(1, n + 1),
        "yearly_kwh": yearly,
        "cumulative_kwh": cumulative,
        "retention": ret,
        "t80_year": t80,
        "profile": prof,
    }
