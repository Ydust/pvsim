"""Validate an official provincial PV or solar generation inventory."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from pvsim.source_data import load_capacity_rows


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "source_tables" / "provincial_pv_generation_2024_official.csv"
OUT_CSV = ROOT / "outputs" / "government_pv_generation_inventory_validation.csv"
OUT_MD = ROOT / "docs" / "SI_GOVERNMENT_PV_GENERATION_INVENTORY_VALIDATION.md"

NBS_NATIONAL_SOLAR_GENERATION_TWH = 839.04
MAX_NATIONAL_CLOSURE_ERROR_PCT = 2.0

REQUIRED_COLUMNS = [
    "province",
    "year",
    "metric",
    "generation",
    "unit",
    "coverage",
    "source_name",
    "source_url",
    "source_doc",
    "retrieved_date",
    "source_audit_status",
    "source_note",
]

UNIT_TO_TWH = {
    "TWh": 1.0,
    "GWh": 0.001,
    "MWh": 0.000001,
    "kWh": 0.000000001,
    "100 million kWh": 0.1,
    "10 thousand kWh": 0.00001,
    "亿千瓦时": 0.1,
    "万千瓦时": 0.00001,
    "千瓦时": 0.000000001,
}


@dataclass(frozen=True)
class ValidationResult:
    inventory_path: Path
    exists: bool
    row_count: int
    province_count: int
    missing_columns: tuple[str, ...]
    missing_provinces: tuple[str, ...]
    duplicate_provinces: tuple[str, ...]
    unsupported_units: tuple[str, ...]
    non_2024_rows: int
    non_absolute_metric_rows: int
    non_full_coverage_rows: int
    missing_provenance_rows: int
    derived_or_proxy_rows: int
    total_generation_twh: float
    national_closure_error_pct: float

    @property
    def submission_ready(self) -> bool:
        return (
            self.exists
            and self.row_count == 31
            and self.province_count == 31
            and not self.missing_columns
            and not self.missing_provinces
            and not self.duplicate_provinces
            and not self.unsupported_units
            and self.non_2024_rows == 0
            and self.non_absolute_metric_rows == 0
            and self.non_full_coverage_rows == 0
            and self.missing_provenance_rows == 0
            and self.derived_or_proxy_rows == 0
            and self.national_closure_error_pct <= MAX_NATIONAL_CLOSURE_ERROR_PCT
        )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _expected_provinces() -> list[str]:
    return sorted(row["province"] for row in load_capacity_rows())


def _unit_factor(unit: str) -> float:
    normalized = unit.strip()
    if normalized not in UNIT_TO_TWH:
        raise KeyError(normalized)
    return UNIT_TO_TWH[normalized]


def _is_absolute_pv_generation(metric: str) -> bool:
    text = metric.strip().lower()
    has_generation = "generation" in text or "发电量" in text
    has_pv = "pv" in text or "solar" in text or "光伏" in text or "太阳能" in text
    forbidden = ("capacity", "装机", "utilization", "利用率", "利用小时", "hour")
    return has_generation and has_pv and not any(term in text for term in forbidden)


def _is_full_coverage(coverage: str) -> bool:
    text = coverage.strip().lower()
    full_terms = ("full fleet", "all grid-connected", "all pv", "全口径", "全部", "全量", "并网全量")
    excluded_terms = ("above-designated", "规模以上", "规上", "sample", "样本", "company", "企业")
    return any(term in text for term in full_terms) and not any(term in text for term in excluded_terms)


def _is_derived_or_proxy(row: dict[str, str]) -> bool:
    text = " ".join(
        row.get(field, "")
        for field in ["metric", "coverage", "source_doc", "source_audit_status", "source_note"]
    ).lower()
    forbidden = (
        "derived",
        "proxy",
        "capacity times hours",
        "estimated",
        "modelled",
        "modeled",
        "推算",
        "估算",
        "模型",
        "利用小时",
        "利用率",
        "装机乘",
    )
    return any(term in text for term in forbidden)


def validate_inventory(path: Path = DEFAULT_INPUT) -> ValidationResult:
    expected = _expected_provinces()
    if not path.exists():
        return ValidationResult(
            inventory_path=path,
            exists=False,
            row_count=0,
            province_count=0,
            missing_columns=tuple(REQUIRED_COLUMNS),
            missing_provinces=tuple(expected),
            duplicate_provinces=(),
            unsupported_units=(),
            non_2024_rows=0,
            non_absolute_metric_rows=0,
            non_full_coverage_rows=0,
            missing_provenance_rows=0,
            derived_or_proxy_rows=0,
            total_generation_twh=0.0,
            national_closure_error_pct=100.0,
        )

    rows = _read_csv(path)
    columns = list(rows[0].keys()) if rows else []
    missing_columns = tuple(column for column in REQUIRED_COLUMNS if column not in columns)
    if missing_columns:
        return ValidationResult(
            inventory_path=path,
            exists=True,
            row_count=len(rows),
            province_count=0,
            missing_columns=missing_columns,
            missing_provinces=tuple(expected),
            duplicate_provinces=(),
            unsupported_units=(),
            non_2024_rows=0,
            non_absolute_metric_rows=0,
            non_full_coverage_rows=0,
            missing_provenance_rows=len(rows),
            derived_or_proxy_rows=0,
            total_generation_twh=0.0,
            national_closure_error_pct=100.0,
        )

    provinces = [row["province"].strip() for row in rows]
    province_set = set(provinces)
    duplicate_provinces = tuple(sorted({province for province in provinces if provinces.count(province) > 1}))
    missing_provinces = tuple(province for province in expected if province not in province_set)
    unsupported_units = tuple(sorted({row["unit"].strip() for row in rows if row["unit"].strip() not in UNIT_TO_TWH}))
    non_2024_rows = sum(1 for row in rows if row["year"].strip() != "2024")
    non_absolute_metric_rows = sum(1 for row in rows if not _is_absolute_pv_generation(row["metric"]))
    non_full_coverage_rows = sum(1 for row in rows if not _is_full_coverage(row["coverage"]))
    provenance_fields = ["source_name", "source_url", "source_doc", "retrieved_date", "source_audit_status"]
    missing_provenance_rows = sum(
        1 for row in rows if any(not row[field].strip() for field in provenance_fields)
    )
    derived_or_proxy_rows = sum(1 for row in rows if _is_derived_or_proxy(row))

    total_generation_twh = 0.0
    if not unsupported_units:
        for row in rows:
            total_generation_twh += float(row["generation"]) * _unit_factor(row["unit"])
    closure_error_pct = (
        abs(total_generation_twh - NBS_NATIONAL_SOLAR_GENERATION_TWH)
        / NBS_NATIONAL_SOLAR_GENERATION_TWH
        * 100.0
    )

    return ValidationResult(
        inventory_path=path,
        exists=True,
        row_count=len(rows),
        province_count=len(province_set),
        missing_columns=missing_columns,
        missing_provinces=missing_provinces,
        duplicate_provinces=duplicate_provinces,
        unsupported_units=unsupported_units,
        non_2024_rows=non_2024_rows,
        non_absolute_metric_rows=non_absolute_metric_rows,
        non_full_coverage_rows=non_full_coverage_rows,
        missing_provenance_rows=missing_provenance_rows,
        derived_or_proxy_rows=derived_or_proxy_rows,
        total_generation_twh=total_generation_twh,
        national_closure_error_pct=closure_error_pct,
    )


def result_row(result: ValidationResult) -> dict[str, str]:
    missing_provinces = (
        "all_expected_provinces"
        if not result.exists and len(result.missing_provinces) == 31
        else "; ".join(result.missing_provinces)
    )
    return {
        "inventory_path": str(result.inventory_path),
        "exists": str(result.exists),
        "row_count": str(result.row_count),
        "province_count": str(result.province_count),
        "missing_columns": "; ".join(result.missing_columns),
        "missing_provinces": missing_provinces,
        "duplicate_provinces": "; ".join(result.duplicate_provinces),
        "unsupported_units": "; ".join(result.unsupported_units),
        "non_2024_rows": str(result.non_2024_rows),
        "non_absolute_metric_rows": str(result.non_absolute_metric_rows),
        "non_full_coverage_rows": str(result.non_full_coverage_rows),
        "missing_provenance_rows": str(result.missing_provenance_rows),
        "derived_or_proxy_rows": str(result.derived_or_proxy_rows),
        "total_generation_twh": f"{result.total_generation_twh:.6f}",
        "national_closure_error_pct": f"{result.national_closure_error_pct:.6f}",
        "submission_ready": str(result.submission_ready),
    }


def write_outputs(result: ValidationResult) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    row = result_row(result)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    status = "accepted" if result.submission_ready else "not accepted"
    lines = [
        "# SI Government PV Generation Inventory Validation",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Validation status: {status}.",
        "",
        "This gate validates a candidate complete government province-level PV or solar absolute-generation inventory. It accepts only a 31-province full-coverage official source table with absolute energy units, row-level provenance and national closure against the NBS 2024 national solar-generation aggregate.",
        "",
        "| Check | Value |",
        "| --- | ---: |",
        f"| Candidate file exists | {result.exists} |",
        f"| Row count | {result.row_count} |",
        f"| Province count | {result.province_count} |",
        f"| Total generation | {result.total_generation_twh:.3f} TWh |",
        f"| National closure error | {result.national_closure_error_pct:.3f} percent |",
        f"| Submission ready | {result.submission_ready} |",
        "",
        "The candidate is rejected if it is derived from capacity, fleet hours or utilization rates, or if it reports only above-designated-size industry, company assets, sample assets or another partial coverage.",
        "",
        "Machine-readable validation output: `outputs/government_pv_generation_inventory_validation.csv`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(path: Path = DEFAULT_INPUT) -> ValidationResult:
    result = validate_inventory(path)
    write_outputs(result)
    return result


def main() -> int:
    result = run()
    print(f"Government PV generation inventory validation written to {OUT_CSV} and {OUT_MD}.")
    print(f"Submission ready: {result.submission_ready}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
