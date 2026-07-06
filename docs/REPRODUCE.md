# Reproduce The Current Manuscript

This file lists the commands for the active NEWFig1 to NEWFig5 manuscript set and the SI evidence checks.

First-time PVGIS calls require internet. Later runs use the local cache in `data/tmy_cache`.

For exact reproduction of the verified environment:

```bash
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

## Main Figures

| Figure | Command | Output |
| --- | --- | --- |
| Fig 1 | `.venv\Scripts\python.exe -m scripts.fig_main1_inversion` | `outputs/figures/NEWFig1_inversion.png` |
| Fig 2 | `.venv\Scripts\python.exe -m scripts.fig_main2_mechanisms` | `outputs/figures/NEWFig2_mechanisms.png` |
| Fig 3 | `.venv\Scripts\python.exe -m scripts.fig_yield_segmentation` | `outputs/figures/NEWFig3_segmentation.png` |
| Fig 4 | `.venv\Scripts\python.exe -m scripts.fig_economics_timing` | `outputs/figures/NEWFig4_economics_timing.png` |
| Fig 5 | `.venv\Scripts\python.exe -m scripts.fig_main5_deployment` | `outputs/figures/NEWFig5_deployment.png` |

## Core Validation

| Check | Command | Output |
| --- | --- | --- |
| Unit and data tests | `.venv\Scripts\python.exe -m pytest -q` | 58 passed |
| pvlib numerical benchmark | `.venv\Scripts\python.exe -m scripts.validate_against_pvlib` | pvlib comparison table and max error |
| Fleet validation | `.venv\Scripts\python.exe -m scripts.fig_validation_fleet` | fleet validation figure and SI CSVs |
| Source audit gate | `.venv\Scripts\python.exe -m scripts.source_audit_gate` | `docs/SI_SOURCE_AUDIT_STATUS.md` |
| Strict source release gate | `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` | zero when 62 release-gated official rows are complete |

## SI Evidence

| Evidence | Command | Key output |
| --- | --- | --- |
| Scientific defense tables | `.venv\Scripts\python.exe -m scripts.si_scientific_defense_tables` | `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md` |
| Cloud spectral boundary | `.venv\Scripts\python.exe -m scripts.cloud_spectral_sensitivity` | `docs/SI_CLOUD_SPECTRAL_SENSITIVITY.md` |
| ERA5 grid uncertainty | `.venv\Scripts\python.exe -m scripts.grid_uncertainty_appendix` | `docs/SI_GRID_UNCERTAINTY.md` |
| Silicon baseline sensitivity | `.venv\Scripts\python.exe -m scripts.silicon_baseline_sensitivity` | `docs/SI_SILICON_BASELINE_SENSITIVITY.md` |
| Perovskite parameter sensitivity | `.venv\Scripts\python.exe -m scripts.perovskite_parameter_sensitivity` | `docs/SI_PEROVSKITE_PARAMETER_SENSITIVITY.md` |
| Mechanism specificity | `.venv\Scripts\python.exe -m scripts.mechanism_specificity` | `docs/SI_MECHANISM_SPECIFICITY.md` |
| Transferability boundary | `.venv\Scripts\python.exe -m scripts.global_transferability_boundary` | `docs/SI_TRANSFERABILITY_BOUNDARY.md` |
| National aggregate external validation | `.venv\Scripts\python.exe -m scripts.national_external_validation` | `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` |
| PV utilization external validation | `.venv\Scripts\python.exe -m scripts.pv_utilization_external_validation` | `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` |
| NBS spatial generation context | `.venv\Scripts\python.exe -m scripts.nbs_spatial_generation_validation` | `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` |
| CTGR spatial PV generation validation | `.venv\Scripts\python.exe -m scripts.ctgr_spatial_pv_generation_validation` | `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` |
| External validation local audit | `.venv\Scripts\python.exe -m scripts.external_validation_audit` | `docs/EXTERNAL_VALIDATION_AUDIT.md` |
| Release manifest | `.venv\Scripts\python.exe -m scripts.release_manifest` | `docs/RELEASE_MANIFEST.md` |
| Source audit status | `.venv\Scripts\python.exe -m scripts.source_audit_gate` | `outputs/si_source_audit_status.csv` |

## Review Package

```bash
.venv\Scripts\python.exe -m scripts.make_review_html
```

Outputs:

| File | Role |
| --- | --- |
| `docs/PAPER_C_review_en.html` | English manuscript with embedded main figures |
| `docs/PAPER_C_review_zh.html` | Chinese review manuscript with embedded main figures |

## Legacy Exploration Figures

Older scripts such as `scripts.run_comparison`, `scripts.portfolio_v1`, `scripts.map_pv_china` and the animation scripts are retained as exploratory or historical support. They are not the active five-figure manuscript spine.
