# Figure 5 data

Construction-investment support calculations and plotting data. `share` is the supported fraction of initial system investment.

## Files

- `Figure5_baseline_technology.csv`: 2,022 records (337 cities, three technologies, two constraints), containing unsubsidized NPV, initial system investment and discounted delivered electricity.
- `Figure5_policy_summary.csv`: 24 combinations of 0/10/20/30% anchors, two constraints and three allocation rules.
- `Figure5_policy_curves.csv`: 1,806 summary records spanning 0-30% at 0.1-percentage-point intervals.
- `Figure5_policy_city.csv`: 8,088 city configurations with payments, NPV and generation.
- `Figure5_policy_sensitivity.csv`: 594 records across 11 economic scenarios, two constraints, three allocation rules, three support levels and three administration rates.
- `Sensitivity_definitions.json`: parameter overrides for the 11 scenarios; Central has no overrides.
- `Figure5a_linked_city_display.csv`: baseline choices, support classes, boxplot groups and plotting coordinates for 337 cities.
- `Figure5a_box_statistics.csv`: 15 descriptive boxplot records covering all 337 cities; Other17 groups 166 cities.

## Fields and units

`adcode` is the city identifier and should remain text. `city` and `province` contain names. `context=cap` represents 1 MWp per city; `area` represents 1 ha per city. These are separate opportunity sets. Si/csi denotes crystalline silicon, SJ/perovskite single-junction perovskite, and T/tandem a two-terminal tandem. Choice codes are -1 for no construction, 0 for Si, 1 for SJ and 2 for T.

`strategy=General` supports all three technologies; `New technology` supports SJ and T. `Matched gap` reproduces the complete city configuration of General at the same share using gap payments.

`share` is a 0-1 fraction of initial system construction investment, not replacement cost or the tandem premium. Payments exclude site cost. Values ending in `_usd` use the common real-USD price basis. Initial payments require no further discounting; future cash flows are already discounted. `before/after_npv_usd` includes the no-build option, while `npv_usd` in the baseline technology table retains negative values for individual construction alternatives. `private_gain_usd` includes fiscal transfers and is not social benefit.

`direct_support_usd` is the payment to the selected construction option. `support_si/sj/t_usd` describes eligibility for mutually exclusive alternatives and must not be summed as actual spending. `admin_usd` is assumed administration cost; `total_public_usd` combines transfers and administration. `new_support/switch_support/same_support` allocates payments to newly viable projects, technology switchers and unchanged adopters. The default administration rate is 5%; sensitivity values are 0/0.05/0.10.

`before/after_viable` counts viable projects. `new_viable` is a count in summary tables and a 0/1 flag in city tables. `after_si/sj/t` counts selected technologies, and `switches` counts previously viable projects that change technology. `additional_discounted_mwh` is the change in 25-year discounted delivered electricity; divide by 1e6 for TWh.

In panel a, `class_id` and `paired_class` denote joint unsubsidized capacity/site choices. `best_build_npv_kusd` is the maximum construction NPV in thousand USD before adding the zero-valued no-build option. Support classes Initially viable, At20%, Added at30% and Beyond30% contain 258, 55, 20 and 4 cities. `matched_new_viable` marks projects made viable under General20. `display_y` separates overlapping marks without changing their horizontal NPV coordinates. Boxplot minimum, quartiles, median and maximum are descriptive city statistics, not confidence intervals or significance tests.

## Interpretation

The Beijing construction-support instrument is a policy reference. Common eligibility, initial payments, support levels and future projects are counterfactual assumptions, not a subsidy register for 337 cities or a 2035 policy forecast. Gap matching assumes complete information and acceptance at USD 1 above indifference. The 5% administration rate is not a measured implementation cost.

Entry point: `code/run.py`.
