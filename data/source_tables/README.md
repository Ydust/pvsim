# Source Tables

This directory stores versioned tabular inputs used by the paper scripts.

## `provincial_pv_capacity_2024.csv`

This table records the 2024 provincial PV capacity distribution used for capacity-weighted figures.

- `raw_gw` is the compiled 31-province table. It sums to 868.9 GW.
- `scaled_to_national_gw` preserves the same provincial shares and closes to the national 2024 PV total of 886.6 GW.
- `scale_factor` is 886.6 / 868.9.
- `source_name`, `source_url`, `source_doc`, `retrieved_date`, `source_audit_status` and `source_note` keep the source-family provenance beside every provincial row.

The model uses the scaled values through `pvsim.provinces.PROVINCE_PV_2024_GW`. The raw values are retained as `RAW_PROVINCE_PV_2024_GW` for auditability.

## `provincial_fleet_hours_2024.csv`

This table records provincial PV fleet utilisation hours used for the system-level spatial anchor. It is not a pure device-physics validation, because fleet hours include BOS losses, curtailment, dispatch and O&M effects.

Every row carries the same provenance fields as the capacity table.

The plotting and SI scripts load this table through `pvsim.source_data.load_fleet_hours`.

## Remaining Source-Appendix Work

For journal submission, add row-level official URLs or document identifiers when available. The current tables are versioned inputs with complete provenance fields, but not every provincial row has a separate permanent official document yet.
