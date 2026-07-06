# Supporting Information

Manuscript: Perovskite gains most where sunlight is weakest

Last updated: 2026-07-01

Submission file status: complete supporting information, separated from main manuscript

## S0 Scope, Data Sources And Source Boundaries

This study evaluates land-based photovoltaic deployment in China. The scope includes ground-mounted utility PV and rooftop or distributed PV. Offshore and floating PV are not modelled as separate technology scenarios because their thermal boundary conditions, corrosion and humidity exposure, platforms, operation and cost differ from land-based systems.

The source hierarchy separates measured inputs, official validation layers, system-level anchors, model outputs and scenario parameters. Provincial installed capacity, official PV generation-utilisation rates and fleet-utilisation hours are all grid-connected aggregate layers. They are not split into land-based utility, rooftop, floating or offshore subfleets.

Table S0.1. Source tables and use.

| Table | File | Use | Status |
| --- | --- | --- | --- |
| S0.1 | `data/source_tables/provincial_pv_capacity_2024.csv` | Capacity weighting and deployment mismatch | Official 31-province NEA source rows |
| S0.2 | `data/source_tables/provincial_fleet_hours_2024.csv` | System-level spatial anchor | Versioned anchor, not official row-level release evidence |
| S0.3 | `data/source_tables/nea_pv_utilization_rate_2024.csv` | Official PV operation validation | Official NEA row-level evidence |
| S0.4 | `data/source_tables/nbs_provincial_total_power_generation_2024.csv` | Official absolute generation context | Total electricity, not PV-specific |
| S0.5 | `data/source_tables/ctgr_pv_generation_by_region_2024.csv` | PV-specific absolute generation sample | Exchange-filed company operating-region sample |
| S0.6 | `outputs/provincial_source_evidence_matrix.csv` | Row-level source evidence matrix | 62 official rows complete |
| S0.7 | `outputs/government_pv_generation_inventory_validation.csv` | Candidate complete government PV generation gate | Not accepted because no official candidate table exists |

The NEA provincial capacity rows sum to 885.673 GW after the Xinjiang Production and Construction Corps is merged into Xinjiang. The model preserves official provincial shares and scales uniformly to the 2024 national PV total of 886.6 GW.

The complete government province-level PV absolute generation inventory has not been acquired. The validator in `scripts/validate_government_pv_generation_inventory.py` rejects capacity-derived, utilisation-derived, company-sample, above-designated-size industry and partial-coverage tables. The current candidate status is not accepted because `data/source_tables/provincial_pv_generation_2024_official.csv` does not exist.

## S1 Model Architecture And Counterfactual Switches

The digital twin is a modular chain so each physical assumption can be tested and switched independently.

Table S1.1. Model chain.

| Stage | Inputs | Model step | Outputs |
| --- | --- | --- | --- |
| Weather drivers | PVGIS TMY, ERA5-Land climatology, latitude and longitude | Solar geometry and weather harmonisation | GHI, DNI, DHI, air temperature, wind speed and zenith |
| Plane-of-array irradiance | Horizontal irradiance and mounting geometry | Transposition to module plane | Broadband POA irradiance |
| Optical modifiers | POA irradiance and incidence angle | Martin-Ruiz IAM, optional bifacial gain and DC optical losses | Optical effective irradiance |
| Spectral response | Zenith, air mass and EQE curves | SPECTRL2 clear-sky spectral factor | Technology-specific spectral multiplier |
| Cell temperature | POA irradiance, air temperature and wind speed | Faiman heat-transfer model | Cell temperature |
| Electrical model | Effective irradiance and cell temperature | De Soto five-parameter single-diode model solved with Lambert W | IV curve, maximum power and DC power |
| System output | DC array power and inverter settings | PVWatts inverter, clipping and system losses | AC power and annual specific yield |
| Degradation and economics | Year-one yield and technology parameters | Degradation, burn-in, discounted energy and LCOE | LCOE trajectories |
| Substitution scenarios | LCOE paths and Monte Carlo draws | Softmax merit-order allocation | New-build shares and crossover years |

The spectral module uses clear-sky spectral physics. Cloudiness enters through broadband irradiance and temperature rather than through an explicit cloud spectral colour term.

Table S1.2. Counterfactual switches.

