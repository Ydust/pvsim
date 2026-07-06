# SI NBS Spatial Generation Validation

Last updated: 2026-07-01

Validation status: official spatial absolute electricity-generation context available.

This appendix adds an official province-level absolute generation layer from the National Bureau of Statistics China Statistical Yearbook 2025, Table 9-19. The table reports total electricity generation by province for 2024.

Source URL: `https://www.stats.gov.cn/sj/ndsj/2025/html/C09-19.jpg`

| Check | Value |
| --- | ---: |
| Province-level rows | 31 |
| National reference | 100868.81 100 million kWh |
| Province sum | 100868.83 100 million kWh |
| Province sum minus national reference | 0.02 100 million kWh |
| Median province generation | 2602.85 100 million kWh |

Largest provincial electricity-generation rows:

| Province | 2024 total generation | 2024 total generation |
| --- | ---: | ---: |
| Inner Mongolia | 8344.00 100 million kWh | 834.400 TWh |
| Guangdong | 7354.51 100 million kWh | 735.451 TWh |
| Jiangsu | 6807.37 100 million kWh | 680.737 TWh |
| Shandong | 6773.25 100 million kWh | 677.325 TWh |
| Xinjiang | 5478.02 100 million kWh | 547.802 TWh |
| Sichuan | 5307.27 100 million kWh | 530.727 TWh |
| Zhejiang | 4983.55 100 million kWh | 498.355 TWh |
| Yunnan | 4646.34 100 million kWh | 464.634 TWh |

Interpretation:

This layer is an official spatial measured-generation layer, but it reports total electricity generation rather than PV generation. It strengthens the external data package by adding an absolute generation quantity with a province axis. It must not be cited as province-level PV generation validation.

The PV-specific spatial operation layer remains the NEA PV generation utilization-rate layer. The CTGR operating-region layer adds a PV-specific absolute measured generation sample. A complete government province-level PV generation table remains a stronger future source target.

Machine-readable outputs: `outputs/si_nbs_spatial_generation_validation.csv` and `outputs/si_nbs_spatial_generation_validation_summary.csv`
