# Outdoor validation outputs

These tables describe paired outdoor measurements and operating-domain comparisons.

- `paired_holdout_predictions.csv`: individual co-located power-response predictions. The chronological and leave-one-date-out rows are alternative evaluations of overlapping source observations, not additional samples.
- `holdout_split_register.csv`: training/test dates and training-only high-irradiance reference scales. No device parameters were fitted.
- `holdout_summary.csv`: equal-date-weighted log errors and conditional date-bootstrap bias intervals. Constant-ratio comparator included.
- `day_level_error_audit.csv`: all PSM50 leave-one-date-out dates, including the four-record date with the largest error. No additional outlier removal.
- `observed_operating_domain_bins.csv`: counts in zero-anchored joint irradiance–temperature bins.
- `city_operating_domain_overlap.csv`: 337 city anchors × 2 technology datasets × 10 domain definitions. `fraction_poa` weights by incident plane-of-array irradiation, not generated electricity. `fraction_hours` counts daylight hours (POA ≥20 W/m²).
- `operating_domain_overlap_summary.csv`: spatial summaries, not confidence intervals or validation success rates.
- `weather_input_hashes.csv`: exact cached weather input identities.
- `analysis_protocol.json`: sample sizes, raw-data integrity checks and interpretation boundaries.


Single-junction measurements: Jaramillo and Montoya, Mendeley Data v1, DOI 10.17632/9jx8mdh8xd.1, CC BY 4.0; related article DOI 10.1016/j.solmat.2018.10.018. The two early minimodules share one location and one silicon comparator. The normalized ratios cannot identify absolute STC-specific yield superiority.

Tandem measurements: Aydin et al., Nature Energy (2020), DOI 10.1038/s41560-020-00687-4, existing derived 377-record source table. There is no synchronized independent silicon power comparator. The two-terminal data only define an observed operating domain here.

Run `code/run.py field_validation`. Weather inputs, measurement records and preprocessing code are included. Package versions are in `environment/requirements.txt`. The Aydin workbook source URL is listed in the data README. Original data licences apply.

The domain statistic is sensitive to discretization and tests only two variables. It does not validate spectrum, ageing, absolute annual energy yield or nationwide technology preference.
