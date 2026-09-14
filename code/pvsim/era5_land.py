"""ERA5-Land weather data access."""

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
            print('  [CDS] Fetch ERA5-Land Monthly mean (Multi-year×12month×4Variable)...', flush=True)
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


    ddir = os.path.join(CACHE, "china_raw_dir")
    with zipfile.ZipFile(raw) as z:
        z.extractall(ddir)
        ncs = [os.path.join(ddir, n) for n in z.namelist() if n.endswith(".nc")]
    if verbose:
        print(f'  Extract {len(ncs)} nc File, Read + Interannual average...', flush=True)

    ds = xr.open_mfdataset(ncs, combine="by_coords") if len(ncs) > 1 else xr.open_dataset(ncs[0])

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


    ghi_J = monthly_clim("ssrd")
    tair_K = monthly_clim("t2m")              # K
    u10 = monthly_clim("u10"); v10 = monthly_clim("v10")

    ghi = ghi_J / 3.6e6                        # → kWh/m²/day
    tair = tair_K - 273.15                     # → °C
    wind = np.sqrt(u10**2 + v10**2)

    result = {"lon": LON, "lat": LAT, "ghi": ghi, "tair": tair, "wind": wind}
    np.savez_compressed(npz, **result)
    if verbose:
        print(f'  Completed: {lat.size}×{lon.size} grid points, GHI Range of annual means {np.nanmin(ghi.mean(0)) * 365:.0f}-{np.nanmax(ghi.mean(0)) * 365:.0f} kWh/m²/yr',
              flush=True)
    return result


if __name__ == "__main__":
    g = fetch_china_climatology()
    print(f"ERA5-Land China grid: {g['lon'].shape}")
    print(f"GHI[7month] samples: {np.nanmean(g['ghi'][6]):.2f} kWh/m²/day")
    print(f"Tair[7month] samples: {np.nanmean(g['tair'][6]):.1f} °C")
