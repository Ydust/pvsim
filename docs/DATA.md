# External data

This repository ships code, manuscript drafts, literature-cited parameters,
versioned provincial source tables and generated audit summaries. Several
external data sources are still required to reproduce all national-scale
figures from raw inputs.

The provincial source tables live in `data/source_tables`. Their current audit
status is documented by `docs/SI_SOURCE_AUDIT_STATUS.md`. The source audit gate
has 0 missing provenance fields and 62 row-level official records complete.
The fleet-hour table remains a system-level validation anchor, but it is not
counted as a release-gated official row layer.

## 1.  PVGIS — typical meteorological year

- Source: Joint Research Centre, [PVGIS API](https://re.jrc.ec.europa.eu/api/).
- Used by: `pvsim.weather.from_pvgis_tmy(latitude, longitude, …)`.
- Behaviour: the first call for each (lat, lon) downloads ≈ 800 kB and caches
  it under `data/tmy_cache/<key>.csv`.  Subsequent calls are offline.
- License: re-use permitted with attribution.

You do not need to download anything manually — running any city-level
script (`scripts.run_cities`, `scripts.animate_cities`, …) will populate
the cache on demand.

## 2.  Global Energy Monitor (GEM) — GeoJSON power-plant layers

Used by `scripts.map_pv_china`, `scripts.map_pv_layers`,
`scripts.anim_pv_growth`, `scripts.anim_pv_lifecycle`, and the retirement /
recycling / replacement analyses.

| Layer | Filename pattern | Source |
|---|---|---|
| Solar plants | `China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson` | <https://globalenergymonitor.org> |
| Coal plants  | `China_coal_power_plants_vJan2024_3__*.geojson` | GEM |
| Wind plants  | `China_Wind_Power_Plants_GEM_202406__*.geojson` | GEM |
| Gas plants   | `China_Gas_Power_Plants_EH_v2024__*.geojson` | GEM |
| Nuclear plants | `China_Nuclear_Power_Plants_vSep2024__*.geojson` | GEM |
| Transmission | `China_PowerTransmission_2025_Figshare__*.geojson` | <https://figshare.com> |
| Admin boundary | `CHN_adm_shp__0__CHN_adm_shp.geojson` | GADM via GEM repackaging |

Use the `CHINA_GEOJSON` environment variable when the boundary or GEM copy
lives outside the repository. Some legacy scripts still expose a local `GEO`
constant, but manuscript-facing ERA5 grid code first checks `CHINA_GEOJSON`
and then `data/geojson`.

## 2b.  Gridded climatology — NASA POWER and ERA5-Land

Used by the grid-scale geographic-inversion analysis
(`scripts.fig_grid_inversion`, `scripts.fig_grid_inversion_era5`).

| Source | Resolution | Land cells in China | Access | Module |
|---|---|---|---|---|
| NASA POWER | 1° (CERES/MERRA-2) | ~954 | free, no key | `pvsim.nasa_power` |
| ERA5-Land | 0.1° (~9 km) | ~95,000 | needs CDS credentials | `pvsim.era5_land` |

- **NASA POWER** downloads on demand (regional climatology endpoint, tiled), caches
  under `data/power_cache/`. No registration required.
- **ERA5-Land** needs a free Copernicus CDS account and a `~/.cdsapirc` with your
  Personal Access Token (new CDS format: `url: https://cds.climate.copernicus.eu/api`).
  You must accept the `reanalysis-era5-land-monthly-means` licence on the dataset page.
  The processed multi-year monthly climatology caches to `data/era5_cache/china_clim.npz`
  (~90 MB raw download, one-time). Variables: `ssrd` (-> GHI), `t2m`, `u10`/`v10` (-> wind).

Both feed a monthly reduced-order grid model. For the perovskite-advantage variable used in
the 0.1° map, validation against full 8760-hour simulations at the 31 provincial anchors gives
R^2 ≈ 0.38 and RMSE ≈ 0.96 percentage points, so the grid layer is used for spatial pattern
and regional ranking rather than point forecasts.

## 3.  Literature parameters

All material parameters, embodied-carbon factors, grid emission factors, metal
intensities, lifetime assumptions, and tandem cost baselines are documented
inline with their literature citation:

- `pvsim/materials.py` — De Soto five-parameter values, temperature
  coefficients, optical & recombination bandgaps, encapsulation degradation.
- `pvsim/policy_data.py` — China PV installation target, IEA grid
  decarbonisation trajectory, USGS metal supply, Cordell et al. 2025 tandem
  MSP curve.
- `scripts/fig_embodied_carbon.py`, `scripts/fig_recycling.py` — Fraunhofer
  ISE, IPCC AR6, IEA-PVPS Task 12 ranges for kg CO₂eq/Wp and material
  intensities.

When you change any of these, please update the citation in the same
docstring or comment.
