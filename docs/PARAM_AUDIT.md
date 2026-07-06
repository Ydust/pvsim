# Parameter & data audit (pre-draft hardening)

Verification of every load-bearing parameter before manuscript drafting.
Verdict key: 🟢 solid/cited · 🟡 representative, needs firmer source in text ·
🔴 error found & corrected.

## Load-bearing parameters (each headline finding depends on these)

| Parameter | Value used | Literature check | Verdict |
|---|---|---|---|
| c-Si γ_Pmax | −0.45 %/°C | −0.40 to −0.45 (early/standard c-Si); modern PERC/TOPCon ≈ −0.35 | 🟡 OK for "early c-Si" framing; state explicitly, add sensitivity note |
| Perovskite γ_Pmax | −0.15 %/°C | Moot et al. ACS Energy Letters 2021: −0.08 to −0.25, champion −0.13; range to −0.7 | 🟢 central, even conservative |
| Tandem γ_Pmax | −0.30 %/°C | Babics et al. ACS Energy Letters 2023 reports tandem temperature coefficients in the same range | 🟢 |
| **Geographic inversion mechanism** (γ difference) | c-Si−perov ≈ 0.30 %/°C | γ values both verified | 🟢 **mechanism solid** |
| Tandem MSP / capex | cell $0.428/W | Cordell et al. NREL TEA (OSTI 2481281), Table 2 | 🟢 matches source (local PDF verified) |
| Perovskite lifetime/deg | 15 yr / 3%/yr / 10% burn-in (→25 yr breakthrough) | representative; stability improving fast (IEC 61215; GCL claims) | 🟡 representative; MC samples the uncertainty (Fig 6) |
| **Indium intensity** | ~~30 kg/MW~~ → **1.9 kg/MW @100nm ITO** | Wagner *Joule* 2024 Table S13 (100nm = 1922 t/TWp) | 🔴 **was 15× too high — CORRECTED** |
| c-Si Ag intensity | 10 kg/MW | ITRPV 2023 ~10–15 mg/W | 🟢 |
| China indium production | ~600→676 t/yr | USGS MCS: global ~900–1100, China ~half | 🟡 order OK; cite USGS, add global 968 t/yr |

## Supporting data

| Data | Value | Source | Verdict |
|---|---|---|---|
| China PV cumulative 2024 | 887 GW | NEA 886.66 GW | 🟢 |
| Grid emission factor 2024→2050 | 0.55→0.10 kgCO₂/kWh | IEA ETP / DRC | 🟡 trajectory plausible, cite |
| c-Si module price 2015→2024 | $0.55→$0.10/W | BNEF/ITRPV; backcast R²=0.887 | 🟢 fit validates |
| Mono share 2015→2023 | 24%→98% | ITRPV roadmaps | 🟢 calibration R²=0.83 |
| ERA5 ssrd → GHI | /3.6e6 | cross-checked vs POWER magnitude (1010–2357 kWh/m²/yr) | 🟢 |

## 🔴 The one material error and its fix

**Indium intensity was 30 kg/MW; correct value ≈1.9 kg/MW (100 nm ITO).**
Root cause: the total all-material demand (30,170 t/TWp, Wagner Joule 2024) was
mistakenly assigned to indium alone.

Consequence corrected:
- China 2030 perovskite+tandem indium demand: ~~2006 t/yr~~ → **38 t/yr**
- vs China production ~676 t/yr: ~~3.0× over (hard cap)~~ → **~10% (not binding)**
- "Shandong+Hebei consume 58%" — number exists but is meaningless when total is slack.

**Reframing (kept as Shift 3, but honest):** indium is a *global, ITO-thickness-
dependent* constraint — at 1 TWp/yr with 100 nm ITO it is ~199% of world primary
production (Wagner 2024) — that motivates indium-free TCO (AZO/FTO); it does NOT
gate China's near-term transition. Fig 4 rebuilt accordingly
(`MainFig4_indium_constraint.png`).

## Net impact on the three headline findings

| Shift | Status after audit |
|---|---|
| ① Lifetime gate | 🟢 intact (γ + mechanism verified) |
| ② Geographic inversion | 🟢 intact (γ difference verified; already robust 5-scenario + 95k cells) |
| ③ Indium | 🟠 reframed from "China 3× cap" to "global TW-scale limit"; honest and still novel |

## Open items to address in the manuscript text

1. State c-Si γ = −0.45 is the early-/standard-cell value; add a one-line
   sensitivity (modern −0.35 shrinks but does not flip the inversion).
2. Cite USGS for indium production; Wagner *Joule* 2024 for indium intensity.
3. Note grid-EF and lifetime trajectories are scenario inputs (already in MC).