| Quantity | Switch or run pair | Interpretation |
| --- | --- | --- |
| Spectral component | Full run minus spectrally flat run with `apply_spectral=False` | Isolates band-gap and air-mass spectral response |
| Temperature component | Difference in power-temperature coefficients applied to the energy-weighted cell-temperature departure from 25 C | Isolates the temperature-coefficient mechanism |
| IAM residual | No-spectral run minus no-spectral-no-IAM run | Captures incidence-angle optical residual |
| Reduced-order grid layer | Full 8760-hour provincial anchors calibrate monthly ERA5-Land reduced runs | Supports spatial pattern and ranking |

## S2 Numerical Validation And Fleet Anchoring

The single-diode implementation is benchmarked against pvlib De Soto and singlediode calculations. Across STC, hot high-irradiance, low-light and cold high-irradiance cases, the global maximum deviation across Pmp, Voc, Isc and fill factor is 0.0007 percent.

The fleet anchor compares clean-physics modern-silicon yield against provincial fleet-utilisation hours. The raw spatial correlation is r = 0.889. After a uniform mean system-loss correction of 15.3 percent, RMSE is 102 kWh per kWp and MAPE is 7.1 percent. This is a system-level validation because fleet hours include balance-of-system losses, curtailment, dispatch and operations.

Table S2.1. Validation hooks.

| Check | Command or file | Current result |
| --- | --- | --- |
| Numerical benchmark | `.venv\Scripts\python.exe -m scripts.validate_against_pvlib` | Maximum deviation 0.0007 percent |
| Fleet validation | `outputs/si_fleet_validation_summary.csv` | r = 0.889 and corrected RMSE = 102 kWh per kWp |
| Data integrity | `.venv\Scripts\python.exe -m pytest -q` | 63 passed |
| Source audit gate | `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` | 62 official rows complete |
| Release manifest | `.venv\Scripts\python.exe -m scripts.release_manifest` | Complete file-level SHA256 manifest |

## S3 Spatial Inversion Robustness

The main spatial result is that perovskite's per-kWp advantage over modern silicon is larger in lower-irradiance South and Southwest China than in the high-irradiance Northwest.

The reduced-order ERA5-Land grid contains 94,998 land cells. It is calibrated against the 31 full 8760-hour provincial anchors. Validation gives R2 = 0.377 and RMSE = 0.962 percentage points for the advantage variable. The grid irradiance-advantage relation remains negative with r = -0.514.

Table S3.1. Grid uncertainty.

| Metric | Value |
| --- | ---: |
| Full provincial anchors | 31 |
| ERA5-Land land cells | 94,998 |
| Reduced-order R2 | 0.377 |
| Reduced-order RMSE | 0.962 percentage points |
| Median absolute error | 0.703 percentage points |
| P90 absolute error | 1.444 percentage points |
| Maximum provincial error | 2.532 percentage points |
| Grid irradiance-advantage relation | r = -0.514 |

The reduced-order grid is therefore a spatial-pattern and ranking layer, not a plant-level point forecast. Province-level numerical claims use the full 8760-hour anchors.

Modern silicon baseline sensitivity preserves the inversion. HJT-like, TOPCon-like and PERC-like silicon cases give median perovskite advantages of 2.90 percent, 3.43 percent and 3.87 percent. The irradiance relation remains negative with r from -0.603 to -0.500.

Perovskite parameter sensitivity also preserves the inversion. A nine-case grid spanning temperature coefficient from -0.10 to -0.25 percent per C and spectral-response scaling from 0.7 to 1.3 keeps resource band IV above resource band I in every case. The weakest median case still has a 1.84 percent advantage.

## S4 Mechanism Specificity

The advantage is decomposed into temperature, spectral and optical residual terms. The temperature component follows perovskite's smaller power-temperature coefficient acting on real cell temperature. The spectral component follows wider-band-gap response under lower air mass.

Province-only partial correlations support separable mechanism attribution. After controlling for irradiance, air mass and cell temperature, the thermal component versus weighted cell temperature gives partial r = 0.957. The spectral component versus air mass gives partial r = -0.931.

Temporal fingerprinting separates the two mechanisms. The temperature component is concentrated in summer, while the spectral component persists through the year as a midday band. This prevents a shared solar-noon peak from being mistaken for a single hidden irradiance driver.

