"""Build a row-level evidence matrix for provincial official source layers."""

from __future__ import annotations

import csv
from pathlib import Path

from pvsim.source_data import load_capacity_rows, load_pv_utilization_province_rows


ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "outputs" / "provincial_source_evidence_matrix.csv"
OUT_MD = ROOT / "docs" / "SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md"

FIELDNAMES = [
    "dataset",
    "province",
    "metric",
    "year",
    "value",
    "unit",
    "current_source_name",
    "current_source_url",
    "current_source_doc",
    "retrieved_date",
    "current_audit_status",
    "row_level_official_url",
    "row_level_official_document_id",
    "row_level_official_status",
    "required_evidence",
    "next_action",
]


def _capacity_worklist_rows() -> list[dict[str, str]]:
    rows = []
    for row in load_capacity_rows():
        complete = "row-level official" in row["source_audit_status"].lower()
        rows.append(
            {
                "dataset": "provincial_pv_capacity_2024",
                "province": row["province"],
                "metric": "scaled PV capacity",
                "year": "2024",
                "value": row["scaled_to_national_gw"],
                "unit": "GW",
                "current_source_name": row["source_name"],
                "current_source_url": row["source_url"],
                "current_source_doc": row["source_doc"],
                "retrieved_date": row["retrieved_date"],
                "current_audit_status": row["source_audit_status"],
                "row_level_official_url": row["source_url"] if complete else "",
                "row_level_official_document_id": row["source_doc"] if complete else "",
                "row_level_official_status": "complete" if complete else "pending",
                "required_evidence": "Official provincial or national table that reports the 2024 province value or a reproducible official aggregation path",
                "next_action": "No action for this row" if complete else "Add stable official URL or document identifier and update source table audit status",
            }
        )
    return rows


def _pv_utilization_rows() -> list[dict[str, str]]:
    rows = []
    for row in load_pv_utilization_province_rows():
        complete = "row-level official" in row["source_audit_status"].lower()
        rows.append(
            {
                "dataset": "nea_pv_utilization_rate_2024",
                "province": row["province"],
                "metric": "PV generation utilization rate",
                "year": row["year"],
                "value": row["pv_utilization_rate_pct_2024"],
                "unit": "percent",
                "current_source_name": row["source_name"],
                "current_source_url": row["source_url"],
                "current_source_doc": row["source_doc"],
                "retrieved_date": row["retrieved_date"],
                "current_audit_status": row["source_audit_status"],
                "row_level_official_url": row["source_url"] if complete else "",
                "row_level_official_document_id": row["source_doc"] if complete else "",
                "row_level_official_status": "complete" if complete else "pending",
                "required_evidence": "Official national table that reports the 2024 province or reporting-region PV generation utilization rate",
                "next_action": "No action for this row" if complete else "Add stable official URL or document identifier and update source table audit status",
            }
        )
    return rows


def build_rows() -> list[dict[str, str]]:
    return _capacity_worklist_rows() + _pv_utilization_rows()


def write_csv(rows: list[dict[str, str]], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]], path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = sum(1 for row in rows if row["row_level_official_status"] == "pending")
    complete = sum(1 for row in rows if row["row_level_official_status"] == "complete")
    capacity = sum(1 for row in rows if row["dataset"] == "provincial_pv_capacity_2024")
    utilization = sum(1 for row in rows if row["dataset"] == "nea_pv_utilization_rate_2024")
    capacity_pending = sum(
        1
        for row in rows
        if row["dataset"] == "provincial_pv_capacity_2024"
        and row["row_level_official_status"] == "pending"
    )
    utilization_pending = sum(
        1
        for row in rows
        if row["dataset"] == "nea_pv_utilization_rate_2024"
        and row["row_level_official_status"] == "pending"
    )
    lines = [
        "# SI Provincial Source Evidence Matrix",
        "",
        "Last updated: 2026-07-01",
        "",
        "Evidence status: capacity rows complete, PV utilization-rate rows complete.",
        "",
        "This file records the row-level official evidence used by the journal-facing source audit. It covers provincial PV capacity and the official NEA PV generation-utilization layer.",
        "",
        "| Scope | Rows | Complete row-level official evidence | Pending row-level official evidence |",
        "| --- | ---: | ---: | ---: |",
        f"| Provincial PV capacity 2024 | {capacity} | {capacity - capacity_pending} | {capacity_pending} |",
        f"| NEA provincial PV utilization rate 2024 | {utilization} | {utilization - utilization_pending} | {utilization_pending} |",
        f"| Total | {len(rows)} | {complete} | {pending} |",
        "",
        "Required evidence fields:",
        "",
        "| Field | Meaning |",
        "| --- | --- |",
        "| row_level_official_url | Stable official URL for the row value or the official table that contains it |",
        "| row_level_official_document_id | Official document number, statistical bulletin identifier or archive identifier |",
        "| row_level_official_status | pending or complete |",
        "| required_evidence | The exact evidence needed to close the row |",
        "| next_action | The next source-audit action |",
        "",
        "Release rule:",
        "",
        "A provincial row should be marked complete only after the value can be traced to an official document or to a reproducible official aggregation path. Source-family provenance alone remains insufficient for a Joule-plus release package.",
        "",
        "The versioned provincial fleet-hour table is retained for the system-level validation figure but is no longer counted as a release-gated official source layer.",
        "",
        "Machine-readable matrix: `outputs/provincial_source_evidence_matrix.csv`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> list[dict[str, str]]:
    rows = build_rows()
    write_csv(rows)
    write_markdown(rows)
    return rows


def main() -> int:
    rows = run()
    pending = sum(1 for row in rows if row["row_level_official_status"] == "pending")
    print(f"Provincial source evidence matrix written to {OUT_CSV} and {OUT_MD}.")
    print(f"Rows checked: {len(rows)}; pending row-level official evidence: {pending}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
