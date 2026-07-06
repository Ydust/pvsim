# Government Provincial PV Generation Inventory Audit

Last updated: 2026-07-01

Status: complete official provincial PV generation inventory not acquired.

This audit records the dedicated attempt to acquire a complete government source table for 2024 province-level PV or solar absolute generation. The table has not been acquired and must not be claimed in the manuscript or SI.

A row can pass only when it carries province, year, PV or solar generation, an absolute energy unit, official source URL or document ID and retrieval date. Derived values from capacity, fleet hours or utilization rates do not pass this gate.

| Candidate | Authority | Result | Blocking issue | Complete inventory | Follow-up |
| --- | --- | --- | --- | --- | --- |
| 2024 renewable power monitoring result | National Energy Administration | Reports national solar generation and regional PV utilization rates, but no province-level PV absolute generation rows | Metric is utilization rate by region, not absolute generation in kWh by province | False | Do not use this layer as a province-level PV generation volume inventory |
| National Data regional annual database | National Bureau of Statistics | Interface is the official candidate location for annual province data, but API calls from this environment returned 403 UrlACL and no export was acquired | Machine-readable table cannot be downloaded in the current environment | False | A browser-side official export is required before any row can be accepted |
| China Statistical Yearbook 2025 Table 9-19 | National Bureau of Statistics | Reports provincial total electricity generation and hydropower, but no solar or PV generation column | PV-specific absolute generation is absent | False | Use only as official provincial total-electricity context |
| 2018 PV power statistics page | National Energy Administration | Reports national PV generation and provincial PV capacity rows, but not provincial PV generation volume rows | Appendix columns are capacity, not generation | False | Useful for understanding NEA publication pattern, not for 2024 province generation validation |
| Local xuni_fangzhen and PV_WRF workspaces | Local reproducibility package | No complete government provincial PV absolute generation table was found | Existing accepted layers are NEA utilization rates, NBS total electricity generation and CTGR company-asset generation | False | Keep the complete government inventory marked unavailable until an official source table is added |
| Public web search for 2024 provincial PV generation | Official and public web sources | Search results returned national values, capacity tables, utilization rates, company samples or secondary pages, not a complete official province table | No official 31-province PV generation inventory was located | False | Repeat only if a new official release or manual NBS export is available |
| Candidate official export validation gate | Local reproducibility package | Validation gate is available, but the official 2024 provincial PV generation source table is not present | No candidate file exists at data/source_tables/provincial_pv_generation_2024_official.csv | False | Run the validator after an official National Data export or equivalent government table is added |

## Decision

The current package remains strong enough to cite official national solar generation, official regional PV utilization-rate validation, official provincial total-electricity context and an exchange-filed PV absolute generation sample. It is not strong enough to claim a complete government province-level PV absolute generation inventory.

The next acceptable action is an official export from National Data or another government document that contains 31 province rows for 2024 PV or solar generation in kWh or a directly convertible energy unit. The validator in `scripts/validate_government_pv_generation_inventory.py` will reject partial, proxy or derived tables. Until the validator passes, every reference to this dataset stays unavailable.

Machine-readable audit output: `outputs/government_pv_generation_inventory_audit.csv`
