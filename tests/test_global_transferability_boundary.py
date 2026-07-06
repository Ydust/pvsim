import numpy as np

from scripts.global_transferability_boundary import (
    build_phase_grid,
    fit_phase_model,
    predict_advantage,
)


def test_transferability_boundary_coefficients_have_expected_signs():
    model, _ = fit_phase_model()
    assert model.thermal_slope_per_c > 0
    assert model.spectral_slope_per_blue_index > 0


def test_transferability_phase_plane_has_positive_and_negative_regions():
    model, _ = fit_phase_model()
    grid = build_phase_grid(model)
    assert grid["predicted_advantage_pct"].min() < 0
    assert grid["predicted_advantage_pct"].max() > 0
    warm_low_airmass = predict_advantage(model, tcell=np.array([40.0]), airmass=np.array([1.4]))[0]
    cold_high_airmass = predict_advantage(model, tcell=np.array([10.0]), airmass=np.array([2.6]))[0]
    assert warm_low_airmass > cold_high_airmass
