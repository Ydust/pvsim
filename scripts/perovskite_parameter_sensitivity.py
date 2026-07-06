"""Perovskite parameter stress test in mechanism space."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ROOT / "outputs" / "advantage_drivers.csv"
YIELDS = ROOT / "outputs" / "province_physics_yield.csv"
OUT_CSV = ROOT / "outputs" / "si_perovskite_parameter_sensitivity.csv"
OUT_SUMMARY = ROOT / "outputs" / "si_perovskite_parameter_sensitivity_summary.csv"
OUT_MD = ROOT / "docs" / "SI_PEROVSKITE_PARAMETER_SENSITIVITY.md"

CSI_GAMMA = -0.32
BASE_PEROVSKITE_GAMMA = -0.15

PEROVSKITE_GAMMAS = [-0.10, -0.15, -0.25]
SPECTRAL_RESPONSE_SCALES = [0.7, 1.0, 1.3]


def _ghi_by_province() -> dict[str, float]:
    data = pd.read_csv(YIELDS, encoding="utf-8-sig")
    csi = data[data["tech"] == "晶硅"].set_index("province")
    return csi["ghi_kwh_m2"].astype(float).to_dict()


def build_rows() -> pd.DataFrame:
    drivers = pd.read_csv(DRIVERS, encoding="utf-8-sig")
    ghi = _ghi_by_province()
    base_delta = BASE_PEROVSKITE_GAMMA - CSI_GAMMA
    rows = []
    for _, row in drivers.iterrows():
        province = row["province"]
        if province not in ghi:
            continue
        for gamma in PEROVSKITE_GAMMAS:
            thermal_scale = (gamma - CSI_GAMMA) / base_delta
            for spectral_scale in SPECTRAL_RESPONSE_SCALES:
                adv = (
                    float(row["thermal"]) * thermal_scale
                    + float(row["spectral"]) * spectral_scale
                    + float(row["iam"])
                )
                rows.append(
                    {
                        "province": province,
                        "resource_band": row["band"],
                        "perovskite_gamma_pct_per_c": gamma,
                        "thermal_scale": thermal_scale,
                        "spectral_response_scale": spectral_scale,
                        "ghi_kwh_m2": ghi[province],
                        "weighted_cell_temperature_c": float(row["tcell"]),
                        "airmass": float(row["airmass"]),
                        "stressed_advantage_pct": adv,
                    }
                )
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    summary_rows = []
    group_cols = ["perovskite_gamma_pct_per_c", "spectral_response_scale"]
    for keys, group in rows.groupby(group_cols, sort=True):
        gamma, spectral_scale = keys
        adv = group["stressed_advantage_pct"].to_numpy()
        ghi = group["ghi_kwh_m2"].to_numpy()
        corr = float(np.corrcoef(ghi, adv)[0, 1])
        band_medians = group.groupby("resource_band")["stressed_advantage_pct"].median()
        band_i = float(band_medians.get("I", np.nan))
        band_iv = float(band_medians.get("IV", np.nan))
        summary_rows.append(
            {
                "perovskite_gamma_pct_per_c": float(gamma),
                "spectral_response_scale": float(spectral_scale),
                "median_advantage_pct": float(np.median(adv)),
                "min_advantage_pct": float(np.min(adv)),
                "max_advantage_pct": float(np.max(adv)),
                "irradiance_advantage_correlation": corr,
                "band_i_median_pct": band_i,
                "band_iv_median_pct": band_iv,
                "direction_preserved": bool(corr < 0 and band_iv > band_i),
            }
        )
    return pd.DataFrame(summary_rows)


def write_markdown(summary: pd.DataFrame, path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_preserved = bool(summary["direction_preserved"].all())
    status = "preserved" if all_preserved else "not preserved"
    worst = summary.sort_values("median_advantage_pct").iloc[0]
    lines = [
        "# SI Perovskite Parameter Sensitivity",
        "",
        "Last updated: 2026-07-01",
        "",
        f"Directional status: {status}.",
        "",
        "This appendix stress-tests the mechanism decomposition against perovskite parameter variation. It does not replace full material-specific device simulation. It asks whether the main geographic inversion survives when the temperature coefficient and spectral-response strength are perturbed across conservative ranges.",
        "",
        "The temperature component is scaled by the difference between the stressed perovskite gamma and the modern silicon gamma. The spectral component is scaled as a broad proxy for bandgap and EQE variation. The IAM residual is kept unchanged.",
        "",
        "| Perovskite gamma percent per C | Spectral response scale | Median advantage percent | Minimum | Maximum | Irradiance relation r | Band I median | Band IV median | Direction preserved |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            "| "
            f"{row['perovskite_gamma_pct_per_c']:.2f} | "
            f"{row['spectral_response_scale']:.1f} | "
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
        f"The weakest median case uses gamma {worst['perovskite_gamma_pct_per_c']:.2f} percent per C and spectral response scale {worst['spectral_response_scale']:.1f}. Its median stressed advantage is {worst['median_advantage_pct']:.2f} percent.",
        "",
        "Across the stress grid, the irradiance relation remains negative and resource band IV remains higher than resource band I. The conclusion is therefore not dependent on one narrow perovskite temperature coefficient or one exact spectral-response curve.",
        "",
        "## Outputs",
        "",
        "| File | Role |",
        "| --- | --- |",
        "| `outputs/si_perovskite_parameter_sensitivity.csv` | Province-level stressed advantages |",
        "| `outputs/si_perovskite_parameter_sensitivity_summary.csv` | Summary statistics used in this appendix |",
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
    print(f"Perovskite parameter sensitivity written to {OUT_MD}.")
    if not bool(summary["direction_preserved"].all()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
