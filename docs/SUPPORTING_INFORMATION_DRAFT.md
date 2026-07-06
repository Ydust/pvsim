# Supporting Information Draft

Manuscript: Perovskite field advantage and deployment geography in China

Last updated: 2026-07-01

## S0 Data Sources And Scope

This study evaluates land-based photovoltaic deployment in China. The deployment scope includes ground-mounted utility PV and rooftop or distributed PV. Offshore and floating PV are not modelled as separate technology scenarios because their thermal boundary conditions, corrosion and humidity reliability, platform costs and O&M differ from land-based systems.

Provincial installed capacity, official PV generation-utilization rates and fleet utilisation hours are used as grid-connected PV aggregates. The release-gated official source matrix uses provincial capacity and NEA PV utilization-rate rows. The fleet-hour table is retained as a system-level spatial anchor.

Table S0.1 lists the provincial capacity source table. The 31-province capacity distribution now comes from the National Energy Administration 2024 PV power construction status table. The official row values sum to 885.673 GW after Xinjiang Production and Construction Corps is merged into Xinjiang to preserve the 31-province scope. The model preserves the official provincial shares and scales them uniformly to the 2024 national PV total of 886.6 GW. This gives a capacity-weighted input that closes to the national total without changing provincial ranking. The table carries source name, source URL, source document description, retrieval date, audit status and row note.

Table S0.2 lists the provincial fleet-hour source table. Fleet-hour values are used only as a system-level spatial anchor. They include BOS losses, curtailment, dispatch and O&M effects, so they are not used as pure device-physics validation and are not counted as release-gated official row evidence.

Table S0.3 lists the NEA PV generation-utilization layer. It is official, PV-specific and spatially resolved after aggregating Inner Mongolia grid regions to the 31-province modelling scope.

Table S0.4 lists the NBS provincial total electricity-generation layer. It supplies an official spatial absolute generation context. It is not PV-specific and is not cited as province-level PV generation.

Table S0.5 lists the CTGR operating-region PV generation layer. It supplies exchange-filed, PV-specific absolute generation and grid-export quantities with a spatial operating-region axis. It is a company asset sample, not a complete government province-level PV generation inventory.

Source appendix: `docs/SOURCE_APPENDIX.md`

Source audit gate: `docs/SI_SOURCE_AUDIT_STATUS.md`

Source evidence matrix: `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md`

PV utilization external layer: `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md`

NBS spatial generation layer: `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md`

CTGR spatial PV generation layer: `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md`

Source tables:

| Table | File | Use |
| --- | --- | --- |
| Table S0.1 | `data/source_tables/provincial_pv_capacity_2024.csv` | Capacity weighting and Fig 5 deployment mismatch |
| Table S0.2 | `data/source_tables/provincial_fleet_hours_2024.csv` | Fleet-anchored system validation |
| Table S0.3 | `data/source_tables/nea_pv_utilization_rate_2024.csv` | Official PV generation-utilization external validation |
| Table S0.4 | `data/source_tables/nbs_provincial_total_power_generation_2024.csv` | Official spatial absolute generation context |
| Table S0.5 | `data/source_tables/ctgr_pv_generation_by_region_2024.csv` | Exchange-filed PV absolute generation spatial sample |
| Table S0.6 | `outputs/provincial_source_evidence_matrix.csv` | Row-level official source evidence matrix |

## S1 Model Validation And Fleet Anchor

### S1.1 Model Architecture

The digital twin is a modular chain. Each module can be tested, replaced or switched independently. Table S1.1 should appear before detailed equations so reviewers can see where each physical assumption enters the analysis.

