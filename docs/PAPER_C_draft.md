# Perovskite gains most where sunlight is weakest: a physics-resolved reassessment of China's solar transition

**Authors:** [TBD]
**Target:** Joule-plus internal standard
**Status:** research-type rewrite, dated 2026-06: adopts the `NEWFig1-5` spine — geographic
inversion, physical mechanisms, market ruler, lifetime economics and deployment.

---

## eTOC blurb

Perovskite's smaller temperature coefficient gives it a field-yield edge over silicon, but the
edge is not where solar-resource intuition expects it. Using a numerically benchmarked,
fleet-anchored digital twin mapped over ~95,000 land cells across China, we show that
perovskite gains most where sunlight is weakest, because high operating temperature and
low-air-mass spectra add in the hot Southwest. Efficiency rankings then
split by market: land-based utility projects reward energy per kWp, while rooftops reward
energy per m². Lifetime
and degradation gate the economics, so deployment should follow physics rather than the current
Northwest-heavy build-out.

---

## Summary

Because metal-halide perovskite has a smaller power-temperature coefficient than crystalline
silicon, it harvests proportionally more energy under field operation than its standard-test
efficiency implies — an effect now well documented at the cell and site level by Moot
et al. 2021 and Dirnberger et al. 2015. What remains unresolved is how that physics changes national
technology choice: where the advantage is largest, which mechanism drives it, whether efficiency
ratings predict field energy, and when the advantage becomes economic. We answer these questions
for China by driving a single-diode digital twin over ~95,000 0.1° land cells across China.
The numerical benchmark agrees with pvlib to 0.0007%. The operating-fleet anchor gives
r=0.89 between provincial clean-physics yields and versioned fleet-utilisation hours.

We find that perovskite's per-kWp advantage over modern silicon is modest, about 3%, but
spatially inverted: it is largest in the hot, low-latitude Southwest and smallest in the sunny
Northwest, with annual irradiance anticorrelation at r=-0.51. Counterfactual decomposition
separates two independent mechanisms — a temperature term tied to operating temperature with
r=+0.98, and a spectral term tied to air mass with r=-0.85 — with distinct monthly fingerprints.
Changing the performance ruler flips the technology ranking: perovskite is lower in STC
efficiency at 0.88x but higher in field yield per kWp at 1.03x, while tandem's value is area
yield at 1.30x per m².
Economically, the yield edge is small relative to capex, lifetime and degradation: a Monte Carlo
scenario ensemble gives P10/P50/P90 LCOE-crossover years of 2030/2032/2039, with 2.7% of
draws not crossing by 2050. The deployment consequence is concrete: the top third of perovskite-advantage
provinces hold only 24% of 2024 installed capacity, so perovskite should be steered to the
Southwest/South land-based utility markets, tandems to rooftops, and modern c-Si retained in
low-advantage ground-mounted regions.

---

## Context & Scale

China operates over 887 GW of PV in 2024 and is expected to approach 2,400 GW by 2050, with the
next terawatt widely anticipated to shift from silicon toward perovskite and perovskite/silicon
tandems. Where each technology is sited is being decided now, largely on standard-test
efficiency and $/W. At this scale a few percent of misallocated energy yield is tens of GW, so
the question of *where* an emerging technology actually outperforms the incumbent — and *why* —
is consequential rather than academic. We show that, for perovskite versus the high-efficiency
silicon now installed, the answer is counterintuitive and spatially organised by a resolvable
physical mechanism, with direct implications for land-based utility-scale siting. The spatial
deployment scope is land-based PV in China, including ground-mounted utility and rooftop or
distributed PV; offshore and floating PV are not explicitly modelled because their thermal
boundary conditions, corrosion/humidity reliability, platforms and operating costs differ.

---

## Introduction

Standard-test efficiency is a poor predictor of field energy yield because modules operate far
from 25 °C and AM1.5G; annual energy yield, not nameplate efficiency, is therefore the
accepted basis for comparing technologies, as shown by Dirnberger et al. 2015. Metal-halide perovskite is
favourable on this metric. Its reported power-temperature coefficient is −0.1 to −0.2 %/°C,
markedly smaller than silicon's −0.3 to −0.45 %/°C range, as reported by Moot et al. 2021, and its wider band gap shifts
its spectral response toward the blue, so it benefits at elevated temperature and under
blue-rich spectra, consistent with spectral-yield comparisons by Dirnberger et al. 2015. Energy-yield modelling has quantified these gains for
perovskite/silicon tandems, including the spectral sensitivity of two-terminal current matching
and the location dependence of the optimal top-cell band gap, as shown by Hörantner and Snaith 2017
and Gota et al. 2020.

