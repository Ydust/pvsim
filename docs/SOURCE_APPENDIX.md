# Source Appendix For Provincial Inputs

Last updated: 2026-07-01

This appendix documents the provincial source tables used by the paper scripts after the source-data audit.

## Provincial PV Capacity In 2024

Source table: `data/source_tables/provincial_pv_capacity_2024.csv`

The 31-province capacity table now uses the National Energy Administration 2024 PV power construction status table. The official source reports cumulative grid-connected PV capacity by province in ten-thousand kW. The table is converted to GW. Xinjiang and Xinjiang Production and Construction Corps are merged to preserve the 31-province modelling scope. The official 31-province distribution sums to 885.673 GW. The paper uses the same provincial distribution and applies a uniform scale factor so that the capacity-weighted model input closes to the national 2024 PV total of 886.6 GW.

| Field | Meaning |
| --- | --- |
| `province` | Province-level administrative unit |
| `raw_gw` | Compiled provincial value in GW |
| `scaled_to_national_gw` | Model input after uniform scaling to 886.6 GW |
| `scale_factor` | 886.6 divided by 885.673 |
| `national_total_gw` | National total used for closure |
| `source_name` | Source family |
| `source_url` | Stable source-family URL |
| `source_doc` | Source-family document description |
| `retrieved_date` | Date when the source-family entry was checked |
| `source_audit_status` | Row audit status |
| `source_note` | Audit note for this row |

The code uses `pvsim.provinces.PROVINCE_PV_2024_GW`, while `RAW_PROVINCE_PV_2024_GW` keeps the unscaled source distribution.

Current audit status: every capacity row has row-level official provenance from the National Energy Administration source page and official table image.

Machine-readable source audit: `docs/SI_SOURCE_AUDIT_STATUS.md`

Row-level evidence worklist: `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md`

## Provincial PV Fleet Utilisation Hours

Source table: `data/source_tables/provincial_fleet_hours_2024.csv`

This table is used only as a system-level spatial anchor. It compares clean-physics digital-twin yields with real fleet utilisation hours. Fleet utilisation includes BOS losses, curtailment, dispatch and O&M effects, so it should not be described as pure device-physics validation.

| Field | Meaning |
| --- | --- |
| `province` | Province-level administrative unit |
| `year` | Reporting year |
| `fleet_hours` | Fleet utilisation hours in h per year |
| `source_name` | Source family |
| `source_url` | Stable source-family URL |
| `source_doc` | Source-family document description |
| `retrieved_date` | Date when the source-family entry was checked |
| `source_audit_status` | Row audit status |
| `source_note` | Audit note for this row |

The code reads this table through `pvsim.source_data.load_fleet_hours`.

Current audit status: the source-family fields are populated for every row. This table is retained as a system-level anchor and is not counted as a journal-facing row-level official source layer.

## Official PV Utilization Rate

Source table: `data/source_tables/nea_pv_utilization_rate_2024.csv`

The National Energy Administration renewable monitoring result reports 2023 and 2024 PV generation utilization rates by region. Inner Mongolia is reported by grid region and is aggregated to one modelling province in the derived 31-row layer. This source is PV-specific and official, but it reports utilization rate rather than absolute PV generation in kWh.

Derived SI layer: `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md`

Row-level evidence matrix: `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md`

## NBS Provincial Total Electricity Generation

Source table: `data/source_tables/nbs_provincial_total_power_generation_2024.csv`

The National Bureau of Statistics China Statistical Yearbook 2025 Table 9-19 reports 2024 total electricity generation by province. The transcribed 31-province sum is 100868.83 hundred million kWh, matching the national table value of 100868.81 hundred million kWh within rounding. This is an official spatial absolute generation context layer. It is not PV-specific and should not be cited as province-level PV generation.

Derived SI layer: `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md`

## CTGR Operating-Region PV Generation

Source table: `data/source_tables/ctgr_pv_generation_by_region_2024.csv`

China Three Gorges Renewables reports 2024 generation and grid-export quantities by operating region and generation type in its exchange-filed 2024 annual report. The PV rows cover 25 operating regions and sum to 254.0083 hundred million kWh of PV generation and 248.3109 hundred million kWh of PV grid export. The generation total closes to the annual-report PV total of 254.01 hundred million kWh within rounding.

This is a PV-specific absolute measured generation layer with a spatial operating-region axis. It is a company asset sample, not a complete government province-level PV generation inventory.

Derived SI layer: `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md`

## Validation Checks

The following automated checks guard these inputs:

| Check | File |
| --- | --- |
| The scaled capacity table closes to 886.6 GW | `tests/test_data_integrity.py` |
| The raw capacity table remains 885.673 GW for auditability | `tests/test_data_integrity.py` |
| Capacity source CSV values match `pvsim.provinces` | `tests/test_data_integrity.py` |
| Capacity rows include complete provenance fields | `tests/test_data_integrity.py` |
| Fleet-hour source table covers all 31 provinces | `tests/test_data_integrity.py` |
| Fleet-hour rows include complete provenance fields | `tests/test_data_integrity.py` |
| Source-audit release gate checks 62 official rows | `tests/test_source_audit_gate.py` |
| Source evidence matrix covers all 62 official rows | `tests/test_provincial_source_evidence_matrix.py` |
| PV utilization external layer covers 31 provinces | `tests/test_pv_utilization_external_validation.py` |
| NBS spatial generation layer covers 31 provinces | `tests/test_nbs_spatial_generation_validation.py` |
| CTGR PV generation layer covers 25 operating regions and closes to annual report total | `tests/test_ctgr_spatial_pv_generation_validation.py` |

Current verification result: `58 passed`.

## Current Audit Status

The release-gated official source matrix now has 62 complete rows and 0 pending rows. It consists of 31 capacity rows and 31 NEA PV utilization-rate rows. The fleet-hour table remains versioned and test-covered as a system-level validation anchor, but it is not described as an official row-level source table.

The non-strict source audit command writes `outputs/si_source_audit_status.csv` and `docs/SI_SOURCE_AUDIT_STATUS.md`. The strict command now passes for the release-gated official source layers.
