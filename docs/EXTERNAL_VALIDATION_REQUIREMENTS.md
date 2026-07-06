# External Generation Validation Requirements

Last updated: 2026-07-01

This file defines the evidence hierarchy for external generation validation.

## Current Workspace Status

The workspace contains a provincial fleet-hour anchor table, derived validation outputs, an official national aggregate solar-generation check, an official regional PV generation-utilization layer, an official NBS provincial total electricity-generation layer and an exchange-filed CTGR operating-region PV generation layer. It does not contain plant-level PV generation, monthly provincial PV generation or third-party measured performance-ratio data.

Current available validation:

| Evidence | Status | What it can support |
| --- | --- | --- |
| Provincial fleet utilisation hours | Available | System-level spatial anchor |
| Official national aggregate solar generation | Available as partial check | National-scale plausibility only |
| Official regional PV generation utilization rate | Available | Location-resolved PV operation validation |
| Official provincial total electricity generation | Available | Spatial absolute generation context, not PV-specific validation |
| CTGR operating-region PV generation | Available | PV-specific absolute generation sample with a spatial axis |
| Full 8,760-hour provincial anchors | Available | Device-physics simulation at representative provincial sites |
| ERA5-Land 0.1 degree reduced grid | Available with uncertainty appendix | National spatial pattern and regional ranking |
| Complete government province-level PV generation inventory | Not available | Stronger future validation target for national province-level PV-specific absolute generation |

## Minimum Dataset To Close The Gap

At least one independent measured layer with a location axis is required for a Joule-plus open-data package. The current package meets this with the NEA PV utilization-rate layer for PV operation, the NBS provincial total electricity-generation layer for absolute spatial context and the CTGR operating-region PV generation layer for a PV-specific absolute generation sample. A complete government province-level PV generation inventory remains the stronger future target.

Local availability audit: `docs/EXTERNAL_VALIDATION_AUDIT.md`

Dedicated government inventory acquisition audit: `docs/GOVERNMENT_PV_GENERATION_INVENTORY_AUDIT.md`

Manual official export protocol and validator: `docs/NBS_MANUAL_EXPORT_PROTOCOL.md` and `scripts/validate_government_pv_generation_inventory.py`

| Candidate dataset | Minimum fields | Acceptance test |
| --- | --- | --- |
| Plant-level monthly generation | Plant ID, latitude, longitude, capacity, month, generation, source URL or document ID | Compare measured and simulated monthly specific yield after declared system-loss treatment |
| Province-level monthly generation | Province, month, installed capacity, generation, source URL or document ID | Compare seasonal shape and annual specific yield against provincial anchors |
| Multi-year provincial utilisation hours | Province, year, utilisation hours, source URL or document ID | Test whether the 2024 spatial relation persists across independent years |
| Third-party PR benchmark | Site or climate class, technology, PR, period, source URL or document ID | Check whether inferred system-loss correction is within observed PR range |

## Validation Rules

The dataset must be independent of model calibration.

Rows must carry source URL or document ID, retrieval date, unit, reporting period and capacity convention.

The validation script must report correlation, bias, MAE, RMSE and MAPE. If monthly data are used, it must also report seasonal correlation.

Loss treatment must be explicit. Clean-physics simulation, BOS loss, curtailment, availability and clipping must not be mixed without stating the convention.

The result should enter SI as an external validation layer. It should not replace the current pvlib numerical benchmark or the provincial fleet-hour spatial anchor.

## Current Decision

The national aggregate check in `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` may be cited as an independent official plausibility check. The NEA utilization-rate layer in `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` may be cited as location-resolved official PV operation validation. The NBS layer in `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` may be cited as an official province-level absolute generation context layer. The CTGR layer in `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` may be cited as an exchange-filed PV-specific absolute generation sample with an operating-region axis. The dedicated acquisition audit records that a complete government province-level PV generation inventory has not been acquired. Do not claim one until such a source table is added and tested.
