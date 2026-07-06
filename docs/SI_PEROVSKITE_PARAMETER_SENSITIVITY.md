# SI Perovskite Parameter Sensitivity

Last updated: 2026-07-01

Directional status: preserved.

This appendix stress-tests the mechanism decomposition against perovskite parameter variation. It does not replace full material-specific device simulation. It asks whether the main geographic inversion survives when the temperature coefficient and spectral-response strength are perturbed across conservative ranges.

The temperature component is scaled by the difference between the stressed perovskite gamma and the modern silicon gamma. The spectral component is scaled as a broad proxy for bandgap and EQE variation. The IAM residual is kept unchanged.

| Perovskite gamma percent per C | Spectral response scale | Median advantage percent | Minimum | Maximum | Irradiance relation r | Band I median | Band IV median | Direction preserved |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| -0.25 | 0.7 | 1.84 | 0.58 | 2.69 | -0.545 | 0.97 | 2.44 | True |
| -0.25 | 1.0 | 2.28 | 0.78 | 3.24 | -0.553 | 1.22 | 2.94 | True |
| -0.25 | 1.3 | 2.67 | 0.97 | 3.79 | -0.558 | 1.47 | 3.43 | True |
| -0.15 | 0.7 | 3.00 | 0.74 | 4.60 | -0.532 | 1.43 | 4.19 | True |
| -0.15 | 1.0 | 3.43 | 0.93 | 5.15 | -0.540 | 1.68 | 4.68 | True |
| -0.15 | 1.3 | 3.84 | 1.13 | 5.70 | -0.546 | 1.93 | 5.17 | True |
| -0.10 | 0.7 | 3.62 | 0.82 | 5.56 | -0.529 | 1.66 | 5.06 | True |
| -0.10 | 1.0 | 4.00 | 1.01 | 6.11 | -0.536 | 1.91 | 5.55 | True |
| -0.10 | 1.3 | 4.43 | 1.21 | 6.65 | -0.541 | 2.15 | 6.04 | True |

## Interpretation

The weakest median case uses gamma -0.25 percent per C and spectral response scale 0.7. Its median stressed advantage is 1.84 percent.

Across the stress grid, the irradiance relation remains negative and resource band IV remains higher than resource band I. The conclusion is therefore not dependent on one narrow perovskite temperature coefficient or one exact spectral-response curve.

## Outputs

| File | Role |
| --- | --- |
| `outputs/si_perovskite_parameter_sensitivity.csv` | Province-level stressed advantages |
| `outputs/si_perovskite_parameter_sensitivity_summary.csv` | Summary statistics used in this appendix |
