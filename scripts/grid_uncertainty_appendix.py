"""Build the SI uncertainty appendix for the ERA5 reduced-order grid layer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


OUT = Path("outputs")
DOC = Path("docs/SI_GRID_UNCERTAINTY.md")


def _markdown_table(df: pd.DataFrame, digits: int = 3) -> str:
    data = df.copy()
    for col in data.columns:
        if pd.api.types.is_float_dtype(data[col]):
            data[col] = data[col].map(lambda x: f"{x:.{digits}f}")
    lines = [
        "| " + " | ".join(data.columns) + " |",
        "| " + " | ".join(["---"] * len(data.columns)) + " |",
    ]
    for _, row in data.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in data.columns) + " |")
    return "\n".join(lines)


def build_tables() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame
]:
    summary = pd.read_csv(OUT / "si_grid_reduced_validation_summary.csv")
    by_province = pd.read_csv(OUT / "si_grid_reduced_validation_by_province.csv")
    by_band = pd.read_csv(OUT / "si_grid_reduced_validation_by_band.csv")

    abs_error = by_province["error_pct_points"].abs()
    quantiles = pd.DataFrame(
        [
            {
                "metric": "absolute error percentile",
                "p50_pct_points": abs_error.quantile(0.50),
                "p75_pct_points": abs_error.quantile(0.75),
                "p90_pct_points": abs_error.quantile(0.90),
                "max_pct_points": abs_error.max(),
            }
        ]
    )

    outliers = by_province.assign(abs_error_pct_points=abs_error).sort_values(
        "abs_error_pct_points", ascending=False
    )
    outliers = outliers.head(8)[
        [
            "province_en",
            "resource_band",
            "full_8760h_adv_pct",
            "reduced_era5_adv_pct",
            "error_pct_points",
            "abs_error_pct_points",
        ]
    ]
    return summary, by_province, by_band, quantiles, outliers


def write_outputs(
    summary: pd.DataFrame,
    by_band: pd.DataFrame,
    quantiles: pd.DataFrame,
    outliers: pd.DataFrame,
) -> None:
    quantiles.to_csv(
        OUT / "si_grid_uncertainty_quantiles.csv", index=False, encoding="utf-8-sig"
    )
    outliers.to_csv(
        OUT / "si_grid_uncertainty_outliers.csv", index=False, encoding="utf-8-sig"
    )
    s = summary.iloc[0]
    lines = [
        "# SI ERA5 Grid Uncertainty Appendix",
        "",
        "This appendix defines how the ERA5-Land 0.1 degree reduced-order layer should be used.",
        "",
        "The grid layer is calibrated against 31 provincial full 8,760-hour anchors. It supports national spatial pattern and regional ranking. It should not be used as a plant-level or individual-cell prediction.",
        "",
        "## Validation Summary",
        "",
        f"The advantage-variable validation has R2 = {s['r2']:.3f}, RMSE = {s['rmse_pct_points']:.3f} percentage points, MAE = {s['mae_pct_points']:.3f} percentage points and bias = {s['bias_pct_points']:.3f} percentage points.",
        "",
        f"The grid contains {int(s['grid_cells'])} land cells. Across those cells, annual irradiance and perovskite advantage remain negatively correlated with r = {s['grid_r_ghi_vs_adv']:.3f}.",
        "",
        "## Absolute Error Distribution",
        "",
        _markdown_table(quantiles, 3),
        "",
        "## Resource-Band Compression",
        "",
        _markdown_table(by_band, 3),
        "",
        "## Largest Provincial Errors",
        "",
        _markdown_table(outliers, 3),
        "",
        "## Use Rule",
        "",
        "Use the grid figure for national pattern, resource-band ordering and visual localisation of the inversion. Use the 31 full-hourly provincial anchors for province-level numerical claims. Treat any cell-level colour as a climatological pattern value with an uncertainty scale of about one percentage point in the advantage variable.",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    summary, _, by_band, quantiles, outliers = build_tables()
    write_outputs(summary, by_band, quantiles, outliers)
    print("Grid uncertainty appendix written:")
    print("  outputs/si_grid_uncertainty_quantiles.csv")
    print("  outputs/si_grid_uncertainty_outliers.csv")
    print("  docs/SI_GRID_UNCERTAINTY.md")


if __name__ == "__main__":
    main()
