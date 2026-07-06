# SI Source Audit Status

Last updated: 2026-07-01

Current gate status: submission ready.

This audit covers the journal-facing provincial official source layers. It is a release gate for data provenance, not a model result.

| Table | Rows | Missing provenance fields | Row-level official complete | Row-level official pending | Source URLs | Retrieved dates |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Provincial PV capacity 2024 | 31 | 0 | 31 | 0 | 1 | 2026-07-01 |
| NEA provincial PV utilization rate 2024 | 31 | 0 | 31 | 0 | 1 | 2026-07-01 |

## Interpretation

The current provincial tables contain 62 rows. All required provenance fields are populated, so the missing provenance field count is 0.

The release gate now finds 0 rows with row-level official documents still pending.

The capacity table and the NEA PV utilization-rate layer can be described as row-level official. The fleet-hour table remains a versioned system-level anchor and is not counted as journal-facing row-level official evidence.

The row-level evidence worklist is reported in `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` and `outputs/provincial_source_evidence_matrix.csv`.

## Commands

| Purpose | Command |
| --- | --- |
| Regenerate this audit | `.venv\Scripts\python.exe -m scripts.source_audit_gate` |
| Regenerate the row-level worklist | `.venv\Scripts\python.exe -m scripts.provincial_source_evidence_matrix` |
| Enforce final release gate | `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` |
