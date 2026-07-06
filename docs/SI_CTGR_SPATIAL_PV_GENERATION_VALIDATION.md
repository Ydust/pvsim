# SI CTGR Spatial PV Generation Validation

Last updated: 2026-07-01

Validation status: company-asset PV absolute generation layer with a spatial operating-region axis available.

This appendix adds an exchange-filed corporate PV generation layer from China Three Gorges Renewables 2024 annual report. The annual report table gives operating-region and generation-type rows for 2024, including PV generation and PV grid export in ten-thousand kWh. The layer is independent of the model and PV-specific. It covers the company's controlled assets, so it is a sample validation layer rather than a national provincial PV generation inventory.

Source URL: `https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-04-30/600905_20250430_FYJO.pdf`

| Check | Value |
| --- | ---: |
| Operating-region rows | 25 |
| Company PV generation | 254.0083 100 million kWh |
| Company PV generation | 25.40083 TWh |
| Annual-report PV generation total | 254.01 100 million kWh |
| Difference from annual-report total | -0.0017 100 million kWh |
| Company PV grid export | 248.3109 100 million kWh |
| Mean grid-export ratio | 97.76 percent |
| Share of NBS national solar generation | 3.03 percent |

Largest company PV generation regions:

| Operating region | PV generation | PV grid export | Grid-export ratio |
| --- | ---: | ---: | ---: |
| Inner Mongolia | 59.8048 100 million kWh | 58.1955 100 million kWh | 97.31 percent |
| Qinghai | 29.6328 100 million kWh | 29.1316 100 million kWh | 98.31 percent |
| Yunnan | 23.6053 100 million kWh | 22.9603 100 million kWh | 97.27 percent |
| Shanxi | 19.7705 100 million kWh | 19.4025 100 million kWh | 98.14 percent |
| Gansu | 13.4016 100 million kWh | 13.0725 100 million kWh | 97.54 percent |
| Anhui | 12.5900 100 million kWh | 12.3523 100 million kWh | 98.11 percent |
| Shandong | 12.3528 100 million kWh | 12.0863 100 million kWh | 97.84 percent |
| Zhejiang | 12.1879 100 million kWh | 11.8898 100 million kWh | 97.55 percent |

Interpretation:

The row total closes to the annual-report PV generation total of 254.01 hundred million kWh within rounding. The company sample supplies the previously missing PV-specific absolute generation layer with a spatial axis. It must not be used as a complete government province-level PV generation inventory.

This layer should be cited together with the NEA PV utilization-rate layer, the NBS national solar-generation check and the NBS provincial total electricity-generation context. Together they provide official national scale, official grid-operation scale, official total-electricity spatial context and exchange-disclosed PV-specific absolute generation sample evidence.

Machine-readable outputs: `outputs/si_ctgr_spatial_pv_generation_validation.csv` and `outputs/si_ctgr_spatial_pv_generation_validation_summary.csv`
