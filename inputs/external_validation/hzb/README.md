# HZB outdoor response data

For the same calendar month (March 2022/2023), the median approximately irradiance/temperature-matched response ratios of three cells are 0.820, 0.861 and 0.905. The corresponding differences of about 18.0%, 13.9% and 9.5% are not independently identified annual degradation rates. Device state, residual weather differences and calibration changes may remain confounded. Low-irradiance results depend more strongly on binning and common coverage.

The source contains three cells on one substrate and no silicon control. It does not establish a ranking of modern modules across sites. CSV units and timezone metadata are not fully verified, so the analysis uses dimensionless descriptive comparisons at the source numerical scale and does not report absolute efficiency or energy. The national model is not refitted.

Source DOI: https://doi.org/10.5442/ND000013. License: CC0.

Run `hzb_response_20260910/analyse.py` with numpy and pandas installed. Original files are retained in the adjacent `public_field_search_round2_20260910/raw` directory. The three cells are not pooled as independent replicates; date medians and bin weighting are defined in the analysis.
