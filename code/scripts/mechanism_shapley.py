"""Order-independent factorial attribution for PV mechanism switches.

The three modeled mechanisms are represented by binary switches:
temperature response, spectral response and incidence-angle modifier (IAM).
The all-off case is retained as an electrical/low-light baseline. Shapley
values allocate both main effects and interactions without depending on the
order in which switches are enabled.
"""

from __future__ import annotations

from math import factorial
from typing import Mapping, TypeVar


FEATURES = ("temperature", "spectral", "iam")
FULL_MASK = (1 << len(FEATURES)) - 1

Value = TypeVar("Value")


def config_for_mask(mask: int) -> dict[str, bool]:
    """Translate a factorial bit mask to ``SystemConfig`` switch values."""
    if mask < 0 or mask > FULL_MASK:
        raise ValueError(f"Mechanism mask must be between 0 and {FULL_MASK}")
    return {
        "apply_temperature": bool(mask & 0b001),
        "apply_spectral": bool(mask & 0b010),
        "apply_iam": bool(mask & 0b100),
    }


def factorial_suffix(mask: int) -> str:
    """Return an explicit, column-safe switch label for a factorial mask."""
    config = config_for_mask(mask)
    return (
        f"t{int(config['apply_temperature'])}"
        f"_s{int(config['apply_spectral'])}"
        f"_i{int(config['apply_iam'])}"
    )


def shapley_components(values: Mapping[int, Value]) -> dict[str, Value]:
    """Return Shapley contributions from all 2^3 factorial outcomes.

    ``values[0]`` is the all-off electrical baseline and ``values[7]`` is the
    fully enabled model. Values may be scalars or pandas Series because the
    calculation only uses addition, subtraction and scalar multiplication.
    """
    expected = set(range(FULL_MASK + 1))
    missing = expected.difference(values)
    if missing:
        raise ValueError(f"Missing factorial outcomes: {sorted(missing)}")

    n_features = len(FEATURES)
    result: dict[str, Value] = {}
    for feature_index, feature in enumerate(FEATURES):
        bit = 1 << feature_index
        contribution = values[0] * 0.0
        for subset in range(FULL_MASK + 1):
            if subset & bit:
                continue
            subset_size = subset.bit_count()
            weight = (
                factorial(subset_size)
                * factorial(n_features - subset_size - 1)
                / factorial(n_features)
            )
            contribution = contribution + weight * (
                values[subset | bit] - values[subset]
            )
        result[feature] = contribution
    return result
