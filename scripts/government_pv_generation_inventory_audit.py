"""Audit attempts to acquire a complete official provincial PV generation inventory."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "outputs" / "government_pv_generation_inventory_audit.csv"
OUT_MD = ROOT / "docs" / "GOVERNMENT_PV_GENERATION_INVENTORY_AUDIT.md"


@dataclass(frozen=True)
class AcquisitionCheck:
    candidate: str
    authority: str
    source_url: str
    evidence_checked: str
    result: str
    blocking_issue: str
    complete_government_inventory: bool
    follow_up: str


def candidate_rows() -> list[AcquisitionCheck]:
    return [
        AcquisitionCheck(
            candidate="2024 renewable power monitoring result",
            authority="National Energy Administration",
            source_url="https://www.nea.gov.cn/20251113/cc1fb0298a2944f8bd5441f67c9be9b3/c.html",
            evidence_checked="Official notice page and local official Word attachment",
            result="Reports national solar generation and regional PV utilization rates, but no province-level PV absolute generation rows",
            blocking_issue="Metric is utilization rate by region, not absolute generation in kWh by province",
            complete_government_inventory=False,
            follow_up="Do not use this layer as a province-level PV generation volume inventory",
        ),
        AcquisitionCheck(
            candidate="National Data regional annual database",
            authority="National Bureau of Statistics",
            source_url="https://data.stats.gov.cn/easyquery.htm?cn=E0103",
            evidence_checked="Official regional annual interface and data API endpoints",
            result="Interface is the official candidate location for annual province data, but API calls from this environment returned 403 UrlACL and no export was acquired",
            blocking_issue="Machine-readable table cannot be downloaded in the current environment",
            complete_government_inventory=False,
            follow_up="A browser-side official export is required before any row can be accepted",
        ),
        AcquisitionCheck(
            candidate="China Statistical Yearbook 2025 Table 9-19",
            authority="National Bureau of Statistics",
            source_url="https://www.stats.gov.cn/sj/ndsj/2025/html/C09-19.jpg",
            evidence_checked="Official yearbook image table for provincial major energy product output",
            result="Reports provincial total electricity generation and hydropower, but no solar or PV generation column",
            blocking_issue="PV-specific absolute generation is absent",
            complete_government_inventory=False,
            follow_up="Use only as official provincial total-electricity context",
        ),
        AcquisitionCheck(
            candidate="2018 PV power statistics page",
            authority="National Energy Administration",
            source_url="https://www.nea.gov.cn/2019-03/19/c_137907428.htm",
            evidence_checked="Official historical PV statistics page and appendix layout",
            result="Reports national PV generation and provincial PV capacity rows, but not provincial PV generation volume rows",
            blocking_issue="Appendix columns are capacity, not generation",
            complete_government_inventory=False,
            follow_up="Useful for understanding NEA publication pattern, not for 2024 province generation validation",
        ),
        AcquisitionCheck(
            candidate="Local xuni_fangzhen and PV_WRF workspaces",
            authority="Local reproducibility package",
            source_url="local workspace search",
            evidence_checked="CSV, JSON, Markdown, Python, Word, PDF, image and spreadsheet inventories",
            result="No complete government provincial PV absolute generation table was found",
            blocking_issue="Existing accepted layers are NEA utilization rates, NBS total electricity generation and CTGR company-asset generation",
            complete_government_inventory=False,
            follow_up="Keep the complete government inventory marked unavailable until an official source table is added",
        ),
        AcquisitionCheck(
            candidate="Public web search for 2024 provincial PV generation",
            authority="Official and public web sources",
            source_url="multiple searches on 2026-07-01",
            evidence_checked="Queries for provincial PV generation, solar generation, NEA, NBS, State Grid and monitoring-center sources",
            result="Search results returned national values, capacity tables, utilization rates, company samples or secondary pages, not a complete official province table",
            blocking_issue="No official 31-province PV generation inventory was located",
            complete_government_inventory=False,
            follow_up="Repeat only if a new official release or manual NBS export is available",
        ),
        AcquisitionCheck(
            candidate="Candidate official export validation gate",
            authority="Local reproducibility package",
            source_url="scripts/validate_government_pv_generation_inventory.py",
            evidence_checked="Schema, provenance, coverage, unit and national-closure validation logic",
            result="Validation gate is available, but the official 2024 provincial PV generation source table is not present",
            blocking_issue="No candidate file exists at data/source_tables/provincial_pv_generation_2024_official.csv",
            complete_government_inventory=False,
            follow_up="Run the validator after an official National Data export or equivalent government table is added",
        ),
    ]


def build_rows() -> list[dict[str, str | bool]]:
    return [
        {
            "candidate": row.candidate,
            "authority": row.authority,
            "source_url": row.source_url,
            "evidence_checked": row.evidence_checked,
            "result": row.result,
            "blocking_issue": row.blocking_issue,
            "complete_government_inventory": row.complete_government_inventory,
            "follow_up": row.follow_up,
        }
        for row in candidate_rows()
    ]


def audit_status(rows: list[dict[str, str | bool]] | None = None) -> dict[str, str | bool | int]:
    rows = build_rows() if rows is None else rows
    obtained = any(bool(row["complete_government_inventory"]) for row in rows)
    return {
        "obtained": obtained,
        "checked_candidates": len(rows),
        "decision": (
            "complete official provincial PV generation inventory acquired"
            if obtained
            else "complete official provincial PV generation inventory not acquired"
        ),
        "required_acceptance_fields": "province, year, PV or solar generation, absolute energy unit, official source URL or document ID, retrieval date",
    }


def write_csv(rows: list[dict[str, str | bool]], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "candidate",
        "authority",
        "source_url",
        "evidence_checked",
        "result",
        "blocking_issue",
        "complete_government_inventory",
        "follow_up",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str | bool]], path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status = audit_status(rows)
    lines = [
        "# Government Provincial PV Generation Inventory Audit",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Status: {status['decision']}.",
        "",
        "This audit records the dedicated attempt to acquire a complete government source table for 2024 province-level PV or solar absolute generation. The table has not been acquired and must not be claimed in the manuscript or SI.",
        "",
        "A row can pass only when it carries province, year, PV or solar generation, an absolute energy unit, official source URL or document ID and retrieval date. Derived values from capacity, fleet hours or utilization rates do not pass this gate.",
        "",
        "| Candidate | Authority | Result | Blocking issue | Complete inventory | Follow-up |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['candidate']} | "
            f"{row['authority']} | "
            f"{row['result']} | "
            f"{row['blocking_issue']} | "
            f"{row['complete_government_inventory']} | "
            f"{row['follow_up']} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        "The current package remains strong enough to cite official national solar generation, official regional PV utilization-rate validation, official provincial total-electricity context and an exchange-filed PV absolute generation sample. It is not strong enough to claim a complete government province-level PV absolute generation inventory.",
        "",
        "The next acceptable action is an official export from National Data or another government document that contains 31 province rows for 2024 PV or solar generation in kWh or a directly convertible energy unit. The validator in `scripts/validate_government_pv_generation_inventory.py` will reject partial, proxy or derived tables. Until the validator passes, every reference to this dataset stays unavailable.",
        "",
        "Machine-readable audit output: `outputs/government_pv_generation_inventory_audit.csv`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> list[dict[str, str | bool]]:
    rows = build_rows()
    write_csv(rows)
    write_markdown(rows)
    return rows


def main() -> int:
    rows = run()
    status = audit_status(rows)
    print(f"Government PV generation inventory audit written to {OUT_CSV} and {OUT_MD}.")
    print(status["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
