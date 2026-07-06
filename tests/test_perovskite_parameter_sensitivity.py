from scripts.perovskite_parameter_sensitivity import build_rows, summarize


def test_perovskite_parameter_sensitivity_covers_stress_grid():
    rows = build_rows()
    assert rows["perovskite_gamma_pct_per_c"].nunique() == 3
    assert rows["spectral_response_scale"].nunique() == 3
    assert len(rows) == 31 * 9


def test_perovskite_parameter_sensitivity_preserves_direction():
    summary = summarize(build_rows())
    assert len(summary) == 9
    assert summary["direction_preserved"].all()
    assert (summary["irradiance_advantage_correlation"] < 0).all()
