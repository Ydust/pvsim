# SI PV Utilization External Validation

Last updated: 2026-07-01

Validation status: location-resolved official PV generation-utilization layer available.

This appendix adds an external official PV operation layer from the National Energy Administration. The source is the 2024 National renewable power development monitoring and evaluation result, Table 4. It reports 2023 and 2024 PV generation utilization rates by region. The layer has a location axis and is independent of the model.

Source URL: `https://www.nea.gov.cn/20251113/cc1fb0298a2944f8bd5441f67c9be9b3/c.html`

| Check | Value |
| --- | ---: |
| Province-level rows after aggregating Inner Mongolia grid regions | 31 |
| National 2024 PV generation utilization rate | 96.8 percent |
| Median province-level 2024 utilization rate | 98.1 percent |
| Lowest province-level 2024 utilization rate | 68.6 percent |
| Regions at 100 percent utilization | 4 |

Lowest utilization regions:

| Province | Reporting regions | 2023 rate | 2024 rate | 2024 deficit |
| --- | --- | ---: | ---: | ---: |
| 西藏 | 西藏 | 78.0 | 68.6 | 31.4 |
| 青海 | 青海 | 91.4 | 90.3 | 9.7 |
| 甘肃 | 甘肃 | 95.0 | 91.3 | 8.7 |
| 新疆 | 新疆 | 96.9 | 92.2 | 7.8 |
| 陕西 | 陕西 | 96.5 | 94.5 | 5.5 |
| 宁夏 | 宁夏 | 96.4 | 95.3 | 4.7 |

Interpretation:

This layer validates a grid-operation component of PV generation, not clean device physics. It should be used to explain where observed PV output is affected by curtailment and grid absorption. It should not be used as a replacement for province-level monthly PV generation or plant-level generation records.

The layer closes the location-resolved official PV operation evidence gap. The CTGR operating-region layer adds a PV-specific absolute generation sample. A complete government province-level PV generation inventory remains a stronger future source target.

Machine-readable outputs: `outputs/si_pv_utilization_external_validation.csv` and `outputs/si_pv_utilization_external_validation_summary.csv`
