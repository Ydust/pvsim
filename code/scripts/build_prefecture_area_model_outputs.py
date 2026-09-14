"""Build one prefecture-area aggregation layer for all five main figures.

The 337 full-hourly PVGIS city simulations remain the high-fidelity anchors.
ERA5-Land 0.1-degree land cells provide the within-prefecture integration
grid. Smooth anchor fields use a GHI-latitude-longitude trend plus an
eight-neighbour inverse-distance-squared residual surface. GHI and the
perovskite advantage retain their existing reduced-order physical baselines.
"""

from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from scripts.build_prefecture_spatial_layers import (
    GRID,
    CORRECTED_GRID_OUTPUT,
    _geometry_bbox,
    _geometry_contains,
    load_boundaries,
)
from scripts.run_all_cities import TECHS, build_city_lcoe
from scripts.mechanism_shapley import (
    FULL_MASK,
    factorial_suffix,
    shapley_components,
)


ANCHOR_SUMMARY = Path("outputs/city_physics_summary.csv")
ANCHOR_LONG = Path("outputs/city_physics_yield.csv")
ANCHOR_MECHANISMS = Path("outputs/city_mechanism_attribution.csv")
ANCHOR_MONTHLY = Path("outputs/city_monthly_mechanism_fingerprint.csv")

AREA_SUMMARY = Path("outputs/prefecture_area_weighted_physics_summary.csv")
AREA_LONG = Path("outputs/prefecture_area_weighted_physics_yield.csv")
AREA_MECHANISMS = Path("outputs/prefecture_area_weighted_mechanisms.csv")
AREA_MONTHLY = Path("outputs/prefecture_area_weighted_monthly_mechanisms.csv")
AREA_LCOE = Path("outputs/prefecture_area_weighted_lcoe.csv")
AREA_PROVINCE = Path("outputs/prefecture_area_weighted_province_summary.csv")
AREA_AUDIT = Path("outputs/prefecture_area_aggregation_audit.csv")
ANCHOR_COMPARISON = Path("outputs/si_anchor_vs_area_weighting.csv")
ANCHOR_COMPARISON_SUMMARY = Path(
    "outputs/si_anchor_vs_area_weighting_summary.csv"
)

NEIGHBOURS = 8
DISTANCE_FLOOR = 0.02
LON_SCALE = math.cos(math.radians(35.0))


def _metric_audit(
    metric: str,
    truth: np.ndarray,
    prediction: np.ndarray,
    unit: str,
    estimator: str,
) -> dict[str, float | str | int]:
    truth = np.asarray(truth, float)
    prediction = np.asarray(prediction, float)
    error = prediction - truth
    denominator = float(np.sum((truth - truth.mean()) ** 2))
    r2 = float("nan") if denominator == 0 else float(
        1.0 - np.sum(error ** 2) / denominator
    )
    return {
        "metric": metric,
        "unit": unit,
        "estimator": estimator,
        "anchor_count": int(len(truth)),
        "loo_r2": r2,
        "loo_rmse": float(np.sqrt(np.mean(error ** 2))),
        "loo_mae": float(np.mean(np.abs(error))),
        "anchor_min": float(np.min(truth)),
        "anchor_max": float(np.max(truth)),
        "prediction_min": float(np.min(prediction)),
        "prediction_max": float(np.max(prediction)),
    }


def _spatial_index(
    grid: pd.DataFrame,
    anchors: pd.DataFrame,
) -> dict[str, np.ndarray | cKDTree]:
    grid_xy = np.column_stack([
        grid["lon"].to_numpy(float) * LON_SCALE,
        grid["lat"].to_numpy(float),
    ])
    city_xy = np.column_stack([
        anchors["lon"].to_numpy(float) * LON_SCALE,
        anchors["lat"].to_numpy(float),
    ])
    grid_tree = cKDTree(grid_xy)
    _, anchor_grid_indices = grid_tree.query(city_xy, k=1)
    city_tree = cKDTree(city_xy)
    distance, neighbours = city_tree.query(grid_xy, k=NEIGHBOURS)
    weights = 1.0 / np.maximum(distance, DISTANCE_FLOOR) ** 2
    loo_distance, loo_neighbours = city_tree.query(
        city_xy, k=NEIGHBOURS + 1
    )
    loo_distance = loo_distance[:, 1:]
    loo_neighbours = loo_neighbours[:, 1:]
    loo_weights = 1.0 / np.maximum(loo_distance, DISTANCE_FLOOR) ** 2
    return {
        "grid_xy": grid_xy,
        "city_xy": city_xy,
        "anchor_grid_indices": np.asarray(anchor_grid_indices, int),
        "neighbours": np.asarray(neighbours, int),
        "weights": weights,
        "loo_neighbours": np.asarray(loo_neighbours, int),
        "loo_weights": loo_weights,
    }


