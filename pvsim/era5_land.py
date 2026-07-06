"""ERA5-Land 0.1° 月度气候态获取 (Gap 1 升级: 1° POWER → 0.1° ERA5-Land).

ERA5-Land (ECMWF, ~9km/0.1°) 比 NASA POWER (1°) 细一个量级.
拉中国 bbox 月均气候态 (多年平均): GHI / 2m 气温 / 10m 风速.

- 需 CDS 凭证 (~/.cdsapirc) 与已接受的 reanalysis-era5-land-monthly-means license.
- 一次 retrieve 拉全部变量 × 12 月 × 多年, 年际平均成气候态, 缓存 npz.
- 单位: ssrd J/m² (日累计均值) → kWh/m²/day = /3.6e6 (与 POWER 同量级, 已校核).

来源: Muñoz-Sabater et al. 2021, ERA5-Land (C3S/ECMWF).
"""

from __future__ import annotations

import os
import zipfile
import numpy as np

CACHE = "data/era5_cache"
MONTHS_NUM = [f"{m:02d}" for m in range(1, 13)]
VARS = {
    "ghi":  "surface_solar_radiation_downwards",
    "tair": "2m_temperature",
    "u10":  "10m_u_component_of_wind",
    "v10":  "10m_v_component_of_wind",
}


def fetch_china_climatology(years=(2017, 2018, 2019, 2020, 2021),
                            area=(54, 73, 18, 135), verbose=True):
    """拉中国 bbox ERA5-Land 月度气候态 (多年平均).

    area = (North, West, South, East).
    返回 dict: lon[ny,nx], lat[ny,nx],
               ghi[12,ny,nx] (kWh/m²/day), tair[12,ny,nx] (°C), wind[12,ny,nx] (m/s).
    缓存 data/era5_cache/china_clim.npz.
    """
    os.makedirs(CACHE, exist_ok=True)
    npz = os.path.join(CACHE, "china_clim.npz")
    if os.path.exists(npz):
        d = np.load(npz)
        return {k: d[k] for k in d.files}

    import cdsapi
    import xarray as xr

    raw = os.path.join(CACHE, "china_raw.zip")
    if not os.path.exists(raw):
        if verbose:
            print("  [CDS] 拉取 ERA5-Land 月均 (多年×12月×4变量)...", flush=True)
        c = cdsapi.Client()
        c.retrieve("reanalysis-era5-land-monthly-means", {
            "product_type": "monthly_averaged_reanalysis",
            "variable": list(VARS.values()),
            "year": [str(y) for y in years],
            "month": MONTHS_NUM,
            "time": "00:00",
            "area": list(area),
            "data_format": "netcdf",
            "download_format": "zip",
        }, raw)

    # 解压 + 读取
    ddir = os.path.join(CACHE, "china_raw_dir")
    with zipfile.ZipFile(raw) as z:
        z.extractall(ddir)
        ncs = [os.path.join(ddir, n) for n in z.namelist() if n.endswith(".nc")]
    if verbose:
        print(f"  解压 {len(ncs)} nc 文件, 读取 + 年际平均...", flush=True)

    ds = xr.open_mfdataset(ncs, combine="by_coords") if len(ncs) > 1 else xr.open_dataset(ncs[0])
    # 时间维: valid_time (year×month). 按月份分组年际平均.
    tdim = "valid_time" if "valid_time" in ds.dims else ("time" if "time" in ds.dims else None)
    months = ds[tdim].dt.month.values
    lat = ds["latitude"].values
    lon = ds["longitude"].values
    LON, LAT = np.meshgrid(lon, lat)

    def monthly_clim(varname):
        arr = ds[varname].values  # [time, lat, lon]
        out = np.empty((12, lat.size, lon.size))
        for mi in range(1, 13):
            sel = arr[months == mi]
            out[mi-1] = np.nanmean(sel, axis=0)
        return out

    # ERA5 netcdf 用短变量名
    ghi_J = monthly_clim("ssrd")              # J/m² (日累计均值)
    tair_K = monthly_clim("t2m")              # K
    u10 = monthly_clim("u10"); v10 = monthly_clim("v10")

    ghi = ghi_J / 3.6e6                        # → kWh/m²/day
    tair = tair_K - 273.15                     # → °C
    wind = np.sqrt(u10**2 + v10**2)            # 10m 风速 m/s

    result = {"lon": LON, "lat": LAT, "ghi": ghi, "tair": tair, "wind": wind}
    np.savez_compressed(npz, **result)
    if verbose:
        print(f"  完成: {lat.size}×{lon.size} 格点, GHI 年均范围 "
              f"{np.nanmin(ghi.mean(0))*365:.0f}-{np.nanmax(ghi.mean(0))*365:.0f} kWh/m²/yr",
              flush=True)
    return result


if __name__ == "__main__":
    g = fetch_china_climatology()
    print(f"ERA5-Land 中国网格: {g['lon'].shape}")
    print(f"GHI[7月] 样本: {np.nanmean(g['ghi'][6]):.2f} kWh/m²/day")
    print(f"Tair[7月] 样本: {np.nanmean(g['tair'][6]):.1f} °C")
