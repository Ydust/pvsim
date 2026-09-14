"""Weather inputs and cache handling."""

from __future__ import annotations

from pvsim.labels import label as _text_label

import json
import os

import numpy as np
import pandas as pd
import pvlib
from pvlib.location import Location


def get_location(latitude=31.23, longitude=121.47, tz="Asia/Shanghai",
                 altitude=10.0, name=_text_label('shanghai')) -> Location:

    return Location(latitude, longitude, tz=tz, altitude=altitude, name=name)


def make_weather(times, location: Location, ghi, dni, dhi,
                 temp_air, wind_speed, surface_tilt=None,
                 surface_azimuth=180.0) -> pd.DataFrame:

    if surface_tilt is None:
        surface_tilt = abs(location.latitude)

    solpos = location.get_solarposition(times)
    zenith = solpos["apparent_zenith"]
    azimuth = solpos["azimuth"]
    dni_extra = pvlib.irradiance.get_extra_radiation(times)

    aoi = pvlib.irradiance.aoi(surface_tilt, surface_azimuth, zenith, azimuth)
    total = pvlib.irradiance.get_total_irradiance(
        surface_tilt, surface_azimuth, zenith, azimuth,
        dni=dni, ghi=ghi, dhi=dhi, dni_extra=dni_extra, model="haydavies",
    )

    df = pd.DataFrame({
        "ghi": np.asarray(ghi, float),
        "dni": np.asarray(dni, float),
        "dhi": np.asarray(dhi, float),
        "temp_air": np.asarray(temp_air, float),
        "wind_speed": np.asarray(wind_speed, float),
        "solar_zenith": zenith.to_numpy(float),
        "solar_azimuth": azimuth.to_numpy(float),
        "aoi": np.asarray(aoi, float),
        "poa_global": total["poa_global"].to_numpy(float),
        "poa_direct": total["poa_direct"].to_numpy(float),
        "poa_diffuse": total["poa_diffuse"].to_numpy(float),
    }, index=times)
    df[["poa_global", "poa_direct", "poa_diffuse"]] = \
        df[["poa_global", "poa_direct", "poa_diffuse"]].clip(lower=0.0).fillna(0.0)
    return df


def _synthetic_temp(times, tmean=20.0, diurnal=8.0, seasonal=12.0):

    hours = times.hour + times.minute / 60.0
    doy = times.dayofyear
    diur = diurnal * np.sin(2 * np.pi * (hours - 9.0) / 24.0)
    seas = seasonal * np.sin(2 * np.pi * (doy - 110) / 365.0)
    return tmean + seas + diur


def clear_sky_day(date="2023-06-21", location: Location | None = None,
                  surface_tilt=None, freq="15min",
                  cloud_factor=1.0, tmean=25.0, wind=1.5) -> pd.DataFrame:

    loc = location or get_location()
    times = pd.date_range(f"{date} 00:00", f"{date} 23:59", freq=freq, tz=loc.tz)
    cs = loc.get_clearsky(times, model="ineichen")
    ghi, dni, dhi = cs["ghi"] * cloud_factor, cs["dni"] * cloud_factor, cs["dhi"] * cloud_factor
    temp = _synthetic_temp(times, tmean=tmean, diurnal=8.0, seasonal=0.0)
    wind_arr = np.full(len(times), wind)
    return make_weather(times, loc, ghi, dni, dhi, temp, wind_arr, surface_tilt)


def clear_sky_year(year=2023, location: Location | None = None,
                   surface_tilt=None, freq="1h", tmean=16.0) -> pd.DataFrame:

    loc = location or get_location()
    times = pd.date_range(f"{year}-01-01 00:00", f"{year}-12-31 23:59",
                          freq=freq, tz=loc.tz)
    cs = loc.get_clearsky(times, model="ineichen")
    temp = _synthetic_temp(times, tmean=tmean, diurnal=8.0, seasonal=12.0)
    wind_arr = np.full(len(times), 1.5)
    return make_weather(times, loc, cs["ghi"], cs["dni"], cs["dhi"],
                        temp, wind_arr, surface_tilt)


