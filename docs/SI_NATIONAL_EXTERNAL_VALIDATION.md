# SI National External Validation

Last updated: 2026-07-01

Validation status: partial national aggregate check.

This check adds one independent official measured-generation reference. It uses the National Bureau of Statistics 2024 Statistical Communique. The source reports national solar generation, national year-end solar capacity and the capacity growth rate. The check is independent of the model and useful for national-scale plausibility. It is not a province-level or plant-level external validation layer because it has no location axis.

Source URL: `https://www.stats.gov.cn/sj/zxfb/202502/t20250228_1958817.html`

| Quantity | Value | Unit | Interpretation |
| --- | ---: | --- | --- |
| Official 2024 solar generation | 839.04 | TWh | Independent measured national generation |
| Official year-end solar capacity | 886.66 | GW | National capacity denominator at year end |
| Official capacity growth | 45.2 | percent | Used only to infer a simple start-year denominator |
| Model scaled national capacity | 886.60 | GW | Sum of the scaled provincial capacity table |
| Model minus official capacity | -0.06 | GW | Confirms capacity closure is within rounding |
| Inferred start-year capacity | 610.65 | GW | Year-end capacity divided by one plus growth |
| Simple average capacity | 748.65 | GW | Average of start-year and year-end capacity |
| Observed specific yield using year-end capacity | 946.3 | kWh per kW | Lower specific-yield bound under fast growth |
| Observed specific yield using simple average capacity | 1120.7 | kWh per kW | Preferred aggregate comparison denominator |
| Clean model c-Si national yield | 1493.6 | kWh per kWp | Capacity-weighted 31-province model output |
| Mean system-loss correction | 15.3 | percent | Inferred from provincial fleet-hour anchor |
| Loss-corrected model c-Si yield | 1265.4 | kWh per kWp | Aggregate model value after system-loss correction |
| Bias against average-capacity observed yield | 144.7 | kWh per kWp | Model minus official aggregate denominator result |
| Bias against average-capacity observed yield | 12.9 | percent | Same bias in relative terms |

Interpretation:

The official year-end capacity denominator gives a low observed specific-yield value because solar capacity grew rapidly during 2024. A simple average of inferred start-year and year-end capacity gives 1120.7 kWh per kW. The loss-corrected model gives 1265.4 kWh per kWp. The comparison is close enough for a national-scale plausibility check, but the remaining 144.7 kWh per kWp difference cannot be interpreted as a pure model error. It also reflects intra-year capacity additions, fleet age, curtailment, availability, regional timing and source convention differences.

Release decision:

This check should be cited as national aggregate validation only. It is paired with the NEA PV utilization-rate layer for PV-specific spatial operation evidence, the NBS provincial total electricity-generation layer for absolute spatial generation context and the CTGR operating-region layer for a PV-specific absolute generation sample. It does not by itself provide a complete government province-level PV generation inventory.

Machine-readable table: `outputs/si_national_external_validation.csv`
