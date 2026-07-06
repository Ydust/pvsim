# SI Cloud Spectral Boundary Stress Test

This check does not introduce a cloud optical model. It perturbs the clear-sky SPECTRL2 spectrum with smooth blue and red tilts, then renormalises each spectrum to the same broadband irradiance.

The purpose is narrow. It asks whether a smooth spectral-colour perturbation would overturn the clear-sky air-mass ordering used in the mechanism attribution.

Result: every stress case keeps a negative slope between relative air mass and the perovskite spectral advantage over modern silicon. The clear-sky spectral mechanism therefore does not require an explicit cloud-blue-shift term.

## Summary

| stress_case | beta | min_perovskite_vs_csi_pct | max_perovskite_vs_csi_pct | slope_pct_per_airmass | corr_with_airmass | keeps_clear_sky_direction |
| --- | --- | --- | --- | --- | --- | --- |
| strong blue tilt | -0.300 | 3.930 | 7.801 | -1.398 | -1.000 | True |
| moderate blue tilt | -0.150 | 1.313 | 5.174 | -1.396 | -1.000 | True |
| clear-sky base | 0.000 | -1.322 | 2.519 | -1.389 | -1.000 | True |
| moderate red tilt | 0.150 | -3.971 | -0.160 | -1.379 | -1.000 | True |
| strong red tilt | 0.300 | -6.627 | -2.855 | -1.365 | -1.000 | True |

## Files

| File | Role |
| --- | --- |
| `outputs/si_cloud_spectral_sensitivity.csv` | Zenith-level stress table |
| `outputs/si_cloud_spectral_sensitivity_summary.csv` | Stress-case summary |
