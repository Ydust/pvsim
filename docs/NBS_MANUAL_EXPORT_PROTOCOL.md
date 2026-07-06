# NBS Manual Export Protocol For Provincial PV Generation

Last updated: 2026-07-01

This protocol is the fallback path when National Data blocks scripted access. It defines the exact official export needed before the manuscript may claim a complete government province-level PV or solar absolute-generation inventory.

## Target

Use the National Bureau of Statistics National Data interface at `https://data.stats.gov.cn/easyquery.htm?cn=E0103`.

Export a 2024 province-level table only if the indicator is PV generation or solar generation and the unit is an absolute energy unit. Do not export installed capacity, utilization rate, utilization hours, total electricity generation, above-designated-size industrial generation or any derived calculation.

## Required File

Save the official export as:

`data/source_tables/provincial_pv_generation_2024_official.csv`

The accepted columns are:

| Column | Meaning |
| --- | --- |
| `province` | Province name matching the 31-province capacity table |
| `year` | Must be 2024 |
| `metric` | PV generation or solar generation |
| `generation` | Numeric absolute generation value |
| `unit` | TWh, GWh, MWh, kWh, 100 million kWh, 10 thousand kWh, 亿千瓦时, 万千瓦时 or 千瓦时 |
| `coverage` | Full fleet or equivalent full-coverage official wording |
| `source_name` | Official source agency |
| `source_url` | Official page URL |
| `source_doc` | Table, document or export name |
| `retrieved_date` | Retrieval date |
| `source_audit_status` | Row-level official complete |
| `source_note` | Brief row-level note |

## Validation

Run:

`.venv\Scripts\python.exe -m scripts.validate_government_pv_generation_inventory`

The gate accepts the file only when all checks pass:

| Requirement | Acceptance rule |
| --- | --- |
| Province coverage | Exactly 31 provinces, no duplicates |
| Metric | PV or solar absolute generation |
| Year | 2024 for every row |
| Unit | Directly convertible to TWh |
| Coverage | Full fleet, not a partial industrial, company or sample scope |
| Provenance | Official source URL or document ID on every row |
| Derivation | No capacity times hours, utilization-rate or model-derived rows |
| National closure | Sum closes to NBS national 2024 solar generation within 2 percent |

The validator writes:

`outputs/government_pv_generation_inventory_validation.csv`

`docs/SI_GOVERNMENT_PV_GENERATION_INVENTORY_VALIDATION.md`
