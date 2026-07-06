import pytest

from scripts.national_external_validation import build_rows, build_summary


def test_national_external_validation_uses_official_aggregate_values():
    summary = build_summary()
    assert summary["validation_status"] == "partial national aggregate check"
    assert summary["nbs_generation_twh"] == pytest.approx(839.04)
    assert summary["nbs_year_end_capacity_gw"] == pytest.approx(886.66)
    assert summary["nbs_capacity_growth_pct"] == pytest.approx(45.2)
    assert str(summary["source_url"]).startswith("https://www.stats.gov.cn/")


def test_national_external_validation_compares_against_loss_corrected_model():
    summary = build_summary()
    assert summary["observed_specific_yield_average_capacity_kwh_per_kw"] == pytest.approx(
        1120.73, abs=0.1
    )
    assert summary["loss_corrected_model_csi_yield_kwh_per_kwp"] == pytest.approx(
        1265.40, abs=0.1
    )
    assert 10.0 < summary["bias_vs_average_capacity_pct"] < 20.0
    assert abs(summary["model_capacity_gap_gw"]) < 0.1


def test_national_external_validation_rows_are_machine_readable():
    rows = build_rows()
    metrics = {row["metric"] for row in rows}
    assert "nbs_solar_generation" in metrics
    assert "loss_corrected_model_csi_yield" in metrics
    assert "bias_vs_average_capacity" in metrics
