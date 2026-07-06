"""Audit local workspaces for an independent measured PV generation layer."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PV_WRF_ROOT = Path("C:/new/PV_WRF")
OUT_CSV = ROOT / "outputs" / "external_validation_local_audit.csv"
OUT_MD = ROOT / "docs" / "EXTERNAL_VALIDATION_AUDIT.md"


@dataclass(frozen=True)
class Candidate:
    name: str
    path: Path
    data_type: str
    has_generation: bool
    has_capacity: bool
    has_time_axis: bool
    has_location: bool
    acceptable: bool
    note: str


def candidate_rows() -> list[Candidate]:
    return [
        Candidate(
            name="Provincial fleet utilisation source table",
            path=ROOT / "data/source_tables/provincial_fleet_hours_2024.csv",
            data_type="annual provincial utilisation hours",
            has_generation=False,
            has_capacity=False,
            has_time_axis=True,
            has_location=True,
            acceptable=False,
            note="Useful system-level spatial anchor, but not an independent measured generation layer and not counted as a release-gated official row layer",
        ),
        Candidate(
            name="Fleet validation derived output",
            path=ROOT / "outputs/si_fleet_validation_by_province.csv",
            data_type="derived model validation table",
            has_generation=False,
            has_capacity=True,
            has_time_axis=True,
            has_location=True,
            acceptable=False,
            note="Derived from the model and fleet-hour anchor, so it cannot serve as an independent external validation dataset",
        ),
        Candidate(
            name="NBS national aggregate solar generation check",
            path=ROOT / "outputs/si_national_external_validation.csv",
            data_type="official national aggregate measured generation check",
            has_generation=True,
            has_capacity=True,
            has_time_axis=True,
            has_location=False,
            acceptable=False,
            note="Independent official measured generation and capacity at national aggregate scale, useful for plausibility but not location-resolved validation",
        ),
        Candidate(
            name="NBS provincial total electricity generation layer",
            path=ROOT / "outputs/si_nbs_spatial_generation_validation.csv",
            data_type="official spatial absolute total-electricity generation layer",
            has_generation=True,
            has_capacity=False,
            has_time_axis=True,
            has_location=True,
            acceptable=False,
            note="Official province-level measured electricity generation for 2024, useful as absolute spatial context but not PV-specific generation validation",
        ),
        Candidate(
            name="NEA provincial PV generation utilization rate",
            path=ROOT / "outputs/si_pv_utilization_external_validation.csv",
            data_type="official location-resolved PV generation-utilization layer",
            has_generation=True,
            has_capacity=False,
            has_time_axis=True,
            has_location=True,
            acceptable=True,
            note="Official PV-specific regional utilization-rate layer for 2023 and 2024, acceptable as location-resolved operation validation but not as absolute generation-volume validation",
        ),
        Candidate(
            name="CTGR operating-region PV generation layer",
            path=ROOT / "outputs/si_ctgr_spatial_pv_generation_validation.csv",
            data_type="exchange-disclosed company-asset PV absolute generation sample",
            has_generation=True,
            has_capacity=False,
            has_time_axis=True,
            has_location=True,
            acceptable=True,
            note="SSE-filed CTGR annual report reports 2024 PV generation and grid export by operating region, acceptable as PV-specific absolute measured generation sample but not as a national official province inventory",
        ),
        Candidate(
            name="Climate TRACE China power source API response",
            path=ROOT / "data/source_tables/climatetrace_power_CHN_2024.json",
            data_type="third-party power-source activity inventory without China solar rows",
            has_generation=True,
            has_capacity=True,
            has_time_axis=True,
            has_location=True,
            acceptable=False,
            note="Downloaded 2024 China power-source response contains point-source MWh activity but no solar asset rows in the inspected API result",
        ),
        Candidate(
            name="PV_WRF global power plant database",
            path=PV_WRF_ROOT / "analysis_outputs/source_data/global_power_plant_database.csv",
            data_type="plant catalogue",
            has_generation=False,
            has_capacity=True,
            has_time_axis=False,
            has_location=True,
            acceptable=False,
            note="Contains plant metadata and capacity-factor estimates, not plant-level or province-level measured PV generation",
        ),
        Candidate(
            name="PV_WRF Climate TRACE power files",
            path=PV_WRF_ROOT / "analysis_outputs/source_data",
            data_type="power-sector emissions inventory",
            has_generation=False,
            has_capacity=False,
            has_time_axis=True,
            has_location=True,
            acceptable=False,
            note="Useful emissions context, but not a measured PV generation validation layer for China",
        ),
        Candidate(
            name="PV_WRF climate inputs",
            path=PV_WRF_ROOT / "climate_data",
            data_type="climate forcing inputs",
            has_generation=False,
            has_capacity=False,
            has_time_axis=True,
            has_location=True,
            acceptable=False,
            note="Contains ERA5, TerraClimate, MODIS and land-cover inputs, not measured PV generation",
        ),
        Candidate(
            name="PV_WRF annual solar NetCDF",
            path=PV_WRF_ROOT / "year_sum_solar.nc",
            data_type="solar or climate gridded field",
            has_generation=False,
            has_capacity=False,
            has_time_axis=True,
            has_location=True,
            acceptable=False,
            note="May support climate or resource context, but it is not an observed PV generation layer",
        ),
    ]


def build_rows() -> list[dict[str, str | bool]]:
    rows = []
    for candidate in candidate_rows():
        rows.append(
            {
                "name": candidate.name,
                "path": str(candidate.path),
                "exists": candidate.path.exists(),
                "data_type": candidate.data_type,
                "has_generation": candidate.has_generation,
                "has_capacity": candidate.has_capacity,
                "has_time_axis": candidate.has_time_axis,
                "has_location": candidate.has_location,
                "acceptable": candidate.acceptable,
                "note": candidate.note,
            }
        )
    return rows


def write_csv(rows: list[dict[str, str | bool]], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name",
        "path",
        "exists",
        "data_type",
        "has_generation",
        "has_capacity",
        "has_time_axis",
        "has_location",
        "acceptable",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str | bool]], path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    acceptable = [row for row in rows if row["acceptable"]]
    status = "available" if acceptable else "not available"
    pv_absolute_samples = [
        row
        for row in rows
        if row["has_generation"]
        and row["has_location"]
        and "PV absolute generation sample" in str(row["data_type"])
    ]
    pv_absolute_status = "available" if pv_absolute_samples else "not available"
    spatial_absolute = [
        row
        for row in rows
        if row["has_generation"] and row["has_location"] and "absolute" in str(row["data_type"])
    ]
    absolute_status = "available" if spatial_absolute else "not available"
    national_checks = [
        row for row in rows if row["has_generation"] and row["has_capacity"] and not row["has_location"]
    ]
    lines = [
        "# External Validation Local Audit",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Independent location-resolved PV operation layer: {status}.",
        "",
        f"PV-specific absolute generation sample with spatial axis: {pv_absolute_status}.",
        "",
        f"Official spatial absolute generation context layer: {absolute_status}.",
        "",
        "This audit checks the local `xuni_fangzhen` and `PV_WRF` workspaces for data that could satisfy the manuscript P0 location-resolved external-validation requirement.",
        "",
        "| Candidate | Exists | Data type | Generation | Capacity | Time axis | Location | Acceptable | Note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['name']} | "
            f"{row['exists']} | "
            f"{row['data_type']} | "
            f"{row['has_generation']} | "
            f"{row['has_capacity']} | "
            f"{row['has_time_axis']} | "
            f"{row['has_location']} | "
            f"{row['acceptable']} | "
            f"{row['note']} |"
        )
    lines += [
        "",
        "## Conclusion",
        "",
        "The current local workspace now contains a usable official PV generation-utilization layer with a location axis. The existing fleet-hour table remains valuable as a system-level spatial anchor, but it is not a substitute for plant-level monthly generation, province-level monthly generation or multi-year official utilisation records with row-level provenance.",
        "",
        "A national aggregate official solar generation check is available when `outputs/si_national_external_validation.csv` has been generated. It is independent and measured, so it strengthens national-scale plausibility. It does not close the P0 location requirement because it has no plant or provincial location axis.",
        "",
        "The NBS provincial total electricity-generation layer adds an official absolute measured-generation layer with a province axis. It does not close the PV-specific absolute generation-volume gap because it reports total electricity generation rather than PV generation.",
        "",
        "The NEA PV utilization-rate layer closes the location-resolved official PV operation evidence gap. It does not close the stricter PV-specific absolute generation-volume gap because it reports utilization rates, not generation in kWh by province.",
        "",
        "The CTGR operating-region layer closes the available external PV-specific absolute generation sample gap. It reports measured PV generation and grid export by operating region for one exchange-filed company asset portfolio. It does not close the complete government province-level PV generation inventory gap.",
        "",
        "The required fields and acceptance tests remain defined in `docs/EXTERNAL_VALIDATION_REQUIREMENTS.md`.",
    ]
    if not national_checks:
        lines.insert(
            -1,
            "No national aggregate measured-generation check is currently listed.",
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> list[dict[str, str | bool]]:
    rows = build_rows()
    write_csv(rows)
    write_markdown(rows)
    return rows


def main() -> int:
    rows = run()
    print(f"External validation audit written to {OUT_CSV} and {OUT_MD}.")
    if not any(row["acceptable"] for row in rows):
        print("No acceptable independent measured PV generation layer is available locally.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
