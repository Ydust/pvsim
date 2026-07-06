import csv

import pytest

from pvsim.source_data import load_capacity_rows
from scripts.validate_government_pv_generation_inventory import (
    NBS_NATIONAL_SOLAR_GENERATION_TWH,
    REQUIRED_COLUMNS,
    validate_inventory,
)


def _write_candidate(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _valid_rows():
    provinces = [row["province"] for row in load_capacity_rows()]
    value = NBS_NATIONAL_SOLAR_GENERATION_TWH / len(provinces)
    return [
        {
            "province": province,
            "year": "2024",
            "metric": "PV generation",
            "generation": f"{value:.9f}",
            "unit": "TWh",
            "coverage": "full fleet",
            "source_name": "Government source",
            "source_url": "https://example.gov/source",
            "source_doc": "Official province PV generation table",
            "retrieved_date": "2026-07-01",
            "source_audit_status": "row-level official complete",
            "source_note": "Official absolute generation row",
        }
        for province in provinces
    ]


def test_missing_candidate_is_not_submission_ready(tmp_path):
    result = validate_inventory(tmp_path / "missing.csv")
    assert not result.exists
    assert not result.submission_ready
    assert result.row_count == 0
    assert len(result.missing_provinces) == 31


def test_valid_official_full_inventory_shape_passes(tmp_path):
    path = tmp_path / "candidate.csv"
    _write_candidate(path, _valid_rows())
    result = validate_inventory(path)
    assert result.submission_ready
    assert result.row_count == 31
    assert result.total_generation_twh == pytest.approx(NBS_NATIONAL_SOLAR_GENERATION_TWH)


def test_proxy_or_partial_inventory_is_rejected(tmp_path):
    rows = _valid_rows()
    rows[0]["coverage"] = "above-designated-size industry"
    rows[1]["source_note"] = "Derived from capacity times fleet hours"
    path = tmp_path / "candidate.csv"
    _write_candidate(path, rows)
    result = validate_inventory(path)
    assert not result.submission_ready
    assert result.non_full_coverage_rows == 1
    assert result.derived_or_proxy_rows == 1