The tandem architecture is a negative control for the single-junction spectral mechanism. The tandem's silicon bottom cell absorbs red light transmitted by the perovskite top cell, so the tandem behaves closer to a full-spectrum absorber. In the current device set, tandem has strong area yield but little per-kWp spectral advantage against modern silicon.

Cloud spectral boundary checks apply smooth blue and red tilts to clear-sky spectra while holding broadband irradiance fixed. All stress cases preserve the negative relation between relative air mass and perovskite spectral advantage over modern silicon. The paper therefore attributes the main spectral term to air mass and solar geometry rather than cloud colour.

The transferability appendix fits a mechanism phase plane from the China-derived temperature and spectral components. The fitted thermal slope is 0.186 percentage points per C, and the fitted spectral slope is 1.757 percentage points per unit blue-index. This phase plane is a boundary statement, not a global validation map.

## S5 Efficiency Rulers, Economics And Deployment

The paper uses three performance rulers.

Table S5.1. Performance rulers.

| Ruler | Question answered | Market implication |
| --- | --- | --- |
| STC efficiency | How much lab-rated power fits into module area | Useful for nameplate comparison |
| Annual yield per kWp | How much energy a rated watt produces in the field | Land-based utility economics |
| Annual yield per square metre | How much energy a limited area produces | Rooftop and area-constrained deployment |

Single-junction perovskite is lower than modern silicon by STC efficiency but higher by annual yield per kWp. Tandem is strongest by annual yield per square metre. This is why Fig 3 separates land-utility deployment from rooftop deployment.

The substitution model is a reduced-form scenario model. It is calibrated against the 2015 to 2023 multi-crystalline to mono-crystalline silicon transition and gives R2 = 0.829 with RMSE = 11.9 share percentage points. This supports scenario timing but not a deterministic adoption forecast.

Monte Carlo priors span learning rates, cost floors, perovskite breakthrough year, post-breakthrough lifetime and allocation sharpness. Perovskite learning is centred near 0.27, tandem near 0.30 and c-Si near 0.18. Perovskite breakthrough year is sampled from 2028 to 2042, and post-breakthrough lifetime from 18 to 25 years.

Deployment interpretation is kept to three statements.

Table S5.2. Deployment statements.

| Statement | Evidence | Scope |
| --- | --- | --- |
| Perovskite should first target hot high-advantage South and Southwest utility regions | Figs 1 and 5 | Land-based utility per-kWp deployment |
| Tandem value is strongest where area is scarce | Fig 3 and tandem negative control | Rooftop and area-constrained deployment |
| Modern silicon remains competitive where advantage is small or durability risk is high | Fig 4 and Fig 5 | Conservative deployment and reliability gating |

The land-utility row-spacing penalty is technology independent. It rises from about 1.9 percent in Hainan to about 10.8 percent in Heilongjiang and correlates with latitude at r = 0.98.

## S6 External Validation Layers And Boundaries

Table S6.1. External validation layers.

| Layer | Evidence | What it supports | Boundary |
| --- | --- | --- | --- |
| NBS national solar generation | 839.04 TWh in 2024 | National aggregate plausibility | No location axis |
| NEA PV utilisation rate | National 96.8 percent and provincial minimum 68.6 percent | Official PV-specific spatial operation | Utilisation rate, not absolute generation |
| NBS provincial total electricity | 31 province rows and 100868.83 hundred million kWh sum | Official absolute generation context | Total electricity, not PV-specific |
| CTGR PV generation | 25 operating-region rows and 25.40083 TWh | PV-specific absolute generation sample | Company asset sample |
| Candidate government PV inventory | Validation gate exists | Future complete official PV province table | Not accepted because no official candidate file exists |

The NBS national aggregate check uses the 2024 Statistical Communique. The official year-end capacity denominator gives a low observed specific yield because solar capacity grew rapidly in 2024. A simple average of inferred start-year and year-end capacity gives 1120.7 kWh per kW. The loss-corrected model gives 1265.4 kWh per kWp. The difference reflects intra-year additions, fleet age, curtailment, availability, regional timing and source conventions.

The NEA PV utilisation layer reports 2023 and 2024 PV generation-utilisation rates by region. It is official, PV-specific and spatially resolved after aggregating Inner Mongolia regions to the 31-province modelling scope. It validates grid-operation evidence and does not replace measured province-level generation.

