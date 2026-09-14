"""Optical transmission and incidence-angle effects."""

from __future__ import annotations

import numpy as np
import pvlib


def iam(aoi_deg, model: str = "martin_ruiz", **kwargs) -> np.ndarray:

    aoi_deg = np.asarray(aoi_deg, float)
    if model == "martin_ruiz":
        return np.asarray(pvlib.iam.martin_ruiz(aoi_deg, **kwargs))
    elif model == "physical":
        return np.asarray(pvlib.iam.physical(aoi_deg, **kwargs))
    elif model == "ashrae":
        return np.asarray(pvlib.iam.ashrae(aoi_deg, **kwargs))
    raise ValueError(f'Unknown IAM Model: {model}')


def effective_poa(poa_direct, poa_diffuse, aoi_deg,
                  model: str = "martin_ruiz") -> np.ndarray:

    poa_direct = np.asarray(poa_direct, float)
    poa_diffuse = np.asarray(poa_diffuse, float)
    iam_b = iam(aoi_deg, model=model)
    iam_d = 0.95
    return poa_direct * iam_b + poa_diffuse * iam_d


def rear_irradiance(ghi, albedo: float = 0.2, rear_view_factor: float = 0.4):

    ghi = np.asarray(ghi, float)
    return ghi * albedo * rear_view_factor


def bifacial_effective_irradiance(front_eff, ghi, bifaciality: float,
                                  albedo: float = 0.2,
                                  rear_view_factor: float = 0.4) -> np.ndarray:

    front_eff = np.asarray(front_eff, float)
    rear = rear_irradiance(ghi, albedo, rear_view_factor)
    return front_eff + bifaciality * rear