Three gaps motivate this work. First, most energy-yield comparisons are made at the cell level or
for a handful of representative sites, leaving the *spatial structure* of the advantage across a
large country unresolved. Second, perovskite is typically benchmarked against high-efficiency or
idealised silicon at the device level, whereas the policy-relevant comparison is against the
modern, ≈22 %-efficient silicon actually being installed — a baseline that roughly halves the
temperature advantage. Third, the advantage is usually reported as a single number, not
*decomposed* into the temperature and spectral mechanisms that drive it and that scale
differently with geography. We address all three by resolving the perovskite-over-silicon
energy-yield advantage to ~95,000 0.1° land cells across China, against a calibrated modern-silicon
baseline, and separating it into mechanisms by counterfactual toggling of the twin's spectral
and optical sub-models. We then translate the result into siting, and bound it economically.

---

## Results

### Perovskite gains most where sunlight is weakest through two mechanisms, Figs 1-2

We first place the central result directly on the national grid. Running the digital twin over
~95,000 ERA5-Land 0.1° land cells shows that the per-kWp advantage of single-junction
perovskite over modern silicon is not largest in the high-irradiance Northwest. It is largest in
the humid, low-latitude Southwest and South, as shown in Fig 1a. Across grid cells, the advantage
is anti-correlated with annual irradiance, with r=−0.51 in Fig 1b. For this device comparison, the
relative value of switching to perovskite is greatest where sunlight is weakest. Aggregating by
resource band, the advantage rises from roughly 1.6–2.3% on the plateau/Northwest to ~4.4% in
the Southwest-oriented band IV, and resolves into a temperature term plus a spectral term
in Fig 1c. The magnitude is modest, but the sign of the geography is counterintuitive and
material at terawatt scale.

The 0.1° layer is used as a climatological spatial-pattern map, not as a plant-level point
forecast. It is tied to full 8,760-hour simulations at provincial anchors and to gridded
meteorology, so the appropriate inference is the robust inversion and regional ranking rather
than exact yield at any individual land cell.

The pattern is not an artefact of comparing against a weak reference cell. The main baseline is
the modern TOPCon/PERC-type silicon now relevant to Chinese additions. This baseline has about
22% STC efficiency and γ≈−0.32 %/°C,
not the ~15% early silicon often used in perovskite benchmarking. Moving from early to modern
silicon reduces the advantage but does not remove the inversion, identifying it as a property
of device physics interacting with China's climate.
SI sensitivity tables extend this beyond one comparator: HJT-like, TOPCon-like and PERC-like
silicon baselines all preserve the negative irradiance relation, and a nine-case perovskite
gamma and spectral-response stress grid preserves the same direction.

Counterfactual decomposition shows that the advantage in Fig 1 is not a single empirical
residual but the sum of two mechanisms. The *temperature* term follows perovskite's smaller
power-temperature coefficient acting on real operating temperature: across provincial anchors
and PVGIS-sampled climate points, the component is almost linear in irradiance-weighted cell temperature, with
r=+0.98 in Fig 2a. The *spectral* term follows perovskite's wider band gap and blue-shifted
response: at lower air mass, where the spectrum is bluer, the device produces more current per
unit broadband irradiance, and the component is anti-correlated with irradiance-weighted air
mass, with r=−0.85 in Fig 2a.

This attribution is deliberately conservative: the SPECTRL2 spectral model is clear-sky, so the
spectral component is attributed to solar geometry and air mass, not to cloud-induced spectral
shifts. Cloudiness enters the analysis through broadband irradiance and operating temperature,
not through a cloud-colour correction.
Province-only partial-correlation checks in the SI keep the expected mechanism signs after
controlling for irradiance, air mass and cell temperature, with partial r=0.957 for the thermal
component versus weighted cell temperature and partial r=-0.931 for the spectral component
versus air mass.

The two mechanisms also separate in time. Monthly decomposition across 31 provinces shows that
the temperature term turns on mainly in summer and approaches zero in winter, whereas the
spectral term persists throughout the year in Fig 2b. This explains why the two mechanisms can
reinforce each other spatially in the Southwest/South: those regions are both hotter and more
favourable spectrally. A cross-technology check supports the same interpretation: a two-terminal
tandem behaves closer to a full-spectrum absorber because the silicon bottom cell harvests the
red light transmitted by the perovskite top cell, so its spectral component is near zero in
Fig 3y. The inversion is therefore specifically a single-junction perovskite effect.

