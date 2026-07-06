"""Generate SI defense tables for the paper's scientific hardening pass.

The tables are deliberately tied to the existing figure scripts so the numbers
used in the manuscript, SI plan and figures come from the same assumptions.

Outputs:
  outputs/si_fleet_validation_by_province.csv
  outputs/si_fleet_validation_summary.csv
  outputs/si_grid_reduced_validation_by_province.csv
  outputs/si_grid_reduced_validation_summary.csv
  outputs/si_mc_parameters.csv
  outputs/si_substitution_calibration.csv
  docs/SI_SCIENTIFIC_DEFENSE_TABLES.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pvsim.era5_land import fetch_china_climatology
from pvsim.economic_priors import mc_parameter_rows
from pvsim.materials import CSI_MODERN, PEROVSKITE
from pvsim.module import array_dc_power, module_stc_power
from pvsim.provinces import PROVINCES, PROVINCE_EN
from scripts.fig_substitution_validation import (
    HIST_YEARS,
    MONO_SHARE_OBS,
    calibrate_T,
)
from scripts.fig_validation_fleet import BASELINE_LOSS, FLEET_HOURS

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = Path("outputs")
DOC = Path("docs/SI_SCIENTIFIC_DEFENSE_TABLES.md")
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
U0, U1 = 25.0, 6.84
CSI_STC = module_stc_power(CSI_MODERN)
PEROV_STC = module_stc_power(PEROVSKITE)


def build_power_lut(tech, g_grid: np.ndarray, t_grid: np.ndarray):
    """Build a (G, Tcell) -> module power lookup table."""
    gg, tt = np.meshgrid(g_grid, t_grid, indexing="ij")
    p = array_dc_power(tech, gg.ravel(), tt.ravel(), n_modules=1, npts=60)
    p = np.atleast_1d(p).reshape(gg.shape)
    return g_grid, t_grid, p


def interp_lut(lut, g: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Pure NumPy bilinear interpolation for the regular (G, Tcell) LUT."""
    g_grid, t_grid, p = lut
    g_flat = np.asarray(g, dtype=float).ravel()
    t_flat = np.asarray(t, dtype=float).ravel()
    g_clip = np.clip(g_flat, g_grid[0], g_grid[-1])
    t_clip = np.clip(t_flat, t_grid[0], t_grid[-1])

    gi = np.searchsorted(g_grid, g_clip, side="right") - 1
    ti = np.searchsorted(t_grid, t_clip, side="right") - 1
    gi = np.clip(gi, 0, len(g_grid) - 2)
    ti = np.clip(ti, 0, len(t_grid) - 2)

    g0, g1 = g_grid[gi], g_grid[gi + 1]
    t0, t1 = t_grid[ti], t_grid[ti + 1]
    wg = (g_clip - g0) / np.maximum(g1 - g0, 1e-12)
    wt = (t_clip - t0) / np.maximum(t1 - t0, 1e-12)

    p00 = p[gi, ti]
    p10 = p[gi + 1, ti]
    p01 = p[gi, ti + 1]
    p11 = p[gi + 1, ti + 1]
    out = ((1 - wg) * (1 - wt) * p00 +
           wg * (1 - wt) * p10 +
           (1 - wg) * wt * p01 +
           wg * wt * p11)
    return out.reshape(np.asarray(g).shape)


def advantage_grid(ghi12, tair12, wind12, k, lut_csi, lut_perov):
    """Monthly reduced-order perovskite advantage (%)."""
    g_eff = k * ghi12
    tcell = tair12 + g_eff / (U0 + U1 * wind12)
    pts_csi = interp_lut(lut_csi, g_eff, tcell)
    pts_per = interp_lut(lut_perov, g_eff, tcell)
    w = DAYS[:, None]
    y_csi = np.sum(pts_csi * w, axis=0) / CSI_STC
    y_per = np.sum(pts_per * w, axis=0) / PEROV_STC
    return (y_per / y_csi - 1) * 100