| Stage | Inputs | Model step | Outputs |
| --- | --- | --- | --- |
| Weather drivers | PVGIS TMY, ERA5-Land monthly climatology, site latitude and longitude | Solar geometry and meteorology harmonisation | GHI, DNI, DHI, air temperature, wind speed and solar zenith |
| Plane-of-array irradiance | Horizontal irradiance, location and mounting geometry | Transposition from horizontal plane to tilted module plane | Broadband POA irradiance |
| Optical modifiers | POA irradiance and incidence angle | IAM correction, optional bifacial gain and DC optical losses | Optical effective irradiance |
| Spectral response | Zenith angle, air mass and EQE curves | SPECTRL2 clear-sky spectral factor | Spectral multiplier for each technology |
| Cell temperature | POA irradiance, air temperature and wind speed | Faiman heat-transfer model | Cell temperature |
| Electrical model | Effective irradiance and cell temperature | De Soto five-parameter single-diode model solved with Lambert W | IV curve, maximum power point and DC power |
| System output | DC array power and inverter settings | PVWatts inverter, clipping and system losses | AC power and annual specific yield |
| Degradation and economics | Year-one yield and technology parameters | Degradation, burn-in, discounted energy and LCOE calculation | LCOE trajectories |
| Substitution scenarios | LCOE paths, learning curves, lifetime breakthrough year and Monte Carlo draws | Softmax merit-order allocation calibrated against the silicon multi-to-mono transition | New-build shares and crossover years |

The spectral module uses clear-sky spectral physics. Cloudiness enters through broadband irradiance and temperature, not through an explicit cloud spectral blue-shift term. The 0.1 degree ERA5-Land layer is a reduced-order spatial layer calibrated to the 31 provincial 8,760-hour anchors. It supports spatial pattern and ranking, not plant-level point prediction.

### S1.2 Counterfactual Switches

The mechanism decomposition should be reported as switch-paired runs rather than as an informal visual interpretation. Table S1.2 defines the recommended run pairs.

| Quantity | Switch or run pair | Interpretation |
| --- | --- | --- |
| Spectral component | Full run minus spectrally flat run with `apply_spectral=False` | Isolates band-gap and air-mass spectral response |
| Temperature component | No-spectral-no-IAM run, then the difference in power-temperature coefficients is multiplied by cell-temperature departure from 25 C over the energy-weighted operating distribution | Isolates the power-temperature coefficient effect |
| IAM residual | No-spectral run minus no-spectral-no-IAM run | Captures incidence-angle optical residual |
| Grid reduced-order layer | Full 8,760-hour provincial anchors are used to calibrate monthly ERA5-Land reduced runs | Supports spatial pattern and ranking, not point forecast |

### S1.3 Validation Hooks

The SI should keep the following hooks visible so that model structure and numerical performance are traceable.

| Check | File or command | Role |
| --- | --- | --- |
| Numerical single-diode benchmark | `.venv\Scripts\python.exe -m scripts.validate_against_pvlib` | Confirms agreement with pvlib De Soto and singlediode calculations |
| Fleet-anchored spatial validation | `.venv\Scripts\python.exe -m scripts.fig_validation_fleet` | Compares clean-physics provincial yield against real fleet utilisation hours |
| National aggregate external validation | `.venv\Scripts\python.exe -m scripts.national_external_validation` | Compares official national solar generation with loss-corrected national model yield |
| PV utilization external validation | `.venv\Scripts\python.exe -m scripts.pv_utilization_external_validation` | Adds official regional PV generation-utilization rates from NEA |
| NBS spatial generation context | `.venv\Scripts\python.exe -m scripts.nbs_spatial_generation_validation` | Adds official province-level total electricity generation from NBS |
| CTGR spatial PV generation validation | `.venv\Scripts\python.exe -m scripts.ctgr_spatial_pv_generation_validation` | Adds exchange-filed operating-region PV generation and grid export |
| Data integrity tests | `tests/test_data_integrity.py` | Verifies national capacity closure and source-table consistency |
| Source audit gate | `.venv\Scripts\python.exe -m scripts.source_audit_gate` | Checks 62 official source rows for provenance completeness |
| SI evidence tables | `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md` | Collects validation, robustness and scenario-calibration statistics |

The single-diode implementation is benchmarked against pvlib De Soto plus singlediode calculations. Across STC, hot high-irradiance, low-light and cold high-irradiance conditions, the global maximum numerical deviation is 0.0007 percent.

Figure S1 should show the numerical twin validation, 8,760-hour operation pattern and degradation context. It supports the claim that the physics engine is numerically consistent before it is used for national-scale comparisons.

Figure S2 should show the fleet-anchored system validation. The clean-physics modern-silicon twin is compared against provincial fleet utilisation hours. The raw spatial correlation is r = 0.889. After a uniform mean system-loss correction, RMSE is 102 kWh per kWp and MAPE is 7.1 percent.

