"""Build the versioned mainland-China city-anchor catalogue.

Scope: 333 prefecture-level administrative units plus the four municipalities.
County-level direct-admin units and non-city development zones are excluded.

Source: GeoJSON.CN China atlas, version pinned below. The catalogue stores only
administrative names, codes and published centre coordinates, not boundaries.
"""

from __future__ import annotations

from pvsim.labels import label as _text_label

import argparse
import csv
import json
import math
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pvsim.provinces import PROVINCES


ATLAS_VERSION = "1.6.3"
ATLAS_ROOT = f"https://geojson.cn/api/china/{ATLAS_VERSION}"
DEFAULT_OUTPUT = Path("data/source_tables/china_prefecture_city_anchors.csv")
PROVINCE_CODES = (
    "110000", "120000", "130000", "140000", "150000",
    "210000", "220000", "230000", "310000", "320000",
    "330000", "340000", "350000", "360000", "370000",
    "410000", "420000", "430000", "440000", "450000",
    "460000", "500000", "510000", "520000", "530000",
    "540000", "610000", "620000", "630000", "640000",
    "650000",
)
MUNICIPALITY_CODES = {"110000", "120000", "310000", "500000"}
EXCLUDED_LEVEL2_CODES = {"133100"}  # Xiong'an New Area is not a prefecture.
FIELDNAMES = (
    "adcode", "city", "city_fullname", "province", "province_fullname",
    "province_code", "admin_type", "latitude", "longitude", "altitude_m",
    "source_latitude", "source_longitude", "source_crs", "cache_key",
    "coordinate_source", "source_version", "source_url",
)

_PI = math.pi
_A = 6378245.0
_EE = 0.00669342162296594323


def _download_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "pvsim/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _transform_latitude(lon: float, lat: float) -> float:
    value = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat
    value += 0.1 * lon * lat + 0.2 * math.sqrt(abs(lon))
    value += (20.0 * math.sin(6.0 * lon * _PI)
              + 20.0 * math.sin(2.0 * lon * _PI)) * 2.0 / 3.0
    value += (20.0 * math.sin(lat * _PI)
              + 40.0 * math.sin(lat / 3.0 * _PI)) * 2.0 / 3.0
    value += (160.0 * math.sin(lat / 12.0 * _PI)
              + 320.0 * math.sin(lat * _PI / 30.0)) * 2.0 / 3.0
    return value


def _transform_longitude(lon: float, lat: float) -> float:
    value = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon
    value += 0.1 * lon * lat + 0.1 * math.sqrt(abs(lon))
    value += (20.0 * math.sin(6.0 * lon * _PI)
              + 20.0 * math.sin(2.0 * lon * _PI)) * 2.0 / 3.0
    value += (20.0 * math.sin(lon * _PI)
              + 40.0 * math.sin(lon / 3.0 * _PI)) * 2.0 / 3.0
    value += (150.0 * math.sin(lon / 12.0 * _PI)
              + 300.0 * math.sin(lon / 30.0 * _PI)) * 2.0 / 3.0
    return value


def gcj02_to_wgs84(lat_gcj: float, lon_gcj: float) -> tuple[float, float]:
    """Approximate inverse of China's GCJ-02 offset for PVGIS WGS-84 input."""
    delta_lat = _transform_latitude(lon_gcj - 105.0, lat_gcj - 35.0)
    delta_lon = _transform_longitude(lon_gcj - 105.0, lat_gcj - 35.0)
    rad_lat = lat_gcj / 180.0 * _PI
    magic = math.sin(rad_lat)
    magic = 1.0 - _EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    delta_lat = (
        delta_lat * 180.0
        / ((_A * (1.0 - _EE)) / (magic * sqrt_magic) * _PI)
    )
    delta_lon = (
        delta_lon * 180.0
        / (_A / sqrt_magic * math.cos(rad_lat) * _PI)
    )
    return lat_gcj * 2.0 - (lat_gcj + delta_lat), lon_gcj * 2.0 - (lon_gcj + delta_lon)


def _admin_type(fullname: str, municipality: bool = False) -> str:
    if municipality:
        return "municipality"
    if fullname.endswith(_text_label('build_city_catalog_text')):
        return "autonomous_prefecture"
    if fullname.endswith(_text_label('build_city_catalog_text_2')):
        return "prefecture"
    if fullname.endswith(_text_label('build_city_catalog_text_3')):
        return "league"
    return "prefecture_level_city"


def _known_anchor_overrides() -> dict[tuple[str, str], object]:
    return {(province.name, province.city): province for province in PROVINCES}


def build_rows(documents: dict[str, dict]) -> list[dict]:
    national = documents["100000"]
    province_properties = {
        feature["properties"]["code"]: feature["properties"]
        for feature in national["features"]
        if feature["properties"].get("code") in PROVINCE_CODES
    }
    overrides = _known_anchor_overrides()
    rows = []

    for province_code in PROVINCE_CODES:
        province_props = province_properties[province_code]
        province = province_props["name"]
        province_fullname = province_props.get("fullname", province)
        source_url = f"{ATLAS_ROOT}/{province_code}.json"

        if province_code in MUNICIPALITY_CODES:
            city_properties = [province_props]
        else:
            city_properties = [
                feature["properties"]
                for feature in documents[province_code]["features"]
                if str(feature["properties"]["code"]).endswith("00")
                and str(feature["properties"]["code"])
                not in EXCLUDED_LEVEL2_CODES
            ]

        for city_props in city_properties:
            adcode = str(city_props["code"])
            city = city_props["name"]
            city_fullname = city_props.get("fullname", city)
            source_lon, source_lat = map(float, city_props["center"])
            lat, lon = gcj02_to_wgs84(source_lat, source_lon)
            altitude = ""
            cache_key = f"city_{adcode}"
            coordinate_source = "GeoJSON.CN GCJ-02 centre converted to WGS-84"

            known = overrides.get((province, city))
            if known is not None:
                lat, lon = known.lat, known.lon
                altitude = known.alt
                cache_key = known.key
                coordinate_source = "existing pvsim representative-city anchor"

            rows.append({
                "adcode": adcode,
                "city": city,
                "city_fullname": city_fullname,
                "province": province,
                "province_fullname": province_fullname,
                "province_code": province_code,
                "admin_type": _admin_type(
                    city_fullname, province_code in MUNICIPALITY_CODES,
                ),
                "latitude": f"{lat:.6f}",
                "longitude": f"{lon:.6f}",
                "altitude_m": altitude,
                "source_latitude": f"{source_lat:.6f}",
                "source_longitude": f"{source_lon:.6f}",
                "source_crs": "GCJ-02",
                "cache_key": cache_key,
                "coordinate_source": coordinate_source,
                "source_version": ATLAS_VERSION,
                "source_url": source_url,
            })

    rows.sort(key=lambda row: row["adcode"])
    if len(rows) != 337:
        raise RuntimeError(f"Expected 337 city anchors, received {len(rows)}")
    if len({row["adcode"] for row in rows}) != len(rows):
        raise RuntimeError("Duplicate administrative codes in city catalogue")
    return rows


def fetch_documents(workers: int = 8) -> dict[str, dict]:
    codes = ("100000",) + PROVINCE_CODES

    def fetch(code: str) -> tuple[str, dict]:
        return code, _download_json(f"{ATLAS_ROOT}/{code}.json")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return dict(executor.map(fetch, codes))


def write_catalog(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    rows = build_rows(fetch_documents(max(1, args.workers)))
    write_catalog(rows, args.output)
    print(f"Wrote {len(rows)} city anchors to {args.output}")


if __name__ == "__main__":
    main()
