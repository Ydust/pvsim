"""Photovoltaic system simulation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pvlib

from .materials import CellTechnology
from .cell import operating_point
from .module import array_dc_power, module_stc_power
from .temperature import cell_temperature
from .optics import effective_poa, bifacial_effective_irradiance
from .spectral import (
    spectral_factor_from_zenith,
    tandem_reference_spectrum_factor,
)


@dataclass
class SystemConfig:
    n_modules: int = 20
    dc_ac_ratio: float = 1.2
    inverter_eta_nom: float = 0.96
    dc_loss: float = 0.05
    mismatch_loss: float = 0.02
    apply_spectral: bool = True
    apply_temperature: bool = True
    apply_iam: bool = True
    apply_bifacial: bool = True

    albedo: float = 0.2
    rear_view_factor: float = 0.4
    thermal_u0: float = 25.0
    thermal_u1: float = 6.84
    bifaciality_override: float | None = None


def inverter_ac(dc_power, pdc0, eta_nom=0.96):

    return np.asarray(pvlib.inverter.pvwatts(np.asarray(dc_power, float),
                                             pdc0, eta_inv_nom=eta_nom))


def array_kwp(tech: CellTechnology, cfg: SystemConfig) -> float:

    return cfg.n_modules * module_stc_power(tech) / 1000.0


def simulate(tech: CellTechnology, weather: pd.DataFrame, cfg: SystemConfig,
             npts: int = 120) -> dict:

    w = weather
    poa_global = w["poa_global"].to_numpy(float)


    if cfg.apply_iam:
        eff = effective_poa(w["poa_direct"].to_numpy(float),
                            w["poa_diffuse"].to_numpy(float),
                            w["aoi"].to_numpy(float))
    else:
        eff = poa_global.copy()


    bifac = tech.bifaciality if cfg.bifaciality_override is None else cfg.bifaciality_override
    if cfg.apply_bifacial and bifac > 0:
        eff = bifacial_effective_irradiance(eff, w["ghi"].to_numpy(float),
                                            bifac, albedo=cfg.albedo,
                                            rear_view_factor=cfg.rear_view_factor)


    if cfg.apply_temperature:
        tcell = cell_temperature(poa_global, w["temp_air"].to_numpy(float),
                                 w["wind_speed"].to_numpy(float), model="faiman",
                                 u0=cfg.thermal_u0, u1=cfg.thermal_u1)
    else:
        tcell = np.full_like(poa_global, 25.0)


    if cfg.apply_spectral:
        sf = spectral_factor_from_zenith(
            tech, w["solar_zenith"].to_numpy(float), tcell_C=tcell
        )
    elif tech.name == "tandem":
        sf = tandem_reference_spectrum_factor(tcell)
    else:
        sf = np.ones_like(poa_global)
    eff = eff * sf


    dc = array_dc_power(tech, poa_global, tcell, n_modules=cfg.n_modules,
                        effective_irradiance=eff,
                        mismatch_loss=cfg.mismatch_loss, npts=npts)
    dc = np.atleast_1d(dc) * (1.0 - cfg.dc_loss)


    kwp = array_kwp(tech, cfg)
    pdc0 = kwp * 1000.0 / cfg.dc_ac_ratio
    ac = inverter_ac(dc, pdc0, cfg.inverter_eta_nom)


    idx = w.index
    if isinstance(idx, pd.DatetimeIndex) and len(idx) > 1:
        dt_h = (idx[1] - idx[0]).total_seconds() / 3600.0
    else:
        dt_h = 1.0

    energy_dc_kwh = float(np.sum(dc) * dt_h / 1000.0)
    energy_ac_kwh = float(np.sum(ac) * dt_h / 1000.0)
    poa_insol_kwh_m2 = float(np.sum(poa_global) * dt_h / 1000.0)

    specific_yield = energy_ac_kwh / kwp if kwp > 0 else 0.0   # kWh/kWp

    ref_yield = poa_insol_kwh_m2 / 1.0
    pr = specific_yield / ref_yield if ref_yield > 0 else 0.0

    out = pd.DataFrame({
        "poa_global": poa_global,
        "eff_irradiance": eff,
        "spectral_factor": sf,
        "tcell": tcell,
        "dc_power": dc,
        "ac_power": ac,
    }, index=idx)

    return {
        "timeseries": out,
        "kwp": kwp,
        "energy_dc_kwh": energy_dc_kwh,
        "energy_ac_kwh": energy_ac_kwh,
        "specific_yield": specific_yield,
        "performance_ratio": pr,
        "poa_insolation_kwh_m2": poa_insol_kwh_m2,
        "clipping_kwh": max(0.0, energy_dc_kwh * cfg.inverter_eta_nom - energy_ac_kwh),
    }


def simulate_rooftop(tech: CellTechnology, raw_weather: pd.DataFrame, location,
                     cfg: SystemConfig, facets) -> dict:

    from dataclasses import replace
    from .weather import make_weather

    total_ac = None
    total_kwp = 0.0
    parts = {}
    for tilt, azimuth, nmod in facets:
        w = make_weather(raw_weather.index, location,
                         raw_weather["ghi"], raw_weather["dni"], raw_weather["dhi"],
                         raw_weather["temp_air"], raw_weather["wind_speed"],
                         surface_tilt=tilt, surface_azimuth=azimuth)
        r = simulate(tech, w, replace(cfg, n_modules=nmod), npts=80)
        ac = r["timeseries"]["ac_power"]
        total_ac = ac if total_ac is None else total_ac + ac
        total_kwp += r["kwp"]
        parts[(tilt, azimuth)] = ac
    dt_h = (total_ac.index[1] - total_ac.index[0]).total_seconds() / 3600.0
    energy = float(total_ac.sum()) * dt_h / 1000.0
    return {"ac_power": total_ac, "kwp": total_kwp, "parts": parts,
            "energy_ac_kwh": energy,
            "specific_yield": energy / total_kwp if total_kwp > 0 else 0.0}