The national aggregate external check is reported in `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md`. The National Bureau of Statistics reports 2024 solar generation of 839.04 TWh, year-end solar capacity of 886.66 GW and solar-capacity growth of 45.2 percent. Using a simple average of inferred start-year and year-end capacity gives an observed national specific yield of 1120.7 kWh per kW. The loss-corrected capacity-weighted c-Si model gives 1265.4 kWh per kWp after the official NEA provincial capacity table is adopted. This check strengthens national-scale plausibility but remains an aggregate sanity check. It is not a province-level or plant-level external validation layer.

The location-resolved external PV operation layer is reported in `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md`. The National Energy Administration reports 2023 and 2024 PV generation utilization rates by region. The 2024 national rate is 96.8 percent, and the lowest provincial value is 68.6 percent in Tibet. This layer is official, PV-specific and spatially resolved. It validates the grid-utilization component of observed PV generation. It does not replace province-level monthly generation or plant-level generation records.

The spatial absolute generation context layer is reported in `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md`. The National Bureau of Statistics reports 2024 total electricity generation by province in China Statistical Yearbook 2025 Table 9-19. The transcribed 31-province sum is 100868.83 hundred million kWh, matching the national table value within rounding. This layer provides an official province axis and an absolute generation quantity. It must not be cited as province-level PV generation because the NBS table reports total electricity generation.

The PV-specific absolute generation sample is reported in `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md`. China Three Gorges Renewables reports 2024 PV generation and PV grid export by operating region in its exchange-filed 2024 annual report. The 25 operating-region rows sum to 254.0083 hundred million kWh, closing to the annual-report PV generation total of 254.01 hundred million kWh within rounding. This layer is independent of the model and spatially resolved, but it covers one company asset portfolio rather than the national provincial fleet.

Key table: `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md`, Table Sx

## S2 Spatial Inversion Robustness

The main inversion result is that perovskite's relative per-kWp advantage over modern silicon is largest in lower-irradiance humid South and Southwest China, rather than in the high-irradiance Northwest.

### S2.1 Adversarial Scenario Checks

Figure S3 should show the adversarial scenario checks. The test set should include at least the baseline, both technologies bifacial, roof-mount hot operation, open-rack cool operation and a no-spectral or no-IAM structural perturbation. The acceptance criterion is directional stability: the advantage must remain larger in the lower-resource South and Southwest than in the high-resource Northwest under each perturbation.

The inversion is therefore not interpreted as a tuning artefact of one mounting or loss assumption. The recommended caption should state that the adversarial cases preserve the negative relation between annual irradiance and perovskite relative advantage. The companion table should list the scenario name, province count, correlation against annual irradiance, median advantage in each resource band and the highest-error province.

### S2.2 Reduced-Order ERA5-Land Grid Layer

Figure S4 should show the ERA5-Land 0.1 degree grid robustness check. The 0.1 degree layer is a climatological spatial-pattern map and regional-ranking product. It should not be presented as a plant-level or cell-level point forecast.

The reduced-order grid model is calibrated against the 31 provincial full 8,760-hour anchors. The validation gives R2 = 0.377 and RMSE = 0.962 percentage points for the advantage variable. The grid contains 94,998 land cells. Across the grid, annual irradiance and perovskite advantage remain negatively correlated with r = -0.514. This is sufficient evidence for the national inversion pattern and regional ordering, but it is not sufficient evidence for precise yield at an individual land cell.

The grid uncertainty appendix is reported in `docs/SI_GRID_UNCERTAINTY.md`. The median absolute error is 0.703 percentage points, the p90 absolute error is 1.444 percentage points and the maximum provincial error is 2.532 percentage points. The appendix also reports resource-band compression: the reduced layer overestimates band I and underestimates band IV. These diagnostics are why Fig 1 should be read as a spatial-pattern map while province-level numerical claims should use the full 8,760-hour anchors.

| Check | Value | Interpretation |
| --- | --- | --- |
| Full provincial anchors | 31 | High-fidelity 8,760-hour reference layer |
| ERA5-Land grid cells | 94,998 | Climatological spatial-pattern layer |
| Reduced-order R2 | 0.377 | Supports pattern and ranking |
| Reduced-order RMSE | 0.962 percentage points | Too large for plant-level point forecast |
| Grid irradiance-advantage relation | r = -0.514 | Confirms the inversion direction |