def _baseline_residual_field(
    base_grid: np.ndarray,
    anchor_truth: np.ndarray,
    spatial: dict[str, np.ndarray | cKDTree],
) -> tuple[np.ndarray, np.ndarray]:
    anchor_indices = np.asarray(spatial["anchor_grid_indices"], int)
    neighbours = np.asarray(spatial["neighbours"], int)
    weights = np.asarray(spatial["weights"], float)
    loo_neighbours = np.asarray(spatial["loo_neighbours"], int)
    loo_weights = np.asarray(spatial["loo_weights"], float)
    anchor_base = np.asarray(base_grid, float)[anchor_indices]
    residual = np.asarray(anchor_truth, float) - anchor_base
    field = np.asarray(base_grid, float) + (
        weights * residual[neighbours]
    ).sum(axis=1) / weights.sum(axis=1)
    loo_prediction = anchor_base + (
        loo_weights * residual[loo_neighbours]
    ).sum(axis=1) / loo_weights.sum(axis=1)
    return field, loo_prediction


def _trend_residual_field(
    anchor_truth: np.ndarray,
    anchor_features: np.ndarray,
    grid_features: np.ndarray,
    spatial: dict[str, np.ndarray | cKDTree],
) -> tuple[np.ndarray, np.ndarray]:
    truth = np.asarray(anchor_truth, float)
    neighbours = np.asarray(spatial["neighbours"], int)
    weights = np.asarray(spatial["weights"], float)
    loo_neighbours = np.asarray(spatial["loo_neighbours"], int)
    loo_weights = np.asarray(spatial["loo_weights"], float)

    beta = np.linalg.lstsq(anchor_features, truth, rcond=None)[0]
    residual = truth - anchor_features @ beta
    field = grid_features @ beta + (
        weights * residual[neighbours]
    ).sum(axis=1) / weights.sum(axis=1)

    loo_prediction = np.empty(len(truth), dtype=float)
    all_indices = np.arange(len(truth))
    for index in range(len(truth)):
        train = all_indices != index
        beta_i = np.linalg.lstsq(
            anchor_features[train], truth[train], rcond=None
        )[0]
        local = loo_neighbours[index]
        local_residual = truth[local] - anchor_features[local] @ beta_i
        loo_prediction[index] = (
            anchor_features[index] @ beta_i
            + np.average(local_residual, weights=loo_weights[index])
        )
    return field, loo_prediction


def _trend_residual_field_only(
    anchor_truth: np.ndarray,
    anchor_features: np.ndarray,
    grid_features: np.ndarray,
    spatial: dict[str, np.ndarray | cKDTree],
) -> np.ndarray:
    """Build a trend-plus-residual field without expensive LOO diagnostics."""
    truth = np.asarray(anchor_truth, float)
    neighbours = np.asarray(spatial["neighbours"], int)
    weights = np.asarray(spatial["weights"], float)
    beta = np.linalg.lstsq(anchor_features, truth, rcond=None)[0]
    residual = truth - anchor_features @ beta
    return grid_features @ beta + (
        weights * residual[neighbours]
    ).sum(axis=1) / weights.sum(axis=1)


