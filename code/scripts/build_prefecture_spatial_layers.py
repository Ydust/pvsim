"""Build prefecture areal-mean physics and GEM operating-capacity layers.

The full 8,760-hour city-anchor result supplies the absolute physical level.
Within-prefecture variation comes from the ERA5-Land 0.1 degree reduced-order
grid. The reduced grid is bias-corrected at each city anchor before its
latitude-area-weighted mean or plant-location value is calculated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath
from scipy.spatial import cKDTree

from scripts.build_city_catalog import (
    ATLAS_ROOT,
    ATLAS_VERSION,
    MUNICIPALITY_CODES,
    _download_json,
    fetch_documents,
    gcj02_to_wgs84,
)


CATALOG = Path("data/source_tables/china_prefecture_city_anchors.csv")
BOUNDARIES = Path(
    f"data/source_tables/china_prefecture_boundaries_geojsoncn_{ATLAS_VERSION}.geojson"
)
MAP_CONTEXT = Path(
    f"data/source_tables/china_map_context_geojsoncn_{ATLAS_VERSION}.geojson"
)
GRID = Path("outputs/grid_inversion_era5.csv")
CORRECTED_GRID_OUTPUT = Path("outputs/grid_inversion_era5_city_constrained.csv")
CITY_PHYSICS = Path("outputs/city_physics_summary.csv")
AREA_OUTPUT = Path("outputs/prefecture_area_weighted_advantage.csv")
GEM_CITY_OUTPUT = Path("outputs/gem_operating_pv_city_capacity.csv")
GEM_PHASE_OUTPUT = Path("outputs/gem_operating_pv_phase_spatial.csv")
COMPARISON_OUTPUT = Path("outputs/si_area_vs_gem_capacity_weighting.csv")
AUDIT_OUTPUT = Path("outputs/prefecture_spatial_layer_audit.csv")

GEM_FILENAME = (
    "China_Solar_Power_Plants_GEM_202406__0__"
    "China_Solar_Power_Plants_GEM_202406.geojson"
)
GEM_CANDIDATES = (
    Path("data/source_tables") / GEM_FILENAME,
    Path.home() / "new" / "geojson" / GEM_FILENAME,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _transform_ring(ring: list[list[float]]) -> list[list[float]]:
    transformed = []
    for lon_gcj, lat_gcj, *rest in ring:
        lat_wgs, lon_wgs = gcj02_to_wgs84(float(lat_gcj), float(lon_gcj))
        transformed.append([lon_wgs, lat_wgs, *rest])
    return transformed


def _transform_geometry(geometry: dict) -> dict:
    geom_type = geometry["type"]
    coordinates = geometry["coordinates"]
    if geom_type == "Polygon":
        converted = [_transform_ring(ring) for ring in coordinates]
    elif geom_type == "MultiPolygon":
        converted = [
            [_transform_ring(ring) for ring in polygon]
            for polygon in coordinates
        ]
    else:
        raise ValueError(f"Unsupported prefecture geometry: {geom_type}")
    return {"type": geom_type, "coordinates": converted}


def _transform_context_geometry(geometry: dict) -> dict:
    """Convert polygon or line context geometry from GCJ-02 to WGS-84."""
    geom_type = geometry["type"]
    coordinates = geometry["coordinates"]
    if geom_type in {"Polygon", "MultiPolygon"}:
        return _transform_geometry(geometry)
    if geom_type == "LineString":
        converted = _transform_ring(coordinates)
    elif geom_type == "MultiLineString":
        converted = [_transform_ring(line) for line in coordinates]
    else:
        raise ValueError(f"Unsupported map-context geometry: {geom_type}")
    return {"type": geom_type, "coordinates": converted}


def build_map_context(
    output: Path = MAP_CONTEXT,
    national_document: dict | None = None,
) -> Path:
    """Write Taiwan and the national maritime-line feature for map context.

    These features complete the national-map silhouette but remain outside the
    337-prefecture model/statistical domain.
    """
    national = national_document or _download_json(f"{ATLAS_ROOT}/100000.json")
    selected = []
    for feature in national["features"]:
        properties = feature.get("properties", {})
        code = str(properties.get("code") or "")
        geometry_type = feature.get("geometry", {}).get("type")
        if code == "710000":
            role = "taiwan_geographic_context"
        elif geometry_type in {"LineString", "MultiLineString"}:
            role = "south_china_sea_maritime_line"
        else:
            continue
        selected.append({
            "type": "Feature",
            "properties": {
                "role": role,
                "source_name": properties.get("name"),
                "source_fullname": properties.get("fullname"),
                "source_code": code or None,
                "source_url": f"{ATLAS_ROOT}/100000.json",
                "source_version": ATLAS_VERSION,
                "source_crs": "GCJ-02",
                "output_crs": "WGS-84",
                "model_domain": False,
            },
            "geometry": _transform_context_geometry(feature["geometry"]),
        })

    roles = {feature["properties"]["role"] for feature in selected}
    expected = {
        "taiwan_geographic_context",
        "south_china_sea_maritime_line",
    }
    if roles != expected:
        raise RuntimeError(
            f"Expected Taiwan and maritime-line context features, received {sorted(roles)}"
        )
    document = {
        "type": "FeatureCollection",
        "name": "China national-map context outside the 337-prefecture model domain",
        "source": "GeoJSON.CN China atlas",
        "source_version": ATLAS_VERSION,
        "source_crs": "GCJ-02",
        "output_crs": "WGS-84",
        "conversion": "Approximate inverse GCJ-02 transform used by city catalogue",
        "model_domain": False,
        "features": selected,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return output


def build_boundaries(output: Path = BOUNDARIES, workers: int = 8) -> Path:
    """Download the pinned atlas and write the 337 WGS-84 city geometries."""
    catalog = pd.read_csv(CATALOG, encoding="utf-8-sig", dtype={"adcode": str})
    documents = fetch_documents(max(1, workers))
    national = {
        str(feature["properties"]["code"]): feature
        for feature in documents["100000"]["features"]
        if feature.get("properties", {}).get("code") is not None
    }
    features = []
    for row in catalog.itertuples(index=False):
        code = str(row.adcode)
        province_code = str(row.province_code)
        if code in MUNICIPALITY_CODES:
            source_feature = national[code]
            source_url = f"{ATLAS_ROOT}/100000.json"
        else:
            source_feature = next(
                feature
                for feature in documents[province_code]["features"]
                if str(feature["properties"]["code"]) == code
            )
            source_url = f"{ATLAS_ROOT}/{province_code}.json"
        features.append({
            "type": "Feature",
            "properties": {
                "adcode": code,
                "city": row.city,
                "city_fullname": row.city_fullname,
                "province": row.province,
                "province_code": province_code,
                "source_url": source_url,
                "source_version": ATLAS_VERSION,
                "source_crs": "GCJ-02",
                "output_crs": "WGS-84",
            },
            "geometry": _transform_geometry(source_feature["geometry"]),
        })

    document = {
        "type": "FeatureCollection",
        "name": "Mainland China prefecture-level boundaries",
        "source": "GeoJSON.CN China atlas",
        "source_version": ATLAS_VERSION,
        "source_crs": "GCJ-02",
        "output_crs": "WGS-84",
        "conversion": "Approximate inverse GCJ-02 transform used by city catalogue",
        "features": features,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    if len(features) != 337:
        raise RuntimeError(f"Expected 337 boundary features, received {len(features)}")
    return output


def _polygon_parts(geometry: dict) -> list[list[list[list[float]]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError(f"Unsupported geometry: {geometry['type']}")


def _geometry_bbox(geometry: dict) -> tuple[float, float, float, float]:
    points = np.vstack([
        np.asarray(ring, float)[:, :2]
        for polygon in _polygon_parts(geometry)
        for ring in polygon
    ])
    return (
        float(points[:, 0].min()),
        float(points[:, 1].min()),
        float(points[:, 0].max()),
        float(points[:, 1].max()),
    )


def _geometry_contains(geometry: dict, points: np.ndarray) -> np.ndarray:
    """Return point-in-polygon membership, subtracting interior rings."""
    inside = np.zeros(len(points), dtype=bool)
    for polygon in _polygon_parts(geometry):
        polygon_inside = MplPath(np.asarray(polygon[0], float)[:, :2]).contains_points(
            points, radius=1e-10,
        )
        for hole in polygon[1:]:
            polygon_inside &= ~MplPath(
                np.asarray(hole, float)[:, :2]
            ).contains_points(points, radius=1e-10)
        inside |= polygon_inside
    return inside


def load_boundaries(path: Path = BOUNDARIES) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)["features"]


def _nearest_grid_index(
    grid_lon: np.ndarray,
    grid_lat: np.ndarray,
    lon: float,
    lat: float,
) -> int:
    lon_scale = math.cos(math.radians(lat))
    distance = ((grid_lon - lon) * lon_scale) ** 2 + (grid_lat - lat) ** 2
    return int(np.nanargmin(distance))


def _anchor_constrained_grid(
    grid: pd.DataFrame, physics: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Interpolate 337 full-hourly anchor residuals over the reduced grid."""
    scale = math.cos(math.radians(35.0))
    grid_xy = np.column_stack([
        grid["lon"].to_numpy(float) * scale,
        grid["lat"].to_numpy(float),
    ])
    city_xy = np.column_stack([
        physics["lon"].to_numpy(float) * scale,
        physics["lat"].to_numpy(float),
    ])
    grid_tree = cKDTree(grid_xy)
    _, anchor_grid_indices = grid_tree.query(city_xy, k=1)
    anchor_truth = physics["perovskite_advantage_pct"].to_numpy(float)
    anchor_reduced = grid.iloc[np.asarray(anchor_grid_indices, int)]["adv"].to_numpy(float)
    residual = anchor_truth - anchor_reduced

    city_tree = cKDTree(city_xy)
    distance, neighbours = city_tree.query(grid_xy, k=8)
    weights = 1.0 / np.maximum(distance, 0.02) ** 2
    residual_field = np.sum(weights * residual[neighbours], axis=1) / weights.sum(axis=1)
    corrected = grid["adv"].to_numpy(float) + residual_field

    loo_distance, loo_neighbours = city_tree.query(city_xy, k=9)
    loo_distance = loo_distance[:, 1:]
    loo_neighbours = loo_neighbours[:, 1:]
    loo_weights = 1.0 / np.maximum(loo_distance, 0.02) ** 2
    loo_residual = np.sum(
        loo_weights * residual[loo_neighbours], axis=1
    ) / loo_weights.sum(axis=1)
    loo_prediction = anchor_reduced + loo_residual
    error = loo_prediction - anchor_truth
    denominator = float(np.sum((anchor_truth - anchor_truth.mean()) ** 2))
    audit = {
        "city_residual_surface_loo_r2": float(1.0 - np.sum(error ** 2) / denominator),
        "city_residual_surface_loo_rmse_pct_points": float(np.sqrt(np.mean(error ** 2))),
        "city_residual_surface_loo_mae_pct_points": float(np.mean(np.abs(error))),
        "city_residual_surface_neighbours": 8.0,
        "city_residual_surface_power": 2.0,
    }
    return corrected, residual_field, audit


