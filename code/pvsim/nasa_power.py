"""NASA POWER weather data access."""

from __future__ import annotations

import os
import json
import time

import numpy as np
import requests

CACHE_DIR = "data/power_cache"
BASE = "https://power.larc.nasa.gov/api/temporal/climatology/regional"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

PARAMS = {
    "ghi": "ALLSKY_SFC_SW_DWN",
    "tair": "T2M",
    "wind": "WS2M",
    "dni": "ALLSKY_SFC_SW_DNI",
    "dhi": "ALLSKY_SFC_SW_DIFF",
}


def _tile_fetch(param_key, lat_min, lat_max, lon_min, lon_max, timeout=120):

    os.makedirs(CACHE_DIR, exist_ok=True)
    tag = f"{param_key}_{lat_min}_{lat_max}_{lon_min}_{lon_max}"
    path = os.path.join(CACHE_DIR, f"{tag}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return {eval(k): v for k, v in json.load(f).items()}

    params = {
        "parameters": PARAMS[param_key], "community": "RE",
        "latitude-min": lat_min, "latitude-max": lat_max,
        "longitude-min": lon_min, "longitude-max": lon_max,
        "format": "JSON",
    }

    last_err = None
    feats = None
    for attempt in range(4):
        try:
            r = requests.get(BASE, params=params, timeout=timeout)
            r.raise_for_status()
            feats = r.json().get("features", [])
            break
        except Exception as e:
            last_err = e
            time.sleep(2.0 * (attempt + 1))
    if feats is None:
        print(f'    [Skip] tile {tag} Repeated failure: {type(last_err).__name__}', flush=True)
        return {}
    out = {}
    for f in feats:
        lon, lat = f["geometry"]["coordinates"][:2]
        elev = f["geometry"]["coordinates"][2] if len(f["geometry"]["coordinates"]) > 2 else 0
        vals = f["properties"]["parameter"][PARAMS[param_key]]
        rec = {m: vals.get(m) for m in MONTHS}
        rec["ANN"] = vals.get("ANN")
        rec["elev"] = elev
        out[(round(lon, 3), round(lat, 3))] = rec

    with open(path, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in out.items()}, f)
    return out


def fetch_china_grid(lat_range=(18, 54), lon_range=(73, 135), tile=10,
                     params=("ghi", "tair", "wind"), pause=0.3, verbose=True):

    lat0, lat1 = lat_range
    lon0, lon1 = lon_range
    lat_edges = list(range(lat0, lat1, tile)) + [lat1]
    lon_edges = list(range(lon0, lon1, tile)) + [lon1]

    merged = {}
    n_req = 0
    for pk in params:
        for i in range(len(lat_edges) - 1):
            for j in range(len(lon_edges) - 1):
                la0, la1 = lat_edges[i], lat_edges[i+1]
                lo0, lo1 = lon_edges[j], lon_edges[j+1]
                tile_data = _tile_fetch(pk, la0, la1, lo0, lo1)
                n_req += 1
                for coord, rec in tile_data.items():
                    merged.setdefault(coord, {})[pk] = rec
                if verbose and n_req % 5 == 0:
                    print(f'    POWER Request {n_req} (param={pk})...', flush=True)
                time.sleep(pause)
    if verbose:
        print(f'    Completed {n_req} Request, {len(merged)} grid points', flush=True)
    return merged


if __name__ == "__main__":
    g = fetch_china_grid()
    print(f'China bbox Number of grid points: {len(g)}')

    for coord, rec in g.items():
        if all(k in rec for k in ("ghi", "tair", "wind")):
            print(f"Example {coord}: GHI_ANN={rec['ghi']['ANN']:.2f}, Tair_ANN={rec['tair']['ANN']:.1f}, elev={rec['ghi']['elev']:.0f}")
            break
