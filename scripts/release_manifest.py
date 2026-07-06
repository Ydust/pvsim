"""Build a file-level release manifest for the manuscript package."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "outputs" / "release_manifest.csv"
OUT_MD = ROOT / "docs" / "RELEASE_MANIFEST.md"


@dataclass(frozen=True)
class ManifestTarget:
    path: str
    group: str
    role: str


TARGETS = [
    ManifestTarget("README.md", "package metadata", "Repository overview"),
    ManifestTarget("CITATION.cff", "package metadata", "Citation metadata"),
    ManifestTarget(".zenodo.json", "package metadata", "Archive metadata draft"),
    ManifestTarget("requirements-lock.txt", "environment", "Verified Python package lock"),
    ManifestTarget("pyproject.toml", "environment", "Test and package configuration"),
    ManifestTarget("docs/PAPER_C_draft.md", "manuscript", "English manuscript draft"),
    ManifestTarget("docs/PAPER_MAIN_COMPLETE.md", "manuscript", "Complete separated main manuscript"),
    ManifestTarget("docs/PAPER_MAIN_COMPLETE_zh.md", "manuscript", "Complete separated Chinese main manuscript"),
    ManifestTarget("docs/PAPER_C_draft_zh.md", "manuscript", "Chinese manuscript draft"),
    ManifestTarget("docs/SUPPORTING_INFORMATION_DRAFT.md", "manuscript", "Supporting information draft"),
    ManifestTarget("docs/SUPPORTING_INFORMATION_COMPLETE.md", "manuscript", "Complete separated supporting information"),
    ManifestTarget("docs/SUPPORTING_INFORMATION_COMPLETE_zh.md", "manuscript", "Complete separated Chinese supporting information"),
    ManifestTarget("docs/DATA_PROVENANCE.md", "provenance", "Input and assumption tiering"),
    ManifestTarget("docs/DATA_SOURCES_AND_REFERENCES_zh.md", "provenance", "Chinese data-source and reference-system overview"),
    ManifestTarget("docs/MODEL_ARCHITECTURE_AND_CALCULATION_LOGIC_zh.md", "provenance", "Chinese model architecture and calculation-logic overview"),
    ManifestTarget("docs/SOURCE_APPENDIX.md", "provenance", "Provincial source-table appendix"),
    ManifestTarget("docs/SI_SOURCE_AUDIT_STATUS.md", "provenance", "Provincial release-gate audit"),
    ManifestTarget("docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md", "provenance", "Provincial row-level source evidence worklist"),
    ManifestTarget("docs/EXTERNAL_VALIDATION_AUDIT.md", "provenance", "External validation local audit"),
    ManifestTarget("docs/GOVERNMENT_PV_GENERATION_INVENTORY_AUDIT.md", "provenance", "Government provincial PV generation inventory acquisition audit"),
    ManifestTarget("docs/NBS_MANUAL_EXPORT_PROTOCOL.md", "provenance", "Manual protocol for official provincial PV generation export"),
    ManifestTarget("docs/SI_GOVERNMENT_PV_GENERATION_INVENTORY_VALIDATION.md", "provenance", "Candidate government provincial PV generation inventory validation"),
    ManifestTarget("docs/SI_NATIONAL_EXTERNAL_VALIDATION.md", "provenance", "National aggregate external validation check"),
    ManifestTarget("docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md", "provenance", "Location-resolved PV utilization external validation"),
    ManifestTarget("docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md", "provenance", "NBS spatial absolute generation context"),
    ManifestTarget("docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md", "provenance", "CTGR spatial PV generation sample validation"),
    ManifestTarget("docs/REFERENCE_AUDIT.md", "provenance", "Crossref DOI audit"),
    ManifestTarget("docs/JOULE_PLUS_GAP_AUDIT.md", "review audit", "Remaining submission risks"),
    ManifestTarget("docs/SCIENTIFIC_HARDENING_CHECKLIST.md", "review audit", "Scientific hardening checklist"),
    ManifestTarget("docs/SI_SCIENTIFIC_DEFENSE_TABLES.md", "SI evidence", "Validation and robustness tables"),
    ManifestTarget("docs/SI_GRID_UNCERTAINTY.md", "SI evidence", "ERA5 grid uncertainty appendix"),
    ManifestTarget("docs/SI_CLOUD_SPECTRAL_SENSITIVITY.md", "SI evidence", "Cloud spectral boundary appendix"),
    ManifestTarget("docs/SI_SILICON_BASELINE_SENSITIVITY.md", "SI evidence", "Modern silicon baseline sensitivity"),
    ManifestTarget("docs/SI_PEROVSKITE_PARAMETER_SENSITIVITY.md", "SI evidence", "Perovskite parameter sensitivity"),
    ManifestTarget("docs/SI_MECHANISM_SPECIFICITY.md", "SI evidence", "Mechanism specificity checks"),
    ManifestTarget("docs/SI_TRANSFERABILITY_BOUNDARY.md", "SI evidence", "Mechanism phase-plane transferability boundary"),
    ManifestTarget("data/source_tables/provincial_pv_capacity_2024.csv", "source table", "Provincial PV capacity"),
    ManifestTarget("data/source_tables/provincial_fleet_hours_2024.csv", "source table", "Provincial fleet utilisation hours"),
    ManifestTarget("data/source_tables/nea_pv_utilization_rate_2024.csv", "source table", "NEA regional PV generation utilization rates"),
    ManifestTarget("data/source_tables/nbs_provincial_total_power_generation_2024.csv", "source table", "NBS provincial total electricity generation"),
    ManifestTarget("data/source_tables/ctgr_pv_generation_by_region_2024.csv", "source table", "CTGR operating-region PV generation"),
    ManifestTarget("data/source_tables/nea_2024_pv_construction.jpeg", "source evidence", "NEA 2024 PV construction official table image"),
    ManifestTarget("data/source_tables/nea_2024_renewable_monitoring_result.doc", "source evidence", "NEA renewable monitoring official attachment"),
    ManifestTarget("data/source_tables/nbs_2025_yearbook_C09_19.jpg", "source evidence", "NBS 2025 yearbook Table 9-19 official image"),
    ManifestTarget("data/source_tables/sse_600905_2024_annual_report.pdf", "source evidence", "CTGR 2024 annual report official exchange filing"),
    ManifestTarget("outputs/figures/NEWFig1_inversion.png", "main figure", "Fig 1 image"),
    ManifestTarget("outputs/figures/NEWFig2_mechanisms.png", "main figure", "Fig 2 image"),
    ManifestTarget("outputs/figures/NEWFig3_segmentation.png", "main figure", "Fig 3 image"),
    ManifestTarget("outputs/figures/NEWFig4_economics_timing.png", "main figure", "Fig 4 image"),
    ManifestTarget("outputs/figures/NEWFig5_deployment.png", "main figure", "Fig 5 image"),
    ManifestTarget("outputs/si_source_audit_status.csv", "SI data", "Source-audit summary data"),
    ManifestTarget("outputs/provincial_source_evidence_matrix.csv", "SI data", "Provincial row-level source evidence worklist"),
    ManifestTarget("outputs/external_validation_local_audit.csv", "SI data", "External validation local audit data"),
    ManifestTarget("outputs/government_pv_generation_inventory_audit.csv", "SI data", "Government provincial PV generation inventory acquisition audit data"),
    ManifestTarget("outputs/government_pv_generation_inventory_validation.csv", "SI data", "Candidate government provincial PV generation inventory validation data"),
    ManifestTarget("outputs/si_national_external_validation.csv", "SI data", "National aggregate external validation data"),
    ManifestTarget("outputs/si_pv_utilization_external_validation.csv", "SI data", "Location-resolved PV utilization external validation data"),
    ManifestTarget("outputs/si_pv_utilization_external_validation_summary.csv", "SI data", "Location-resolved PV utilization external validation summary"),
    ManifestTarget("outputs/si_nbs_spatial_generation_validation.csv", "SI data", "NBS spatial generation validation data"),
    ManifestTarget("outputs/si_nbs_spatial_generation_validation_summary.csv", "SI data", "NBS spatial generation validation summary"),
    ManifestTarget("outputs/si_ctgr_spatial_pv_generation_validation.csv", "SI data", "CTGR spatial PV generation validation data"),
    ManifestTarget("outputs/si_ctgr_spatial_pv_generation_validation_summary.csv", "SI data", "CTGR spatial PV generation validation summary"),
    ManifestTarget("outputs/si_silicon_baseline_sensitivity_summary.csv", "SI data", "Silicon baseline summary data"),
    ManifestTarget("outputs/si_perovskite_parameter_sensitivity_summary.csv", "SI data", "Perovskite parameter summary data"),
    ManifestTarget("outputs/si_mechanism_specificity.csv", "SI data", "Mechanism specificity data"),
    ManifestTarget("outputs/si_transferability_phase_summary.csv", "SI data", "Transferability phase-plane summary"),
    ManifestTarget("outputs/figures/SI_transferability_phase_plane.png", "SI figure", "Transferability phase-plane figure"),
    ManifestTarget("outputs/si_grid_uncertainty_quantiles.csv", "SI data", "Grid uncertainty quantiles"),
    ManifestTarget("outputs/si_cloud_spectral_sensitivity_summary.csv", "SI data", "Cloud spectral summary data"),
    ManifestTarget("pvsim/materials.py", "core code", "Device parameter definitions"),
    ManifestTarget("pvsim/source_data.py", "core code", "Versioned source-table loaders"),
    ManifestTarget("pvsim/economic_priors.py", "core code", "Monte Carlo economic priors"),
    ManifestTarget("scripts/source_audit_gate.py", "analysis script", "Source-audit release gate"),
    ManifestTarget("scripts/provincial_source_evidence_matrix.py", "analysis script", "Provincial source evidence worklist"),
    ManifestTarget("scripts/external_validation_audit.py", "analysis script", "External validation local audit"),
    ManifestTarget("scripts/government_pv_generation_inventory_audit.py", "analysis script", "Government provincial PV generation inventory acquisition audit"),
    ManifestTarget("scripts/validate_government_pv_generation_inventory.py", "analysis script", "Candidate government provincial PV generation inventory validation"),
    ManifestTarget("scripts/national_external_validation.py", "analysis script", "National aggregate external validation"),
    ManifestTarget("scripts/pv_utilization_external_validation.py", "analysis script", "Location-resolved PV utilization external validation"),
    ManifestTarget("scripts/nbs_spatial_generation_validation.py", "analysis script", "NBS spatial generation validation"),
    ManifestTarget("scripts/ctgr_spatial_pv_generation_validation.py", "analysis script", "CTGR spatial PV generation validation"),
    ManifestTarget("scripts/silicon_baseline_sensitivity.py", "analysis script", "Silicon baseline sensitivity"),
    ManifestTarget("scripts/perovskite_parameter_sensitivity.py", "analysis script", "Perovskite parameter sensitivity"),
    ManifestTarget("scripts/mechanism_specificity.py", "analysis script", "Mechanism specificity checks"),
    ManifestTarget("scripts/global_transferability_boundary.py", "analysis script", "Transferability phase-plane boundary"),
    ManifestTarget("scripts/grid_uncertainty_appendix.py", "analysis script", "Grid uncertainty appendix"),
    ManifestTarget("scripts/cloud_spectral_sensitivity.py", "analysis script", "Cloud spectral boundary test"),
    ManifestTarget("tests/test_data_integrity.py", "tests", "Source-table and capacity closure tests"),
    ManifestTarget("tests/test_external_validation_audit.py", "tests", "External validation local audit tests"),
    ManifestTarget("tests/test_government_pv_generation_inventory_audit.py", "tests", "Government provincial PV generation inventory acquisition audit tests"),
    ManifestTarget("tests/test_validate_government_pv_generation_inventory.py", "tests", "Candidate government provincial PV generation inventory validation tests"),
    ManifestTarget("tests/test_national_external_validation.py", "tests", "National aggregate external validation tests"),
    ManifestTarget("tests/test_pv_utilization_external_validation.py", "tests", "Location-resolved PV utilization external validation tests"),
    ManifestTarget("tests/test_nbs_spatial_generation_validation.py", "tests", "NBS spatial generation validation tests"),
    ManifestTarget("tests/test_ctgr_spatial_pv_generation_validation.py", "tests", "CTGR spatial PV generation validation tests"),
    ManifestTarget("tests/test_source_audit_gate.py", "tests", "Source-audit gate tests"),
    ManifestTarget("tests/test_provincial_source_evidence_matrix.py", "tests", "Provincial source evidence worklist tests"),
    ManifestTarget("tests/test_silicon_baseline_sensitivity.py", "tests", "Silicon baseline sensitivity tests"),
    ManifestTarget("tests/test_perovskite_parameter_sensitivity.py", "tests", "Perovskite parameter sensitivity tests"),
    ManifestTarget("tests/test_mechanism_specificity.py", "tests", "Mechanism specificity tests"),
    ManifestTarget("tests/test_global_transferability_boundary.py", "tests", "Transferability boundary tests"),
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest() -> list[dict[str, str | int | bool]]:
    rows: list[dict[str, str | int | bool]] = []
    for target in TARGETS:
        path = ROOT / target.path
        exists = path.exists()
        rows.append(
            {
                "path": target.path,
                "group": target.group,
                "role": target.role,
                "exists": exists,
                "bytes": path.stat().st_size if exists else 0,
                "sha256": _sha256(path) if exists else "",
            }
        )
    return rows


def write_csv(rows: list[dict[str, str | int | bool]], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["path", "group", "role", "exists", "bytes", "sha256"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str | int | bool]], path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    missing = [row for row in rows if not row["exists"]]
    status = "complete" if not missing else "incomplete"
    lines = [
        "# Release Manifest",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Manifest status: {status}.",
        "",
        "This manifest records the journal-facing files that should travel together in a reproducibility package. It gives a file-level checksum boundary for the manuscript, SI evidence, source tables, core scripts, outputs and tests.",
        "",
        "| Group | File | Bytes | SHA256 | Role |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        sha = str(row["sha256"])
        sha_short = sha[:16] if sha else "missing"
        lines.append(
            "| "
            f"{row['group']} | "
            f"`{row['path']}` | "
            f"{row['bytes']} | "
            f"`{sha_short}` | "
            f"{row['role']} |"
        )
    lines += [
        "",
        "## Release Gate",
        "",
        "A final archive should include every file listed above or explain why a file is generated on demand. The full checksums are stored in `outputs/release_manifest.csv`.",
        "",
        "The manifest is not a substitute for row-level source provenance or external validation layers. Those are checked by the dedicated audit scripts.",
        "",
        "## Command",
        "",
        "`.venv\\Scripts\\python.exe -m scripts.release_manifest`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> list[dict[str, str | int | bool]]:
    rows = build_manifest()
    write_csv(rows)
    write_markdown(rows)
    return rows


def main() -> int:
    rows = run()
    missing = [row["path"] for row in rows if not row["exists"]]
    print(f"Release manifest written to {OUT_CSV} and {OUT_MD}.")
    if missing:
        print("Missing release targets:")
        for path in missing:
            print(f"  {path}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