### Efficiency ratings mispredict field energy, Fig 3

This result is easy to miss because standard-test efficiency is not annual field energy.
Modern silicon, single-junction perovskite and tandem have STC efficiencies of about 22.0%,
19.3% and 28.3%. By that ruler, perovskite is less efficient than the silicon it would replace.
By annual energy per kWp, however, it is about 1.03× modern silicon because its thermal benefit
offsets part of the lower efficiency, as shown in Fig 3a. Conversely, the tandem's high efficiency appears
only weakly per kWp, at about 1.01×, but strongly per square metre, at about 1.30×. The land-based utility market should
therefore be judged primarily per kWp, where single-junction perovskite has a small edge; the
rooftop market should be judged per area, where tandem is the area-constrained technology.

Changing the ruler from STC efficiency to per-kWp energy flips the apparent ranking in Fig 3b.
Perovskite is worst by efficiency but best by per-kWp energy, while tandem is best by efficiency
and area value rather than by land-based utility-scale per-kWp yield. This segmentation sets the boundary
for deployment: single-junction perovskite is a land-based utility-scale capacity play, tandem is a
rooftop-area play, and modern silicon remains competitive where per-kWp advantages are small or
durability risk dominates.

### Substitution is lifetime-gated, Fig 4

Whether this yield edge becomes substitution is governed by lifetime, degradation and capex,
not by the ~3% physics edge alone. In the 31-province, 2027–2050 NPV LCOE calculation, the
provincial cloud is summarized as national mean lines with 10–90% provincial bands: before the
2032 lifetime breakthrough assumption, perovskite LCOE is high because of 15-year lifetime and
faster degradation; after breakthrough to 25 years it enters the competitive range in Fig 4a.
The cost-lever decomposition makes the hierarchy explicit. Relative to an optimistic
perovskite baseline, removing the ~3% yield edge adds only ~0.07 cents/kWh, whereas capex,
lifetime and degradation assumptions move LCOE much more strongly in Fig 4b. The first gate is
therefore durability.

A reduced-form substitution model calibrated on the 2015–2023 multi- to mono-crystalline
silicon switch, with R²=0.83, translates that economic bound into scenario timing. In Fig 4c,
the central allocation path shows structured coexistence through the 2030s without treating the
path as a forecast. A 1,000-draw Monte-Carlo ensemble
over learning rates, cost floors, breakthrough year, final lifetime and choice sharpness gives
an LCOE-crossover distribution, not a deterministic adoption forecast: P10/P50/P90 =
2030/2032/2039, with 2.7% of draws not crossing by 2050 because lifetime remains inadequate, as shown
in Fig 4d. The geography of value is mirrored by a geography of risk in Fig 4x, while the
geography of timing is only weakly dispersed in Fig 4y.

### Deploy by physics, not irradiance intuition, Fig 5

Placing provincial perovskite advantage and high-latitude land penalty on the same land-based utility
decision plane exposes the mismatch directly. The high-advantage, lower-penalty Southwest/South
occupies the land-utility priority region, but its bubbles show 2024 installed capacity and are not the
largest; several large-capacity provinces sit in middle-advantage or higher-penalty regions
in Fig 5a. Binning provinces by advantage, the top third of regions holds only ~24% of installed
PV capacity in Fig 5b. If single-junction perovskite enters land-based utility deployment first, the
highest-value initial sites should therefore follow operating-temperature, relative-advantage
and land-penalty maps, not simply maximum irradiance or existing capacity.

High-latitude ground-mounted deployment also carries a technology-independent land penalty: row
spacing and self-shading losses rise with latitude, with r=0.98 in Fig 5c. The Northwest thus combines
strong absolute irradiance with smaller perovskite relative advantage and higher land penalty.
Together, the five figures imply a segmented strategy: deploy single-junction perovskite first
in hot, high-advantage Southwest/South land-based utility markets; deploy tandem where area is scarce,
especially rooftops; and retain modern silicon in ground-mounted regions where the per-kWp advantage
is small and durability risk is most consequential.

---

## Discussion

