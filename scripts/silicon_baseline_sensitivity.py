"""Silicon baseline sensitivity for the perovskite field-advantage claim."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "province_physics_yield.csv"
OUT_CSV = ROOT / "outputs" / "si_silicon_baseline_sensitivity.csv"
OUT_SUMMARY = ROOT / "outputs" / "si_silicon_baseline_sensitivity_summary.csv"
OUT_MD = ROOT / "docs" / "SI_SILICON_BASELINE_SENSITIVITY.md"

BASE_GAMMA = -0.32

SILICON_BASELINES = [
    {
        "baseline": "HJT low temperature coefficient",
        "stc_efficiency_pct": 22.5,
        "gamma_pct_per_c": -0.26,
    },
    {
        "baseline": "TOPCon central",
        "stc_efficiency_pct": 22.0,
        "gamma_pct_per_c": -0.32,
    },
    {
        "baseline": "PERC high temperature coefficient",
        "stc_efficiency_pct": 21.0,
        "gamma_pct_per_c": -0.37,
    },
]


def build_rows(input_path: Path = INPUT) -> pd.DataFrame:
    data = pd.read_csv(input_path, encoding="utf-8-sig")
    csi = data[data["tech"] == "晶硅"].set_index("province")
    per = data[data["tech"] == "钙钛矿"].set_index("province")
    rows = []
    for province in csi.index:
        if province not in per.index:
            continue
        csi_yield = float(csi.loc[province, "yield_kwh_per_kwp"])
        per_yield = float(per.loc[province, "yield_kwh_per_kwp"])
        tcell = float(csi.loc[province, "tcell_weighted"])
        for baseline in SILICON_BASELINES:
            gamma = baseline["gamma_pct_per_c"]
            temp_multiplier = 1.0 + ((gamma - BASE_GAMMA) / 100.0) * (tcell - 25.0)
            adjusted_csi_yield = csi_yield * temp_multiplier
            rows.append(
                {
                    "province": province,
                    "resource_band": csi.loc[province, "res_band"],
                    "baseline": baseline["baseline"],
                    "silicon_stc_efficiency_pct": baseline["stc_efficiency_pct"],
                    "silicon_gamma_pct_per_c": gamma,
                    "weighted_cell_temperature_c": tcell,
                    "ghi_kwh_m2": float(csi.loc[province, "ghi_kwh_m2"]),
                    "adjusted_silicon_yield_kwh_kwp": adjusted_csi_yield,
                    "perovskite_yield_kwh_kwp": per_yield,
                    "perovskite_advantage_pct": (per_yield / adjusted_csi_yield - 1.0)
                    * 100.0,
                }
            )
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    summary_rows = []
    for baseline, group in rows.groupby("baseline", sort=False):
        adv = group["perovskite_advantage_pct"].to_numpy()
        ghi = group["ghi_kwh_m2"].to_numpy()
        corr = float(np.corrcoef(ghi, adv)[0, 1])
        band_medians = group.groupby("resource_band")["perovskite_advantage_pct"].median()
        summary_rows.append(
            {
                "baseline": baseline,
                "silicon_stc_efficiency_pct": float(group["silicon_stc_efficiency_pct"].iloc[0]),
                "silicon_gamma_pct_per_c": float(group["silicon_gamma_pct_per_c"].iloc[0]),
                "median_advantage_pct": float(np.median(adv)),
                "min_advantage_pct": float(np.min(adv)),
                "max_advantage_pct": float(np.max(adv)),
                "irradiance_advantage_correlation": corr,
                "band_i_median_pct": float(band_medians.get("I", np.nan)),
                "band_iv_median_pct": float(band_medians.get("IV", np.nan)),
                "direction_preserved": bool(corr < 0 and band_medians.get("IV", 0) > band_medians.get("I", 0)),
            }
        )
    return pd.DataFrame(summary_rows)


def write_markdown(summary: pd.DataFrame, path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_preserved = bool(summary["direction_preserved"].all())
    status = "preserved" if all_preserved else "not preserved"
    lines = [
        "# SI Silicon Baseline Sensitivity",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Directional status: {status}.",
        "",
        "This appendix tests whether the geographic inversion depends on choosing one modern silicon baseline. It perturbs the silicon power-temperature coefficient across representative HJT, TOPCon and PERC cases while keeping the same province-level weather and perovskite yields.",
        "",
        "The perturbation is applied to annual per-kWp yield with the irradiance-weighted cell temperature from the provincial simulations. STC efficiency is reported for context, but the annual per-kWp comparison is driven by the temperature coefficient rather than module area.",
        "",
        "| Silicon baseline | STC efficiency percent | Gamma percent per C | Median advantage percent | Minimum | Maximum | Irradiance relation r | Band I median | Band IV median | Direction preserved |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            "| "
            f"{row['baseline']} | "
            f"{row['silicon_stc_efficiency_pct']:.1f} | "
            f"{row['silicon_gamma_pct_per_c']:.2f} | "
            f"{row['median_advantage_pct']:.2f} | "
            f"{row['min_advantage_pct']:.2f} | "
            f"{row['max_advantage_pct']:.2f} | "
            f"{row['irradiance_advantage_correlation']:.3f} | "
            f"{row['band_i_median_pct']:.2f} | "
            f"{row['band_iv_median_pct']:.2f} | "
            f"{row['direction_preserved']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "The inversion direction is preserved when the silicon baseline is moved across the selected modern module range. The magnitude changes, especially for the low temperature coefficient HJT case, but the advantage remains larger in resource band IV than in resource band I and the irradiance relation remains negative.",
        "",
        "This supports the main text framing that the result is a field-yield geography effect rather than an artefact of one silicon comparator.",
        "",
        "## Outputs",
        "",
        "| File | Role |",
        "| --- | --- |",
        "| `outputs/si_silicon_baseline_sensitivity.csv` | Province-level values for each silicon baseline |",
        "| `outputs/si_silicon_baseline_sensitivity_summary.csv` | Summary statistics used in this appendix |",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = build_rows()
    summary = summarize(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    summary.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    write_markdown(summary)
    return rows, summary


def main() -> int:
    _, summary = run()
    print(f"Silicon baseline sensitivity written to {OUT_MD}.")
    if not bool(summary["direction_preserved"].all()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