The NBS provincial total-electricity layer reports 2024 total electricity generation by province. The province sum closes to the national reference within 0.02 hundred million kWh. It supplies an official province axis and absolute generation volume, but it is not PV-specific.

The CTGR layer is exchange-filed and PV-specific. It reports 25 operating-region rows, 254.0083 hundred million kWh of PV generation and 248.3109 hundred million kWh of grid export. It closes to the annual-report PV generation total within rounding. It is a sample validation layer rather than a complete national government province inventory.

The complete government province-level PV generation inventory remains unavailable. The manual export protocol is `docs/NBS_MANUAL_EXPORT_PROTOCOL.md`. The validation gate is `scripts/validate_government_pv_generation_inventory.py`.

## S7 Supplementary Figure And Table Inventory

Table S7.1. Main and supplementary figure files.

| Label | File | Role |
| --- | --- | --- |
| Fig 1 | `outputs/figures/NEWFig1_inversion.png` | Geographic inversion and resource-band mechanism split |
| Fig 2 | `outputs/figures/NEWFig2_mechanisms.png` | Mechanism drivers and monthly fingerprints |
| Fig 3 | `outputs/figures/NEWFig3_segmentation.png` | Efficiency ruler and market segmentation |
| Fig 4 | `outputs/figures/NEWFig4_economics_timing.png` | Lifetime-gated economics and crossover timing |
| Fig 5 | `outputs/figures/NEWFig5_deployment.png` | Deployment mismatch and land-utility decision plane |
| Fig S1 | `outputs/figures/MainFigV_fleet_validation.png` | Fleet-anchored system validation |
| Fig S2 | `outputs/figures/MainFig3x_temporal_fingerprint.png` | Temporal mechanism fingerprint |
| Fig S3 | `outputs/figures/MainFig3y_tandem_decomposition.png` | Tandem negative control |
| Fig S4 | `outputs/figures/MainFig4x_degradation_risk.png` | Geography of lifetime risk |
| Fig S5 | `outputs/figures/MainFig4y_substitution_timing_geo.png` | Conditional timing geography |
| Fig S6 | `outputs/figures/SI_transferability_phase_plane.png` | Mechanism transferability boundary |

Table S7.2. Audit and validation files.

| File | Role |
| --- | --- |
| `docs/SI_SOURCE_AUDIT_STATUS.md` | 62-row official source audit status |
| `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` | Row-level official evidence matrix |
| `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` | Official national solar generation sanity check |
| `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` | Official NEA PV utilisation validation |
| `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` | Official NBS total-electricity spatial context |
| `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` | Exchange-filed CTGR PV generation sample |
| `docs/GOVERNMENT_PV_GENERATION_INVENTORY_AUDIT.md` | Acquisition audit for complete government PV inventory |
| `docs/SI_GOVERNMENT_PV_GENERATION_INVENTORY_VALIDATION.md` | Candidate inventory validation status |
| `docs/RELEASE_MANIFEST.md` | File-level SHA256 release manifest |

## S8 Reproducibility

The verified environment is captured by `requirements-lock.txt`, with a flexible install listed in `requirements.txt`.

Table S8.1. Core reproducibility commands.

| Check | Command | Current result |
| --- | --- | --- |
| Unit and data-integrity tests | `.venv\Scripts\python.exe -m pytest -q` | 63 passed |
| Source audit gate | `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` | 62 official rows complete |
| National aggregate validation | `.venv\Scripts\python.exe -m scripts.national_external_validation` | Official national check written |
| PV utilisation validation | `.venv\Scripts\python.exe -m scripts.pv_utilization_external_validation` | Official PV operation layer written |
| NBS spatial context | `.venv\Scripts\python.exe -m scripts.nbs_spatial_generation_validation` | Official total-electricity context written |
| CTGR PV generation sample | `.venv\Scripts\python.exe -m scripts.ctgr_spatial_pv_generation_validation` | Exchange-filed PV sample written |
| Government PV inventory gate | `.venv\Scripts\python.exe -m scripts.validate_government_pv_generation_inventory` | Submission ready is False |
| Release manifest | `.venv\Scripts\python.exe -m scripts.release_manifest` | Complete manifest written |

The release manifest records file sizes and SHA256 checksums for manuscript drafts, SI evidence, source tables, main figures, core scripts, outputs and tests. It is a package boundary and does not replace row-level source provenance.
