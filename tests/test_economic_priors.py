import numpy as np

from pvsim.economic_priors import (
    CAPEX_FLOOR_PRIORS_USD_W,
    LEARNING_RATE_CLIP,
    MC_DRAWS,
    MC_RANDOM_SEED,
    POST_BREAKTHROUGH_LIFETIME_RANGE_YR,
    SOFTMAX_T_CLIP_CENTS_KWH,
    mc_parameter_rows,
    sample_mc_inputs,
)


def test_mc_parameter_rows_are_traceable():
    rows = mc_parameter_rows(0.15)
    assert len(rows) == 10
    required = {
        "parameter",
        "distribution_or_value",
        "source_or_anchor",
        "prior_reason",
        "stress_test_role",
        "used_in",
    }
    for row in rows:
        assert set(row) == required
        assert all(str(value).strip() for value in row.values())


def test_mc_sampler_uses_declared_bounds():
    rng = np.random.default_rng(MC_RANDOM_SEED)
    for _ in range(MC_DRAWS):
        learning_rates, floors, breakthrough_year, lifetime_final, softmax_t = (
            sample_mc_inputs(rng, 0.15)
        )
        assert all(
            LEARNING_RATE_CLIP[0] <= value <= LEARNING_RATE_CLIP[1]
            for value in learning_rates.values()
        )
        for tech, value in floors.items():
            low, high = CAPEX_FLOOR_PRIORS_USD_W[tech]
            assert low <= value <= high
        assert 2028 <= breakthrough_year <= 2042
        assert (
            POST_BREAKTHROUGH_LIFETIME_RANGE_YR[0]
            <= lifetime_final
            <= POST_BREAKTHROUGH_LIFETIME_RANGE_YR[1]
        )
        assert SOFTMAX_T_CLIP_CENTS_KWH[0] <= softmax_t <= SOFTMAX_T_CLIP_CENTS_KWH[1]