Our central result is that the perovskite-over-silicon energy-yield advantage inverts with
resource quality and is carried by two separable mechanisms. This sharpens, and in one respect
overturns, the prevailing picture. Cell- and site-level energy-yield studies by Moot et al. 2021
and Dirnberger et al. 2015 establish that perovskite's smaller temperature coefficient and blue-shifted
response raise its field yield; we show that, integrated over a country and referenced
to the silicon now installed, the net per-kWp gain is modest, about 3%, and — counterintuitively —
*greatest where irradiance is lowest*. The intuition that the sunniest, highest-yield sites are
where an advanced cell matters most is therefore inverted for this comparison. Decomposing the
advantage rather than reporting it as one number further shows that the temperature and spectral
mechanisms, often discussed together, are independent in space, time and across architecture —
and that, against modern silicon, the temperature term alone survives for the two-terminal
tandem, which we accordingly identify as an area- rather than yield-driven technology.

Two choices make the result robust rather than baseline-dependent. First, the comparison is
against modern ≈22% silicon, not the ≈15% early cell common in perovskite benchmarking; this
roughly halves the advantage but leaves the inversion and its mechanisms intact, indicating they
are properties of the device physics. Second, the twin is validated numerically and then
benchmarked against the operating fleet at r=0.89, so the spatial pattern is anchored to reality
even though the fleet comparison also contains BOS losses, curtailment and dispatch. The official release-gated operation evidence is the NEA PV utilization-rate layer. A model
correction surfaced by this design is worth noting: the two-terminal tandem's temperature
coefficient, left by a hand-set parameter at an unphysical −0.06 %/°C, was re-calibrated to the
literature −0.30 %/°C, which removes a spurious tandem land-based utility advantage — illustrating the
value of an inspectable, emergent-coefficient model over one in which γ is an input.

The principal limitation is perovskite durability, which gates whether the yield advantage is
ever realised economically: we do not assume a lifetime breakthrough but sample it, reporting
the 2.7% of futures without an LCOE crossover by 2050 and a geography of lifetime risk in which
the policy-favoured Northwest is the most fragile. Indium material constraints bind at the
global multi-TW/yr scale rather than for China's near-term transition, as detailed in the SI.
Two boundaries of scope point to follow-on work: the optimal cell band gap is, by
detailed-balance calculation, nearly invariant across China's narrow air-mass range. The
single-junction optimum is about 1.40 eV, and the tandem top-cell optimum is about 1.74 eV, so a globally wider climate range may be needed to expose location-specific band-gap
design; and absolute-yield, transmission-aware land siting optimisation would complement the
per-kWp-advantage map presented here. These conclusions should not be extrapolated directly to
offshore or floating PV: water and marine environments may lower module temperature and weaken
the perovskite temperature advantage, while salt spray, humidity, platforms and operating costs
would change both the lifetime gate and LCOE.

The practical implication is specific: land-based utility-scale technology choice for perovskite should be
made on an operating-temperature map, not an irradiance map, placing it first in the hot
Southwest rather than the sunny Northwest; rooftop programmes are where the tandem's efficiency
is monetised; and, because durability gates the transition, location-aware reliability
qualification — weighted to the hot Southwest and the thin-margin Northwest — is worth more than
further cell-cost reduction.

---

## Methods

### The digital twin

A De Soto five-parameter single-diode cell model is used; parameters per technology in `pvsim/
materials.py` with literature citations. I-V solved via Lambert W; module/array assembly with
series/parallel scaling. Cell temperature is calculated with the Faiman model, using u0=25 and
u1=6.84 W m^-2 K^-1 as configurable defaults. Optics: Martin-Ruiz IAM; spectral mismatch from a SPECTRL2 clear-sky spectrum
integrated against each technology's EQE, tabulated against solar zenith. This clear-sky
spectral treatment captures air-mass effects but not cloud-induced spectral shifts. Optional bifacial
gain uses a view-factor model, with a PVWatts inverter. The temperature behaviour is generated by a
physical saturation-current law. I0 at temperature T equals I0_ref times the cube of T over Tref,
multiplied by an exponential activation-energy term. The activation energy is calibrated so the
modelled gamma_Pmax matches the literature value per technology — i.e. temperature
coefficients are *reproduced*, not imposed.

### Validation

`scripts/validate_against_pvlib.py`: max-power agreement with pvlib is better than 0.001% for
P_mp and 0.0007% across P_mp, V_oc, I_sc and FF over STC, hot/high-irradiance, low-light and cold/high-
irradiance conditions. A C# port used by an interactive simulator reproduces the Python twin
bit-for-bit. The operating-fleet comparison is used as a system-level spatial validation:
provincial clean-physics yields correlate with reported utilisation hours, while the mean
offset is interpreted as BOS, curtailment and dispatch loss rather than a device-physics error.
ERA5-Land grid uncertainty is reported in the SI grid appendix. The 0.1 degree layer is used
for national spatial pattern and regional ranking, while province-level numerical claims use
the full 8,760-hour anchors.

