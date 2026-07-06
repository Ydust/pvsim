"""Build a company-asset spatial PV generation validation layer."""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "data" / "source_tables" / "ctgr_pv_generation_by_region_2024.csv"
OUT_CSV = ROOT / "outputs" / "si_ctgr_spatial_pv_generation_validation.csv"
OUT_SUMMARY = ROOT / "outputs" / "si_ctgr_spatial_pv_generation_validation_summary.csv"
OUT_MD = ROOT / "docs" / "SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md"

REPORTED_PV_GENERATION_100M_KWH = 254.01
REPORTED_PV_GRID_100M_KWH = 248.3109
NBS_NATIONAL_SOLAR_GENERATION_TWH = 839.04


def load_source(path: Path = SOURCE_CSV) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 25:
        raise ValueError(f"Expected 25 operating-region rows, got {len(rows)}")
    regions = [row["operating_region"].strip() for row in rows]
    if len(set(regions)) != len(regions):
        raise ValueError("Duplicate operating region in CTGR PV generation table")
    missing = [
        row["operating_region"]
        for row in rows
        if row["source_audit_status"] != "row-level official corporate disclosure complete"
    ]
    if missing:
        raise ValueError(f"Incomplete CTGR source-audit rows: {missing}")
    return rows


def build_layer() -> tuple[list[dict[str, str]], dict[str, str]]:
    rows = load_source()
    layer: list[dict[str, str]] = []
    generation_values = []
    grid_values = []
    for row in rows:
        generation_10000_kwh = float(row["pv_generation_10000_kwh"])
        grid_10000_kwh = float(row["pv_grid_generation_10000_kwh"])
        generation_values.append(generation_10000_kwh)
        grid_values.append(grid_10000_kwh)
        layer.append(
            {
                "operating_region": row["operating_region"],
                "year": "2024",
                "pv_generation_10000_kwh": f"{generation_10000_kwh:.0f}",
                "pv_generation_100million_kwh": f"{generation_10000_kwh / 10000.0:.4f}",
                "pv_generation_twh": f"{generation_10000_kwh / 100000.0:.5f}",
                "pv_grid_generation_10000_kwh": f"{grid_10000_kwh:.0f}",
                "pv_grid_generation_100million_kwh": f"{grid_10000_kwh / 10000.0:.4f}",
                "pv_grid_generation_twh": f"{grid_10000_kwh / 100000.0:.5f}",
                "grid_export_ratio_pct": f"{grid_10000_kwh / generation_10000_kwh * 100.0:.2f}",
                "reporting_company": row["reporting_company"],
                "stock_code": row["stock_code"],
                "source_name": row["source_name"],
                "source_url": row["source_url"],
                "source_doc": row["source_doc"],
                "report_pages": row["report_pages"],
                "retrieved_date": row["retrieved_date"],
                "source_audit_status": row["source_audit_status"],
                "validation_role": "exchange-disclosed company-asset PV absolute generation sample with operating-region axis",
            }
        )
    total_generation_10000 = sum(generation_values)
    total_grid_10000 = sum(grid_values)
    total_generation_100m = total_generation_10000 / 10000.0
    total_grid_100m = total_grid_10000 / 10000.0
    total_generation_twh = total_generation_10000 / 100000.0
    top_region = max(layer, key=lambda row: float(row["pv_generation_10000_kwh"]))
    summary = {
        "check": "CTGR operating-region PV generation layer",
        "operating_region_rows": str(len(layer)),
        "company_pv_generation_10000_kwh": f"{total_generation_10000:.0f}",
        "company_pv_generation_100million_kwh": f"{total_generation_100m:.4f}",
        "company_pv_generation_twh": f"{total_generation_twh:.5f}",
        "annual_report_pv_generation_100million_kwh": f"{REPORTED_PV_GENERATION_100M_KWH:.2f}",
        "generation_difference_100million_kwh": f"{total_generation_100m - REPORTED_PV_GENERATION_100M_KWH:.4f}",
        "company_pv_grid_generation_10000_kwh": f"{total_grid_10000:.0f}",
        "company_pv_grid_generation_100million_kwh": f"{total_grid_100m:.4f}",
        "company_pv_grid_generation_twh": f"{total_grid_10000 / 100000.0:.5f}",
        "annual_report_pv_grid_generation_100million_kwh": f"{REPORTED_PV_GRID_100M_KWH:.4f}",
        "grid_generation_difference_100million_kwh": f"{total_grid_100m - REPORTED_PV_GRID_100M_KWH:.4f}",
        "mean_grid_export_ratio_pct": f"{total_grid_10000 / total_generation_10000 * 100.0:.2f}",
        "median_region_pv_generation_100million_kwh": f"{median(generation_values) / 10000.0:.4f}",
        "largest_region": top_region["operating_region"],
        "largest_region_pv_generation_100million_kwh": top_region["pv_generation_100million_kwh"],
        "share_of_nbs_national_solar_generation_pct": f"{total_generation_twh / NBS_NATIONAL_SOLAR_GENERATION_TWH * 100.0:.2f}",
        "source_url": rows[0]["source_url"],
        "source_doc": rows[0]["source_doc"],
        "pv_specific": "True",
        "national_complete_inventory": "False",
        "government_statistical_inventory": "False",
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
        key=lambda row: float(row["pv_generation_10000_kwh"]),
        reverse=True,
    )[:8]
    lines = [
        "# SI CTGR Spatial PV Generation Validation",
        "",
        "Last updated: 2026-07-01",
        "",
        "Validation status: company-asset PV absolute generation layer with a spatial operating-region axis available.",
        "",
        "This appendix adds an exchange-filed corporate PV generation layer from China Three Gorges Renewables 2024 annual report. The annual report table gives operating-region and generation-type rows for 2024, including PV generation and PV grid export in ten-thousand kWh. The layer is independent of the model and PV-specific. It covers the company's controlled assets, so it is a sample validation layer rather than a national provincial PV generation inventory.",
        "",
        "Source URL: `https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-04-30/600905_20250430_FYJO.pdf`",
        "",
        "| Check | Value |",
        "| --- | ---: |",
        f"| Operating-region rows | {summary['operating_region_rows']} |",
        f"| Company PV generation | {summary['company_pv_generation_100million_kwh']} 100 million kWh |",
        f"| Company PV generation | {summary['company_pv_generation_twh']} TWh |",
        f"| Annual-report PV generation total | {summary['annual_report_pv_generation_100million_kwh']} 100 million kWh |",
        f"| Difference from annual-report total | {summary['generation_difference_100million_kwh']} 100 million kWh |",
        f"| Company PV grid export | {summary['company_pv_grid_generation_100million_kwh']} 100 million kWh |",
        f"| Mean grid-export ratio | {summary['mean_grid_export_ratio_pct']} percent |",
        f"| Share of NBS national solar generation | {summary['share_of_nbs_national_solar_generation_pct']} percent |",
        "",
        "Largest company PV generation regions:",
        "",
        "| Operating region | PV generation | PV grid export | Grid-export ratio |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in top:
        lines.append(
            "| "
            f"{row['operating_region']} | "
            f"{row['pv_generation_100million_kwh']} 100 million kWh | "
            f"{row['pv_grid_generation_100million_kwh']} 100 million kWh | "
            f"{row['grid_export_ratio_pct']} percent |"
        )
    lines += [
        "",
        "Interpretation:",
        "",
        "The row total closes to the annual-report PV generation total of 254.01 hundred million kWh within rounding. The company sample supplies the previously missing PV-specific absolute generation layer with a spatial axis. It must not be used as a complete government province-level PV generation inventory.",
        "",
        "This layer should be cited together with the NEA PV utilization-rate layer, the NBS national solar-generation check and the NBS provincial total electricity-generation context. Together they provide official national scale, official grid-operation scale, official total-electricity spatial context and exchange-disclosed PV-specific absolute generation sample evidence.",
        "",
        "Machine-readable outputs: `outputs/si_ctgr_spatial_pv_generation_validation.csv` and `outputs/si_ctgr_spatial_pv_generation_validation_summary.csv`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> tuple[list[dict[str, str]], dict[str, str]]:
    layer, summary = build_layer()
    write_csv(layer, summary)
    write_markdown(layer, summary)
    return layer, summary


def main() -> int:
    layer, summary = run()
    print(f"CTGR spatial PV generation layer written to {OUT_CSV} and {OUT_MD}.")
    print(
        "Rows: "
        f"{len(layer)}; company PV generation: "
        f"{summary['company_pv_generation_100million_kwh']} 100 million kWh."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
