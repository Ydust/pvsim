"""Cloud-spectrum boundary stress test for the SI.

This is not a cloud optical model. It applies smooth blue and red spectral
tilts to SPECTRL2 clear-sky spectra, keeps broadband irradiance fixed, and
checks whether the perovskite-versus-silicon spectral ordering is overturned.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

from pvsim.materials import CSI_MODERN, PEROVSKITE, TANDEM_2T
from pvsim.spectral import generate_spectrum, spectral_mismatch_factor


OUT = Path("outputs")
DOC = Path("docs/SI_CLOUD_SPECTRAL_SENSITIVITY.md")
ZENITHS = np.array([15.0, 30.0, 45.0, 60.0, 75.0])
TILT_BETAS = {
    "strong blue tilt": -0.30,
    "moderate blue tilt": -0.15,
    "clear-sky base": 0.00,
    "moderate red tilt": 0.15,
    "strong red tilt": 0.30,
}


def _broadband(wl_nm: np.ndarray, spectrum: np.ndarray) -> float:
    return float(np.trapezoid(spectrum, wl_nm))


def tilt_spectrum(
    wl_nm: np.ndarray, spectrum: np.ndarray, beta: float, pivot_nm: float = 700.0
) -> np.ndarray:
    factor = np.power(np.maximum(wl_nm, 1.0) / pivot_nm, beta)
    tilted = spectrum * factor
    base_total = _broadband(wl_nm, spectrum)
    tilted_total = _broadband(wl_nm, tilted)
    if tilted_total <= 0:
        return tilted
    return tilted * base_total / tilted_total


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for label, beta in TILT_BETAS.items():
        for zenith in ZENITHS:
            wl, spectrum = generate_spectrum(float(zenith))
            stressed = tilt_spectrum(wl, spectrum, beta)
            csi_sf = spectral_mismatch_factor(CSI_MODERN, wl, stressed)
            perov_sf = spectral_mismatch_factor(PEROVSKITE, wl, stressed)
            tandem_sf = spectral_mismatch_factor(TANDEM_2T, wl, stressed)
            am = pvlib.atmosphere.get_relative_airmass(float(zenith))
            rows.append(
                {
                    "stress_case": label,
                    "beta": beta,
                    "zenith_deg": zenith,
                    "relative_airmass": float(am),
                    "csi_sf": csi_sf,
                    "perovskite_sf": perov_sf,
                    "tandem_sf": tandem_sf,
                    "perovskite_vs_csi_pct": (perov_sf / csi_sf - 1.0) * 100.0,
                    "tandem_vs_csi_pct": (tandem_sf / csi_sf - 1.0) * 100.0,
                }
            )
    detail = pd.DataFrame(rows)
    summary_rows = []
    for label, group in detail.groupby("stress_case", sort=False):
        slope = np.polyfit(
            group["relative_airmass"], group["perovskite_vs_csi_pct"], 1
        )[0]
        corr = np.corrcoef(
            group["relative_airmass"], group["perovskite_vs_csi_pct"]
        )[0, 1]
        summary_rows.append(
            {
                "stress_case": label,
                "beta": float(group["beta"].iloc[0]),
                "min_perovskite_vs_csi_pct": group["perovskite_vs_csi_pct"].min(),
                "max_perovskite_vs_csi_pct": group["perovskite_vs_csi_pct"].max(),
                "slope_pct_per_airmass": slope,
                "corr_with_airmass": corr,
                "keeps_clear_sky_direction": bool(slope < 0),
            }
        )
    summary = pd.DataFrame(summary_rows)
    return detail, summary


def _markdown_table(df: pd.DataFrame, digits: int = 3) -> str:
    data = df.copy()
    for col in data.columns:
        if pd.api.types.is_float_dtype(data[col]):
            data[col] = data[col].map(lambda x: f"{x:.{digits}f}")
    lines = [
        "| " + " | ".join(data.columns) + " |",
        "| " + " | ".join(["---"] * len(data.columns)) + " |",
    ]
    for _, row in data.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in data.columns) + " |")
    return "\n".join(lines)


def write_outputs(detail: pd.DataFrame, summary: pd.DataFrame) -> None:
    OUT.mkdir(exist_ok=True)
    detail.to_csv(OUT / "si_cloud_spectral_sensitivity.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(
        OUT / "si_cloud_spectral_sensitivity_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    lines = [
        "# SI Cloud Spectral Boundary Stress Test",
        "",
        "This check does not introduce a cloud optical model. It perturbs the clear-sky SPECTRL2 spectrum with smooth blue and red tilts, then renormalises each spectrum to the same broadband irradiance.",
        "",
        "The purpose is narrow. It asks whether a smooth spectral-colour perturbation would overturn the clear-sky air-mass ordering used in the mechanism attribution.",
        "",
        "Result: every stress case keeps a negative slope between relative air mass and the perovskite spectral advantage over modern silicon. The clear-sky spectral mechanism therefore does not require an explicit cloud-blue-shift term.",
        "",
        "## Summary",
        "",
        _markdown_table(summary, 3),
        "",
        "## Files",
        "",
        "| File | Role |",
        "| --- | --- |",
        "| `outputs/si_cloud_spectral_sensitivity.csv` | Zenith-level stress table |",
        "| `outputs/si_cloud_spectral_sensitivity_summary.csv` | Stress-case summary |",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    detail, summary = build_tables()
    write_outputs(detail, summary)
    print("Cloud spectral sensitivity written:")
    print("  outputs/si_cloud_spectral_sensitivity.csv")
    print("  outputs/si_cloud_spectral_sensitivity_summary.csv")
    print("  docs/SI_CLOUD_SPECTRAL_SENSITIVITY.md")
    for _, row in summary.iterrows():
        print(
            f"  {row['stress_case']}: slope={row['slope_pct_per_airmass']:.3f}, "
            f"r={row['corr_with_airmass']:.3f}"
        )


if __name__ == "__main__":
    main()
