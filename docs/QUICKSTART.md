# Quick Start

This guide takes a fresh checkout to the current manuscript figures and checks.

## 1. Install

```bash
git clone https://github.com/<your-org>/pvsim.git
cd pvsim
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

For a flexible environment, use `requirements.txt`. The verified local environment uses Python 3.12 and the locked requirements file.

## 2. Verify

```bash
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m scripts.validate_against_pvlib
.venv\Scripts\python.exe -m scripts.source_audit_gate
```

Expected current results:

| Check | Expected result |
| --- | --- |
| Unit and data tests | 58 passed |
| pvlib benchmark | global maximum deviation 0.0007 percent |
| Source audit gate | 0 missing provenance fields, 62 row-level official records complete |

The strict source audit command should pass:

```bash
.venv\Scripts\python.exe -m scripts.source_audit_gate --strict
```

It should return zero when every release-gated provincial row has row-level official provenance.

## 3. Regenerate Current Main Figures

```bash
.venv\Scripts\python.exe -m scripts.fig_main1_inversion
.venv\Scripts\python.exe -m scripts.fig_main2_mechanisms
.venv\Scripts\python.exe -m scripts.fig_yield_segmentation
.venv\Scripts\python.exe -m scripts.fig_economics_timing
.venv\Scripts\python.exe -m scripts.fig_main5_deployment
```

Outputs:

| Figure | File |
| --- | --- |
| Fig 1 | `outputs/figures/NEWFig1_inversion.png` |
| Fig 2 | `outputs/figures/NEWFig2_mechanisms.png` |
| Fig 3 | `outputs/figures/NEWFig3_segmentation.png` |
| Fig 4 | `outputs/figures/NEWFig4_economics_timing.png` |
| Fig 5 | `outputs/figures/NEWFig5_deployment.png` |

## 4. Regenerate SI Evidence Tables

```bash
.venv\Scripts\python.exe -m scripts.si_scientific_defense_tables
.venv\Scripts\python.exe -m scripts.cloud_spectral_sensitivity
.venv\Scripts\python.exe -m scripts.grid_uncertainty_appendix
.venv\Scripts\python.exe -m scripts.silicon_baseline_sensitivity
.venv\Scripts\python.exe -m scripts.perovskite_parameter_sensitivity
.venv\Scripts\python.exe -m scripts.mechanism_specificity
.venv\Scripts\python.exe -m scripts.global_transferability_boundary
.venv\Scripts\python.exe -m scripts.national_external_validation
.venv\Scripts\python.exe -m scripts.pv_utilization_external_validation
.venv\Scripts\python.exe -m scripts.nbs_spatial_generation_validation
.venv\Scripts\python.exe -m scripts.ctgr_spatial_pv_generation_validation
.venv\Scripts\python.exe -m scripts.external_validation_audit
.venv\Scripts\python.exe -m scripts.release_manifest
.venv\Scripts\python.exe -m scripts.source_audit_gate
```

Key outputs are written to `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md`, `docs/SI_CLOUD_SPECTRAL_SENSITIVITY.md`, `docs/SI_GRID_UNCERTAINTY.md`, `docs/SI_SILICON_BASELINE_SENSITIVITY.md`, `docs/SI_PEROVSKITE_PARAMETER_SENSITIVITY.md`, `docs/SI_MECHANISM_SPECIFICITY.md`, `docs/SI_TRANSFERABILITY_BOUNDARY.md`, `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md`, `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md`, `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md`, `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md`, `docs/EXTERNAL_VALIDATION_AUDIT.md`, `docs/RELEASE_MANIFEST.md` and `docs/SI_SOURCE_AUDIT_STATUS.md`.

## 5. Build Review HTML

```bash
.venv\Scripts\python.exe -m scripts.make_review_html
```

This writes `docs/PAPER_C_review_en.html` and `docs/PAPER_C_review_zh.html` with embedded figures.

## 6. External Data Notes

PVGIS weather calls use `data/tmy_cache` after first download. ERA5-Land and GEM layers require external data access or local cached files. See `docs/DATA.md` and `docs/DATA_PROVENANCE.md` for details.
