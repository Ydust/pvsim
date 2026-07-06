# SI Provincial Source Evidence Matrix

Last updated: 2026-07-01

Evidence status: capacity rows complete, PV utilization-rate rows complete.

This file records the row-level official evidence used by the journal-facing source audit. It covers provincial PV capacity and the official NEA PV generation-utilization layer.

| Scope | Rows | Complete row-level official evidence | Pending row-level official evidence |
| --- | ---: | ---: | ---: |
| Provincial PV capacity 2024 | 31 | 31 | 0 |
| NEA provincial PV utilization rate 2024 | 31 | 31 | 0 |
| Total | 62 | 62 | 0 |

Required evidence fields:

| Field | Meaning |
| --- | --- |
| row_level_official_url | Stable official URL for the row value or the official table that contains it |
| row_level_official_document_id | Official document number, statistical bulletin identifier or archive identifier |
| row_level_official_status | pending or complete |
| required_evidence | The exact evidence needed to close the row |
| next_action | The next source-audit action |

Release rule:

A provincial row should be marked complete only after the value can be traced to an official document or to a reproducible official aggregation path. Source-family provenance alone remains insufficient for a Joule-plus release package.

The versioned provincial fleet-hour table is retained for the system-level validation figure but is no longer counted as a release-gated official source layer.

Machine-readable matrix: `outputs/provincial_source_evidence_matrix.csv`