### S2.3 Resource-Band Sanity Check

The resource-band check should be reported beside Fig S4 because it shows where the reduced-order layer compresses the provincial signal. The full 8,760-hour provincial anchors give median perovskite advantages of 1.68, 2.24, 3.51 and 4.68 percent from resource band I to band IV. The reduced-order layer preserves the broad inversion but compresses the band IV median to 3.41 percent and overestimates band I. The main text should therefore use the grid as a spatial-pattern map and use provincial anchors for numerical province-level claims.

Key table: `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md`, Tables Sy and Sz

### S2.4 Modern Silicon Baseline Sensitivity

The modern silicon comparator should not be a single fragile parameter choice. The silicon baseline sensitivity appendix is reported in `docs/SI_SILICON_BASELINE_SENSITIVITY.md`. It perturbs the silicon power-temperature coefficient across representative HJT, TOPCon and PERC cases while keeping the same provincial weather and perovskite yields.

The inversion direction is preserved in all three cases. The median perovskite advantage is 2.90 percent for the HJT low-temperature-coefficient case, 3.43 percent for the TOPCon central case and 3.87 percent for the PERC high-temperature-coefficient case. The irradiance relation remains negative with r from -0.603 to -0.500, and resource band IV remains higher than resource band I. This supports the claim that the inversion is not an artefact of one modern silicon comparator.

### S2.5 Transferability Boundary

The transferability boundary appendix is reported in `docs/SI_TRANSFERABILITY_BOUNDARY.md`. It fits a mechanism phase plane from the China-derived temperature and spectral components, then reports where the same decomposition predicts positive or negative per-kWp perovskite advantage as a function of irradiance-weighted cell temperature and air mass.

This is not a global validation map. It is a boundary statement. The fitted thermal slope is 0.186 percentage points per C, and the fitted spectral slope is 1.757 percentage points per unit blue-index. The phase plane shows that warmer, lower-air-mass climates sit in the positive region, while colder high-air-mass climates can cross the zero boundary. This prevents over-exporting the China result without rerunning the full global weather and spectral model.

## S3 Mechanism Decomposition

The geographic inversion is decomposed into a temperature term and a spectral term. The temperature term follows perovskite's smaller power-temperature coefficient acting on real cell temperature. The spectral term follows the wider-band-gap, bluer response of perovskite under lower air mass.

### S3.1 Physical Attribution

The decomposition uses the switch definitions in Table S1.2. The spectral component is the full run minus a spectrally flat run. The temperature component is calculated from the difference between perovskite and silicon power-temperature coefficients acting on the cell-temperature departure from 25 C. The IAM residual is retained as a separate optical term.

This attribution is intentionally conservative. The spectral model is SPECTRL2 clear-sky physics, so the spectral term should be described as a solar-geometry and air-mass term. Cloudiness enters through broadband irradiance and cell temperature. It is not used as an explicit cloud spectral blue-shift mechanism.

The cloud spectral boundary stress test is reported in `docs/SI_CLOUD_SPECTRAL_SENSITIVITY.md`. It applies smooth blue and red spectral tilts to the clear-sky spectra while holding broadband irradiance fixed. All stress cases keep the negative relation between relative air mass and perovskite spectral advantage over modern silicon, so the air-mass attribution is not overturned by this spectral-colour perturbation.

The perovskite parameter sensitivity appendix is reported in `docs/SI_PEROVSKITE_PARAMETER_SENSITIVITY.md`. It perturbs the perovskite temperature coefficient from -0.10 to -0.25 percent per C and scales the spectral-response component from 0.7 to 1.3. All nine stress cases preserve the negative irradiance relation and keep resource band IV above resource band I. The weakest median case still has a median advantage of 1.84 percent.

The mechanism specificity appendix is reported in `docs/SI_MECHANISM_SPECIFICITY.md`. Province-only partial correlations keep the expected signs after controlling for irradiance, air mass and cell temperature. The thermal component versus weighted cell temperature gives partial r = 0.957, and the spectral component versus air mass gives partial r = -0.931. This supports separable mechanism attribution without overstating causal proof.

### S3.2 Temporal Fingerprint

