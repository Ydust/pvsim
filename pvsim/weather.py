"""环境数据驱动：合成理想曲线 + 真实气象 (TMY/EPW)。

提供两类数据源：
    1) 合成 clear-sky：用 pvlib 的 Ineichen 晴空模型 + 太阳位置 + 倾斜面转换，
       生成单日或全年的 GHI/DNI/DHI/POA + 合成气温，机理清晰、可控。
    2) 真实气象：读取 TMY3 / EPW 文件 (pvlib.iotools)，更贴近实际。

两者都输出统一的 weather DataFrame（列见 make_weather），可直接喂给 system.simulate。
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pvlib
from pvlib.location import Location


def get_location(latitude=31.23, longitude=121.47, tz="Asia/Shanghai",
                 altitude=10.0, name="上海") -> Location:
    """默认上海（可改）。"""
    return Location(latitude, longitude, tz=tz, altitude=altitude, name=name)


def make_weather(times, location: Location, ghi, dni, dhi,
                 temp_air, wind_speed, surface_tilt=None,
                 surface_azimuth=180.0) -> pd.DataFrame:
    """由辐照三分量 + 气温/风速，转换出含 POA 的统一气象表。

    surface_tilt 缺省取纬度（朝向赤道最优倾角近似）；北半球 surface_azimuth=180(朝南)。
    返回列: ghi,dni,dhi,temp_air,wind_speed,solar_zenith,solar_azimuth,aoi,
            poa_global,poa_direct,poa_diffuse。
    """
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
    """合成气温：日内正弦(15时峰)+ 年内正弦(夏峰)。"""
    hours = times.hour + times.minute / 60.0
    doy = times.dayofyear
    diur = diurnal * np.sin(2 * np.pi * (hours - 9.0) / 24.0)
    seas = seasonal * np.sin(2 * np.pi * (doy - 110) / 365.0)
    return tmean + seas + diur


def clear_sky_day(date="2023-06-21", location: Location | None = None,
                  surface_tilt=None, freq="15min",
                  cloud_factor=1.0, tmean=25.0, wind=1.5) -> pd.DataFrame:
    """单日 clear-sky 气象。cloud_factor<1 模拟整体云衰减(0=全阴,1=全晴)。"""
    loc = location or get_location()
    times = pd.date_range(f"{date} 00:00", f"{date} 23:59", freq=freq, tz=loc.tz)
    cs = loc.get_clearsky(times, model="ineichen")
    ghi, dni, dhi = cs["ghi"] * cloud_factor, cs["dni"] * cloud_factor, cs["dhi"] * cloud_factor
    temp = _synthetic_temp(times, tmean=tmean, diurnal=8.0, seasonal=0.0)
    wind_arr = np.full(len(times), wind)
    return make_weather(times, loc, ghi, dni, dhi, temp, wind_arr, surface_tilt)


def clear_sky_year(year=2023, location: Location | None = None,
                   surface_tilt=None, freq="1h", tmean=16.0) -> pd.DataFrame:
    """全年 clear-sky 气象（理想无云上界）。"""
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
    """合成"类 TMY"全年：在 clear-sky 上叠加随机逐日云量，更接近真实年。"""
    loc = location or get_location()
    times = pd.date_range(f"{year}-01-01 00:00", f"{year}-12-31 23:59",
                          freq=freq, tz=loc.tz)
    cs = loc.get_clearsky(times, model="ineichen")
    rng = np.random.default_rng(seed)
    # 每天一个云量系数(0.35~1.0)，平滑到逐时
    ndays = times.normalize().nunique()
    daily = 0.35 + 0.65 * rng.beta(5, 2, size=ndays)
    day_index = (times.normalize() - times.normalize()[0]).days
    kt = daily[day_index]
    ghi = cs["ghi"] * kt
    # 云越多散射占比越高
    dhi = cs["dhi"] * kt + cs["dni"] * (1 - kt) * 0.25 * np.cos(np.radians(
        loc.get_solarposition(times)["apparent_zenith"].clip(upper=89)))
    dni = (cs["dni"] * kt).clip(lower=0)
    dhi = dhi.clip(lower=0)
    temp = _synthetic_temp(times, tmean=tmean, diurnal=8.0, seasonal=12.0)
    wind_arr = np.full(len(times), 1.8)
    return make_weather(times, loc, ghi, dni, dhi, temp, wind_arr, surface_tilt)


def from_tmy3(path: str, location: Location | None = None,
              surface_tilt=None) -> pd.DataFrame:
    """读取 TMY3 (.csv) 真实气象文件。"""
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
                   cache_dir="data/tmy_cache") -> pd.DataFrame:
    """从 PVGIS 拉取真实典型气象年(TMY)并转出统一气象表；首次联网, 之后读本地缓存。

    PVGIS 基于卫星/再分析数据, 全球覆盖。返回的 weather 表含 POA, 可直接喂 system.simulate。
    """
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{name}.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        res = pvlib.iotools.get_pvgis_tmy(latitude, longitude,
                                          map_variables=True, timeout=60)
        df = res[0]
        df.to_csv(path)

    times = df.index
    if times.tz is None:
        times = times.tz_localize("UTC")
        df.index = times
    loc = Location(latitude, longitude, tz=tz, altitude=altitude, name=name)
    wind = df["wind_speed"] if "wind_speed" in df.columns else pd.Series(1.5, index=times)
    return make_weather(times, loc, df["ghi"], df["dni"], df["dhi"],
                        df["temp_air"], wind, surface_tilt)


def from_epw(path: str, location: Location | None = None,
             surface_tilt=None) -> pd.DataFrame:
    """读取 EPW (EnergyPlus Weather) 真实气象文件。"""
    data, meta = pvlib.iotools.read_epw(path, coerce_year=2023)
    loc = location or Location(meta["latitude"], meta["longitude"],
                               altitude=meta.get("altitude", 0))
    times = data.index
    return make_weather(times, loc, data["ghi"], data["dni"], data["dhi"],
                        data["temp_air"], data["wind_speed"], surface_tilt)
