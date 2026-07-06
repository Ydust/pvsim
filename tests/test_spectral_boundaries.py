from scripts.cloud_spectral_sensitivity import build_tables


def test_cloud_spectral_stress_keeps_airmass_direction():
    _, summary = build_tables()
    assert summary["keeps_clear_sky_direction"].all()
    assert (summary["slope_pct_per_airmass"] < 0).all()
