from scripts.silicon_baseline_sensitivity import build_rows, summarize


def test_silicon_baseline_sensitivity_covers_all_variants():
    rows = build_rows()
    assert rows["baseline"].nunique() == 3
    assert len(rows) == 31 * 3


def test_silicon_baseline_sensitivity_preserves_inversion_direction():
    summary = summarize(build_rows())
    assert summary["direction_preserved"].all()
    assert (summary["irradiance_advantage_correlation"] < 0).all()
