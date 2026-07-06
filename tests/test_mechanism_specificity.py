from scripts.mechanism_specificity import build_checks


def test_mechanism_specificity_checks_preserve_expected_directions():
    checks = build_checks()
    assert len(checks) == 5
    assert checks["direction_preserved"].all()


def test_mechanism_specificity_core_channels_are_strong_after_controls():
    checks = build_checks().set_index("check")
    assert checks.loc[
        "Thermal component versus cell temperature", "partial_correlation"
    ] > 0.5
    assert checks.loc["Spectral component versus air mass", "partial_correlation"] < -0.5