Figure S5 should show the 8,760-hour temporal fingerprint. The temperature term is seasonal and concentrated in summer. The spectral term persists through the year as a midday band. This supports the statement that the two mechanisms are separable in time.

The recommended SI text should report that the two components can share the same solar-noon timing while remaining seasonally distinct. This matters because a shared diurnal peak could otherwise be mistaken for a single hidden irradiance term. The seasonal fingerprint separates them: the temperature term follows warm operating periods, while the spectral term follows air-mass geometry through the year.

### S3.3 Tandem Negative Control

Figure S6 should show the tandem comparison. Tandem cells are primarily an area-yield technology in this paper's framing. They do not create the same per-kWp spectral advantage as single-junction perovskite, because the tandem absorbs across a broader spectrum.

The tandem result is a negative control for the spectral mechanism. A two-terminal perovskite-silicon tandem has a silicon bottom cell that absorbs red light transmitted by the perovskite top cell. It therefore behaves closer to a full-spectrum absorber than a single-junction perovskite cell. In the current device set, the tandem has high area yield but little per-kWp advantage against modern silicon. This supports the market segmentation in Fig 3 and the deployment split in Fig 5.

## S4 Efficiency And Market Rulers

Figure 3 in the main text changes the performance ruler from STC efficiency to field energy. SI should retain the 31-province data behind that ruler change.

The recommended SI table should list, for each province and each technology, STC efficiency ratio, field yield per kWp, field yield per square metre and resource band. This table prevents national averages from hiding province-level variation.

### S4.1 Ruler Definitions

The paper uses three different performance rulers. They answer different market questions and should not be mixed.

| Ruler | Question answered | Main implication |
| --- | --- | --- |
| STC efficiency | How much lab-rated power fits into module area | Useful for nameplate comparison, weak for field energy |
| Annual yield per kWp | How much energy a rated watt produces in the field | Relevant for land-based utility economics |
| Annual yield per square metre | How much energy roof or land area produces | Relevant for area-constrained rooftops |

Single-junction perovskite is lower than modern silicon by the STC ruler but higher by the annual per-kWp ruler. Tandem is strongest by the area ruler. This is why Fig 3 does not claim one universal winner. It separates land-based utility deployment from rooftop deployment.

### S4.2 Province-Level Table

The SI table behind Fig 3 should be generated from `outputs/province_physics_yield.csv`. For each province, it should include technology, resource band, STC efficiency ratio, annual yield per kWp, annual yield per square metre, performance ratio, irradiance-weighted cell temperature and spectral factor. This table lets readers check whether a national mean hides outlier provinces.

Recommended table columns:

| Column | Role |
| --- | --- |
| Province and resource band | Spatial grouping |
| Technology | c-Si, perovskite or tandem |
| Yield per kWp | Land-based utility energy ruler |
| Yield per square metre | Rooftop area ruler |
| Performance ratio | System-normalised field performance |
| Weighted cell temperature | Temperature-mechanism driver |
| Spectral factor | Spectral-mechanism driver |

Recommended data source: `outputs/province_physics_yield.csv`

## S5 Economic Timing And Substitution Calibration

The economic analysis is a scenario distribution, not a deterministic industry forecast. Perovskite becomes competitive only when the lifetime gate is passed.

### S5.1 Historical Softmax Calibration

Figure S7 should show the historical softmax calibration using the multi-to-mono silicon transition. The reduced substitution model gives R2 = 0.829 and RMSE = 11.9 share percentage points over 2015 to 2023. The maximum absolute residual is 22.1 share percentage points. This level of fit is adequate for a reduced scenario allocation model, but it is not a basis for deterministic adoption forecasts.

The SI should describe the substitution model as a merit-order allocation with finite choice sharpness. Technologies with lower LCOE gain share, but the softmax term allows coexistence and inertia. This is why the main text should use phrases such as scenario timing and crossover distribution rather than prediction or forecast.

### S5.2 Learning And Monte Carlo Priors

Figure S8 should show the 2015 to 2024 Wright learning backcast. This supports the learning-curve parameter choices used in the future-cost scenarios. The Monte Carlo parameter table should also be retained. It states the learning-rate distributions, capex floors, perovskite breakthrough year, post-breakthrough lifetime, softmax allocation temperature, number of draws and random seed. The table must report source or anchor, prior reason and stress-test role for each parameter.

