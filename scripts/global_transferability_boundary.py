"""Build a mechanism phase-plane boundary for transferability claims."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ROOT / "outputs" / "advantage_drivers.csv"
OUT_GRID = ROOT / "outputs" / "si_transferability_phase_plane.csv"
OUT_SUMMARY = ROOT / "outputs" / "si_transferability_phase_summary.csv"
OUT_FIG = ROOT / "outputs" / "figures" / "SI_transferability_phase_plane.png"
OUT_MD = ROOT / "docs" / "SI_TRANSFERABILITY_BOUNDARY.md"


@dataclass(frozen=True)
class PhaseModel:
    thermal_intercept: float
    thermal_slope_per_c: float
    spectral_intercept: float
    spectral_slope_per_blue_index: float
    iam_median: float
    airmass_reference: float


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    design = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(beta[0]), float(beta[1])


def fit_phase_model(drivers_path: Path = DRIVERS) -> tuple[PhaseModel, pd.DataFrame]:
    drivers = pd.read_csv(drivers_path, encoding="utf-8-sig")
    airmass_reference = float(drivers["airmass"].median())
    blue_index = airmass_reference - drivers["airmass"].to_numpy(dtype=float)
    thermal_intercept, thermal_slope = _fit_line(
        drivers["tcell"].to_numpy(dtype=float) - 25.0,
        drivers["thermal"].to_numpy(dtype=float),
    )
    spectral_intercept, spectral_slope = _fit_line(
        blue_index,
        drivers["spectral"].to_numpy(dtype=float),
    )
    model = PhaseModel(
        thermal_intercept=thermal_intercept,
        thermal_slope_per_c=thermal_slope,
        spectral_intercept=spectral_intercept,
        spectral_slope_per_blue_index=spectral_slope,
        iam_median=float(drivers["iam"].median()),
        airmass_reference=airmass_reference,
    )
    return model, drivers


def predict_advantage(model: PhaseModel, tcell: np.ndarray, airmass: np.ndarray) -> np.ndarray:
    blue_index = model.airmass_reference - airmass
    return (
        model.thermal_intercept
        + model.thermal_slope_per_c * (tcell - 25.0)
        + model.spectral_intercept
        + model.spectral_slope_per_blue_index * blue_index
        + model.iam_median
    )


def build_phase_grid(model: PhaseModel) -> pd.DataFrame:
    t_values = np.linspace(5.0, 55.0, 101)
    am_values = np.linspace(1.1, 2.8, 86)
    rows = []
    for tcell in t_values:
        for airmass in am_values:
            rows.append(
                {
                    "tcell_c": tcell,
                    "airmass": airmass,
                    "predicted_advantage_pct": float(
                        predict_advantage(model, np.array([tcell]), np.array([airmass]))[0]
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_summary(model: PhaseModel, grid: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
    thresholds = []
    for airmass in [1.4, 1.8, 2.2, 2.6]:
        numerator = -(
            model.thermal_intercept
            + model.spectral_intercept
            + model.spectral_slope_per_blue_index * (model.airmass_reference - airmass)
            + model.iam_median
        )
        threshold = 25.0 + numerator / model.thermal_slope_per_c
        thresholds.append(
            {
                "case": f"zero advantage at air mass {airmass:.1f}",
                "value": threshold,
                "unit": "cell temperature C",
            }
        )
    thresholds += [
        {
            "case": "China anchor tcell min",
            "value": float(drivers["tcell"].min()),
            "unit": "cell temperature C",
        },
        {
            "case": "China anchor tcell max",
            "value": float(drivers["tcell"].max()),
            "unit": "cell temperature C",
        },
        {
            "case": "China anchor air mass min",
            "value": float(drivers["airmass"].min()),
            "unit": "air mass",
        },
        {
            "case": "China anchor air mass max",
            "value": float(drivers["airmass"].max()),
            "unit": "air mass",
        },
        {
            "case": "Phase-plane positive share",
            "value": float((grid["predicted_advantage_pct"] > 0).mean()),
            "unit": "fraction",
        },
    ]
    return pd.DataFrame(thresholds)


def write_figure(model: PhaseModel, grid: pd.DataFrame, drivers: pd.DataFrame, path: Path = OUT_FIG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pivot = grid.pivot(index="airmass", columns="tcell_c", values="predicted_advantage_pct")
    fig, ax = plt.subplots(figsize=(6.2, 4.8), dpi=220)
    image = ax.contourf(
        pivot.columns,
        pivot.index,
        pivot.values,
        levels=np.linspace(-6, 8, 29),
        cmap="RdYlBu_r",
        extend="both",
    )
    ax.contour(pivot.columns, pivot.index, pivot.values, levels=[0], colors="black", linewidths=1.4)
    ax.scatter(
        drivers["tcell"],
        drivers["airmass"],
        c=drivers["full"],
        cmap="RdYlBu_r",
        vmin=-1,
        vmax=6,
        s=24,
        edgecolor="white",
        linewidth=0.35,
    )
    ax.set_xlabel("Irradiance-weighted cell temperature, C")
    ax.set_ylabel("Irradiance-weighted air mass")
    ax.set_title("Mechanism phase plane for transferability")
    ax.text(
        0.02,
        0.03,
        "black line = zero predicted advantage\npoints = 31 China anchors",
        transform=ax.transAxes,
        fontsize=8,
        va="bottom",
        ha="left",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78},
    )
    cb = fig.colorbar(image, ax=ax, pad=0.02)
    cb.set_label("Predicted perovskite advantage, percent")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_markdown(model: PhaseModel, summary: pd.DataFrame, path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SI Transferability Boundary",
        "",
        "Last updated: 2026-07-01",
        "",
        "This appendix defines a mechanism phase plane for transferability. It is not a global validation map. It states where the China-derived mechanism decomposition would predict a positive or negative per-kWp perovskite advantage as a function of irradiance-weighted cell temperature and air mass.",
        "",
        "The fitted thermal slope is "
        f"{model.thermal_slope_per_c:.3f} percentage points per C. "
        "The fitted spectral slope is "
        f"{model.spectral_slope_per_blue_index:.3f} percentage points per unit blue-index, where blue-index is the China median air mass minus local air mass.",
        "",
        "| Case | Value | Unit |",
        "| --- | ---: | --- |",
    ]
    for row in summary.to_dict("records"):
        lines.append(f"| {row['case']} | {row['value']:.3f} | {row['unit']} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "The positive-advantage region is warmer and lower-air-mass. The China anchors sit mostly inside this positive region, which explains why the national result is robust. Colder high-air-mass climates lie closer to or beyond the zero boundary, so the China result should not be exported globally without rerunning the full weather and spectral model.",
        "",
        "## Outputs",
        "",
        "| File | Role |",
        "| --- | --- |",
        "| `outputs/si_transferability_phase_plane.csv` | Phase-plane grid values |",
        "| `outputs/si_transferability_phase_summary.csv` | Boundary thresholds and China anchor envelope |",
        "| `outputs/figures/SI_transferability_phase_plane.png` | Lightweight SI phase-plane figure |",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> tuple[pd.DataFrame, pd.DataFrame, PhaseModel]:
    model, drivers = fit_phase_model()
    grid = build_phase_grid(model)
    summary = build_summary(model, grid, drivers)
    OUT_GRID.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(OUT_GRID, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    summary.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    write_figure(model, grid, drivers)
    write_markdown(model, summary)
    return grid, summary, model


def main() -> int:
    run()
    print(f"Transferability boundary written to {OUT_MD} and {OUT_FIG}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
