# SI ERA5 Grid Uncertainty Appendix

This appendix defines how the ERA5-Land 0.1 degree reduced-order layer should be used.

The grid layer is calibrated against 31 provincial full 8,760-hour anchors. It supports national spatial pattern and regional ranking. It should not be used as a plant-level or individual-cell prediction.

## Validation Summary

The advantage-variable validation has R2 = 0.377, RMSE = 0.962 percentage points, MAE = 0.818 percentage points and bias = -0.186 percentage points.

The grid contains 94998 land cells. Across those cells, annual irradiance and perovskite advantage remain negatively correlated with r = -0.514.

## Absolute Error Distribution

| metric | p50_pct_points | p75_pct_points | p90_pct_points | max_pct_points |
| --- | --- | --- | --- | --- |
| absolute error percentile | 0.703 | 1.042 | 1.444 | 2.532 |

## Resource-Band Compression

| resource_band | n | full_median_adv_pct | reduced_median_adv_pct | median_error_pct_points |
| --- | --- | --- | --- | --- |
| I | 2 | 1.677 | 3.281 | 1.603 |
| II | 6 | 2.240 | 2.868 | 0.748 |
| III | 18 | 3.512 | 3.388 | -0.503 |
| IV | 5 | 4.679 | 3.412 | -1.405 |

## Largest Provincial Errors

| province_en | resource_band | full_8760h_adv_pct | reduced_era5_adv_pct | error_pct_points | abs_error_pct_points |
| --- | --- | --- | --- | --- | --- |
| Gansu | I | 1.836 | 4.368 | 2.532 | 2.532 |
| Sichuan | IV | 4.728 | 3.247 | -1.481 | 1.481 |
| Chongqing | IV | 5.151 | 3.671 | -1.479 | 1.479 |
| Guangxi | III | 5.034 | 3.590 | -1.444 | 1.444 |
| Hainan | III | 4.993 | 3.565 | -1.427 | 1.427 |
| Guizhou | IV | 3.634 | 2.228 | -1.405 | 1.405 |
| Guangdong | III | 4.945 | 3.766 | -1.179 | 1.179 |
| Xinjiang | II | 1.939 | 2.981 | 1.042 | 1.042 |

## Use Rule

Use the grid figure for national pattern, resource-band ordering and visual localisation of the inversion. Use the 31 full-hourly provincial anchors for province-level numerical claims. Treat any cell-level colour as a climatological pattern value with an uncertainty scale of about one percentage point in the advantage variable.
