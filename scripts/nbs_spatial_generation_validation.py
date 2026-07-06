"""Build an official spatial absolute-generation context layer from NBS."""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "data" / "source_tables" / "nbs_provincial_total_power_generation_2024.csv"
OUT_CSV = ROOT / "outputs" / "si_nbs_spatial_generation_validation.csv"
OUT_SUMMARY = ROOT / "outputs" / "si_nbs_spatial_generation_validation_summary.csv"
OUT_MD = ROOT / "docs" / "SI_NBS_SPATIAL_GENERATION_VALIDATION.md"

NATIONAL_TOTAL_100M_KWH = 100868.81


def load_source(path: Path = SOURCE_CSV) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 31:
        raise ValueError(f"Expected 31 province rows, got {len(rows)}")
    return rows


def build_layer() -> tuple[list[dict[str, str]], dict[str, str]]:
    rows = load_source()
    layer: list[dict[str, str]] = []
    values = []
    for row in rows:
        value_100m_kwh = float(row["total_power_generation_100million_kwh"])
        values.append(value_100m_kwh)
        layer.append(
            {
                "province": row["province"],
                "year": "2024",
                "total_power_generation_100million_kwh": f"{value_100m_kwh:.2f}",
                "total_power_generation_twh": f"{value_100m_kwh / 10.0:.3f}",
                "source_name": row["source_name"],
                "source_url": row["source_url"],
                "source_doc": row["source_doc"],
                "retrieved_date": row["retrieved_date"],
                "source_audit_status": row["source_audit_status"],
                "validation_role": "official spatial absolute electricity-generation context, not PV-specific generation",
            }
        )
    total = sum(values)
    difference = total - NATIONAL_TOTAL_100M_KWH
    summary = {
        "check": "NBS provincial total electricity generation layer",
        "province_rows": str(len(layer)),
        "national_reference_100million_kwh": f"{NATIONAL_TOTAL_100M_KWH:.2f}",
        "province_sum_100million_kwh": f"{total:.2f}",
        "province_sum_minus_national_100million_kwh": f"{difference:.2f}",
        "largest_province": max(layer, key=lambda row: float(row["total_power_generation_100million_kwh"]))["province"],
        "largest_province_100million_kwh": max(values),
        "median_province_100million_kwh": f"{median(values):.2f}",
        "source_url": rows[0]["source_url"],
        "source_doc": rows[0]["source_doc"],
        "pv_specific": "False",
    }
    return layer, summary


def write_csv(layer: list[dict[str, str]], summary: dict[str, str]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(layer[0]))
        writer.writeheader()
        writer.writerows(layer)
    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)


def write_markdown(layer: list[dict[str, str]], summary: dict[str, str]) -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    top = sorted(
        layer,
        key=lambda row: float(row["total_power_generation_100million_kwh"]),
        reverse=True,
    )[:8]
    lines = [
        "# SI NBS Spatial Generation Validation",
        "",
        "Last updated: 2026-07-01",
        "",
        "Validation status: official spatial absolute electricity-generation context available.",
        "",
        "This appendix adds an official province-level absolute generation layer from the National Bureau of Statistics China Statistical Yearbook 2025, Table 9-19. The table reports total electricity generation by province for 2024.",
        "",
        "Source URL: `https://www.stats.gov.cn/sj/ndsj/2025/html/C09-19.jpg`",
        "",
        "| Check | Value |",
        "| --- | ---: |",
        f"| Province-level rows | {summary['province_rows']} |",
        f"| National reference | {summary['national_reference_100million_kwh']} 100 million kWh |",
        f"| Province sum | {summary['province_sum_100million_kwh']} 100 million kWh |",
        f"| Province sum minus national reference | {summary['province_sum_minus_national_100million_kwh']} 100 million kWh |",
        f"| Median province generation | {summary['median_province_100million_kwh']} 100 million kWh |",
        "",
        "Largest provincial electricity-generation rows:",
        "",
        "| Province | 2024 total generation | 2024 total generation |",
        "| --- | ---: | ---: |",
    ]
    for row in top:
        lines.append(
            "| "
            f"{row['province']} | "
            f"{row['total_power_generation_100million_kwh']} 100 million kWh | "
            f"{row['total_power_generation_twh']} TWh |"
        )
    lines += [
        "",
        "Interpretation:",
        "",
        "This layer is an official spatial measured-generation layer, but it reports total electricity generation rather than PV generation. It strengthens the external data package by adding an absolute generation quantity with a province axis. It must not be cited as province-level PV generation validation.",
        "",
        "The PV-specific spatial operation layer remains the NEA PV generation utilization-rate layer. The CTGR operating-region layer adds a PV-specific absolute measured generation sample. A complete government province-level PV generation table remains a stronger future source target.",
        "",
        "Machine-readable outputs: `outputs/si_nbs_spatial_generation_validation.csv` and `outputs/si_nbs_spatial_generation_validation_summary.csv`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> tuple[list[dict[str, str]], dict[str, str]]:
    layer, summary = build_layer()
    write_csv(layer, summary)
    write_markdown(layer, summary)
    return layer, summary


def main() -> int:
    layer, summary = run()
    print(f"NBS spatial generation layer written to {OUT_CSV} and {OUT_MD}.")
    print(
        "Rows: "
        f"{len(layer)}; province sum: {summary['province_sum_100million_kwh']} "
        "100 million kWh."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