def synthetic_tmy_year(year=2023, location: Location | None = None,
                       surface_tilt=None, freq="1h", tmean=16.0,
                       seed=0) -> pd.DataFrame:

    loc = location or get_location()
    times = pd.date_range(f"{year}-01-01 00:00", f"{year}-12-31 23:59",
                          freq=freq, tz=loc.tz)
    cs = loc.get_clearsky(times, model="ineichen")
    rng = np.random.default_rng(seed)

    ndays = times.normalize().nunique()
    daily = 0.35 + 0.65 * rng.beta(5, 2, size=ndays)
    day_index = (times.normalize() - times.normalize()[0]).days
    kt = daily[day_index]
    ghi = cs["ghi"] * kt

    dhi = cs["dhi"] * kt + cs["dni"] * (1 - kt) * 0.25 * np.cos(np.radians(
        loc.get_solarposition(times)["apparent_zenith"].clip(upper=89)))
    dni = (cs["dni"] * kt).clip(lower=0)
    dhi = dhi.clip(lower=0)
    temp = _synthetic_temp(times, tmean=tmean, diurnal=8.0, seasonal=12.0)
    wind_arr = np.full(len(times), 1.8)
    return make_weather(times, loc, ghi, dni, dhi, temp, wind_arr, surface_tilt)


def from_tmy3(path: str, location: Location | None = None,
              surface_tilt=None) -> pd.DataFrame:

    data, meta = pvlib.iotools.read_tmy3(path, map_variables=True)
    loc = location or Location(meta["latitude"], meta["longitude"],
                               altitude=meta.get("altitude", 0))
    times = data.index
    wind = data.get("wind_speed", pd.Series(1.5, index=times))
    temp = data.get("temp_air", pd.Series(20.0, index=times))
    return make_weather(times, loc, data["ghi"], data["dni"], data["dhi"],
                        temp, wind, surface_tilt)


def from_pvgis_tmy(latitude, longitude, altitude=0.0, tz="Asia/Shanghai",
                   name="city", surface_tilt=None,
                   cache_dir="data/tmy_cache", allow_download=True,
                   timeout=60) -> pd.DataFrame:

    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{name}.csv")
    meta_path = os.path.join(cache_dir, f"{name}.meta.json")
    cache_meta = {}
    cache_exists = os.path.exists(path)
    if cache_exists and os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            cache_meta = json.load(f)
        cached_latitude = cache_meta.get("latitude")
        cached_longitude = cache_meta.get("longitude")
        if cached_latitude is not None and cached_longitude is not None:
            coordinate_mismatch = (
                abs(float(cached_latitude) - float(latitude)) > 1e-6
                or abs(float(cached_longitude) - float(longitude)) > 1e-6
            )
            if coordinate_mismatch:
                if not allow_download:
                    raise ValueError(
                        f"PVGIS cache coordinates do not match request: {path}"
                    )
                cache_exists = False

    if cache_exists:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        if not allow_download:
            raise FileNotFoundError(f"PVGIS TMY cache does not exist: {path}")
        res = pvlib.iotools.get_pvgis_tmy(
            latitude, longitude, map_variables=True, timeout=timeout,
        )
        df = res[0]
        raw_meta = res[1] if len(res) > 1 and isinstance(res[1], dict) else {}
        location_meta = raw_meta.get("inputs", {}).get("location", {})
        cache_meta = {
            "source": "PVGIS TMY",
            "latitude": float(location_meta.get("latitude", latitude)),
            "longitude": float(location_meta.get("longitude", longitude)),
            "elevation_m": float(location_meta.get("elevation", 0.0)),
        }
        df.to_csv(path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(cache_meta, f, ensure_ascii=False, indent=2)

    times = df.index
    if times.tz is None:
        times = times.tz_localize("UTC")
        df.index = times
    if altitude is None:
        altitude = float(cache_meta.get("elevation_m", 0.0))
    loc = Location(latitude, longitude, tz=tz, altitude=altitude, name=name)
    wind = df["wind_speed"] if "wind_speed" in df.columns else pd.Series(1.5, index=times)
    weather = make_weather(times, loc, df["ghi"], df["dni"], df["dhi"],
                           df["temp_air"], wind, surface_tilt)
    weather.attrs.update({
        "source": "PVGIS TMY",
        "latitude": float(latitude),
        "longitude": float(longitude),
        "elevation_m": float(altitude),
        "cache_path": path,
    })
    return weather


def from_epw(path: str, location: Location | None = None,
             surface_tilt=None) -> pd.DataFrame:

    data, meta = pvlib.iotools.read_epw(path, coerce_year=2023)
    loc = location or Location(meta["latitude"], meta["longitude"],
                               altitude=meta.get("altitude", 0))
    times = data.index
    return make_weather(times, loc, data["ghi"], data["dni"], data["dhi"],
                        data["temp_air"], data["wind_speed"], surface_tilt)
