# SI Government PV Generation Inventory Validation

Last updated: 2026-07-01

Validation status: not accepted.

This gate validates a candidate complete government province-level PV or solar absolute-generation inventory. It accepts only a 31-province full-coverage official source table with absolute energy units, row-level provenance and national closure against the NBS 2024 national solar-generation aggregate.

| Check | Value |
| --- | ---: |
| Candidate file exists | False |
| Row count | 0 |
| Province count | 0 |
| Total generation | 0.000 TWh |
| National closure error | 100.000 percent |
| Submission ready | False |

The candidate is rejected if it is derived from capacity, fleet hours or utilization rates, or if it reports only above-designated-size industry, company assets, sample assets or another partial coverage.

Machine-readable validation output: `outputs/government_pv_generation_inventory_validation.csv`