def _metrics(pred: np.ndarray, obs: np.ndarray) -> dict[str, float]:
    """Return common regression-style metrics for pred vs obs."""
    pred = np.asarray(pred, dtype=float)
    obs = np.asarray(obs, dtype=float)
    resid = pred - obs
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((obs - obs.mean()) ** 2))
    return {
        "n": int(len(obs)),
        "r": float(np.corrcoef(pred, obs)[0, 1]),
        "r2": float(1 - ss_res / ss_tot) if ss_tot else np.nan,
        "bias": float(resid.mean()),
        "mae": float(np.mean(np.abs(resid))),
        "rmse": float(np.sqrt(np.mean(resid**2))),
        "mape_pct": float(np.mean(np.abs(resid / obs)) * 100),
    }


def _fmt(v: float, digits: int = 2) -> str:
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if not np.isfinite(v):
        return "NA"
    return f"{float(v):.{digits}f}"


def _markdown_table(df: pd.DataFrame, digits: int = 2) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |",
             "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            val = row[col]
            if isinstance(val, float):
                vals.append(_fmt(val, digits))
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def fleet_validation_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    y = pd.read_csv(OUT / "province_physics_yield.csv", encoding="utf-8-sig")
    sy = y[y.tech == "晶硅"].set_index("province")["yield_kwh_per_kwp"]
    band = y[y.tech == "晶硅"].set_index("province")["res_band"]

    rows = []
    for prov, hours in FLEET_HOURS.items():
        if prov not in sy.index:
            continue
        twin = float(sy.loc[prov])
        fleet = float(hours)
        loss = (1 - fleet / twin) * 100
        rows.append({
            "province": prov,
            "province_en": PROVINCE_EN.get(prov, prov),
            "resource_band": band.loc[prov],
            "twin_kwh_per_kwp": twin,
            "fleet_hours": fleet,
            "twin_minus_fleet": twin - fleet,
            "implied_system_loss_pct": loss,
            "excess_over_10pct_baseline": loss - BASELINE_LOSS,
        })
    by_prov = pd.DataFrame(rows)

    raw = _metrics(by_prov["twin_kwh_per_kwp"], by_prov["fleet_hours"])
    mean_loss = float(by_prov["implied_system_loss_pct"].mean())
    corrected = by_prov["twin_kwh_per_kwp"] * (1 - mean_loss / 100)
    corr = _metrics(corrected, by_prov["fleet_hours"])

    summary = pd.DataFrame([
        {
            "check": "raw clean-physics twin vs fleet hours",
            "n": raw["n"],
            "r": raw["r"],
            "bias_kwh_per_kwp": raw["bias"],
            "mae_kwh_per_kwp": raw["mae"],
            "rmse_kwh_per_kwp": raw["rmse"],
            "mape_pct": raw["mape_pct"],
            "mean_loss_pct": mean_loss,
        },
        {
            "check": "uniform-loss-corrected twin vs fleet hours",
            "n": corr["n"],
            "r": corr["r"],
            "bias_kwh_per_kwp": corr["bias"],
            "mae_kwh_per_kwp": corr["mae"],
            "rmse_kwh_per_kwp": corr["rmse"],
            "mape_pct": corr["mape_pct"],
            "mean_loss_pct": mean_loss,
        },
    ])

    by_prov.to_csv(OUT / "si_fleet_validation_by_province.csv", index=False,
                   encoding="utf-8-sig")
    summary.to_csv(OUT / "si_fleet_validation_summary.csv", index=False,
                   encoding="utf-8-sig")
    return by_prov, summary


