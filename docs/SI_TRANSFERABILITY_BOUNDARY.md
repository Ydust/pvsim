# SI Transferability Boundary

Last updated: 2026-07-01

This appendix defines a mechanism phase plane for transferability. It is not a global validation map. It states where the China-derived mechanism decomposition would predict a positive or negative per-kWp perovskite advantage as a function of irradiance-weighted cell temperature and air mass.

The fitted thermal slope is 0.186 percentage points per C. The fitted spectral slope is 1.757 percentage points per unit blue-index, where blue-index is the China median air mass minus local air mass.

| Case | Value | Unit |
| --- | ---: | --- |
| zero advantage at air mass 1.4 | 11.301 | cell temperature C |
| zero advantage at air mass 1.8 | 15.090 | cell temperature C |
| zero advantage at air mass 2.2 | 18.879 | cell temperature C |
| zero advantage at air mass 2.6 | 22.667 | cell temperature C |
| China anchor tcell min | 21.448 | cell temperature C |
| China anchor tcell max | 38.499 | cell temperature C |
| China anchor air mass min | 1.555 | air mass |
| China anchor air mass max | 2.277 | air mass |
| Phase-plane positive share | 0.767 | fraction |

## Interpretation

The positive-advantage region is warmer and lower-air-mass. The China anchors sit mostly inside this positive region, which explains why the national result is robust. Colder high-air-mass climates lie closer to or beyond the zero boundary, so the China result should not be exported globally without rerunning the full weather and spectral model.

## Outputs

| File | Role |
| --- | --- |
| `outputs/si_transferability_phase_plane.csv` | Phase-plane grid values |
| `outputs/si_transferability_phase_summary.csv` | Boundary thresholds and China anchor envelope |
| `outputs/figures/SI_transferability_phase_plane.png` | Lightweight SI phase-plane figure |
