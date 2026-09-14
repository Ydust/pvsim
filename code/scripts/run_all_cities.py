"""Run the physics model for all 337 mainland-China city anchors.

The job is resumable. Each completed city is written to a three-row shard before
the consolidated city and province-summary CSV files are rebuilt.
"""

from __future__ import annotations

from pvsim.labels import label as _text_label

import argparse
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from pvsim import weather as wx
from pvsim.city_catalog import (
    DEFAULT_CITY_CATALOG,
    CityAnchor,
    load_city_catalog,
    select_city_anchors,
)
from pvsim.materials import CSI_MODERN, PEROVSKITE, TANDEM_2T
from pvsim.system import SystemConfig, simulate
from scripts.portfolio_physics import (
    N,
    YEARS,
    capex_path_global,
    lcoe_npv,
    tech_year_params,
)


TECHS = (
    ("c-Si", _text_label('tech_csi'), CSI_MODERN),
    ("perovskite", _text_label('tech_perovskite'), PEROVSKITE),
    ("tandem", _text_label('tech_tandem'), TANDEM_2T),
)
EXPECTED_TECHS = {name for _, name, _ in TECHS}
DEFAULT_SHARD_DIR = Path("outputs/city_physics_shards")
DEFAULT_OUTPUT = Path("outputs/city_physics_yield.csv")
DEFAULT_CITY_SUMMARY = Path("outputs/city_physics_summary.csv")
DEFAULT_PROVINCE_SUMMARY = Path("outputs/city_to_province_physics_summary.csv")
DEFAULT_LCOE_OUTPUT = Path("outputs/city_physics_lcoe.csv")
DEFAULT_FAILURES = Path("outputs/city_physics_failures.csv")


def _simulate_anchor(
    anchor: CityAnchor,
    npts: int,
    cache_dir: str,
    allow_download: bool,
) -> list[dict]:
    weather = wx.from_pvgis_tmy(
        anchor.lat,
        anchor.lon,
        altitude=anchor.altitude_m,
        name=anchor.cache_key,
        cache_dir=cache_dir,
        allow_download=allow_download,
    )
    cfg = SystemConfig(n_modules=20)
    resolved_altitude = float(weather.attrs.get("elevation_m", 0.0))
    ghi_total = float(weather["ghi"].sum() / 1000.0)
    tair_mean = float(weather["temp_air"].mean())
    rows = []

    for code, name, tech in TECHS:
        result = simulate(tech, weather, cfg, npts=npts)
        timeseries = result["timeseries"]
        poa = timeseries["poa_global"].to_numpy(float)
        mask = poa > 50.0
        if mask.any():
            tcell_weighted = float(np.average(
                timeseries["tcell"].to_numpy(float)[mask], weights=poa[mask],
            ))
            spectral_weighted = float(np.average(
                timeseries["spectral_factor"].to_numpy(float)[mask],
                weights=poa[mask],
            ))
        else:
            tcell_weighted = float("nan")
            spectral_weighted = float("nan")
        area_m2 = cfg.n_modules * tech.cells_in_series * tech.area_cm2 * 1e-4

        rows.append({
            "adcode": anchor.adcode,
            "city": anchor.city,
            "city_fullname": anchor.city_fullname,
            "province": anchor.province,
            "province_fullname": anchor.province_fullname,
            "province_code": anchor.province_code,
            "admin_type": anchor.admin_type,
            "lat": anchor.lat,
            "lon": anchor.lon,
            "altitude_m": resolved_altitude,
            "coordinate_source": anchor.coordinate_source,
            "tech": name,
            "code": code,
            "kwp": result["kwp"],
            "yield_kwh_per_kwp": result["specific_yield"],
            "yield_kwh_per_m2": result["energy_ac_kwh"] / area_m2,
            "PR": result["performance_ratio"],
            "tcell_weighted": tcell_weighted,
            "spectral_factor_w": spectral_weighted,
            "ghi_kwh_m2": ghi_total,
            "tair_mean": tair_mean,
            "weather_source": weather.attrs.get("source", "PVGIS TMY"),
            "weather_cache_key": anchor.cache_key,
        })
    return rows


def _shard_path(shard_dir: Path, adcode: str) -> Path:
    return shard_dir / f"{adcode}.csv"