### Data provenance, see `docs/DATA_PROVENANCE.md`

We separate inputs by epistemic status. **Tier 1, measured/observed:** PVGIS typical-
meteorological-year hourly climate for 12 cities and 31 provincial anchors; NASA POWER 1° with
about 954 cells and ERA5-Land 0.1° with about 95k cells for gridded climatology; ASTM G173
reference spectrum; China cumulative PV from 2015 to 2024 from NEA, module price from BNEF and
mono-share history from ITRPV; provincial 2024 capacity from the official NEA source
table, with raw provincial shares scaled to the 886.6 GW national total; provincial fleet-hour
anchors from a versioned system-anchor table; official PV utilization rates from NEA; provincial total electricity generation from NBS; GEM plant geolocations; grid emission-factor baseline
from MEE; indium production from USGS. **Tier 2, literature
physical parameters:** De Soto parameters and temperature coefficients for all four devices —
early c-Si at 15.3% and -0.45 %/°C, **modern TOPCon/PERC c-Si as the baseline at 22% and
-0.32 %/°C from ITRPV 2023/2024**, perovskite from Moot et al. 2021 and tandem from Babics et al. 2023 — band
gaps, metal intensities from Wagner 2024, embodied carbon from Fraunhofer ISE and IPCC AR6, and
tandem capex from NREL Cordell 2025. The main comparison is
against modern silicon; early c-Si is retained only as a historical reference. The tandem
temperature coefficient was re-calibrated from a hand-set value that produced an unphysical
-0.06 %/°C to the literature -0.30 %/°C. **Tier 3, model outputs:** all yields, temperatures, advantages,
decompositions and LCOEs. **Tier 4, scenario/forecast:** future capacity targets, grid
decarbonisation, learning rates, cost floors, lifetime breakthrough, and the substitution
trajectory — every forward parameter is sampled in the Monte-Carlo ensemble and reported as a
P10-P90 scenario range, never a deterministic point forecast.

Installed-capacity, PV utilization-rate and fleet-hour inputs use provincial grid-connected PV aggregates. The 2024
capacity table preserves the compiled provincial distribution and scales it uniformly to the
national total, so capacity-weighted figures close to 886.6 GW without changing province shares. The
physical-yield model does not split land-based utility, rooftop, floating or offshore PV into
separate technology scenarios; offshore or floating projects, where present in official totals,
are treated only as part of the provincial aggregate and are not used for separate deployment
claims.

### Two-mechanism decomposition

For each location the advantage is decomposed by counterfactual toggling: the spectral
component is the difference between the full run and a spectrally-flat run; the temperature
component is calculated from the difference between gamma_perov and gamma_cSi multiplied by
the departure of T_cell from 25 C and integrated over the energy-weighted operating distribution;
the IAM optical residual is small. Drivers,
namely cell temperature and air mass, are irradiance-weighted. Caches are
`outputs/advantage_drivers.csv` for perovskite and `outputs/advantage_drivers_tandem.csv` for
tandem. Temporal decomposition in Fig 3x reshapes the 8,760-hour series to day x solar-hour.
PVGIS timestamps are UTC; local solar time is recovered from the minimum-zenith hour.

### Economics and substitution

NPV LCOE with annual degradation, burn-in, 5% discount and 1.5% opex. Wright learning curve
uses cost as a function of cumulative deployment, equal to cost0 times Q over Q0 raised to minus b,
with b equal to negative log base 2 of one minus LR. National allocation by softmax merit order on LCOE,
calibrated to the 2015-2023 multi->mono switch, with R^2=0.83; learning is driven by an exogenous
global schedule to prevent allocation lock-in. Monte-Carlo: 1,000 draws over learning rates,
floors, breakthrough year, final lifetime and allocation temperature. Degradation-risk analysis
in Fig 4x and timing-geography analysis in Fig 4y sweep, respectively, perovskite degradation
at equal cost and the perovskite cost floor under a central capex trajectory.

### Reproducibility

Python 3.11; environment in `docs/DATA.md`. Every main and SI figure is regenerated by a
named `scripts/fig_*.py`; gridded-climate fetchers cache locally on first run.

---

## Figure legends

<img alt="Figure 1" src="../outputs/figures/NEWFig1_inversion.png">

