# SI Silicon Baseline Sensitivity

Last updated: 2026-07-01

Directional status: preserved.

This appendix tests whether the geographic inversion depends on choosing one modern silicon baseline. It perturbs the silicon power-temperature coefficient across representative HJT, TOPCon and PERC cases while keeping the same province-level weather and perovskite yields.

The perturbation is applied to annual per-kWp yield with the irradiance-weighted cell temperature from the provincial simulations. STC efficiency is reported for context, but the annual per-kWp comparison is driven by the temperature coefficient rather than module area.

| Silicon baseline | STC efficiency percent | Gamma percent per C | Median advantage percent | Minimum | Maximum | Irradiance relation r | Band I median | Band IV median | Direction preserved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| HJT low temperature coefficient | 22.5 | -0.26 | 2.90 | 1.15 | 4.36 | -0.603 | 1.35 | 3.90 | True |
| TOPCon central | 22.0 | -0.32 | 3.43 | 0.93 | 5.15 | -0.540 | 1.68 | 4.68 | True |
| PERC high temperature coefficient | 21.0 | -0.37 | 3.87 | 0.76 | 5.82 | -0.500 | 1.95 | 5.34 | True |

## Interpretation

The inversion direction is preserved when the silicon baseline is moved across the selected modern module range. The magnitude changes, especially for the low temperature coefficient HJT case, but the advantage remains larger in resource band IV than in resource band I and the irradiance relation remains negative.

This supports the main text framing that the result is a field-yield geography effect rather than an artefact of one silicon comparator.

## Outputs

| File | Role |
| --- | --- |
| `outputs/si_silicon_baseline_sensitivity.csv` | Province-level values for each silicon baseline |
| `outputs/si_silicon_baseline_sensitivity_summary.csv` | Summary statistics used in this appendix |