def _cell_index(
    grid: pd.DataFrame,
    boundaries: list[dict],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    points = grid[["lon", "lat"]].to_numpy(float)
    lon = grid["lon"].to_numpy(float)
    lat = grid["lat"].to_numpy(float)
    indices: dict[str, np.ndarray] = {}
    weights: dict[str, np.ndarray] = {}
    for feature in boundaries:
        code = str(feature["properties"]["adcode"])
        min_lon, min_lat, max_lon, max_lat = _geometry_bbox(
            feature["geometry"]
        )
        candidates = np.where(
            (lon >= min_lon)
            & (lon <= max_lon)
            & (lat >= min_lat)
            & (lat <= max_lat)
        )[0]
        selected = (
            candidates[_geometry_contains(feature["geometry"], points[candidates])]
            if len(candidates)
            else np.array([], dtype=int)
        )
        indices[code] = selected
        weights[code] = np.cos(np.deg2rad(lat[selected]))
    return indices, weights


def _aggregate(
    field: np.ndarray,
    anchors: pd.DataFrame,
    cell_indices: dict[str, np.ndarray],
    area_weights: dict[str, np.ndarray],
    fallback: np.ndarray,
    local_weight: np.ndarray | None = None,
) -> np.ndarray:
    result = np.empty(len(anchors), dtype=float)
    for position, code in enumerate(anchors["adcode"]):
        selected = cell_indices[str(code)]
        if not len(selected):
            result[position] = float(fallback[position])
            continue
        weights = area_weights[str(code)]
        if local_weight is not None:
            weights = weights * np.maximum(local_weight[selected], 1e-9)
        result[position] = float(np.average(field[selected], weights=weights))
    return result


def _weighted_quantile(
    values: np.ndarray,
    weights: np.ndarray,
    quantile: float,
) -> float:
    order = np.argsort(values)
    values = np.asarray(values, float)[order]
    weights = np.asarray(weights, float)[order]
    cumulative = np.cumsum(weights) - 0.5 * weights
    cumulative /= weights.sum()
    return float(np.interp(quantile, cumulative, values))


def _build_province_summary(
    area_long: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for keys, group in area_long.groupby(
        ["province_code", "province", "tech", "code"], sort=True
    ):
        province_code, province, tech, code = keys
        weights = group["land_grid_area_weight_sum"].to_numpy(float)
        if weights.sum() <= 0:
            weights = np.ones(len(group), dtype=float)
        rows.append({
            "province_code": province_code,
            "province": province,
            "tech": tech,
            "code": code,
            "prefecture_count": int(group["adcode"].nunique()),
            "mean_yield_kwh_per_kwp": float(np.average(
                group["yield_kwh_per_kwp"], weights=weights
            )),
            "median_yield_kwh_per_kwp": _weighted_quantile(
                group["yield_kwh_per_kwp"].to_numpy(float), weights, 0.5
            ),
            "min_yield_kwh_per_kwp": float(group["yield_kwh_per_kwp"].min()),
            "max_yield_kwh_per_kwp": float(group["yield_kwh_per_kwp"].max()),
            "mean_yield_kwh_per_m2": float(np.average(
                group["yield_kwh_per_m2"], weights=weights
            )),
            "mean_PR": float(np.average(group["PR"], weights=weights)),
            "mean_tcell_weighted": float(np.average(
                group["tcell_weighted"], weights=weights
            )),
            "mean_spectral_factor": float(np.average(
                group["spectral_factor_w"], weights=weights
            )),
            "mean_ghi_kwh_m2": float(np.average(
                group["ghi_kwh_m2"], weights=weights
            )),
            "land_grid_area_weight_sum": float(weights.sum()),
            "aggregation_method": (
                "land-area-weighted mean of prefecture areal surfaces"
            ),
        })
    return pd.DataFrame(rows).sort_values(
        ["province_code", "code"]
    ).reset_index(drop=True)


def main() -> int:
    grid = pd.read_csv(GRID, encoding="utf-8-sig")
    anchors = pd.read_csv(
        ANCHOR_SUMMARY, encoding="utf-8-sig", dtype={"adcode": str}
    ).sort_values("adcode").reset_index(drop=True)
    anchor_long = pd.read_csv(
        ANCHOR_LONG, encoding="utf-8-sig", dtype={"adcode": str}
    )
    mechanisms = pd.read_csv(
        ANCHOR_MECHANISMS, encoding="utf-8-sig", dtype={"adcode": str}
    ).set_index("adcode").loc[anchors["adcode"]].reset_index()
    boundaries = load_boundaries()
    spatial = _spatial_index(grid, anchors)
    cell_indices, area_weights = _cell_index(grid, boundaries)
    audits: list[dict[str, float | str | int]] = []

    ghi_field, ghi_loo = _baseline_residual_field(
        grid["ghi_ann"].to_numpy(float),
        anchors["ghi_kwh_m2"].to_numpy(float),
        spatial,
    )
    advantage_field, advantage_loo = _baseline_residual_field(
        grid["adv"].to_numpy(float),
        anchors["perovskite_advantage_pct"].to_numpy(float),
        spatial,
    )
    audits.append(_metric_audit(
        "ghi_kwh_m2", anchors["ghi_kwh_m2"], ghi_loo,
        "kWh m-2 yr-1", "ERA5 baseline plus anchor residual IDW",
    ))
    audits.append(_metric_audit(
        "perovskite_advantage_pct",
        anchors["perovskite_advantage_pct"], advantage_loo,
        "percentage points", "reduced-order baseline plus anchor residual IDW",
    ))

    corrected_grid = grid.copy()
    corrected_grid["city_constrained_ghi_kwh_m2"] = ghi_field
    corrected_grid["city_constrained_advantage_pct"] = advantage_field
    corrected_grid.to_csv(
        CORRECTED_GRID_OUTPUT, index=False, encoding="utf-8-sig"
    )

    anchor_grid_indices = np.asarray(spatial["anchor_grid_indices"], int)
    grid_features = np.column_stack([
        np.ones(len(grid)),
        ghi_field / 1000.0,
        grid["lat"].to_numpy(float) / 40.0,
        grid["lon"].to_numpy(float) / 110.0,
    ])
    anchor_features = np.column_stack([
        np.ones(len(anchors)),
        ghi_field[anchor_grid_indices] / 1000.0,
        anchors["lat"].to_numpy(float) / 40.0,
        anchors["lon"].to_numpy(float) / 110.0,
    ])

    field_cache: dict[str, np.ndarray] = {
        "ghi_kwh_m2": ghi_field,
        "perovskite_advantage_pct": advantage_field,
    }
    loo_cache: dict[str, np.ndarray] = {
        "ghi_kwh_m2": ghi_loo,
        "perovskite_advantage_pct": advantage_loo,
    }

    annual_targets = {
        "tair_mean": (anchors["tair_mean"].to_numpy(float), "deg C"),
        "csi_yield_kwh_per_kwp": (
            anchors["csi_yield_kwh_per_kwp"].to_numpy(float), "kWh kWp-1"
        ),
        "tandem_advantage_pct": (
            anchors["tandem_advantage_pct"].to_numpy(float),
            "percentage points",
        ),
        "csi_PR": (anchors["csi_PR"].to_numpy(float), "ratio"),
        "perovskite_PR": (
            anchors["perovskite_PR"].to_numpy(float), "ratio"
        ),
        "tandem_PR": (anchors["tandem_PR"].to_numpy(float), "ratio"),
    }
    for metric, (truth, unit) in annual_targets.items():
        field, loo = _trend_residual_field(
            truth, anchor_features, grid_features, spatial
        )
        field_cache[metric] = field
        loo_cache[metric] = loo
        audits.append(_metric_audit(
            metric, truth, loo, unit,
            "GHI-latitude-longitude trend plus anchor residual IDW",
        ))

    csi_field = np.maximum(field_cache["csi_yield_kwh_per_kwp"], 1.0)
    perovskite_field = csi_field * (1.0 + advantage_field / 100.0)
    tandem_field = csi_field * (
        1.0 + field_cache["tandem_advantage_pct"] / 100.0
    )
    field_cache["csi_yield_kwh_per_kwp"] = csi_field
    field_cache["perovskite_yield_kwh_per_kwp"] = perovskite_field
    field_cache["tandem_yield_kwh_per_kwp"] = tandem_field

    perovskite_loo = loo_cache["csi_yield_kwh_per_kwp"] * (
        1.0 + advantage_loo / 100.0
    )
    tandem_loo = loo_cache["csi_yield_kwh_per_kwp"] * (
        1.0 + loo_cache["tandem_advantage_pct"] / 100.0
    )
    audits.append(_metric_audit(
        "perovskite_yield_kwh_per_kwp",
        anchors["perovskite_yield_kwh_per_kwp"], perovskite_loo,
        "kWh kWp-1", "derived from cross-validated c-Si yield and advantage",
    ))
    audits.append(_metric_audit(
        "tandem_yield_kwh_per_kwp",
        anchors["tandem_yield_kwh_per_kwp"], tandem_loo,
        "kWh kWp-1", "derived from cross-validated c-Si yield and advantage",
    ))

    long_fields: dict[tuple[str, str], np.ndarray] = {}
    for code in ("c-Si", "perovskite", "tandem"):
        tech_rows = anchor_long[anchor_long["code"] == code].set_index("adcode")
        tech_rows = tech_rows.loc[anchors["adcode"]]
        for metric, unit in (
            ("tcell_weighted", "deg C"),
            ("spectral_factor_w", "ratio"),
        ):
            truth = tech_rows[metric].to_numpy(float)
            field, loo = _trend_residual_field(
                truth, anchor_features, grid_features, spatial
            )
            long_fields[(code, metric)] = field
            audits.append(_metric_audit(
                f"{code}_{metric}", truth, loo, unit,
                "GHI-latitude-longitude trend plus anchor residual IDW",
            ))

    area_aggregates: dict[str, np.ndarray] = {}
    aggregate_targets = {
        "ghi_kwh_m2": anchors["ghi_kwh_m2"].to_numpy(float),
        "tair_mean": anchors["tair_mean"].to_numpy(float),
        "csi_yield_kwh_per_kwp": anchors["csi_yield_kwh_per_kwp"].to_numpy(float),
        "perovskite_yield_kwh_per_kwp": anchors[
            "perovskite_yield_kwh_per_kwp"
        ].to_numpy(float),
        "tandem_yield_kwh_per_kwp": anchors[
            "tandem_yield_kwh_per_kwp"
        ].to_numpy(float),
        "csi_PR": anchors["csi_PR"].to_numpy(float),
        "perovskite_PR": anchors["perovskite_PR"].to_numpy(float),
        "tandem_PR": anchors["tandem_PR"].to_numpy(float),
    }
    for metric, fallback in aggregate_targets.items():
        area_aggregates[metric] = _aggregate(
            field_cache[metric], anchors, cell_indices, area_weights, fallback
        )

    area_centroid_lon = _aggregate(
        grid["lon"].to_numpy(float), anchors, cell_indices, area_weights,
        anchors["lon"].to_numpy(float),
    )
    area_centroid_lat = _aggregate(
        grid["lat"].to_numpy(float), anchors, cell_indices, area_weights,
        anchors["lat"].to_numpy(float),
    )
    cell_counts = np.array([
        len(cell_indices[str(code)]) for code in anchors["adcode"]
    ], dtype=int)
    area_weight_sums = np.array([
        area_weights[str(code)].sum() for code in anchors["adcode"]
    ], dtype=float)

    summary = anchors[[
        "adcode", "city", "city_fullname", "province", "province_fullname",
        "province_code", "admin_type", "altitude_m",
    ]].copy()
    summary["lat"] = area_centroid_lat
    summary["lon"] = area_centroid_lon
    summary["anchor_lat"] = anchors["lat"].to_numpy(float)
    summary["anchor_lon"] = anchors["lon"].to_numpy(float)
    for metric, values in area_aggregates.items():
        summary[metric] = values
    summary["perovskite_advantage_pct"] = (
        summary["perovskite_yield_kwh_per_kwp"]
        / summary["csi_yield_kwh_per_kwp"] - 1.0
    ) * 100.0
    summary["tandem_advantage_pct"] = (
        summary["tandem_yield_kwh_per_kwp"]
        / summary["csi_yield_kwh_per_kwp"] - 1.0
    ) * 100.0
    density_factors = {
        code: float(np.median(
            anchor_long.loc[
                anchor_long["code"] == code, "yield_kwh_per_m2"
            ].to_numpy(float)
            / anchor_long.loc[
                anchor_long["code"] == code, "yield_kwh_per_kwp"
            ].to_numpy(float)
        ))
        for code in ("c-Si", "perovskite", "tandem")
    }
    for prefix, code in (
        ("csi", "c-Si"), ("perovskite", "perovskite"),
        ("tandem", "tandem"),
    ):
        summary[f"{prefix}_yield_kwh_per_m2"] = (
            summary[f"{prefix}_yield_kwh_per_kwp"] * density_factors[code]
        )
    summary["land_grid_cell_count"] = cell_counts
    summary["land_grid_area_weight_sum"] = area_weight_sums
    summary["aggregation_method"] = np.where(
        cell_counts > 0,
        "area mean of anchor-constrained 0.1 degree land-cell surfaces",
        "full-hourly anchor fallback; no land-grid centre in polygon",
    )

    mechanism_components = (
        "electrical_baseline_pct",
        "thermal_component_pct",
        "spectral_component_pct",
        "iam_component_pct",
    )
    mechanism_fields: dict[str, np.ndarray] = {}
    for metric in ("tcell_weighted_c", "airmass_weighted"):
        truth = mechanisms[metric].to_numpy(float)
        field, loo = _trend_residual_field(
            truth, anchor_features, grid_features, spatial
        )
        mechanism_fields[metric] = field
        unit = "deg C" if metric == "tcell_weighted_c" else "ratio"
        audits.append(_metric_audit(
            metric, truth, loo, unit,
            "GHI-latitude-longitude trend plus anchor residual IDW",
        ))

    mechanism_rows = summary[[
        "adcode", "city", "city_fullname", "province", "province_code",
        "lat", "lon", "anchor_lat", "anchor_lon",
        "land_grid_cell_count", "land_grid_area_weight_sum",
    ]].copy()
    factorial_area: dict[int, pd.Series] = {}
    for mask in range(FULL_MASK + 1):
        suffix = factorial_suffix(mask)
        if mask == FULL_MASK:
            csi_factor_field = csi_field
            perovskite_factor_field = perovskite_field
            csi_fallback = anchors["csi_yield_kwh_per_kwp"].to_numpy(float)
            perovskite_fallback = anchors[
                "perovskite_yield_kwh_per_kwp"
            ].to_numpy(float)
        else:
            csi_column = f"csi_yield_{suffix}_kwh_per_kwp"
            perovskite_column = (
                f"perovskite_yield_{suffix}_kwh_per_kwp"
            )
            csi_fallback = mechanisms[csi_column].to_numpy(float)
            perovskite_fallback = mechanisms[
                perovskite_column
            ].to_numpy(float)
            csi_factor_field, csi_loo = _trend_residual_field(
                csi_fallback, anchor_features, grid_features, spatial
            )
            perovskite_factor_field, perovskite_loo = _trend_residual_field(
                perovskite_fallback, anchor_features, grid_features, spatial
            )
            for technology, truth, loo in (
                ("csi", csi_fallback, csi_loo),
                ("perovskite", perovskite_fallback, perovskite_loo),
            ):
                audits.append(_metric_audit(
                    f"{technology}_yield_{suffix}_kwh_per_kwp",
                    truth,
                    loo,
                    "kWh kWp-1",
                    "factorial GHI-latitude-longitude trend plus anchor "
                    "residual IDW",
                ))
        csi_area = _aggregate(
            csi_factor_field,
            anchors,
            cell_indices,
            area_weights,
            csi_fallback,
        )
        perovskite_area = _aggregate(
            perovskite_factor_field,
            anchors,
            cell_indices,
            area_weights,
            perovskite_fallback,
        )
        advantage = (perovskite_area / csi_area - 1.0) * 100.0
        column = f"advantage_{suffix}_pct"
        mechanism_rows[column] = advantage
        factorial_area[mask] = mechanism_rows[column]

    shapley = shapley_components(factorial_area)
    mechanism_rows["full_advantage_pct"] = factorial_area[FULL_MASK]
    mechanism_rows["electrical_baseline_pct"] = factorial_area[0]
    mechanism_rows["thermal_component_pct"] = shapley["temperature"]
    mechanism_rows["spectral_component_pct"] = shapley["spectral"]
    mechanism_rows["iam_component_pct"] = shapley["iam"]
    for metric in ("tcell_weighted_c", "airmass_weighted"):
        mechanism_rows[metric] = _aggregate(
            mechanism_fields[metric], anchors, cell_indices, area_weights,
            mechanisms[metric].to_numpy(float), local_weight=csi_field,
        )
    mechanism_rows["closure_error_pct_points"] = (
        mechanism_rows["full_advantage_pct"]
        - sum(mechanism_rows[metric] for metric in mechanism_components)
    )
    mechanism_rows["attribution_definition"] = (
        "each of eight temperature-spectral-IAM factorial yield pairs is "
        "aggregated over prefecture land cells before three-factor Shapley "
        "attribution; full = all-off electrical baseline + contributions"
    )
    mechanism_rows["aggregation_method"] = (
        "land-area aggregation of c-Si and perovskite yields for every "
        "factorial configuration, followed by yield-ratio attribution"
    )

    area_long_rows = []
    tech_names = {code: name for code, name, _ in TECHS}
    for index, city in summary.iterrows():
        for prefix, code in (
            ("csi", "c-Si"), ("perovskite", "perovskite"),
            ("tandem", "tandem"),
        ):
            anchor_tech = anchor_long[
                (anchor_long["adcode"] == city["adcode"])
                & (anchor_long["code"] == code)
            ].iloc[0]
            tcell = _aggregate(
                long_fields[(code, "tcell_weighted")],
                anchors.iloc[[index]],
                cell_indices,
                area_weights,
                np.array([float(anchor_tech["tcell_weighted"])]),
                local_weight=field_cache[f"{prefix}_yield_kwh_per_kwp"],
            )[0]
            spectral_factor = _aggregate(
                long_fields[(code, "spectral_factor_w")],
                anchors.iloc[[index]],
                cell_indices,
                area_weights,
                np.array([float(anchor_tech["spectral_factor_w"])]),
                local_weight=field_cache[f"{prefix}_yield_kwh_per_kwp"],
            )[0]
            area_long_rows.append({
                "adcode": city["adcode"],
                "city": city["city"],
                "city_fullname": city["city_fullname"],
                "province": city["province"],
                "province_fullname": city["province_fullname"],
                "province_code": city["province_code"],
                "admin_type": city["admin_type"],
                "lat": city["lat"],
                "lon": city["lon"],
                "altitude_m": city["altitude_m"],
                "tech": tech_names[code],
                "code": code,
                "yield_kwh_per_kwp": city[f"{prefix}_yield_kwh_per_kwp"],
                "yield_kwh_per_m2": city[f"{prefix}_yield_kwh_per_m2"],
                "PR": city[f"{prefix}_PR"],
                "tcell_weighted": tcell,
                "spectral_factor_w": spectral_factor,
                "ghi_kwh_m2": city["ghi_kwh_m2"],
                "tair_mean": city["tair_mean"],
                "land_grid_cell_count": city["land_grid_cell_count"],
                "land_grid_area_weight_sum": city[
                    "land_grid_area_weight_sum"
                ],
                "aggregation_method": city["aggregation_method"],
            })
    area_long = pd.DataFrame(area_long_rows).sort_values(
        ["adcode", "code"]
    ).reset_index(drop=True)
    area_lcoe = build_city_lcoe(area_long)
    area_lcoe["spatial_aggregation_method"] = (
        "LCOE recomputed from prefecture area-weighted annual yield"
    )
    province_summary = _build_province_summary(area_long)

    monthly = pd.read_csv(
        ANCHOR_MONTHLY, encoding="utf-8-sig", dtype={"adcode": str}
    )
    monthly_frames = []
    for month in range(1, 13):
        month_anchor = monthly[monthly["month"] == month].set_index("adcode")
        month_anchor = month_anchor.loc[anchors["adcode"]].reset_index()
        month_frame = summary[[
            "adcode", "city", "city_fullname", "province", "province_code",
            "lat", "lon",
        ]].copy()
        month_frame["month"] = month
        monthly_factorial: dict[int, pd.Series] = {}
        for mask in range(FULL_MASK + 1):
            suffix = factorial_suffix(mask)
            csi_column = f"csi_yield_{suffix}_kwh_per_kwp"
            perovskite_column = (
                f"perovskite_yield_{suffix}_kwh_per_kwp"
            )
            csi_fallback = month_anchor[csi_column].to_numpy(float)
            perovskite_fallback = month_anchor[
                perovskite_column
            ].to_numpy(float)
            csi_month_field = _trend_residual_field_only(
                csi_fallback, anchor_features, grid_features, spatial
            )
            perovskite_month_field = _trend_residual_field_only(
                perovskite_fallback,
                anchor_features,
                grid_features,
                spatial,
            )
            csi_area = _aggregate(
                csi_month_field,
                anchors,
                cell_indices,
                area_weights,
                csi_fallback,
            )
            perovskite_area = _aggregate(
                perovskite_month_field,
                anchors,
                cell_indices,
                area_weights,
                perovskite_fallback,
            )
            advantage = (perovskite_area / csi_area - 1.0) * 100.0
            column = f"advantage_{suffix}_pct"
            month_frame[column] = advantage
            monthly_factorial[mask] = month_frame[column]

        monthly_shapley = shapley_components(monthly_factorial)
        month_frame["full_advantage_pct"] = monthly_factorial[FULL_MASK]
        month_frame["electrical_baseline_pct"] = monthly_factorial[0]
        month_frame["thermal_component_pct"] = monthly_shapley["temperature"]
        month_frame["spectral_component_pct"] = monthly_shapley["spectral"]
        month_frame["iam_component_pct"] = monthly_shapley["iam"]
        month_frame["closure_error_pct_points"] = (
            month_frame["full_advantage_pct"]
            - sum(
                month_frame[metric] for metric in mechanism_components
            )
        )
        month_frame["attribution_definition"] = (
            "monthly yields for all eight factorial configurations are "
            "aggregated over prefecture land cells before Shapley attribution"
        )
        month_frame["aggregation_method"] = (
            "land-area aggregation of monthly c-Si and perovskite yield "
            "surfaces for each factorial configuration"
        )
        monthly_frames.append(month_frame)
    area_monthly = pd.concat(monthly_frames, ignore_index=True).sort_values(
        ["adcode", "month"]
    ).reset_index(drop=True)

    comparison = summary[[
        "adcode", "city", "city_fullname", "province",
        "land_grid_cell_count", "land_grid_area_weight_sum",
    ]].copy()
    comparison_metrics = [
        "ghi_kwh_m2", "tair_mean", "csi_yield_kwh_per_kwp",
        "perovskite_yield_kwh_per_kwp", "tandem_yield_kwh_per_kwp",
        "perovskite_advantage_pct", "tandem_advantage_pct",
    ]
    for metric in comparison_metrics:
        comparison[f"anchor_{metric}"] = anchors[metric].to_numpy(float)
        comparison[f"area_{metric}"] = summary[metric].to_numpy(float)
        comparison[f"area_minus_anchor_{metric}"] = (
            summary[metric].to_numpy(float) - anchors[metric].to_numpy(float)
        )
    comparison_mechanisms = mechanism_components + (
        "tcell_weighted_c", "airmass_weighted",
    )
    for metric in comparison_mechanisms:
        comparison[f"anchor_{metric}"] = mechanisms[metric].to_numpy(float)
        comparison[f"area_{metric}"] = mechanism_rows[metric].to_numpy(float)
        comparison[f"area_minus_anchor_{metric}"] = (
            mechanism_rows[metric].to_numpy(float)
            - comparison[f"anchor_{metric}"].to_numpy(float)
        )

    comparison_summary = []
    for metric in comparison_metrics + list(comparison_mechanisms):
        anchor_values = comparison[f"anchor_{metric}"].to_numpy(float)
        area_values = comparison[f"area_{metric}"].to_numpy(float)
        comparison_summary.append({
            "metric": metric,
            "anchor_unweighted_mean": float(anchor_values.mean()),
            "area_prefecture_unweighted_mean": float(area_values.mean()),
            "mean_shift": float((area_values - anchor_values).mean()),
            "mean_absolute_city_shift": float(
                np.mean(np.abs(area_values - anchor_values))
            ),
            "pearson_r": float(np.corrcoef(anchor_values, area_values)[0, 1]),
        })

    for path in (
        AREA_SUMMARY, AREA_LONG, AREA_MECHANISMS, AREA_MONTHLY, AREA_LCOE,
        AREA_PROVINCE, AREA_AUDIT, ANCHOR_COMPARISON,
        ANCHOR_COMPARISON_SUMMARY,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(AREA_SUMMARY, index=False, encoding="utf-8-sig")
    area_long.to_csv(AREA_LONG, index=False, encoding="utf-8-sig")
    mechanism_rows.to_csv(
        AREA_MECHANISMS, index=False, encoding="utf-8-sig"
    )
    area_monthly.to_csv(AREA_MONTHLY, index=False, encoding="utf-8-sig")
    area_lcoe.to_csv(AREA_LCOE, index=False, encoding="utf-8-sig")
    province_summary.to_csv(
        AREA_PROVINCE, index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(audits).to_csv(AREA_AUDIT, index=False, encoding="utf-8-sig")
    comparison.to_csv(
        ANCHOR_COMPARISON, index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(comparison_summary).to_csv(
        ANCHOR_COMPARISON_SUMMARY, index=False, encoding="utf-8-sig"
    )

    fallback_count = int((cell_counts == 0).sum())
    print(
        f"Built unified area outputs for {len(summary)} prefectures; "
        f"fallbacks={fallback_count}; area mean advantage="
        f"{summary['perovskite_advantage_pct'].mean():.3f}%; "
        f"mechanism closure max="
        f"{mechanism_rows['closure_error_pct_points'].abs().max():.3g} pp."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