def _valid_shard(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return False
    return len(frame) == 3 and set(frame["tech"]) == EXPECTED_TECHS


def _write_shard(shard_dir: Path, adcode: str, rows: list[dict]) -> Path:
    shard_dir.mkdir(parents=True, exist_ok=True)
    path = _shard_path(shard_dir, adcode)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _load_complete_results(
    anchors: list[CityAnchor], shard_dir: Path,
) -> tuple[pd.DataFrame, list[str]]:
    frames = []
    missing = []
    for anchor in anchors:
        path = _shard_path(shard_dir, anchor.adcode)
        if _valid_shard(path):
            frames.append(pd.read_csv(path, encoding="utf-8-sig", dtype={"adcode": str}))
        else:
            missing.append(anchor.adcode)
    if not frames:
        return pd.DataFrame(), missing
    result = pd.concat(frames, ignore_index=True)
    result["adcode"] = result["adcode"].astype(str).str.zfill(6)
    return result.sort_values(["adcode", "code"]).reset_index(drop=True), missing


def build_city_summary(results: pd.DataFrame) -> pd.DataFrame:
    metadata_columns = [
        "adcode", "city", "city_fullname", "province", "province_fullname",
        "province_code", "admin_type", "lat", "lon", "altitude_m",
        "ghi_kwh_m2", "tair_mean",
    ]
    metadata = results[metadata_columns].drop_duplicates("adcode").set_index("adcode")
    yield_kwp = results.pivot(index="adcode", columns="code", values="yield_kwh_per_kwp")
    yield_m2 = results.pivot(index="adcode", columns="code", values="yield_kwh_per_m2")
    pr = results.pivot(index="adcode", columns="code", values="PR")

    summary = metadata.copy()
    summary["csi_yield_kwh_per_kwp"] = yield_kwp["c-Si"]
    summary["perovskite_yield_kwh_per_kwp"] = yield_kwp["perovskite"]
    summary["tandem_yield_kwh_per_kwp"] = yield_kwp["tandem"]
    summary["perovskite_advantage_pct"] = (
        yield_kwp["perovskite"] / yield_kwp["c-Si"] - 1.0
    ) * 100.0
    summary["tandem_advantage_pct"] = (
        yield_kwp["tandem"] / yield_kwp["c-Si"] - 1.0
    ) * 100.0
    summary["csi_yield_kwh_per_m2"] = yield_m2["c-Si"]
    summary["perovskite_yield_kwh_per_m2"] = yield_m2["perovskite"]
    summary["tandem_yield_kwh_per_m2"] = yield_m2["tandem"]
    summary["csi_PR"] = pr["c-Si"]
    summary["perovskite_PR"] = pr["perovskite"]
    summary["tandem_PR"] = pr["tandem"]
    return summary.reset_index().sort_values("adcode").reset_index(drop=True)


def build_province_summary(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.groupby(
        ["province_code", "province", "tech", "code"], as_index=False,
    ).agg(
        city_anchor_count=("adcode", "nunique"),
        mean_yield_kwh_per_kwp=("yield_kwh_per_kwp", "mean"),
        median_yield_kwh_per_kwp=("yield_kwh_per_kwp", "median"),
        min_yield_kwh_per_kwp=("yield_kwh_per_kwp", "min"),
        max_yield_kwh_per_kwp=("yield_kwh_per_kwp", "max"),
        mean_yield_kwh_per_m2=("yield_kwh_per_m2", "mean"),
        mean_PR=("PR", "mean"),
        mean_tcell_weighted=("tcell_weighted", "mean"),
        mean_spectral_factor=("spectral_factor_w", "mean"),
        mean_ghi_kwh_m2=("ghi_kwh_m2", "mean"),
    )
    grouped["aggregation_method"] = "unweighted mean of city administrative-centre anchors"
    return grouped.sort_values(["province_code", "code"]).reset_index(drop=True)


def build_city_lcoe(results: pd.DataFrame) -> pd.DataFrame:
    """Apply the existing 2025-2050 model economics to every city anchor."""
    base_deployment = {
        _text_label('tech_csi'): np.linspace(80, 30, N) + np.linspace(0, 20, N),
        _text_label('tech_perovskite'): np.minimum(np.arange(N) * 4 + 5, 100),
        _text_label('tech_tandem'): np.maximum(0, np.minimum(np.arange(N) * 3 - 12, 80)),
    }
    capex_path = capex_path_global(base_deployment)
    rows = []
    for row in results.itertuples(index=False):
        for index, year in enumerate(YEARS):
            capex = capex_path[row.tech][index]
            life, degradation, burn_in = tech_year_params(row.tech, int(year))
            value = lcoe_npv(
                capex,
                row.yield_kwh_per_kwp,
                life,
                degradation,
                burn_in,
            )
            rows.append({
                "adcode": row.adcode,
                "city": row.city,
                "city_fullname": row.city_fullname,
                "province": row.province,
                "province_code": row.province_code,
                "tech": row.tech,
                "code": row.code,
                "year": int(year),
                "capex_usd_per_w": capex,
                "lcoe_cents_per_kwh": value * 100.0,
                "yield_kwh_per_kwp": row.yield_kwh_per_kwp,
                "tcell_weighted": row.tcell_weighted,
                "scenario_scope": "shared national technology-cost path",
            })
    return pd.DataFrame(rows).sort_values(
        ["adcode", "code", "year"],
    ).reset_index(drop=True)


def _write_consolidated_outputs(
    all_anchors: list[CityAnchor],
    shard_dir: Path,
    output: Path,
    city_summary_path: Path,
    province_summary_path: Path,
    lcoe_output_path: Path,
) -> tuple[int, int]:
    results, missing = _load_complete_results(all_anchors, shard_dir)
    if results.empty:
        return 0, len(missing)
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False, encoding="utf-8-sig")
    build_city_summary(results).to_csv(
        city_summary_path, index=False, encoding="utf-8-sig",
    )
    build_province_summary(results).to_csv(
        province_summary_path, index=False, encoding="utf-8-sig",
    )
    build_city_lcoe(results).to_csv(
        lcoe_output_path, index=False, encoding="utf-8-sig",
    )
    return results["adcode"].nunique(), len(missing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CITY_CATALOG)
    parser.add_argument("--province")
    parser.add_argument("--adcode", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--npts", type=int, default=60)
    parser.add_argument("--cache-dir", default="data/tmy_cache")
    parser.add_argument("--shard-dir", type=Path, default=DEFAULT_SHARD_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--city-summary", type=Path, default=DEFAULT_CITY_SUMMARY)
    parser.add_argument("--province-summary", type=Path, default=DEFAULT_PROVINCE_SUMMARY)
    parser.add_argument("--lcoe-output", type=Path, default=DEFAULT_LCOE_OUTPUT)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    all_anchors = load_city_catalog(args.catalog)
    selected = select_city_anchors(
        all_anchors,
        province=args.province,
        adcodes={str(code).zfill(6) for code in args.adcode} or None,
    )
    if args.limit is not None:
        selected = selected[:max(0, args.limit)]
    if not selected:
        parser.error("No city anchors matched the requested filters")

    if args.refresh:
        for anchor in selected:
            path = _shard_path(args.shard_dir, anchor.adcode)
            if path.exists():
                path.unlink()

    pending = [
        anchor for anchor in selected
        if args.refresh or not _valid_shard(_shard_path(args.shard_dir, anchor.adcode))
    ]
    print(
        f"Selected {len(selected)} anchors; {len(pending)} pending; "
        f"workers={max(1, args.workers)}; npts={args.npts}",
        flush=True,
    )

    failures = []
    completed = 0
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                _simulate_anchor,
                anchor,
                max(20, args.npts),
                args.cache_dir,
                not args.offline,
            ): anchor
            for anchor in pending
        }
        for future in as_completed(futures):
            anchor = futures[future]
            try:
                rows = future.result()
                _write_shard(args.shard_dir, anchor.adcode, rows)
                completed += 1
                print(
                    f"[{completed}/{len(pending)}] {anchor.province} {anchor.city} "
                    f"({anchor.adcode}) complete",
                    flush=True,
                )
            except Exception as exc:
                failures.append({
                    "adcode": anchor.adcode,
                    "province": anchor.province,
                    "city": anchor.city,
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=6),
                })
                print(
                    f"FAILED {anchor.province} {anchor.city} ({anchor.adcode}): {exc}",
                    file=sys.stderr,
                    flush=True,
                )

    if failures:
        args.failures.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(failures).to_csv(args.failures, index=False, encoding="utf-8-sig")
    elif args.failures.exists():
        args.failures.unlink()

    city_count, missing_count = _write_consolidated_outputs(
        all_anchors,
        args.shard_dir,
        args.output,
        args.city_summary,
        args.province_summary,
        args.lcoe_output,
    )
    print(
        f"Consolidated {city_count}/337 cities; missing={missing_count}; "
        f"failures={len(failures)}",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
