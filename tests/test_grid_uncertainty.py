import pandas as pd


def test_grid_uncertainty_outputs_are_bounded():
    summary = pd.read_csv("outputs/si_grid_reduced_validation_summary.csv").iloc[0]
    quantiles = pd.read_csv("outputs/si_grid_uncertainty_quantiles.csv").iloc[0]
    assert summary["grid_cells"] > 90000
    assert summary["grid_r_ghi_vs_adv"] < 0
    assert summary["rmse_pct_points"] < 1.1
    assert quantiles["p90_pct_points"] < 1.6


def test_grid_uncertainty_outliers_are_ranked():
    outliers = pd.read_csv("outputs/si_grid_uncertainty_outliers.csv")
    assert len(outliers) == 8
    assert outliers["abs_error_pct_points"].is_monotonic_decreasing
