import pytest

from scripts.nbs_spatial_generation_validation import (
    NATIONAL_TOTAL_100M_KWH,
    build_layer,
    load_source,
)


def test_nbs_spatial_generation_source_is_official_and_complete():
    rows = load_source()
    assert len(rows) == 31
    assert all(row["source_url"].startswith("https://www.stats.gov.cn/") for row in rows)
    assert all(row["source_audit_status"] == "row-level official complete" for row in rows)


def test_nbs_spatial_generation_layer_has_absolute_generation_axis():
    layer, summary = build_layer()
    assert len(layer) == 31
    assert all(float(row["total_power_generation_twh"]) > 0 for row in layer)
    assert all("not PV-specific" in row["validation_role"] for row in layer)
    assert summary["pv_specific"] == "False"
    assert float(summary["province_sum_100million_kwh"]) == pytest.approx(
        NATIONAL_TOTAL_100M_KWH,
        abs=0.5,
    )