The scenario space is intentionally broad. Perovskite learning rate is centred at 0.27, tandem learning rate at 0.30 and c-Si learning rate at 0.18. Perovskite breakthrough year is sampled from 2028 to 2042, and post-breakthrough lifetime is sampled from 18 to 25 years. These ranges make the lifetime gate explicit rather than assumed.

### S5.3 Lifetime And Degradation Geography

Figure S9 should show the degradation-risk geography. It should make clear that some high-irradiance Northwest provinces are more fragile under lifetime and degradation limits, while the Southwest remains more robust.

The core message is that perovskite's roughly 3 percent field-yield edge is not the dominant economic lever. Capex, lifetime and degradation dominate the LCOE spread. SI should therefore show the maximum tolerable degradation rate by province and should state that a favourable climate advantage cannot rescue an insufficient lifetime.

### S5.4 Conditional Timing Geography

Figure S10 should show the conditional geography of substitution timing. The Southwest can cross first under central cost assumptions, but the spread is modest and should not be described as a precise adoption forecast.

The recommended SI wording is that geography orders the timing when costs are near parity, while a decisive cost advantage makes substitution nearly synchronous. This keeps the claim aligned with Fig 4: economic timing is a scenario distribution, and location modifies that distribution rather than determining it alone.

Key tables: `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md`, Tables Sa and Sb

## S6 Deployment And Land Penalty

Figure S11 should support the land-penalty component in Fig 5. The land penalty is a ground-mounted utility geometry effect driven by row spacing and latitude. It is technology independent in this framing.

### S6.1 Decision-Plane Scope

Fig 5 is a decision plane for land-based utility deployment. It combines perovskite's relative per-kWp advantage with a latitude-driven row-spacing land penalty. It should not be read as a rooftop technology map. Rooftop deployment follows the area-yield ruler and favours tandem modules in the current device set.

The deployment plane also uses provincial 2024 installed capacity as context. The top third of perovskite-advantage provinces hold only about 24 percent of installed PV capacity, while the middle and low-advantage thirds hold about 46 and 30 percent. This is the deployment mismatch claim. It should be linked to the scaled 2024 capacity source table described in S0.

### S6.2 Land-Penalty Evidence

The land penalty comes from fixed-tilt row spacing and self-shading geometry. It rises with latitude because lower winter solar elevation requires larger row spacing for a given shading constraint. It is technology independent under this framing because it is a site-layout geometry term, not a cell-efficiency term.

The supporting file is `outputs/land_use_latitude.csv`. It lists province latitude and the derived shading-loss or row-spacing penalty. The values increase from about 1.9 percent in Hainan to about 10.8 percent in Heilongjiang. The main-text land-penalty panel reports r = 0.98 between latitude and the penalty metric.

### S6.3 Deployment Interpretation

The SI should keep three deployment statements separate.

| Statement | Evidence | Scope |
| --- | --- | --- |
| Perovskite first land-based utility sites should favour high-advantage hot South and Southwest regions | Fig 1 and Fig 5 | Land-based utility per-kWp deployment |
| Tandem value is strongest where area is scarce | Fig 3 and Fig S6 | Rooftop and area-constrained deployment |
| Modern silicon remains competitive where per-kWp advantage is small or durability risk is high | Fig 4 and Fig 5 | Conservative deployment and reliability gating |

## S7 Boundary Evidence

Optional background appendices can retain evidence on indium, carbon payback and band-gap sensitivity. These topics are useful for reviewer questions but should not compete with the five-figure main line.

Recommended optional figures:

| Topic | Recommended file | Role |
| --- | --- | --- |
| Indium | `outputs/figures/MainFig4_indium_constraint.png` | Global multi-TW material boundary |
| Carbon payback | `outputs/figures/45_carbon_payback.png` | Climate context |
| Carbon scenarios | `outputs/figures/46_carbon_scenarios.png` | Climate context |
| Province carbon map | `outputs/figures/47_province_carbon_map.png` | Optional province-level context |
| Band gap | `outputs/figures/feas_optimal_bandgap.png` | Negative result for China-scale band-gap tailoring |

## Reproducibility

Verified environment: `requirements-lock.txt`

Flexible install: `requirements.txt`

Core checks:

