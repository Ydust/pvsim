import pytest

from scripts.ctgr_spatial_pv_generation_validation import (
    REPORTED_PV_GENERATION_100M_KWH,
    build_layer,
    load_source,
)


def test_ctgr_source_is_exchange_filed_and_spatial():
    rows = load_source()
    assert len(rows) == 25
    assert all(row["source_url"].startswith("https://static.sse.com.cn/") for row in rows)
    assert all(
        row["source_audit_status"] == "row-level official corporate disclosure complete"
        for row in rows
    )
    assert {row["operating_region"] for row in rows} >= {"Inner Mongolia", "Qinghai", "Shandong"}


def test_ctgr_layer_closes_to_annual_report_total():
    layer, summary = build_layer()
    assert len(layer) == 25
    assert all(float(row["pv_generation_twh"]) > 0 for row in layer)
    assert all("PV absolute generation sample" in row["validation_role"] for row in layer)
    assert summary["pv_specific"] == "True"
    assert summary["national_complete_inventory"] == "False"
    assert float(summary["company_pv_generation_100million_kwh"]) == pytest.approx(
        REPORTED_PV_GENERATION_100M_KWH,
        abs=0.01,
    )
    assert float(summary["company_pv_generation_twh"]) == pytest.approx(25.40083)
    assert float(summary["share_of_nbs_national_solar_generation_pct"]) > 3.0
