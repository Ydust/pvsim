# Perovskite gains most where sunlight is weakest: a physics-resolved reassessment of China's solar transition

Authors: TBD

Target standard: Joule-plus internal standard

Submission file status: complete main manuscript, separated from supporting information

Last updated: 2026-07-01

## eTOC Blurb

Perovskite photovoltaics have a smaller temperature penalty than crystalline silicon, but their field-yield advantage is not largest where sunlight is strongest. A physics-resolved digital twin mapped across China shows that single-junction perovskite gains most in the hot, lower-irradiance Southwest because temperature and air-mass spectral mechanisms reinforce there. The result changes the deployment rule: perovskite is a land-utility capacity technology for hot high-advantage regions, tandem is an area-constrained rooftop technology, and lifetime gates the economics.

## Summary

Metal-halide perovskites are often compared with crystalline silicon by standard-test efficiency, yet field energy depends on operating temperature, spectral response, system losses and siting. We build a single-diode photovoltaic digital twin, benchmark it numerically against pvlib with a maximum deviation of 0.0007 percent, and drive it over 31 provincial anchors and a 0.1 degree land grid across China. The model is anchored against provincial fleet-utilisation hours and cross-checked against official national solar generation, official National Energy Administration PV utilisation rates, official National Bureau of Statistics provincial total-electricity generation and exchange-filed China Three Gorges Renewables PV generation.

We find a geographically inverted advantage. Single-junction perovskite yields about 3 percent more energy per kWp than modern silicon on average, but the advantage is largest in the hot Southwest and South rather than in the high-irradiance Northwest. Across the grid, annual irradiance and perovskite advantage are negatively correlated with r = -0.51. Counterfactual decomposition separates a temperature term tied to irradiance-weighted cell temperature and a spectral term tied to air mass. The two mechanisms have different monthly fingerprints and are not replicated by the tandem architecture.

Changing the performance ruler changes the technology ranking. Perovskite is lower than modern silicon by standard-test efficiency but higher by field energy per kWp. Tandem is strongest by energy per square metre and therefore serves area-constrained rooftop deployment. Economics remain lifetime-gated: a 1000-draw scenario ensemble gives LCOE-crossover years of 2030, 2032 and 2039 at P10, P50 and P90, with 2.7 percent of draws not crossing by 2050. The top third of perovskite-advantage provinces hold only about 24 percent of 2024 installed capacity, so early deployment should follow operating physics rather than irradiance intuition.

## Introduction

Solar deployment decisions are commonly made with nameplate efficiency and cost per watt. At national scale this is incomplete. Photovoltaic modules operate away from standard-test conditions, and field energy is controlled by irradiance, cell temperature, spectrum, incidence angle, degradation, availability and grid utilisation. Energy yield, not laboratory efficiency alone, is therefore the relevant basis for comparing technologies in the field.

Perovskite solar cells are attractive because their reported power-temperature coefficients are smaller than those of crystalline silicon and because their wider band gaps can gain under lower-air-mass spectra. These device-level properties suggest a field-yield advantage, but they do not tell us where the advantage matters, whether it survives a modern silicon comparator, or how it should alter deployment. The policy-relevant baseline is not early low-efficiency silicon. It is the modern TOPCon, PERC and HJT-class silicon fleet now being installed.

China is the critical test bed. It had about 887 GW of installed solar capacity by the end of 2024 and continues to build at terawatt scale. A few percent error in where an emerging technology is deployed can translate into tens of gigawatts of energy-yield misallocation. The question is therefore spatial, physical and economic: where does perovskite outperform modern silicon, what mechanism drives the pattern, how should the performance ruler change between utility and rooftop markets, and when does the advantage become economic under lifetime uncertainty.