def build_area_layer(
    boundaries: list[dict],
) -> tuple[
    pd.DataFrame,
    dict[str, np.ndarray],
    np.ndarray,
    dict[str, float],
]:
    grid = pd.read_csv(GRID, encoding="utf-8-sig")
    physics_frame = pd.read_csv(
        CITY_PHYSICS, encoding="utf-8-sig", dtype={"adcode": str}
    )
    corrected_adv, residual_field, surface_audit = _anchor_constrained_grid(
        grid, physics_frame
    )
    corrected_grid = grid.copy()
    corrected_grid["city_anchor_residual_field_pct_points"] = residual_field
    corrected_grid["city_constrained_advantage_pct"] = corrected_adv
    corrected_grid.to_csv(CORRECTED_GRID_OUTPUT, index=False, encoding="utf-8-sig")
    physics = physics_frame.set_index("adcode")
    grid_points = grid[["lon", "lat"]].to_numpy(float)
    grid_lon = grid["lon"].to_numpy(float)
    grid_lat = grid["lat"].to_numpy(float)
    rows = []
    cell_indices: dict[str, np.ndarray] = {}

    for feature in boundaries:
        properties = feature["properties"]
        code = str(properties["adcode"])
        city = physics.loc[code]
        min_lon, min_lat, max_lon, max_lat = _geometry_bbox(feature["geometry"])
        candidates = np.where(
            (grid_lon >= min_lon) & (grid_lon <= max_lon)
            & (grid_lat >= min_lat) & (grid_lat <= max_lat)
        )[0]
        if len(candidates):
            selected = candidates[_geometry_contains(
                feature["geometry"], grid_points[candidates]
            )]
        else:
            selected = np.array([], dtype=int)
        cell_indices[code] = selected

        anchor_index = _nearest_grid_index(
            grid_lon, grid_lat, float(city["lon"]), float(city["lat"])
        )
        anchor_full = float(city["perovskite_advantage_pct"])
        grid_anchor = float(grid.iloc[anchor_index]["adv"])
        anchor_surface = float(corrected_adv[anchor_index])
        correction = anchor_full - grid_anchor
        if len(selected):
            weights = np.cos(np.deg2rad(grid_lat[selected]))
            area_adv_reduced = float(np.average(grid.iloc[selected]["adv"], weights=weights))
            area_adv = float(np.average(corrected_adv[selected], weights=weights))
            area_ghi = float(np.average(grid.iloc[selected]["ghi_ann"], weights=weights))
            weight_sum = float(weights.sum())
            method = "337-anchor-constrained 0.1 degree land-cell area mean"
        else:
            area_adv_reduced = grid_anchor
            area_adv = anchor_full
            area_ghi = float(city["ghi_kwh_m2"])
            weight_sum = 0.0
            method = "8760-hour anchor fallback; no land-grid centre in polygon"

        rows.append({
            "adcode": code,
            "city": properties["city"],
            "city_fullname": properties["city_fullname"],
            "province": properties["province"],
            "province_code": properties["province_code"],
            "anchor_lon": float(city["lon"]),
            "anchor_lat": float(city["lat"]),
            "anchor_advantage_8760_pct": anchor_full,
            "grid_anchor_advantage_reduced_pct": grid_anchor,
            "anchor_residual_input_pct_points": correction,
            "anchor_surface_advantage_pct": anchor_surface,
            "anchor_surface_error_pct_points": anchor_surface - anchor_full,
            "area_advantage_reduced_pct": area_adv_reduced,
            "area_weighted_advantage_pct": area_adv,
            "area_weighted_ghi_kwh_m2": area_ghi,
            "land_grid_cell_count": int(len(selected)),
            "land_grid_area_weight_sum": weight_sum,
            "method": method,
        })

    area = pd.DataFrame(rows).sort_values("adcode").reset_index(drop=True)
    AREA_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    area.to_csv(AREA_OUTPUT, index=False, encoding="utf-8-sig")
    return area, cell_indices, corrected_adv, surface_audit


