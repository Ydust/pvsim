# Parameters and result data

The parameter register contains 54 entries. E10 identifies the IRENA source.

- `Anchored_cost_OM_cases.csv`: 36 records from six cost/maintenance conditions, two constraints and three policies.
- `City_degradation_boundaries.csv`: 4,044 records covering 337 cities, two candidate technologies, two constraints and three policies. Missing in-domain boundaries retain their status and blank numeric fields.
- `City_cost_degradation_boundaries.csv`: the same conditions at seven degradation levels, totaling 28,308 records. Negative cost ceilings are retained.
- `Degradation_boundary_summary.csv`: 12 summaries. Quantiles use in-domain boundaries and distinguish never-selected from always-selected cases.
- `Joint_OM_tandem_degradation.csv`: 54 combinations of three maintenance rates, three tandem degradation rates, two constraints and three policies.
- `Round2_definitions.json`: pricing conventions, evidence, root-finding precision and applicability.

Scenario monetary values use constant 2024 USD. The China installation-cost anchor of 591 is held fixed for a 2035 comparison, not projected to 2035. The maintenance survey value of 3.2 and modeling assumption of 10.95 are separately transferred to all three technologies as common cost scenarios, not observations of emerging technologies.

No subsidy, General20 and New20 denote no support, universal 20% support and 20% support for emerging technologies. City boundaries vary one candidate technology at a time with the others fixed. Strictly positive advantage determines selection; equality denotes indifference.

Entry point: `code/run.py`.