We address these questions with a physics-resolved digital twin. The model combines solar geometry, plane-of-array irradiance, incidence-angle optics, clear-sky spectral response, Faiman cell temperature, a De Soto five-parameter single-diode electrical model, PVWatts inverter conversion, degradation and LCOE. We use switch-paired counterfactuals to isolate spectral, temperature and optical components. We then compare the physics pattern with capacity geography and land-utility row-spacing penalties.

The study scope is land-based PV in China. It includes ground-mounted utility PV and rooftop or distributed PV. Offshore and floating PV are not modelled as separate scenarios because water and marine environments change thermal boundary conditions, corrosion and humidity exposure, platforms, operations and economics.

## Results

### Perovskite advantage is largest where sunlight is weakest, Figs 1 and 2

The 0.1 degree land-grid simulation shows that the per-kWp advantage of single-junction perovskite over modern silicon is spatially inverted. It is largest in the hot Southwest and South and smallest across the high-irradiance Northwest and Tibetan plateau. Across land-grid cells, annual irradiance and perovskite advantage are negatively correlated with r = -0.51. This means the relative benefit of switching from modern silicon to perovskite is largest where annual sunlight is weaker.

The effect is modest in magnitude but material at national scale. Resource-band aggregation shows that the advantage rises from about 1.6 to 2.3 percent in plateau and Northwest resource regions to about 4.4 percent in the Southwest-oriented lower-resource band. The 0.1 degree layer is used as a climatological spatial-pattern map rather than a plant-level point forecast. Province-level numeric claims use the 31 full 8760-hour anchors, while the grid supports the inversion and regional ordering.

Counterfactual decomposition shows that the inversion is not a single residual. The temperature component follows perovskite's smaller power-temperature coefficient acting on real cell temperature. Across provincial anchors and sampled climate points, it scales with irradiance-weighted cell temperature at r = 0.98. The spectral component follows the wider-band-gap response under lower air mass. It scales with irradiance-weighted air mass at r = -0.85. Because the spectral module uses SPECTRL2 clear-sky physics, this term is attributed to solar geometry and air mass, not to cloud-colour effects.

The two mechanisms also separate in time. The temperature term is concentrated in summer and is near zero in winter. The spectral term persists through the year as a midday band. A tandem negative control supports the same interpretation: the two-terminal perovskite-silicon tandem behaves closer to a full-spectrum absorber because the silicon bottom cell harvests red light transmitted by the perovskite top cell. It does not carry the same per-kWp spectral advantage as the single-junction perovskite.

### Efficiency ratings mispredict field energy, Fig 3

Changing the performance ruler changes the ranking. Modern silicon, single-junction perovskite and tandem have approximate standard-test efficiencies of 22.0 percent, 19.3 percent and 28.3 percent. By laboratory efficiency, perovskite trails modern silicon. By annual field energy per kWp, it is about 1.03 times modern silicon because the operating-temperature and spectral benefits partly offset lower standard-test efficiency.

Tandem behaves differently. It is strongest by standard-test efficiency and by annual energy per square metre, with an area-yield ratio of about 1.30 relative to modern silicon. Its per-kWp yield advantage is small. This creates a market split. Land-based utility projects should be judged mainly by annual energy per kWp, where single-junction perovskite has the relevant advantage. Rooftop and area-constrained markets should be judged by annual energy per square metre, where tandem is the relevant technology.

This market segmentation avoids a universal-winner claim. Single-junction perovskite is a land-utility capacity technology where the per-kWp advantage is high. Tandem is a rooftop and area-constrained technology. Modern silicon remains competitive in ground-mounted regions where the per-kWp advantage is small or durability risk dominates.

### Substitution is lifetime-gated, Fig 4

The yield edge alone does not make perovskite economic. In the 31-province NPV LCOE calculation, the main levers are capex, lifetime and degradation. Before a lifetime breakthrough, perovskite remains disadvantaged because a 15-year lifetime and faster degradation raise LCOE. After a sampled breakthrough toward a 25-year lifetime, perovskite enters the competitive range.

