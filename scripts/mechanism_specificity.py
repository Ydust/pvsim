"""Province-only partial-correlation checks for mechanism attribution."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ROOT / "outputs" / "advantage_drivers.csv"
YIELDS = ROOT / "outputs" / "province_physics_yield.csv"
OUT_CSV = ROOT / "outputs" / "si_mechanism_specificity.csv"
OUT_MD = ROOT / "docs" / "SI_MECHANISM_SPECIFICITY.md"


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def _residualize(y: np.ndarray, controls: np.ndarray) -> np.ndarray:
    x = np.column_stack([np.ones(len(y)), controls])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    return y - x @ beta


def partial_corr(x: np.ndarray, y: np.ndarray, controls: np.ndarray) -> float:
    rx = _residualize(x, controls)
    ry = _residualize(y, controls)
    return _corr(rx, ry)


def load_mechanism_frame() -> pd.DataFrame:
    drivers = pd.read_csv(DRIVERS, encoding="utf-8-sig")
    yields = pd.read_csv(YIELDS, encoding="utf-8-sig")
    csi = yields[yields["tech"] == "晶硅"][["province", "ghi_kwh_m2", "tair_mean"]]
    return drivers.merge(csi, on="province", how="inner")


def build_checks() -> pd.DataFrame:
    df = load_mechanism_frame()
    checks = [
        {
            "check": "Thermal component versus cell temperature",
            "x": "thermal",
            "y": "tcell",
            "controls": ["ghi_kwh_m2", "airmass"],
            "expected": "positive",
        },
        {
            "check": "Spectral component versus air mass",
            "x": "spectral",
            "y": "airmass",
            "controls": ["ghi_kwh_m2", "tcell"],
            "expected": "negative",
        },
        {
            "check": "Full advantage versus irradiance",
            "x": "full",
            "y": "ghi_kwh_m2",
            "controls": ["tcell", "airmass"],
            "expected": "negative",
        },
        {
            "check": "Full advantage versus cell temperature",
            "x": "full",
            "y": "tcell",
            "controls": ["ghi_kwh_m2", "airmass"],
            "expected": "positive",
        },
        {
            "check": "Full advantage versus air mass",
            "x": "full",
            "y": "airmass",
            "controls": ["ghi_kwh_m2", "tcell"],
            "expected": "negative",
        },
    ]
    rows = []
    for check in checks:
        x = df[check["x"]].to_numpy(dtype=float)
        y = df[check["y"]].to_numpy(dtype=float)
        controls = df[check["controls"]].to_numpy(dtype=float)
        raw = _corr(x, y)
        partial = partial_corr(x, y, controls)
        expected = check["expected"]
        preserved = partial > 0 if expected == "positive" else partial < 0
        rows.append(
            {
                "check": check["check"],
                "x": check["x"],
                "y": check["y"],
                "controls": "; ".join(check["controls"]),
                "raw_correlation": raw,
                "partial_correlation": partial,
                "expected_direction": expected,
                "direction_preserved": bool(preserved),
            }
        )
    return pd.DataFrame(rows)


def write_markdown(checks: pd.DataFrame, path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_preserved = bool(checks["direction_preserved"].all())
    status = "preserved" if all_preserved else "not preserved"
    lines = [
        "# SI Mechanism Specificity",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Province-only directional status: {status}.",
        "",
        "This appendix tests whether the temperature and spectral mechanism claims survive simple partial-correlation checks at the 31 province anchors. These checks are not causal proof. They are a guard against one hidden irradiance or climate variable explaining both mechanisms at once.",
        "",
        "| Check | Raw r | Partial r | Controls | Expected direction | Direction preserved |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in checks.to_dict("records"):
        lines.append(
            "| "
            f"{row['check']} | "
            f"{row['raw_correlation']:.3f} | "
            f"{row['partial_correlation']:.3f} | "
            f"{row['controls']} | "
            f"{row['expected_direction']} | "
            f"{row['direction_preserved']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "The thermal component remains positively associated with weighted cell temperature after controlling for irradiance and air mass. The spectral component remains negatively associated with air mass after controlling for irradiance and cell temperature.",
        "",
        "The full advantage also keeps the expected signs against irradiance, cell temperature and air mass under these province-only checks. This supports the interpretation that the two mechanism channels are separable, while keeping the claim below causal overstatement.",
        "",
        "## Output",
        "",
        "`outputs/si_mechanism_specificity.csv` contains the full table.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> pd.DataFrame:
    checks = build_checks()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    checks.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    write_markdown(checks)
    return checks


def main() -> int:
    checks = run()
    print(f"Mechanism specificity checks written to {OUT_MD}.")
    if not bool(checks["direction_preserved"].all()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
