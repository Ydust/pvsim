# SI Mechanism Specificity

Last updated: 2026-07-01

Province-only directional status: preserved.

This appendix tests whether the temperature and spectral mechanism claims survive simple partial-correlation checks at the 31 province anchors. These checks are not causal proof. They are a guard against one hidden irradiance or climate variable explaining both mechanisms at once.

| Check | Raw r | Partial r | Controls | Expected direction | Direction preserved |
| --- | ---: | ---: | --- | --- | --- |
| Thermal component versus cell temperature | 0.941 | 0.957 | ghi_kwh_m2; airmass | positive | True |
| Spectral component versus air mass | -0.944 | -0.931 | ghi_kwh_m2; tcell | negative | True |
| Full advantage versus irradiance | -0.540 | -0.843 | tcell; airmass | negative | True |
| Full advantage versus cell temperature | 0.911 | 0.935 | ghi_kwh_m2; airmass | positive | True |
| Full advantage versus air mass | -0.850 | -0.755 | ghi_kwh_m2; tcell | negative | True |

## Interpretation

The thermal component remains positively associated with weighted cell temperature after controlling for irradiance and air mass. The spectral component remains negatively associated with air mass after controlling for irradiance and cell temperature.

The full advantage also keeps the expected signs against irradiance, cell temperature and air mass under these province-only checks. This supports the interpretation that the two mechanism channels are separable, while keeping the claim below causal overstatement.

## Output

`outputs/si_mechanism_specificity.csv` contains the full table.