**Figure 1. Perovskite's per-kWp advantage over modern silicon inverts geographically.** Panel a:
Spatial pattern of perovskite advantage over modern c-Si at 0.1° resolution across ~95,000 land cells in China: it is
largest in the hot, low-latitude Southwest and smallest across the high-irradiance Northwest and
Tibetan plateau. Panel b: The grid-cell advantage is inversely correlated with annual irradiance
with r=-0.51; the binned median makes the headline result explicit: weaker sun gives a larger
relative per-kWp gain. Panel c: Resource-band aggregation shows that the inversion is the sum of two
mechanisms, temperature and spectrum, that both peak in the hot Southwest.

<img alt="Figure 2" src="../outputs/figures/NEWFig2_mechanisms.png">

**Figure 2. The geographic inversion is carried by two independent physical mechanisms.** Panel a:
Counterfactual decomposition separates a temperature term, which scales with irradiance-weighted
cell temperature at r=+0.98, from a spectral term, which scales with irradiance-weighted air mass
at r=-0.85. Lower air mass means a bluer spectrum. Pale points are PVGIS-sampled climate points
used to visualize the mechanism relationship; solid points are the 31 provincial anchors.
Panel b: Monthly fingerprints across 31 provinces show temporal independence: the temperature
term is a summer-only benefit, whereas the spectral term persists through the year. Shading
marks the 10-90% range across provinces.

<img alt="Figure 3" src="../outputs/figures/NEWFig3_segmentation.png">

**Figure 3. Efficiency ratings mispredict field energy; changing the ruler flips the ranking.**
Panel a: Relative to modern c-Si, perovskite is lower in STC efficiency at 0.88× but higher in field
yield per kWp at 1.03× and lower per square metre at 0.90×. The tandem is higher in efficiency
at 1.29× and area yield at 1.30× but nearly tied per kWp at 1.01×. Dots show the 31 provinces. Panel b:
The same result as a ranking problem: by lab efficiency, tandem leads and perovskite trails; by
land-based utility energy per kWp, perovskite has the best mean advantage. The correct market
ruler is therefore per kWp for land-based utility projects and per m² for rooftops.

<img alt="Figure 4" src="../outputs/figures/NEWFig4_economics_timing.png">

**Figure 4. The economics and timing of substitution are gated by lifetime.** Panel a: NPV LCOE for
the three technologies from 2028 to 2050; lines are national means and bands mark the 10-90%
range across provinces. A 25-year lifetime breakthrough narrows the gap enough for the
perovskite crossover around 2032, whereas the 15-year case remains uneconomic. Panel b: A delta-LCOE
tornado shows that capex, lifetime and degradation dominate the cost gap; losing the
perovskite yield edge changes LCOE by only +0.07 cents/kWh. Panel c: Central allocation paths show
structured coexistence after the 2032 breakthrough without presenting a point forecast. Panel d:
Monte-Carlo timing scenario ensemble gives P10/P50/P90
LCOE-crossover years of 2030/2032/2039, with an explicit >2050 tail containing 2.7% of draws.

<img alt="Figure 5" src="../outputs/figures/NEWFig5_deployment.png">

**Figure 5. Deploy by physics: high-advantage regions are under-built today.** Panel a: A land-based utility
decision plane compares perovskite per-kWp advantage with row-spacing land penalty; bubble area
shows 2024 installed PV capacity. The high-advantage, lower-penalty priority zone does not
dominate today's capacity. Panel b: Provinces in the top third of
perovskite advantage hold only 24% of installed PV capacity, compared with 46% in the middle
third and 30% in the low-advantage third. Panel c: High-latitude ground-mounted projects also carry a
technology-independent row-spacing land penalty that rises strongly with latitude, with r=0.98,
reinforcing the case for perovskite in the Southwest, tandem on rooftops, and modern c-Si in
low-advantage ground-mounted regions.

---

## Supporting Information

<img alt="Figure 1x" src="../outputs/figures/MainFigV_fleet_validation.png">

**Figure 1x, SI. Fleet-anchored system validation.** Panel a: Twin clean-physics
specific yield for modern c-Si versus versioned provincial PV fleet-utilisation hours. The utilisation
hours are in kWh/kWp/yr and are used as a system-level anchor, not as a release-gated official row layer. The 31 provinces are coloured
by resource band; points fall between the 1:1 no-loss line and the −15% mean-system-loss line,
with r=0.89. The uniform ~15% offset equals the standard balance-of-system loss from soiling,
wiring, availability and curtailment that the clean-physics twin
does not model; after a uniform 15.3% system-loss correction, RMSE is 102 kWh/kWp and MAPE is
7.1%, as reported in Table Sx. Panel b: The province-by-province residual, calculated as 1 − fleet/twin, is an inferred
real-world loss map: a ~10% baseline everywhere, with the excess in the Northwest at about 14%
versus about 7% in the Southwest recovering the known curtailment there. Utilisation hours are representative public values. The official NEA utilization-rate layer is reported separately in SI.

