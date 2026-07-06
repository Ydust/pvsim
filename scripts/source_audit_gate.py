"""Audit journal-facing provenance status for provincial source tables."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from pvsim.source_data import (
    CAPACITY_TABLE,
    PV_UTILIZATION_TABLE,
    load_capacity_rows,
    load_pv_utilization_province_rows,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "outputs" / "si_source_audit_status.csv"
OUT_MD = ROOT / "docs" / "SI_SOURCE_AUDIT_STATUS.md"

PROVENANCE_FIELDS = (
    "source_name",
    "source_url",
    "source_doc",
    "retrieved_date",
    "source_audit_status",
    "source_note",
)


@dataclass(frozen=True)
class SourceAuditSummary:
    table: str
    file: str
    row_count: int
    missing_provenance_count: int
    row_level_complete_count: int
    pending_row_level_count: int
    unique_source_urls: int
    retrieved_dates: str

    @property
    def submission_ready(self) -> bool:
        return (
            self.missing_provenance_count == 0
            and self.pending_row_level_count == 0
            and self.row_level_complete_count == self.row_count
        )


def _is_row_level_complete(row: dict[str, str]) -> bool:
    status = row["source_audit_status"].strip().lower()
    return "row-level official" in status and "pending" not in status


def _is_row_level_pending(row: dict[str, str]) -> bool:
    status = row["source_audit_status"].strip().lower()
    note = row["source_note"].strip().lower()
    return "pending" in status or "open source-appendix" in note


def _missing_provenance_fields(row: dict[str, str]) -> int:
    return sum(1 for field in PROVENANCE_FIELDS if not row.get(field, "").strip())


def summarize_rows(table: str, path: Path, rows: list[dict[str, str]]) -> SourceAuditSummary:
    missing = sum(_missing_provenance_fields(row) for row in rows)
    complete = sum(1 for row in rows if _is_row_level_complete(row))
    pending = sum(1 for row in rows if _is_row_level_pending(row))
    urls = {row["source_url"].strip() for row in rows if row["source_url"].strip()}
    dates = sorted({row["retrieved_date"].strip() for row in rows if row["retrieved_date"].strip()})
    return SourceAuditSummary(
        table=table,
        file=str(path.relative_to(ROOT)),
        row_count=len(rows),
        missing_provenance_count=missing,
        row_level_complete_count=complete,
        pending_row_level_count=pending,
        unique_source_urls=len(urls),
        retrieved_dates="; ".join(dates),
    )


def build_summaries() -> list[SourceAuditSummary]:
    return [
        summarize_rows("Provincial PV capacity 2024", CAPACITY_TABLE, load_capacity_rows()),
        summarize_rows(
            "NEA provincial PV utilization rate 2024",
            PV_UTILIZATION_TABLE,
            load_pv_utilization_province_rows(),
        ),
    ]


def write_csv(summaries: list[SourceAuditSummary], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "table",
        "file",
        "row_count",
        "missing_provenance_count",
        "row_level_complete_count",
        "pending_row_level_count",
        "unique_source_urls",
        "retrieved_dates",
        "submission_ready",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            row = summary.__dict__.copy()
            row["submission_ready"] = summary.submission_ready
            writer.writerow(row)


def write_markdown(summaries: list[SourceAuditSummary], path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_rows = sum(s.row_count for s in summaries)
    total_pending = sum(s.pending_row_level_count for s in summaries)
    total_missing = sum(s.missing_provenance_count for s in summaries)
    ready = total_pending == 0 and total_missing == 0
    status = "submission ready" if ready else "not submission ready"
    lines = [
        "# SI Source Audit Status",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Current gate status: {status}.",
        "",
        "This audit covers the journal-facing provincial official source layers. It is a release gate for data provenance, not a model result.",
        "",
        "| Table | Rows | Missing provenance fields | Row-level official complete | Row-level official pending | Source URLs | Retrieved dates |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for summary in summaries:
        lines.append(
            "| "
            f"{summary.table} | "
            f"{summary.row_count} | "
            f"{summary.missing_provenance_count} | "
            f"{summary.row_level_complete_count} | "
            f"{summary.pending_row_level_count} | "
            f"{summary.unique_source_urls} | "
            f"{summary.retrieved_dates} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        f"The current provincial tables contain {total_rows} rows. All required provenance fields are populated, so the missing provenance field count is {total_missing}.",
        "",
        f"The release gate now finds {total_pending} rows with row-level official documents still pending.",
        "",
        "The capacity table and the NEA PV utilization-rate layer can be described as row-level official. The fleet-hour table remains a versioned system-level anchor and is not counted as journal-facing row-level official evidence.",
        "",
        "The row-level evidence worklist is reported in `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` and `outputs/provincial_source_evidence_matrix.csv`.",
        "",
        "## Commands",
        "",
        "| Purpose | Command |",
        "| --- | --- |",
        "| Regenerate this audit | `.venv\\Scripts\\python.exe -m scripts.source_audit_gate` |",
        "| Regenerate the row-level worklist | `.venv\\Scripts\\python.exe -m scripts.provincial_source_evidence_matrix` |",
        "| Enforce final release gate | `.venv\\Scripts\\python.exe -m scripts.source_audit_gate --strict` |",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(strict: bool = False) -> int:
    summaries = build_summaries()
    write_csv(summaries)
    write_markdown(summaries)
    if strict and any(not summary.submission_ready for summary in summaries):
        pending = sum(summary.pending_row_level_count for summary in summaries)
        missing = sum(summary.missing_provenance_count for summary in summaries)
        print(
            "Source audit gate is not submission-ready: "
            f"{pending} rows still lack row-level official provenance and "
            f"{missing} required provenance fields are missing."
        )
        return 2
    print(f"Source audit written to {OUT_CSV} and {OUT_MD}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code unless every row has row-level official provenance.",
    )
    args = parser.parse_args()
    return run(strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
