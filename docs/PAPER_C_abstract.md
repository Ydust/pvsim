# Paper C — front matter for Joule-plus review

Target standard: Joule-plus. The internal bar is higher than a routine Joule submission.
Companion tool paper: Path D, SoftwareX or JOSS.

---

## Title

**Perovskite gains most where sunlight is weakest: a physics-resolved
reassessment of China's solar transition**

*Graphical-abstract tagline, kept separate and punchy:*
"Physics rewrites the perovskite substitution narrative."

*Alternative titles considered, see FIGURE_SPINE / discussion:*
- A physics-consistent digital twin reframes the timing, geography and material
  limits of China's perovskite transition
- Lifetime, not cost, gates China's perovskite photovoltaic transition
- Hourly device physics overturns cost-curve projections of China's perovskite transition

---

## Keywords

perovskite photovoltaics · technology substitution · digital twin ·
single-diode model · levelized cost of electricity · temperature coefficient ·
technology siting · China energy transition

---

## Context & Scale

China installs more solar capacity than the rest of the world combined, and its
next move — from crystalline silicon to perovskite and perovskite–silicon tandem
cells — is usually projected by extrapolating falling module costs. Cost curves,
however, say nothing about how a panel actually behaves hour-by-hour across a
continent of climates. Resolving that device physics nationwide, we find that
perovskite's field value is not where intuition puts it: the greatest land-based utility
advantage appears in the hot Southwest rather than the sunny Northwest,
because operating temperature and low-air-mass spectra add there. Efficiency ratings also mislead:
land-based utility projects reward energy per kWp, whereas rooftops reward energy
per square metre. Lifetime then gates whether the physics advantage becomes
economic at all. Aligning R&D with durability and deployment with these
physics-resolved regions would make China's perovskite transition faster and
better targeted.

---

## Abstract, about 210 words

China's planned shift from crystalline silicon, here modern c-Si, to perovskite and
perovskite–silicon tandem photovoltaics is routinely projected from cost-curve
extrapolation. Here we replace average-cost assumptions with an 8760-hour,
physics-consistent digital twin: single-diode device physics resolved across
~95,000 0.1° land cells across China, benchmarked numerically against pvlib to
0.0007% and anchored against the operating fleet with r=0.89. The result overturns the
usual geography. Perovskite's land-based utility-scale per-kWp advantage over modern c-Si
is modest, about 3%, but largest where sunlight is weakest, anti-correlating with
annual irradiance with r=-0.51 and peaking in the cloudy, hot Southwest rather
than the policy-favoured Northwest. Counterfactual decomposition shows two
independent mechanisms: a temperature term tied to irradiance-weighted cell
temperature with r=+0.98 and a spectral term tied to air mass with r=-0.85, with
distinct monthly fingerprints. Changing the performance ruler also flips the
technology ranking: perovskite has lower STC efficiency than modern c-Si
by a factor of 0.88× but higher field yield per kWp by a factor of 1.03×, whereas tandem's main value is
area yield at 1.30× per m². Economics then becomes lifetime-gated: losing the
physics yield edge raises LCOE by only +0.07 cents/kWh, while capex, lifetime
and degradation dominate. A Monte Carlo scenario ensemble gives P10/P50/P90
LCOE-crossover years of 2030/2032/2039, with 2.7% of draws not crossing by 2050. The
deployment implication is immediate: provinces in the top third of perovskite
advantage hold only 24% of 2024 installed PV capacity, and high-latitude ground-mounted
projects face a strong row-spacing land penalty with r=0.98. Offshore and floating PV are outside
this land-based deployment scope.

---

## Abstract ↔ figure / evidence map

| Abstract claim | Figure | Key number |
|---|---|---|
| physics-consistent twin, benchmarked and fleet-anchored | methods / SI | pvlib 0.0007%, fleet r=0.89 |
| geographic inversion SW>NW | Fig 1 | r=-0.51, ~95k cells |
| two independent mechanisms | Fig 2 | temperature r=+0.98; spectral r=-0.85 |
| efficiency ratings mispredict energy | Fig 3 | perovskite 0.88× efficiency but 1.03× per kWp; tandem 1.30× per m² |
| lifetime gates substitution scenario timing | Fig 4 | +0.07 cents/kWh yield lever; P10/P50/P90 = 2030/2032/2039; 2.7% no crossover by 2050 |
| land-based deployment mismatch and land penalty | Fig 5 | top advantage third = 24% of capacity; latitude penalty r=0.98 |