<img alt="Figure 3x" src="../outputs/figures/MainFig3x_temporal_fingerprint.png">

**Figure 3x, SI. Two mechanisms, two temporal fingerprints.** Panels a and b: Day-of-year × solar-hour
heatmaps of the temperature and spectral components of the perovskite advantage for Wuhan. The
temperature layer is present only in summer and vanishes in winter; the spectral layer is a
persistent midday band present year-round. Panel c: Power-weighted diurnal profiles show that both components
peak at solar noon, so they share the same timing. Panel d: Power-weighted seasonal profiles show that the temperature term
swings strongly, with coefficient of variation 0.75, while the spectral term is nearly flat at 0.32 —
so the two mechanisms are decoupled in time. Note: our prior expectation of an afternoon
temperature lag was not borne out because cell temperature tracks instantaneous irradiance, and is not
claimed. PVGIS timestamps are UTC; local solar time was recovered from the minimum-zenith hour.

<img alt="Figure 3y" src="../outputs/figures/MainFig3y_tandem_decomposition.png">

**Figure 3y, SI. Against modern silicon the tandem has no per-kWp edge, and none of it is
spectral.** Panel a: National-mean decomposition of the advantage over modern c-Si into non-spectral
components, meaning temperature plus low-light response, and spectral components for perovskite versus tandem; the tandem's
total per-kWp advantage is only 0.9% and its spectral leg is 0.02%, against perovskite's
1.29% spectral. Panel b: Spectral component by resource band: it grows from band I→IV for perovskite
but stays flat near zero for tandem. Panel c: Spectral component versus irradiance-weighted air mass:
perovskite tracks the spectrum with r=-0.94, while tandem stays flat at ~0. A two-terminal tandem is
a full-spectrum absorber because its silicon bottom cell harvests the red light transmitted by the top cell, and
therefore sees the spectrum like silicon — so it carries no land-based utility/temperature advantage, and
its value is area, as shown in Figs 2 and 5, not per-kWp yield.

<img alt="Figure 4x" src="../outputs/figures/MainFig4x_degradation_risk.png">

**Figure 4x, SI. The geography of lifetime risk against modern silicon.** Panel a: At equal capex,
which isolates lifetime, the perovskite LCOE premium over modern c-Si as a surface over province
and degradation rate. Provinces are sorted by advantage; the black parity contour sweeps rightward for
higher-advantage provinces. Panel b: Maximum tolerable degradation rate per province, also called the parity
degradation rate, on an equal-area hex cartogram: green = robust Southwest at ~1.1%/yr, red = fragile
Northwest at ~0.9%/yr. Panel c: Representative LCOE-premium curves compare Southwest provinces,
Chongqing and Sichuan, with Northwest provinces, Xinjiang and Nei Mongol. Even the most robust province demands
degradation <1.1%/yr, against today's ~3%/yr — and the policy-favoured Northwest is the most
fragile.

<img alt="Figure 4y" src="../outputs/figures/MainFig4y_substitution_timing_geo.png">

**Figure 4y, SI. The geography of substitution timing is conditional on the cost margin.** Panel a:
Year in which perovskite first beats modern c-Si on LCOE under a central capex trajectory,
shown on an equal-area hex cartogram: a modest front advancing from the Southwest at ~2037 to the Northwest
at ~2039. Panel b: Crossover year versus per-kWp advantage, coloured by resource band: advantage
cleanly orders the crossover with r=-0.95, and the Southwest goes first. Panel c: The Southwest→Northwest timing
spread as a function of perovskite's cost edge over silicon: a decisive cost win makes
substitution synchronous with ~1 yr spread, while near cost parity the front widens to several
years. That front is late, with some provinces not crossing by 2050. Under central assumptions the spread
is only ~2 years, because the small per-kWp advantage range is dwarfed by the capex decline; the
dominant geography is therefore in advantage magnitude and risk, not timing.

## Figure inventory, file index

**Main**
- **Fig 1** `NEWFig1_inversion` — 0.1° climatological spatial-pattern map + irradiance
  anticorrelation with r=-0.51 + stacked temperature/spectral mechanisms.
