"""Versioned paper source-table loaders."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_TABLE_DIR = ROOT / "data" / "source_tables"
CAPACITY_TABLE = SOURCE_TABLE_DIR / "provincial_pv_capacity_2024.csv"
FLEET_HOURS_TABLE = SOURCE_TABLE_DIR / "provincial_fleet_hours_2024.csv"
PV_UTILIZATION_TABLE = SOURCE_TABLE_DIR / "nea_pv_utilization_rate_2024.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_fleet_hours(path: Path = FLEET_HOURS_TABLE) -> dict[str, float]:
    rows = _read_csv(path)
    hours: dict[str, float] = {}
    for row in rows:
        province = row["province"].strip()
        if province in hours:
            raise ValueError(f"Duplicate province in fleet-hour table: {province}")
        hours[province] = float(row["fleet_hours"])
    if len(hours) != 31:
        raise ValueError(f"Expected 31 provinces in fleet-hour table, got {len(hours)}")
    return hours


def load_capacity_rows(path: Path = CAPACITY_TABLE) -> list[dict[str, str]]:
    rows = _read_csv(path)
    if len(rows) != 31:
        raise ValueError(f"Expected 31 provinces in capacity table, got {len(rows)}")
    provinces = [row["province"].strip() for row in rows]
    if len(set(provinces)) != len(provinces):
        raise ValueError("Duplicate province in capacity table")
    return rows


def load_fleet_hour_rows(path: Path = FLEET_HOURS_TABLE) -> list[dict[str, str]]:
    rows = _read_csv(path)
    if len(rows) != 31:
        raise ValueError(f"Expected 31 provinces in fleet-hour table, got {len(rows)}")
    provinces = [row["province"].strip() for row in rows]
    if len(set(provinces)) != len(provinces):
        raise ValueError("Duplicate province in fleet-hour table")
    return rows


def load_pv_utilization_rows(path: Path = PV_UTILIZATION_TABLE) -> list[dict[str, str]]:
    rows = _read_csv(path)
    if len(rows) < 32:
        raise ValueError(f"Expected national plus provincial PV utilization rows, got {len(rows)}")
    return rows


def load_pv_utilization_province_rows(
    path: Path = PV_UTILIZATION_TABLE,
) -> list[dict[str, str]]:
    rows = [
        row
        for row in load_pv_utilization_rows(path)
        if "national" not in row["source_note"].strip().lower()
    ]
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["province"].strip(), []).append(row)
    out: list[dict[str, str]] = []
    for province, province_rows in grouped.items():
        first = province_rows[0]
        rate_2023 = sum(float(row["pv_utilization_rate_pct_2023"]) for row in province_rows) / len(province_rows)
        rate_2024 = sum(float(row["pv_utilization_rate_pct_2024"]) for row in province_rows) / len(province_rows)
        out.append(
            {
                **first,
                "reporting_region": "; ".join(row["reporting_region"] for row in province_rows),
                "reporting_region_count": str(len(province_rows)),
                "pv_utilization_rate_pct_2023": f"{rate_2023:.1f}",
                "pv_utilization_rate_pct_2024": f"{rate_2024:.1f}",
            }
        )
    if len(out) != 31:
        raise ValueError(f"Expected 31 provinces in PV utilization table, got {len(out)}")
    return sorted(out, key=lambda row: row["province"])