def grid_reduced_validation_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    g = fetch_china_climatology(verbose=False)
    lon, lat = g["lon"], g["lat"]
    ghi, tair, wind = g["ghi"], g["tair"], g["wind"]
    ny, nx = lon.shape
    flat_lon, flat_lat = lon.ravel(), lat.ravel()

    g_grid = np.linspace(5, 1200, 80)
    t_grid = np.linspace(-30, 75, 60)
    lut_csi = build_power_lut(CSI_MODERN, g_grid, t_grid)
    lut_perov = build_power_lut(PEROVSKITE, g_grid, t_grid)

    anchor = pd.read_csv(OUT / "province_physics_yield.csv", encoding="utf-8-sig")
    csi_a = anchor[anchor["tech"] == "晶硅"].set_index("province")
    per_a = anchor[anchor["tech"] == "钙钛矿"].set_index("province")

    provinces, bands, a_ghi, a_tair, a_wind, full_adv = [], [], [], [], [], []
    for prov in PROVINCES:
        if prov.name not in csi_a.index or prov.name not in per_a.index:
            continue
        d = (flat_lon - prov.lon) ** 2 + (flat_lat - prov.lat) ** 2
        idx = int(np.argmin(d))
        iy, ix = divmod(idx, nx)
        provinces.append(prov.name)
        bands.append(prov.res_band)
        a_ghi.append(ghi[:, iy, ix])
        a_tair.append(tair[:, iy, ix])
        a_wind.append(wind[:, iy, ix])
        full_adv.append(
            (per_a.loc[prov.name, "yield_kwh_per_kwp"] /
             csi_a.loc[prov.name, "yield_kwh_per_kwp"] - 1) * 100
        )

    a_ghi = np.array(a_ghi).T
    a_tair = np.array(a_tair).T
    a_wind = np.array(a_wind).T
    full_adv = np.array(full_adv)

    best_k, best_rmse = None, np.inf
    for k in np.arange(60, 360, 5):
        pred = advantage_grid(a_ghi, a_tair, a_wind, k, lut_csi, lut_perov)
        rmse = np.sqrt(np.mean((pred - full_adv) ** 2))
        if rmse < best_rmse:
            best_k, best_rmse = k, rmse
    pred_adv = advantage_grid(a_ghi, a_tair, a_wind, best_k, lut_csi, lut_perov)

    by_prov = pd.DataFrame({
        "province": provinces,
        "province_en": [PROVINCE_EN.get(p, p) for p in provinces],
        "resource_band": bands,
        "full_8760h_adv_pct": full_adv,
        "reduced_era5_adv_pct": pred_adv,
        "error_pct_points": pred_adv - full_adv,
    })
    m = _metrics(by_prov["reduced_era5_adv_pct"], by_prov["full_8760h_adv_pct"])

    grid = pd.read_csv(OUT / "grid_inversion_era5.csv", encoding="utf-8-sig")
    r_grid = float(np.corrcoef(grid["ghi_ann"], grid["adv"])[0, 1])
    summary = pd.DataFrame([{
        "check": "ERA5 reduced-order advantage vs full 8760h provincial anchors",
        "n": m["n"],
        "best_k": float(best_k),
        "r": m["r"],
        "r2": m["r2"],
        "bias_pct_points": m["bias"],
        "mae_pct_points": m["mae"],
        "rmse_pct_points": m["rmse"],
        "grid_cells": int(len(grid)),
        "grid_r_ghi_vs_adv": r_grid,
        "grid_adv_p10": float(grid["adv"].quantile(0.10)),
        "grid_adv_p50": float(grid["adv"].quantile(0.50)),
        "grid_adv_p90": float(grid["adv"].quantile(0.90)),
    }])

    band_summary = by_prov.groupby("resource_band").agg(
        n=("province", "count"),
        full_median_adv_pct=("full_8760h_adv_pct", "median"),
        reduced_median_adv_pct=("reduced_era5_adv_pct", "median"),
        median_error_pct_points=("error_pct_points", "median"),
    ).reset_index()

    by_prov.to_csv(OUT / "si_grid_reduced_validation_by_province.csv",
                   index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "si_grid_reduced_validation_summary.csv",
                   index=False, encoding="utf-8-sig")
    band_summary.to_csv(OUT / "si_grid_reduced_validation_by_band.csv",
                        index=False, encoding="utf-8-sig")
    return by_prov, summary, band_summary