The cost-lever decomposition makes the hierarchy explicit. Removing the roughly 3 percent perovskite yield edge changes LCOE by only about 0.07 cents per kWh. Capex, lifetime and degradation assumptions move LCOE much more strongly. The first gate is therefore durability, not energy yield.

A reduced-form substitution model calibrated against China's 2015 to 2023 multi-crystalline to mono-crystalline silicon transition gives R2 = 0.83. The model is used for scenario timing, not a deterministic adoption forecast. A 1000-draw Monte Carlo ensemble over learning rates, cost floors, breakthrough year, post-breakthrough lifetime and choice sharpness gives LCOE-crossover years of 2030, 2032 and 2039 at P10, P50 and P90. A 2.7 percent tail does not cross by 2050 because lifetime remains inadequate.

Geography modifies the timing but does not dominate it. The Southwest tends to cross first when costs are near parity, while a decisive cost advantage makes substitution nearly synchronous. The main geographic signal is therefore the advantage magnitude and lifetime-risk distribution rather than a precise adoption sequence.

### Deploy by physics, not irradiance intuition, Fig 5

Putting perovskite advantage and land-utility row-spacing penalty on the same provincial decision plane exposes a mismatch. The high-advantage lower-penalty Southwest and South occupy the priority region, but current installed capacity is not concentrated there. The top third of perovskite-advantage provinces hold only about 24 percent of 2024 installed PV capacity, while the middle and low-advantage thirds hold about 46 percent and 30 percent.

High-latitude ground-mounted deployment also carries a technology-independent land penalty. Row spacing and self-shading losses rise strongly with latitude, with r = 0.98. The Northwest therefore combines high absolute irradiance with smaller perovskite relative advantage and higher land penalty. This reinforces the deployment rule: single-junction perovskite should first target hot high-advantage Southwest and South utility markets, tandem should be used where area is scarce, and modern silicon should remain the conservative option where the per-kWp advantage is small or durability risk is high.

## Discussion

The central result is a spatial inversion in technology value. Perovskite's smaller temperature coefficient and spectral response produce a national per-kWp advantage over modern silicon, but the advantage is greatest where annual sunlight is weaker. This overturns the simple intuition that the sunniest regions are always the best first market for advanced cells.

Two features make the result defensible. First, the comparator is modern silicon rather than early silicon. This shrinks the perovskite advantage but does not remove the inversion. Second, the model is both numerically benchmarked and externally anchored. The digital twin agrees with pvlib to 0.0007 percent, and the spatial pattern is checked against fleet-utilisation hours, official national solar generation, official NEA PV utilisation rates, official NBS provincial total-electricity generation and exchange-filed CTGR PV generation. These layers do not provide a complete government province-level PV generation inventory, and the manuscript does not claim one.

The result also clarifies the role of tandem cells. Tandem's value is area yield, not a large land-utility per-kWp advantage. That distinction matters for deployment. A single efficiency ranking hides the fact that land-based utility projects and rooftops monetise different performance rulers.

The main limitation is durability. The roughly 3 percent per-kWp energy edge is too small to overcome an inadequate lifetime. Under current assumptions, lifetime and degradation dominate LCOE. This is why the economics are reported as scenario distributions and crossover percentiles rather than a forecast.

A second limitation is spatial scope. The analysis covers land-based PV in China. Offshore and floating PV may have lower module temperatures, different humidity and salt exposure, different platforms and different costs. The conclusions should therefore not be transferred directly to those systems. A global extension would also require rerunning the full spectral and weather model rather than extrapolating China's mechanism phase plane.

The practical implication is direct. Perovskite deployment should be guided by operating temperature, relative advantage and land-utility geometry rather than by irradiance alone. Tandem should be targeted to area-constrained rooftops. Reliability qualification should focus on the hot high-value Southwest and the thin-margin Northwest because the first determines upside and the second determines whether the technology is robust enough to displace modern silicon.

## Methods

### Digital Twin

