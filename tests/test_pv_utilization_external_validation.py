import pytest

from scripts.pv_utilization_external_validation import build_validation, load_source, province_layer


def test_pv_utilization_source_is_official_and_spatial():
    source = load_source()
    assert "全国" in set(source["province"])
    assert "西藏" in set(source["province"])
    assert all(source["source_url"].str.startswith("https://www.nea.gov.cn/"))
    assert all(source["source_audit_status"] == "row-level official complete")


def test_pv_utilization_layer_covers_provinces_after_region_aggregation():
    layer = province_layer()
    assert len(layer) == 31
    inner_mongolia = layer[layer["province"] == "内蒙古"].iloc[0]
    assert inner_mongolia["reporting_region_count"] == 2
    assert inner_mongolia["pv_utilization_rate_pct_2024"] == pytest.approx(95.5)
    tibet = layer[layer["province"] == "西藏"].iloc[0]
    assert tibet["pv_utilization_rate_pct_2024"] == pytest.approx(68.6)


def test_pv_utilization_validation_summary():
    layer, summary = build_validation()
    row = summary.iloc[0]
    assert len(layer) == 31
    assert row["national_rate_2024_pct"] == pytest.approx(96.8)
    assert row["lowest_region"] == "西藏"
    assert row["min_rate_2024_pct"] == pytest.approx(68.6)
