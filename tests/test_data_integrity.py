import pytest

from pvsim.provinces import (
    NATIONAL_PV_2024_GW,
    PROVINCES,
    PROVINCE_PV_2024_GW,
    RAW_PROVINCE_PV_2024_GW,
)
from pvsim.source_data import load_capacity_rows, load_fleet_hours, load_fleet_hour_rows


PROVENANCE_FIELDS = (
    "source_name",
    "source_url",
    "source_doc",
    "retrieved_date",
    "source_audit_status",
    "source_note",
)


def _assert_provenance_fields(rows):
    for row in rows:
        for field in PROVENANCE_FIELDS:
            assert row[field].strip(), f"Missing {field} for {row['province']}"


def test_province_capacity_closes_to_national_total():
    assert sum(RAW_PROVINCE_PV_2024_GW.values()) == pytest.approx(885.673)
    assert sum(PROVINCE_PV_2024_GW.values()) == pytest.approx(NATIONAL_PV_2024_GW)


def test_capacity_table_covers_all_provinces():
    expected = {p.name for p in PROVINCES}
    assert set(PROVINCE_PV_2024_GW) == expected


def test_capacity_source_table_matches_model_input():
    rows = load_capacity_rows()
    assert sum(float(r["raw_gw"]) for r in rows) == pytest.approx(885.673)
    assert sum(float(r["scaled_to_national_gw"]) for r in rows) == pytest.approx(
        NATIONAL_PV_2024_GW, abs=0.002
    )
    for row in rows:
        province = row["province"]
        assert float(row["raw_gw"]) == pytest.approx(RAW_PROVINCE_PV_2024_GW[province])
        assert float(row["scaled_to_national_gw"]) == pytest.approx(
            PROVINCE_PV_2024_GW[province], abs=0.001
        )


def test_capacity_source_table_has_provenance_fields():
    rows = load_capacity_rows()
    _assert_provenance_fields(rows)


def test_fleet_hour_source_table_covers_all_provinces():
    expected = {p.name for p in PROVINCES}
    fleet_hours = load_fleet_hours()
    assert set(fleet_hours) == expected
    assert all(800 <= hours <= 1900 for hours in fleet_hours.values())


def test_fleet_hour_source_table_has_provenance_fields():
    rows = load_fleet_hour_rows()
    _assert_provenance_fields(rows)