The twin uses a De Soto five-parameter single-diode electrical model solved with Lambert W. Weather drivers are PVGIS typical meteorological year data at provincial anchors and ERA5-Land climatology for the reduced-order spatial layer. Plane-of-array irradiance is computed from horizontal irradiance and mounting geometry. Incidence-angle effects use a Martin-Ruiz modifier. Spectral mismatch is computed from SPECTRL2 clear-sky spectra integrated against technology EQE curves and tabulated by solar zenith and air mass.

Cell temperature is computed with the Faiman model using configurable heat-transfer coefficients. The temperature coefficient of maximum power is reproduced through the saturation-current temperature law rather than imposed as a post-processing correction. System output uses PVWatts inverter conversion, clipping and declared system losses.

The model technologies are modern c-Si, single-junction perovskite and perovskite-silicon tandem, with early c-Si retained only as a historical reference. The main comparator is modern silicon with about 22 percent standard-test efficiency and a power-temperature coefficient near -0.32 percent per C. Perovskite and tandem parameters are drawn from the device and technoeconomic literature listed in the references.

### Validation And Data Provenance

Numerical validation uses `scripts/validate_against_pvlib.py`. Across STC, hot high-irradiance, low-light and cold high-irradiance cases, the global maximum deviation across Pmp, Voc, Isc and fill factor is 0.0007 percent.

The fleet anchor compares clean-physics provincial yields with versioned fleet-utilisation hours. The raw spatial correlation is r = 0.889. After a uniform 15.3 percent system-loss correction, RMSE is 102 kWh per kWp and MAPE is 7.1 percent. This comparison is a system-level anchor because fleet hours include balance-of-system losses, curtailment, dispatch and operations.

Official external checks are separated by what they can support. The NBS 2024 Statistical Communique reports national solar generation of 839.04 TWh and year-end solar capacity of 886.66 GW. The NEA 2024 monitoring result reports regional PV generation-utilisation rates, with a national value of 96.8 percent and a lowest provincial value of 68.6 percent in Tibet. NBS China Statistical Yearbook 2025 Table 9-19 reports 2024 provincial total electricity generation and provides an absolute generation context with a province axis. CTGR 2024 annual-report rows provide a PV-specific absolute generation sample with 25 operating-region rows and 25.40083 TWh of PV generation. No complete government province-level PV absolute generation inventory has been acquired.

Provincial installed capacity uses the NEA 2024 PV construction table. The 31-province source values sum to 885.673 GW after the Xinjiang Production and Construction Corps is merged into Xinjiang. The model preserves provincial shares and scales uniformly to the 2024 national PV total of 886.6 GW.

### Mechanism Decomposition

The spectral component is the full run minus a spectrally flat counterfactual. The temperature component is based on the difference between perovskite and silicon power-temperature coefficients applied over the energy-weighted operating-temperature distribution relative to 25 C. The incidence-angle residual is retained separately. Drivers such as cell temperature and air mass are irradiance-weighted.

Temporal fingerprints reshape the 8760-hour series into day-of-year and solar-hour coordinates. PVGIS timestamps are UTC, and local solar time is recovered from the minimum-zenith hour.

### Economics And Substitution

LCOE is computed as discounted cost divided by discounted generation with annual degradation, burn-in, 5 percent discount rate and 1.5 percent operating expenditure. Future module costs follow Wright learning curves. The substitution model is a softmax merit-order allocation calibrated to China's multi-crystalline to mono-crystalline silicon transition from 2015 to 2023.

Monte Carlo draws sample perovskite, tandem and silicon learning rates, cost floors, perovskite lifetime breakthrough year, post-breakthrough lifetime, degradation and allocation sharpness. Results are reported as scenario distributions. The model does not present a deterministic forecast.

### Reproducibility

The current verification command is `.venv\Scripts\python.exe -m pytest -q`, with 63 tests passing on 2026-07-01. The source audit gate is `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict`, with 62 official provincial source rows complete. The release manifest is regenerated by `.venv\Scripts\python.exe -m scripts.release_manifest`.