def resolve_gem_path() -> Path:
    env_path = os.environ.get("GEM_SOLAR_GEOJSON")
    candidates = ((Path(env_path),) if env_path else ()) + GEM_CANDIDATES
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(
        "GEM June 2024 China solar GeoJSON not found. Set GEM_SOLAR_GEOJSON. "
        f"Searched:\n{searched}"
    )


def _capacity_ac_equivalent(
    reported_mw: np.ndarray,
    rating: np.ndarray,
) -> tuple[np.ndarray, float, float]:
    known_ac = int(np.sum(rating == "MWac"))
    known_dc = int(np.sum(rating == "MWp/dc"))
    ac_probability = known_ac / max(known_ac + known_dc, 1)
    unknown_factor = 0.87 + 0.13 * ac_probability
    factors = np.where(
        rating == "MWac", 1.0,
        np.where(rating == "MWp/dc", 0.87, unknown_factor),
    )
    return reported_mw * factors, ac_probability, unknown_factor


def _assign_points_to_boundaries(
    boundaries: list[dict], points: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    assignments = np.full(len(points), "", dtype=object)
    methods = np.full(len(points), "unassigned", dtype=object)
    for feature in boundaries:
        min_lon, min_lat, max_lon, max_lat = _geometry_bbox(feature["geometry"])
        candidates = np.where(
            (assignments == "")
            & (points[:, 0] >= min_lon) & (points[:, 0] <= max_lon)
            & (points[:, 1] >= min_lat) & (points[:, 1] <= max_lat)
        )[0]
        if not len(candidates):
            continue
        selected = candidates[_geometry_contains(
            feature["geometry"], points[candidates]
        )]
        assignments[selected] = str(feature["properties"]["adcode"])
        methods[selected] = "point-in-prefecture-polygon"
    return assignments, methods


def build_gem_layers(
    boundaries: list[dict],
    area: pd.DataFrame,
    cell_indices: dict[str, np.ndarray],
    corrected_adv: np.ndarray,
    surface_audit: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float | str]]:
    gem_path = resolve_gem_path()
    with gem_path.open(encoding="utf-8-sig") as stream:
        document = json.load(stream)

    records = []
    for feature in document["features"]:
        props = feature["properties"]
        if str(props.get("Status", "")).strip().lower() != "operating":
            continue
        if str(props.get("Technology_Type", "")).strip() == "Solar Thermal":
            continue
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or [
            props.get("Longitude"), props.get("Latitude")
        ]
        records.append({
            "gem_phase_id": props.get("GEM_phase_ID"),
            "gem_location_id": props.get("GEM_location_ID"),
            "longitude": float(coordinates[0]),
            "latitude": float(coordinates[1]),
            "capacity_reported_mw": float(props.get("Capacity__MW_") or 0.0),
            "capacity_rating": str(props.get("Capacity_Rating") or "unknown"),
            "location_accuracy": str(props.get("Location_accuracy") or "unknown"),
            "technology_type": str(props.get("Technology_Type") or "unknown"),
            "start_year": props.get("Start_year"),
            "date_last_researched": props.get("Date_Last_Researched"),
        })
    phases = pd.DataFrame(records)
    reported = phases["capacity_reported_mw"].to_numpy(float)
    rating = phases["capacity_rating"].to_numpy(str)
    ac_equivalent, ac_probability, unknown_factor = _capacity_ac_equivalent(
        reported, rating
    )
    phases["capacity_ac_equivalent_mw"] = ac_equivalent
    assignments, methods = _assign_points_to_boundaries(
        boundaries, phases[["longitude", "latitude"]].to_numpy(float)
    )
    phases["adcode"] = assignments
    phases["assignment_method"] = methods

    grid = pd.read_csv(GRID, encoding="utf-8-sig")
    area_by_code = area.set_index("adcode")
    phases["plant_location_advantage_pct"] = np.nan
    for code, group in phases[phases["adcode"] != ""].groupby("adcode"):
        selected = cell_indices[str(code)]
        row_indices = group.index.to_numpy(int)
        if not len(selected):
            phases.loc[row_indices, "plant_location_advantage_pct"] = float(
                area_by_code.loc[str(code), "anchor_advantage_8760_pct"]
            )
            continue
        mean_lat = float(grid.iloc[selected]["lat"].mean())
        scale = math.cos(math.radians(mean_lat))
        tree = cKDTree(np.column_stack([
            grid.iloc[selected]["lon"].to_numpy(float) * scale,
            grid.iloc[selected]["lat"].to_numpy(float),
        ]))
        query = np.column_stack([
            group["longitude"].to_numpy(float) * scale,
            group["latitude"].to_numpy(float),
        ])
        _, nearest = tree.query(query, k=1)
        sampled = corrected_adv[selected[np.asarray(nearest, int)]]
        phases.loc[row_indices, "plant_location_advantage_pct"] = sampled

    assigned = phases[phases["adcode"] != ""].copy()
    city_rows = []
    for code, group in assigned.groupby("adcode"):
        weights = group["capacity_ac_equivalent_mw"].to_numpy(float)
        total = float(weights.sum())
        city_rows.append({
            "adcode": str(code),
            "gem_operating_phase_count": int(len(group)),
            "gem_operating_location_count": int(group["gem_location_id"].nunique()),
            "gem_capacity_reported_mw": float(group["capacity_reported_mw"].sum()),
            "gem_capacity_ac_equivalent_mw": total,
            "gem_exact_capacity_ac_equivalent_mw": float(group.loc[
                group["location_accuracy"] == "exact", "capacity_ac_equivalent_mw"
            ].sum()),
            "gem_approx_capacity_ac_equivalent_mw": float(group.loc[
                group["location_accuracy"] == "approximate", "capacity_ac_equivalent_mw"
            ].sum()),
            "gem_capacity_weighted_lon": float(np.average(
                group["longitude"], weights=weights
            )),
            "gem_capacity_weighted_lat": float(np.average(
                group["latitude"], weights=weights
            )),
            "gem_capacity_weighted_advantage_pct": float(np.average(
                group["plant_location_advantage_pct"], weights=weights
            )),
        })
    city_capacity = pd.DataFrame(city_rows)
    city_capacity = area[[
        "adcode", "city", "city_fullname", "province", "province_code"
    ]].merge(city_capacity, on="adcode", how="right", validate="one_to_one")
    comparison = area.merge(city_capacity, on=[
        "adcode", "city", "city_fullname", "province", "province_code"
    ], how="left", validate="one_to_one")
    comparison["gem_minus_area_advantage_pct_points"] = (
        comparison["gem_capacity_weighted_advantage_pct"]
        - comparison["area_weighted_advantage_pct"]
    )

    assigned_capacity = float(assigned["capacity_ac_equivalent_mw"].sum())
    audit: dict[str, float | str] = {
        "gem_source_path": str(gem_path.resolve()),
        "gem_source_sha256": _sha256(gem_path),
        "gem_operating_pv_phase_count": float(len(phases)),
        "gem_reported_capacity_total_gw": float(phases["capacity_reported_mw"].sum() / 1000.0),
        "gem_ac_equivalent_capacity_total_gw": float(phases["capacity_ac_equivalent_mw"].sum() / 1000.0),
        "gem_assigned_phase_count": float(len(assigned)),
        "gem_assigned_ac_equivalent_capacity_gw": assigned_capacity / 1000.0,
        "gem_unassigned_phase_count": float(len(phases) - len(assigned)),
        "gem_unassigned_ac_equivalent_capacity_gw": float(
            phases.loc[phases["adcode"] == "", "capacity_ac_equivalent_mw"].sum() / 1000.0
        ),
        "gem_known_ac_phase_probability": ac_probability,
        "gem_unknown_capacity_ac_factor": unknown_factor,
        "boundary_source": "GeoJSON.CN China atlas",
        "boundary_version": ATLAS_VERSION,
        "boundary_sha256": _sha256(BOUNDARIES),
    }
    audit.update(surface_audit)

    city_capacity.to_csv(GEM_CITY_OUTPUT, index=False, encoding="utf-8-sig")
    phases.to_csv(GEM_PHASE_OUTPUT, index=False, encoding="utf-8-sig")
    comparison.to_csv(COMPARISON_OUTPUT, index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"metric": key, "value": value} for key, value in audit.items()
    ]).to_csv(AUDIT_OUTPUT, index=False, encoding="utf-8-sig")
    return city_capacity, phases, comparison, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-boundaries", action="store_true")
    parser.add_argument("--refresh-map-context", action="store_true")
    parser.add_argument("--map-context-only", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if args.refresh_map_context or args.map_context_only or not MAP_CONTEXT.exists():
        print(f"Downloading GeoJSON.CN {ATLAS_VERSION} national map context...")
        build_map_context(MAP_CONTEXT)
    if args.map_context_only:
        print(f"Wrote {MAP_CONTEXT}")
        return
    if args.refresh_boundaries or not BOUNDARIES.exists():
        print(f"Downloading GeoJSON.CN {ATLAS_VERSION} prefecture boundaries...")
        build_boundaries(BOUNDARIES, workers=max(1, args.workers))
    boundaries = load_boundaries()
    area, cell_indices, corrected_adv, surface_audit = build_area_layer(boundaries)
    city_capacity, phases, comparison, audit = build_gem_layers(
        boundaries, area, cell_indices, corrected_adv, surface_audit
    )

    print(
        f"Built {len(area)} prefecture areal means; "
        f"{len(city_capacity)} cities have assigned GEM capacity."
    )
    print(
        "GEM operating PV: "
        f"{audit['gem_reported_capacity_total_gw']:.3f} GW reported; "
        f"{audit['gem_ac_equivalent_capacity_total_gw']:.3f} GWac-equivalent; "
        f"{audit['gem_unassigned_ac_equivalent_capacity_gw']:.3f} GW unassigned."
    )
    covered = comparison["gem_capacity_ac_equivalent_mw"].notna().sum()
    print(f"SI comparison contains {covered} GEM-covered prefectures.")


if __name__ == "__main__":
    main()
