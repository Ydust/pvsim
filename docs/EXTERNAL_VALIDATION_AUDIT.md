# External Validation Local Audit

Last updated: 2026-07-01

Independent location-resolved PV operation layer: available.

PV-specific absolute generation sample with spatial axis: available.

Official spatial absolute generation context layer: available.

This audit checks the local `xuni_fangzhen` and `PV_WRF` workspaces for data that could satisfy the manuscript P0 location-resolved external-validation requirement.

| Candidate | Exists | Data type | Generation | Capacity | Time axis | Location | Acceptable | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Provincial fleet utilisation source table | True | annual provincial utilisation hours | False | False | True | True | False | Useful system-level spatial anchor, but not an independent measured generation layer and not counted as a release-gated official row layer |
| Fleet validation derived output | True | derived model validation table | False | True | True | True | False | Derived from the model and fleet-hour anchor, so it cannot serve as an independent external validation dataset |
| NBS national aggregate solar generation check | True | official national aggregate measured generation check | True | True | True | False | False | Independent official measured generation and capacity at national aggregate scale, useful for plausibility but not location-resolved validation |
| NBS provincial total electricity generation layer | True | official spatial absolute total-electricity generation layer | True | False | True | True | False | Official province-level measured electricity generation for 2024, useful as absolute spatial context but not PV-specific generation validation |
| NEA provincial PV generation utilization rate | True | official location-resolved PV generation-utilization layer | True | False | True | True | True | Official PV-specific regional utilization-rate layer for 2023 and 2024, acceptable as location-resolved operation validation but not as absolute generation-volume validation |
| CTGR operating-region PV generation layer | True | exchange-disclosed company-asset PV absolute generation sample | True | False | True | True | True | SSE-filed CTGR annual report reports 2024 PV generation and grid export by operating region, acceptable as PV-specific absolute measured generation sample but not as a national official province inventory |
| Climate TRACE China power source API response | True | third-party power-source activity inventory without China solar rows | True | True | True | True | False | Downloaded 2024 China power-source response contains point-source MWh activity but no solar asset rows in the inspected API result |
| PV_WRF global power plant database | True | plant catalogue | False | True | False | True | False | Contains plant metadata and capacity-factor estimates, not plant-level or province-level measured PV generation |
| PV_WRF Climate TRACE power files | True | power-sector emissions inventory | False | False | True | True | False | Useful emissions context, but not a measured PV generation validation layer for China |
| PV_WRF climate inputs | True | climate forcing inputs | False | False | True | True | False | Contains ERA5, TerraClimate, MODIS and land-cover inputs, not measured PV generation |
| PV_WRF annual solar NetCDF | True | solar or climate gridded field | False | False | True | True | False | May support climate or resource context, but it is not an observed PV generation layer |

## Conclusion

The current local workspace now contains a usable official PV generation-utilization layer with a location axis. The existing fleet-hour table remains valuable as a system-level spatial anchor, but it is not a substitute for plant-level monthly generation, province-level monthly generation or multi-year official utilisation records with row-level provenance.

A national aggregate official solar generation check is available when `outputs/si_national_external_validation.csv` has been generated. It is independent and measured, so it strengthens national-scale plausibility. It does not close the P0 location requirement because it has no plant or provincial location axis.

The NBS provincial total electricity-generation layer adds an official absolute measured-generation layer with a province axis. It does not close the PV-specific absolute generation-volume gap because it reports total electricity generation rather than PV generation.

The NEA PV utilization-rate layer closes the location-resolved official PV operation evidence gap. It does not close the stricter PV-specific absolute generation-volume gap because it reports utilization rates, not generation in kWh by province.

The CTGR operating-region layer closes the available external PV-specific absolute generation sample gap. It reports measured PV generation and grid export by operating region for one exchange-filed company asset portfolio. It does not close the complete government province-level PV generation inventory gap.

The required fields and acceptance tests remain defined in `docs/EXTERNAL_VALIDATION_REQUIREMENTS.md`.
