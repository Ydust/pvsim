"""Energy policy and electricity-system parameters."""

from __future__ import annotations

from pvsim.labels import label as _text_label

import numpy as np

# ============================================================

# ============================================================


def china_pv_target_gw():

    years = np.arange(2024, 2051)
    target = np.interp(years,
                       [2024, 2030, 2040, 2050],
                       [887,  1500, 2150, 2400])
    return years, target


# ============================================================

# ============================================================


def china_grid_ef_kgco2_per_kwh():
    years = np.arange(2024, 2051)

    ef = np.interp(years,
                   [2024, 2030, 2040, 2050],
                   [0.55, 0.42, 0.25, 0.10])
    return years, ef


# ============================================================

# ============================================================


def critical_metal_supply_t_per_yr():
    years = np.arange(2024, 2051)
    indium = 600 * 1.02 ** (years - 2024)        # +2%/yr
    silver = 3500 * 1.015 ** (years - 2024)      # +1.5%/yr
    return years, {"In": indium, "Ag": silver}


# ============================================================

# ============================================================

#   perovskite tandem photovoltaics", Joule 2024, Table S13 ——


METAL_INTENSITY_KG_PER_MW = {
    # tech_key: {metal: kg/MW}  (In @ 100nm ITO, Wagner Joule 2024 Table S13)
    _text_label('policy_data_text'):   {"Ag": 10.0, "In": 0.0, "Pb": 0.0},
    _text_label('policy_data_text_2'):  {"Ag": 4.0,  "In": 1.0, "Pb": 0.6},
    _text_label('policy_data_text_3'):  {"Ag": 4.0,  "In": 1.0, "Pb": 0.6},
    _text_label('tech_tandem'):       {"Ag": 12.0, "In": 1.9, "Pb": 0.5},
}


INDIUM_T_PER_TWP_BY_ITO = {5: 96, 10: 192, 20: 384, 30: 576, 50: 961,
                            100: 1922, 200: 3843, 300: 5765, 400: 7686}

GLOBAL_INDIUM_T_PER_YR = 968.0


# ============================================================

# ============================================================


EMBODIED_KG_PER_WP = {
    _text_label('policy_data_text'):   {"low": 0.40, "mid": 0.50, "high": 0.65},
    _text_label('policy_data_text_2'):  {"low": 0.10, "mid": 0.15, "high": 0.25},
    _text_label('policy_data_text_3'):  {"low": 0.10, "mid": 0.15, "high": 0.25},
    _text_label('tech_tandem'):       {"low": 0.15, "mid": 0.20, "high": 0.30},
}


# ============================================================

# ============================================================


NATIONAL_YIELD_KWH_PER_KWP = {
    _text_label('policy_data_text'):   1400,
    _text_label('policy_data_text_2'):  1470,
    _text_label('policy_data_text_3'):  1470,
    _text_label('tech_tandem'):       1500,
}


# ============================================================

# ============================================================


def tech_max_share(tech_key, year):
    if tech_key == _text_label('policy_data_text'):
        return 1.0
    if tech_key == _text_label('policy_data_text_2'):
        return min(0.7, max(0, (year - 2024) / 5.0))
    if tech_key == _text_label('policy_data_text_3'):
        return min(0.5, max(0, (year - 2030) / 5.0))
    if tech_key == _text_label('tech_tandem'):
        return min(0.5, max(0, (year - 2030) / 5.0))
    return 0.0


# ============================================================

# ============================================================


def china_pv_historical_2015_2024():
    years = np.arange(2015, 2025)
    cum_gw_china  = np.array([43.2, 77.8, 130.2, 174.6, 204.7, 253.4,
                               308.0, 392.6, 609.5, 886.6])
    cum_gw_global = np.array([229,   305,   404,   505,   593,   720,
                               843,   1057,  1418,  1820])
    module_usd_per_w = np.array([0.55, 0.45, 0.34, 0.24, 0.22, 0.20,
                                  0.27, 0.23, 0.15, 0.10])
    return years, cum_gw_china, cum_gw_global, module_usd_per_w


# ============================================================

# ============================================================
LIFE_DEG = {
    _text_label('policy_data_text'):   {"life": 25, "deg": 0.007, "burn_in": 0.02},
    _text_label('policy_data_text_2'):  {"life": 15, "deg": 0.030, "burn_in": 0.10},
    _text_label('policy_data_text_3'):  {"life": 25, "deg": 0.010, "burn_in": 0.05},
    _text_label('tech_tandem'):       {"life": 25, "deg": 0.007, "burn_in": 0.05},
}
