"""Catalogue of mainland China city-level simulation anchors."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CITY_CATALOG = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "source_tables"
    / "china_prefecture_city_anchors.csv"
)


@dataclass(frozen=True)
class CityAnchor:
    adcode: str
    city: str
    city_fullname: str
    province: str
    province_fullname: str
    province_code: str
    admin_type: str
    lat: float
    lon: float
    altitude_m: float | None
    cache_key: str
    coordinate_source: str
    source_version: str
    source_url: str


def _optional_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    return float(value)


def load_city_catalog(path: str | Path = DEFAULT_CITY_CATALOG) -> list[CityAnchor]:
    """Load and validate the city-anchor source table."""
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    anchors = [
        CityAnchor(
            adcode=row["adcode"],
            city=row["city"],
            city_fullname=row["city_fullname"],
            province=row["province"],
            province_fullname=row["province_fullname"],
            province_code=row["province_code"],
            admin_type=row["admin_type"],
            lat=float(row["latitude"]),
            lon=float(row["longitude"]),
            altitude_m=_optional_float(row.get("altitude_m")),
            cache_key=row["cache_key"],
            coordinate_source=row["coordinate_source"],
            source_version=row["source_version"],
            source_url=row["source_url"],
        )
        for row in rows
    ]

    codes = [anchor.adcode for anchor in anchors]
    if len(codes) != len(set(codes)):
        raise ValueError(f"Duplicate city adcodes in {path}")
    if any(not (15.0 <= anchor.lat <= 55.0 and 70.0 <= anchor.lon <= 140.0)
           for anchor in anchors):
        raise ValueError(f"City coordinate outside mainland-China bounds in {path}")
    return anchors


def select_city_anchors(
    anchors: list[CityAnchor],
    province: str | None = None,
    adcodes: set[str] | None = None,
) -> list[CityAnchor]:
    """Filter anchors by province name/code and/or six-digit city code."""
    selected = anchors
    if province:
        selected = [
            anchor for anchor in selected
            if province in {
                anchor.province,
                anchor.province_fullname,
                anchor.province_code,
            }
        ]
    if adcodes:
        selected = [anchor for anchor in selected if anchor.adcode in adcodes]
    return selected
