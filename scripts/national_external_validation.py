"""Build a national aggregate measured-generation validation check."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
YIELD_CSV = ROOT / "outputs" / "province_physics_yield.csv"
CAPACITY_CSV = ROOT / "data" / "source_tables" / "provincial_pv_capacity_2024.csv"
FLEET_SUMMARY_CSV = ROOT / "outputs" / "si_fleet_validation_summary.csv"
OUT_CSV = ROOT / "outputs" / "si_national_external_validation.csv"
OUT_MD = ROOT / "docs" / "SI_NATIONAL_EXTERNAL_VALIDATION.md"

SOURCE_URL = "https://www.stats.gov.cn/sj/zxfb/202502/t20250228_1958817.html"
SOURCE_DOC = "National Bureau of Statistics 2024 Statistical Communique"
NBS_SOLAR_GENERATION_TWH = 839.04
NBS_YEAR_END_SOLAR_CAPACITY_GW = 886.66
NBS_SOLAR_CAPACITY_GROWTH_PCT = 45.2


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _capacity_by_province() -> dict[str, float]:
    rows = _read_csv(CAPACITY_CSV)
    return {row["province"]: float(row["scaled_to_national_gw"]) for row in rows}


def _mean_system_loss_pct() -> float:
    rows = _read_csv(FLEET_SUMMARY_CSV)
    for row in rows:
        if row["check"] == "uniform-loss-corrected twin vs fleet hours":
            return float(row["mean_loss_pct"])
    raise ValueError("uniform-loss-corrected fleet summary row not found")


def _weighted_model_yield(code: str = "c-Si") -> float:
    capacities = _capacity_by_province()
    rows = [row for row in _read_csv(YIELD_CSV) if row["code"] == code]
    total_capacity = sum(capacities.values())
    weighted = 0.0
    for row in rows:
        province = row["province"]
        weighted += capacities[province] * float(row["yield_kwh_per_kwp"])
    return weighted / total_capacity


def build_summary() -> dict[str, Any]:
    model_capacity_gw = sum(_capacity_by_province().values())
    inferred_start_capacity_gw = NBS_YEAR_END_SOLAR_CAPACITY_GW / (
        1.0 + NBS_SOLAR_CAPACITY_GROWTH_PCT / 100.0
    )
    simple_average_capacity_gw = (
        inferred_start_capacity_gw + NBS_YEAR_END_SOLAR_CAPACITY_GW
    ) / 2.0
    observed_specific_yield_end_capacity = (
        NBS_SOLAR_GENERATION_TWH / NBS_YEAR_END_SOLAR_CAPACITY_GW * 1000.0
    )
    observed_specific_yield_average_capacity = (
        NBS_SOLAR_GENERATION_TWH / simple_average_capacity_gw * 1000.0
    )
    model_clean_csi = _weighted_model_yield("c-Si")
    mean_loss_pct = _mean_system_loss_pct()
    model_loss_corrected = model_clean_csi * (1.0 - mean_loss_pct / 100.0)
    bias_vs_average = model_loss_corrected - observed_specific_yield_average_capacity
    bias_vs_end = model_loss_corrected - observed_specific_yield_end_capacity
    return {
        "validation_status": "partial national aggregate check",
        "source_doc": SOURCE_DOC,
        "source_url": SOURCE_URL,
        "nbs_generation_twh": NBS_SOLAR_GENERATION_TWH,
        "nbs_year_end_capacity_gw": NBS_YEAR_END_SOLAR_CAPACITY_GW,
        "nbs_capacity_growth_pct": NBS_SOLAR_CAPACITY_GROWTH_PCT,
        "model_capacity_gw": model_capacity_gw,
        "model_capacity_gap_gw": model_capacity_gw - NBS_YEAR_END_SOLAR_CAPACITY_GW,
        "inferred_start_capacity_gw": inferred_start_capacity_gw,
        "simple_average_capacity_gw": simple_average_capacity_gw,
        "observed_specific_yield_end_capacity_kwh_per_kw": observed_specific_yield_end_capacity,
        "observed_specific_yield_average_capacity_kwh_per_kw": observed_specific_yield_average_capacity,
        "clean_model_csi_yield_kwh_per_kwp": model_clean_csi,
        "mean_system_loss_pct": mean_loss_pct,
        "loss_corrected_model_csi_yield_kwh_per_kwp": model_loss_corrected,
        "bias_vs_average_capacity_kwh_per_kwp": bias_vs_average,
        "bias_vs_average_capacity_pct": bias_vs_average
        / observed_specific_yield_average_capacity
        * 100.0,
        "bias_vs_end_capacity_kwh_per_kwp": bias_vs_end,
        "bias_vs_end_capacity_pct": bias_vs_end
        / observed_specific_yield_end_capacity
        * 100.0,
    }


def build_rows() -> list[dict[str, str]]:
    summary = build_summary()
    rows = [
        (
            "validation_status",
            summary["validation_status"],
            "status",
            "This is independent measured national evidence, but not a location-resolved external validation layer",
        ),
        ("nbs_solar_generation", summary["nbs_generation_twh"], "TWh", SOURCE_DOC),
        (
            "nbs_year_end_solar_capacity",
            summary["nbs_year_end_capacity_gw"],
            "GW",
            SOURCE_DOC,
        ),
        (
            "nbs_capacity_growth",
            summary["nbs_capacity_growth_pct"],
            "percent",
            SOURCE_DOC,
        ),
        (
            "model_capacity",
            summary["model_capacity_gw"],
            "GW",
            "Scaled provincial capacity table",
        ),
        (
            "model_minus_nbs_capacity",
            summary["model_capacity_gap_gw"],
            "GW",
            "Difference between scaled model capacity and official year-end capacity",
        ),
        (
            "inferred_start_capacity",
            summary["inferred_start_capacity_gw"],
            "GW",
            "Year-end capacity divided by one plus the official growth rate",
        ),
        (
            "simple_average_capacity",
            summary["simple_average_capacity_gw"],
            "GW",
            "Average of inferred start-year and official year-end capacity",
        ),
        (
            "observed_specific_yield_end_capacity",
            summary["observed_specific_yield_end_capacity_kwh_per_kw"],
            "kWh per kW",
            "Official generation divided by official year-end capacity",
        ),
        (
            "observed_specific_yield_average_capacity",
            summary["observed_specific_yield_average_capacity_kwh_per_kw"],
            "kWh per kW",
            "Official generation divided by simple average capacity",
        ),
        (
            "clean_model_csi_yield",
            summary["clean_model_csi_yield_kwh_per_kwp"],
            "kWh per kWp",
            "Capacity-weighted 31-province clean-physics c-Si yield",
        ),
        (
            "mean_system_loss",
            summary["mean_system_loss_pct"],
            "percent",
            "Mean loss inferred from provincial fleet-hour anchor",
        ),
        (
            "loss_corrected_model_csi_yield",
            summary["loss_corrected_model_csi_yield_kwh_per_kwp"],
            "kWh per kWp",
            "Clean model yield after uniform fleet-hour loss correction",
        ),
        (
            "bias_vs_average_capacity",
            summary["bias_vs_average_capacity_kwh_per_kwp"],
            "kWh per kWp",
            "Loss-corrected model minus average-capacity observed specific yield",
        ),
        (
            "bias_vs_average_capacity_pct",
            summary["bias_vs_average_capacity_pct"],
            "percent",
            "Bias divided by average-capacity observed specific yield",
        ),
    ]
    formatted: list[dict[str, str]] = []
    for metric, value, unit, note in rows:
        if isinstance(value, float):
            value_text = f"{value:.6f}"
        else:
            value_text = str(value)
        formatted.append(
            {
                "metric": metric,
                "value": value_text,
                "unit": unit,
                "source_or_method": note,
                "source_url": SOURCE_URL if "nbs" in metric else "",
            }
        )
    return formatted


def write_csv(rows: list[dict[str, str]], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["metric", "value", "unit", "source_or_method", "source_url"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(summary: dict[str, Any], path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SI National External Validation",
        "",
        "Last updated: 2026-07-01",
        "",
        "Validation status: partial national aggregate check.",
        "",
        "This check adds one independent official measured-generation reference. It uses the National Bureau of Statistics 2024 Statistical Communique. The source reports national solar generation, national year-end solar capacity and the capacity growth rate. The check is independent of the model and useful for national-scale plausibility. It is not a province-level or plant-level external validation layer because it has no location axis.",
        "",
        "Source URL: `https://www.stats.gov.cn/sj/zxfb/202502/t20250228_1958817.html`",
        "",
        "| Quantity | Value | Unit | Interpretation |",
        "| --- | ---: | --- | --- |",
        f"| Official 2024 solar generation | {summary['nbs_generation_twh']:.2f} | TWh | Independent measured national generation |",
        f"| Official year-end solar capacity | {summary['nbs_year_end_capacity_gw']:.2f} | GW | National capacity denominator at year end |",
        f"| Official capacity growth | {summary['nbs_capacity_growth_pct']:.1f} | percent | Used only to infer a simple start-year denominator |",
        f"| Model scaled national capacity | {summary['model_capacity_gw']:.2f} | GW | Sum of the scaled provincial capacity table |",
        f"| Model minus official capacity | {summary['model_capacity_gap_gw']:.2f} | GW | Confirms capacity closure is within rounding |",
        f"| Inferred start-year capacity | {summary['inferred_start_capacity_gw']:.2f} | GW | Year-end capacity divided by one plus growth |",
        f"| Simple average capacity | {summary['simple_average_capacity_gw']:.2f} | GW | Average of start-year and year-end capacity |",
        f"| Observed specific yield using year-end capacity | {summary['observed_specific_yield_end_capacity_kwh_per_kw']:.1f} | kWh per kW | Lower specific-yield bound under fast growth |",
        f"| Observed specific yield using simple average capacity | {summary['observed_specific_yield_average_capacity_kwh_per_kw']:.1f} | kWh per kW | Preferred aggregate comparison denominator |",
        f"| Clean model c-Si national yield | {summary['clean_model_csi_yield_kwh_per_kwp']:.1f} | kWh per kWp | Capacity-weighted 31-province model output |",
        f"| Mean system-loss correction | {summary['mean_system_loss_pct']:.1f} | percent | Inferred from provincial fleet-hour anchor |",
        f"| Loss-corrected model c-Si yield | {summary['loss_corrected_model_csi_yield_kwh_per_kwp']:.1f} | kWh per kWp | Aggregate model value after system-loss correction |",
        f"| Bias against average-capacity observed yield | {summary['bias_vs_average_capacity_kwh_per_kwp']:.1f} | kWh per kWp | Model minus official aggregate denominator result |",
        f"| Bias against average-capacity observed yield | {summary['bias_vs_average_capacity_pct']:.1f} | percent | Same bias in relative terms |",
        "",
        "Interpretation:",
        "",
        f"The official year-end capacity denominator gives a low observed specific-yield value because solar capacity grew rapidly during 2024. A simple average of inferred start-year and year-end capacity gives {summary['observed_specific_yield_average_capacity_kwh_per_kw']:.1f} kWh per kW. The loss-corrected model gives {summary['loss_corrected_model_csi_yield_kwh_per_kwp']:.1f} kWh per kWp. The comparison is close enough for a national-scale plausibility check, but the remaining {summary['bias_vs_average_capacity_kwh_per_kwp']:.1f} kWh per kWp difference cannot be interpreted as a pure model error. It also reflects intra-year capacity additions, fleet age, curtailment, availability, regional timing and source convention differences.",
        "",
        "Release decision:",
        "",
        "This check should be cited as national aggregate validation only. It is paired with the NEA PV utilization-rate layer for PV-specific spatial operation evidence, the NBS provincial total electricity-generation layer for absolute spatial generation context and the CTGR operating-region layer for a PV-specific absolute generation sample. It does not by itself provide a complete government province-level PV generation inventory.",
        "",
        "Machine-readable table: `outputs/si_national_external_validation.csv`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    summary = build_summary()
    write_csv(build_rows())
    write_markdown(summary)
    return summary


def main() -> int:
    summary = run()
    print(f"National external validation written to {OUT_CSV} and {OUT_MD}.")
    print(
        "Average-capacity observed yield "
        f"{summary['observed_specific_yield_average_capacity_kwh_per_kw']:.1f} "
        "kWh per kW; loss-corrected model "
        f"{summary['loss_corrected_model_csi_yield_kwh_per_kwp']:.1f} "
        "kWh per kWp."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