## Figure Legends

Figure 1. Perovskite's per-kWp advantage over modern silicon inverts geographically. Panel a shows the 0.1 degree spatial pattern over land cells in China. Panel b shows the negative relation with annual irradiance, with r = -0.51. Panel c shows resource-band aggregation and the split into temperature and spectral mechanisms.

Figure 2. Two physical mechanisms carry the inversion. Panel a separates the temperature component, which scales with irradiance-weighted cell temperature, from the spectral component, which scales with irradiance-weighted air mass. Panel b shows monthly fingerprints across 31 provinces, with a summer temperature term and a year-round spectral term.

Figure 3. Efficiency ratings mispredict field energy. Panel a compares standard-test efficiency, annual energy per kWp and annual energy per square metre for modern silicon, perovskite and tandem. Panel b shows that perovskite leads the land-utility per-kWp ruler, while tandem leads the area-constrained ruler.

Figure 4. Substitution is lifetime-gated. Panel a shows LCOE trajectories with provincial uncertainty bands. Panel b decomposes the LCOE levers and shows that capex, lifetime and degradation dominate the yield edge. Panel c shows central scenario allocation paths. Panel d shows the Monte Carlo LCOE-crossover distribution with P10, P50 and P90 years of 2030, 2032 and 2039.

Figure 5. Deploy by physics rather than irradiance intuition. Panel a compares perovskite per-kWp advantage with row-spacing land penalty and shows 2024 capacity by bubble size. Panel b shows that the top third of advantage provinces hold only 24 percent of installed capacity. Panel c shows the latitude-driven land penalty with r = 0.98.

## References

1. De Soto, W., Klein, S. A., and Beckman, W. A. 2006. Improvement and validation of a model for photovoltaic array performance. Solar Energy 80, 78-88. DOI 10.1016/j.solener.2005.06.010.
2. Faiman, D. 2008. Assessing the outdoor operating temperature of photovoltaic modules. Progress in Photovoltaics 16, 307-315. DOI 10.1002/pip.813.
3. Dirnberger, D. et al. 2015. On the impact of solar spectral irradiance on the yield of different PV technologies. Solar Energy Materials and Solar Cells 132, 431-442. DOI 10.1016/j.solmat.2014.09.034.
4. Dupre, O., Vaillon, R., and Green, M. A. 2015. Physics of the temperature coefficients of solar cells. Solar Energy Materials and Solar Cells 140, 92-100. DOI 10.1016/j.solmat.2015.03.025.
5. Hoerantner, M. T. and Snaith, H. J. 2017. Predicting and optimising the energy yield of perovskite-on-silicon tandem solar cells. Energy and Environmental Science 10, 1983-1993. DOI 10.1039/c7ee01232b.
6. Gota, F. et al. 2020. Energy yield advantages of three-terminal perovskite-silicon tandem photovoltaics. Joule 4, 2387-2403. DOI 10.1016/j.joule.2020.08.021.
7. Moot, T. et al. 2021. Temperature coefficients of perovskite photovoltaics for energy-yield calculations. ACS Energy Letters 6, 2038-2047. DOI 10.1021/acsenergylett.1c00748.
8. Babics, M. et al. 2023. Temperature coefficients of perovskite-silicon tandem solar cells. ACS Energy Letters 8, 3013-3015. DOI 10.1021/acsenergylett.3c00930.
9. Cordell, J. J., Woodhouse, M., and Warren, E. L. 2025. Technoeconomic analysis of perovskite-silicon tandem solar modules. Joule 9, 101781. DOI 10.1016/j.joule.2024.10.013.
10. Wagner, L. et al. 2024. The resource demands of multi-terawatt-scale perovskite tandem photovoltaics. Joule 8, 1142-1160. DOI 10.1016/j.joule.2024.01.024.