- **Fig 2** `NEWFig2_mechanisms` — independent temperature driver with r=+0.98 and spectral driver with r=-0.85
  drivers + monthly fingerprints.
- **Fig 3** `NEWFig3_segmentation` — efficiency vs field-energy ruler; per-kWp and per-m²
  rankings split land-based utility and rooftop markets.
- **Fig 4** `NEWFig4_economics_timing` — LCOE 10-90% bands + delta-LCOE levers +
  substitution trajectory + Monte-Carlo crossover from 2030 to 2039.
- **Fig 5** `NEWFig5_deployment` — advantage-vs-land-penalty decision plane +
  high-advantage top third at only 24% of capacity + land-penalty source with r=0.98.

**SI validation & mechanistic depth**
- `MainFig1_twin_and_devices` — pvlib validation over 126 conditions + 8,760-h advantage heatmap
  + degradation. This was the former main Fig 1 and is now validation support.
- `MainFigV_fleet_validation` — fleet-anchored system validation with r=0.89 and RMSE=102 kWh/kWp
  after uniform 15.3% loss correction + inferred loss/curtailment map, shown as Fig 1x.
- `MainFig3x_temporal_fingerprint` — temperature term seasonal, spectral term year-round,
  demonstrating mechanism independence in time.
- `MainFig3y_tandem_decomposition` — tandem advantage almost purely non-spectral
  because it behaves as a full-spectrum absorber; the spectral-advantage hypothesis is refuted.
- `MainFig4x_degradation_risk` — geography of lifetime risk; SW absorbs ~1.4%/yr and NW ~1.0%/yr.
- `MainFig4y_substitution_timing_geo` — timing ordered by advantage with r=-0.95 but only ~3-yr
  SW->NW spread; conditional on cost margin.

**SI robustness & context**
- `MainFig3b` with 5 adversarial scenarios and `MainFig3c` with the 0.1° grid — inversion robustness.
- `MainFig4_indium_constraint` — global, not national, material limit.
- Carbon payback / scenarios; 2015-2024 learning backcast with R^2=0.887.

**Overviews:** `_OVERVIEW_main_figures.png` for the 5-figure spine and `_OVERVIEW_deep_digs.png`
for the 4 mechanistic digs.

---

## References

1. De Soto, W., Klein, S.A., Beckman, W.A. 2006. Improvement and validation of a model for
   photovoltaic array performance. *Solar Energy* 80, 78–88. DOI 10.1016/j.solener.2005.06.010.
2. Faiman, D. 2008. Assessing the outdoor operating temperature of photovoltaic modules.
   *Prog. Photovolt.* 16, 307–315. DOI 10.1002/pip.813.
3. Dirnberger, D., et al. 2015. On the impact of solar spectral irradiance on the yield of
   different PV technologies. *Sol. Energy Mater. Sol. Cells* 132, 431–442. DOI 10.1016/j.solmat.2014.09.034.
4. Dupré, O., Vaillon, R., Green, M.A. 2015. Physics of the temperature coefficients of solar
   cells. *Sol. Energy Mater. Sol. Cells* 140, 92–100. DOI 10.1016/j.solmat.2015.03.025.
5. Hörantner, M.T., Snaith, H.J. 2017. Predicting and optimising the energy yield of
   perovskite-on-silicon tandem solar cells. *Energy Environ. Sci.* 10, 1983–1993. DOI 10.1039/c7ee01232b.
6. Gota, F., et al. 2020. Energy yield advantages of three-terminal perovskite-silicon
   tandem photovoltaics. *Joule* 4, 2387–2403. DOI 10.1016/j.joule.2020.08.021.
7. Moot, T., et al. 2021. Temperature coefficients of perovskite photovoltaics for energy
   yield calculations. *ACS Energy Lett.* 6, 2038–2047. DOI 10.1021/acsenergylett.1c00748.
8. Babics, M., et al. 2023. Temperature coefficients of perovskite/silicon tandem solar cells.
   *ACS Energy Lett.* 8, 3013–3015. DOI 10.1021/acsenergylett.3c00930.
9. Cordell, J.J., Woodhouse, M., Warren, E.L. 2025. Technoeconomic analysis of
   perovskite/silicon tandem solar modules. *Joule* 9, 101781. DOI 10.1016/j.joule.2024.10.013.
10. Wagner, L., et al. 2024. The resource demands of multi-terawatt-scale perovskite tandem
   photovoltaics. *Joule* 8, 1142–1160. DOI 10.1016/j.joule.2024.01.024.
