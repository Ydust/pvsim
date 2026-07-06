# SI Scientific Defense Tables

These tables support the scientific-hardening pass for `NEWFig1-5`. They should be treated as SI-ready evidence tables, not as new main-figure claims.

## Table Sx. Fleet-Anchored System Validation

The fleet comparison is a system-level spatial anchor. It includes BOS loss, curtailment, dispatch and O&M effects; it is not a pure device-physics validation.

Fleet-hour values are loaded from `data/source_tables/provincial_fleet_hours_2024.csv`, a versioned source table used for the system-level anchor. The table reports provincial grid-connected PV utilisation hours and keeps source notes beside each row.

| check | n | r | bias_kwh_per_kwp | mae_kwh_per_kwp | rmse_kwh_per_kwp | mape_pct | mean_loss_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| raw clean-physics twin vs fleet hours | 31 | 0.89 | 233.21 | 234.79 | 263.68 | 19.03 | 15.28 |
| uniform-loss-corrected twin vs fleet hours | 31 | 0.89 | 8.33 | 87.38 | 102.40 | 7.13 | 15.28 |

## Table Sy. ERA5 Reduced-Order Grid Validation

The 0.1° layer supports the spatial inversion and regional ranking. It should not be presented as a point forecast for individual plants or land cells.

| check | n | best_k | r | r2 | bias_pct_points | mae_pct_points | rmse_pct_points | grid_cells | grid_r_ghi_vs_adv | grid_adv_p10 | grid_adv_p50 | grid_adv_p90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ERA5 reduced-order advantage vs full 8760h provincial anchors | 31 | 155.000 | 0.634 | 0.377 | -0.186 | 0.818 | 0.962 | 94998 | -0.514 | 0.074 | 2.084 | 3.655 |

## Table Sz. Resource-Band Check For Reduced-Order Model

| resource_band | n | full_median_adv_pct | reduced_median_adv_pct | median_error_pct_points |
| --- | --- | --- | --- | --- |
| I | 2 | 1.68 | 3.28 | 1.60 |
| II | 6 | 2.24 | 2.87 | 0.75 |
| III | 18 | 3.51 | 3.39 | -0.50 |
| IV | 5 | 4.68 | 3.41 | -1.41 |

## Table Sa. Historical Softmax Calibration

| check | years | softmax_T_cents_kwh | rmse_share_pct_points | r2 | max_abs_residual_pct_points |
| --- | --- | --- | --- | --- | --- |
| historical multi-to-mono softmax calibration | 2015-2023 | 0.150 | 11.873 | 0.829 | 22.099 |

## Table Sb. Monte Carlo Scenario Parameters

| parameter | distribution_or_value | source_or_anchor | prior_reason | stress_test_role | used_in |
| --- | --- | --- | --- | --- | --- |
| c-Si learning rate | Normal mean 0.18 and SD 0.04; clipped to 0.08-0.45 | 2015-2024 PV price backcast plus ITRPV and BNEF cost history | Mature incumbent still has residual cost decline and manufacturing uncertainty | Tests whether silicon cost decline delays perovskite substitution | Main Fig 4 MC |
| perovskite learning rate | Normal mean 0.27 and SD 0.04; clipped to 0.08-0.45 | Scenario prior because bankable perovskite deployment history does not yet exist | Allows faster early learning without assuming guaranteed commercial dominance | Tests whether high learning can overcome the lifetime gate | Main Fig 4 MC |
| tandem learning rate | Normal mean 0.30 and SD 0.04; clipped to 0.08-0.45 | NREL tandem TEA baseline plus emerging PV learning envelope | Represents immature two-terminal tandem manufacturing uncertainty | Tests whether area efficiency can compensate for higher capex | Main Fig 4 MC |
| c-Si capex floor | Uniform 0.35-0.45 USD per W | Observed 2024 module price floor and long-run system floor envelope | Prevents mature silicon from declining without a physical and supply-chain floor | Sets the incumbent cost threshold | Main Fig 4 MC |
| perovskite capex floor | Uniform 0.32-0.45 USD per W | Scenario process floor; no bankable market price series exists | Allows low-cost manufacturing while retaining parity and underperformance cases | Separates cost-led substitution from yield-led substitution | Main Fig 4 MC |
| tandem capex floor | Uniform 0.42-0.58 USD per W | NREL Cordell 2025 tandem TEA and floor uncertainty | Retains higher process complexity for tandem manufacturing | Tests whether tandem remains area-driven rather than yield-driven | Main Fig 4 MC |
| perovskite breakthrough year | Discrete uniform integer years 2028-2042 | Durability-transition scenario bracket | Does not assume that bankable lifetime arrives on a fixed schedule | Controls whether substitution starts early or remains blocked | Main Fig 4 MC |
| post-breakthrough perovskite lifetime | Uniform 18-25 years | Scenario range from partial bankability to full silicon-like lifetime | Keeps incomplete lifetime improvement visible in the economics | Controls never-substitute tail risk | Main Fig 4 MC |
| softmax allocation temperature | Normal mean 0.45 and SD 0.23; clipped to 0.15-2.0 cents per kWh | 2015-2023 multi-to-mono calibration expanded threefold | Avoids overconfident winner-take-all adoption from a short historical analogue | Controls coexistence and inertia in new-build share allocation | Main Fig 4 MC |
| number of draws | 1000 draws with random seed 42 | Reproducibility setting | Keeps uncertainty summaries deterministic across reruns | Defines Monte Carlo precision | Main Fig 4 MC |

Generated by `python -m scripts.si_scientific_defense_tables`.
