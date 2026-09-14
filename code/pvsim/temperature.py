"""Photovoltaic cell temperature models."""

from __future__ import annotations

import numpy as np


def faiman(poa_global, temp_air, wind_speed=1.0, u0=25.0, u1=6.84):

    poa_global = np.asarray(poa_global, float)
    temp_air = np.asarray(temp_air, float)
    wind_speed = np.asarray(wind_speed, float)
    return temp_air + poa_global / (u0 + u1 * wind_speed)


def noct_cell_temp(poa_global, temp_air, noct=45.0):

    poa_global = np.asarray(poa_global, float)
    temp_air = np.asarray(temp_air, float)
    return temp_air + (noct - 20.0) / 800.0 * poa_global


def cell_temperature(poa_global, temp_air, wind_speed=1.0, model="faiman",
                     noct=45.0, u0=25.0, u1=6.84):

    if model == "faiman":
        return faiman(poa_global, temp_air, wind_speed, u0=u0, u1=u1)
    elif model == "noct":
        return noct_cell_temp(poa_global, temp_air, noct)
    raise ValueError(f'Unknown temperature model: {model}')