| Check | Command | Current result |
| --- | --- | --- |
| Unit and data-integrity tests | `.venv\Scripts\python.exe -m pytest -q` | 58 passed |
| pvlib numerical benchmark | `.venv\Scripts\python.exe -m scripts.validate_against_pvlib` | global maximum deviation 0.0007 percent |
| SI evidence tables | `.venv\Scripts\python.exe -m scripts.si_scientific_defense_tables` | tables written to `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md` |
| Cloud spectral boundary | `.venv\Scripts\python.exe -m scripts.cloud_spectral_sensitivity` | direction preserved in all stress cases |
| ERA5 grid uncertainty | `.venv\Scripts\python.exe -m scripts.grid_uncertainty_appendix` | uncertainty appendix written to `docs/SI_GRID_UNCERTAINTY.md` |
| Silicon baseline sensitivity | `.venv\Scripts\python.exe -m scripts.silicon_baseline_sensitivity` | direction preserved for HJT, TOPCon and PERC baselines |
| Perovskite parameter sensitivity | `.venv\Scripts\python.exe -m scripts.perovskite_parameter_sensitivity` | direction preserved across nine gamma and spectral-response stress cases |
| Mechanism specificity | `.venv\Scripts\python.exe -m scripts.mechanism_specificity` | province-only partial correlations preserve expected mechanism directions |
| Transferability boundary | `.venv\Scripts\python.exe -m scripts.global_transferability_boundary` | mechanism phase plane written to `docs/SI_TRANSFERABILITY_BOUNDARY.md` |
| National aggregate external validation | `.venv\Scripts\python.exe -m scripts.national_external_validation` | official national generation check written to `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` |
| PV utilization external validation | `.venv\Scripts\python.exe -m scripts.pv_utilization_external_validation` | official regional PV utilization layer written to `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` |
| NBS spatial generation context | `.venv\Scripts\python.exe -m scripts.nbs_spatial_generation_validation` | official province-level total electricity generation layer written to `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` |
| CTGR spatial PV generation validation | `.venv\Scripts\python.exe -m scripts.ctgr_spatial_pv_generation_validation` | exchange-filed PV absolute generation sample written to `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` |
| External validation local audit | `.venv\Scripts\python.exe -m scripts.external_validation_audit` | official PV operation layer, official absolute generation context and CTGR PV absolute generation sample available |
| Release manifest | `.venv\Scripts\python.exe -m scripts.release_manifest` | complete file-level SHA256 manifest written to `docs/RELEASE_MANIFEST.md` |
| Reference audit | `docs/REFERENCE_AUDIT.md` | core physical and economic references checked against Crossref DOI records |
| Source audit gate | `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` | 62 rows checked, 0 missing provenance fields, 62 row-level official records complete |
| Source evidence matrix | `.venv\Scripts\python.exe -m scripts.provincial_source_evidence_matrix` | 62-row official evidence matrix written to `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` |

## Release Manifest

The release manifest is reported in `docs/RELEASE_MANIFEST.md` and `outputs/release_manifest.csv`. It records file size and SHA256 checksums for the manuscript drafts, SI evidence, source tables, main figures, core scripts, outputs and tests that should travel together in a journal-facing reproducibility package.

The manifest is a file-level package boundary. It does not replace row-level source provenance or the external validation audit.

## Current Source-Audit Status

The release-gated provincial official source matrix is versioned, closed and covered by automated tests. It contains 31 capacity rows and 31 NEA PV utilization-rate rows. The source audit gate checks 62 provincial rows, finds 0 missing provenance fields, 62 row-level official records complete and 0 row-level official records pending. The fleet-hour table remains versioned and test-covered as a system-level validation anchor, but it is not described as an official row-level source table.

## External-Validation Boundary

The current validation set includes pvlib numerical agreement, provincial fleet-hour spatial anchoring, national aggregate official solar generation checking, official regional PV generation-utilization rates, official NBS provincial total electricity generation, exchange-filed CTGR operating-region PV generation, ERA5 grid uncertainty and cloud spectral boundary tests. It includes a location-resolved PV operation layer, a province-level absolute total-electricity generation context layer and a PV-specific absolute generation sample with a spatial operating-region axis. It does not include a complete government province-level PV generation inventory, so the manuscript must not claim national province-level PV generation validation.