def mc_and_calibration_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    t_fit, rmse, r2, pred, lc_multi, lc_mono = calibrate_T()

    cal = pd.DataFrame({
        "year": HIST_YEARS,
        "mono_share_observed_pct": MONO_SHARE_OBS * 100,
        "mono_share_model_pct": pred * 100,
        "residual_pct_points": (pred - MONO_SHARE_OBS) * 100,
        "multi_lcoe_cents_kwh": lc_multi,
        "mono_lcoe_cents_kwh": lc_mono,
    })

    cal_summary = pd.DataFrame([{
        "check": "historical multi-to-mono softmax calibration",
        "years": "2015-2023",
        "softmax_T_cents_kwh": t_fit,
        "rmse_share_pct_points": rmse * 100,
        "r2": r2,
        "max_abs_residual_pct_points": float(np.max(np.abs(cal["residual_pct_points"]))),
    }])

    params = pd.DataFrame(mc_parameter_rows(t_fit))

    cal.to_csv(OUT / "si_substitution_calibration.csv", index=False,
               encoding="utf-8-sig")
    cal_summary.to_csv(OUT / "si_substitution_calibration_summary.csv",
                       index=False, encoding="utf-8-sig")
    params.to_csv(OUT / "si_mc_parameters.csv", index=False, encoding="utf-8-sig")
    return cal, cal_summary, params


def write_markdown(
    fleet_summary: pd.DataFrame,
    grid_summary: pd.DataFrame,
    band_summary: pd.DataFrame,
    cal_summary: pd.DataFrame,
    mc_params: pd.DataFrame,
) -> None:
    lines = [
        "# SI Scientific Defense Tables",
        "",
        "These tables support the scientific-hardening pass for `NEWFig1-5`. "
        "They should be treated as SI-ready evidence tables, not as new main-figure claims.",
        "",
        "## Table Sx. Fleet-Anchored System Validation",
        "",
        "The fleet comparison is a system-level spatial anchor. It includes BOS loss, curtailment, "
        "dispatch and O&M effects; it is not a pure device-physics validation.",
        "",
        "Fleet-hour values are loaded from `data/source_tables/provincial_fleet_hours_2024.csv`, "
        "a versioned source table used for the system-level anchor. The table reports provincial "
        "grid-connected PV utilisation hours and keeps source notes beside each row.",
        "",
        _markdown_table(fleet_summary, 2),
        "",
        "## Table Sy. ERA5 Reduced-Order Grid Validation",
        "",
        "The 0.1° layer supports the spatial inversion and regional ranking. It should not be "
        "presented as a point forecast for individual plants or land cells.",
        "",
        _markdown_table(grid_summary, 3),
        "",
        "## Table Sz. Resource-Band Check For Reduced-Order Model",
        "",
        _markdown_table(band_summary, 2),
        "",
        "## Table Sa. Historical Softmax Calibration",
        "",
        _markdown_table(cal_summary, 3),
        "",
        "## Table Sb. Monte Carlo Scenario Parameters",
        "",
        _markdown_table(mc_params, 2),
        "",
        "Generated by `python -m scripts.si_scientific_defense_tables`.",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    fleet_by_prov, fleet_summary = fleet_validation_tables()
    grid_by_prov, grid_summary, band_summary = grid_reduced_validation_tables()
    cal, cal_summary, mc_params = mc_and_calibration_tables()
    write_markdown(fleet_summary, grid_summary, band_summary, cal_summary, mc_params)

    print("SI scientific-defense tables written:")
    for path in [
        OUT / "si_fleet_validation_by_province.csv",
        OUT / "si_fleet_validation_summary.csv",
        OUT / "si_grid_reduced_validation_by_province.csv",
        OUT / "si_grid_reduced_validation_summary.csv",
        OUT / "si_grid_reduced_validation_by_band.csv",
        OUT / "si_substitution_calibration.csv",
        OUT / "si_substitution_calibration_summary.csv",
        OUT / "si_mc_parameters.csv",
        DOC,
    ]:
        print(f"  {path}")
    print("\nKey results:")
    print(f"  fleet raw r={fleet_summary.loc[0, 'r']:.3f}, "
          f"mean loss={fleet_summary.loc[0, 'mean_loss_pct']:.1f}%")
    print(f"  grid reduced R2={grid_summary.loc[0, 'r2']:.3f}, "
          f"RMSE={grid_summary.loc[0, 'rmse_pct_points']:.2f} pct points")
    print(f"  calibration R2={cal_summary.loc[0, 'r2']:.3f}, "
          f"RMSE={cal_summary.loc[0, 'rmse_share_pct_points']:.1f} share points")


if __name__ == "__main__":
    main()
