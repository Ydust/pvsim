"""Build a location-resolved external PV generation-utilization layer."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "data" / "source_tables" / "nea_pv_utilization_rate_2024.csv"
FLEET_VALIDATION_CSV = ROOT / "outputs" / "si_fleet_validation_by_province.csv"
OUT_CSV = ROOT / "outputs" / "si_pv_utilization_external_validation.csv"
OUT_SUMMARY = ROOT / "outputs" / "si_pv_utilization_external_validation_summary.csv"
OUT_MD = ROOT / "docs" / "SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md"


def load_source(path: Path = SOURCE_CSV) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def province_layer(source: pd.DataFrame | None = None) -> pd.DataFrame:
    data = load_source() if source is None else source.copy()
    data = data[data["province"] != "全国"].copy()
    grouped = (
        data.groupby("province", as_index=False)
        .agg(
            reporting_regions=("reporting_region", lambda s: "; ".join(s)),
            reporting_region_count=("reporting_region", "count"),
            pv_utilization_rate_pct_2023=("pv_utilization_rate_pct_2023", "mean"),
            pv_utilization_rate_pct_2024=("pv_utilization_rate_pct_2024", "mean"),
            source_url=("source_url", "first"),
            source_doc=("source_doc", "first"),
            source_audit_status=("source_audit_status", "first"),
        )
        .sort_values("province")
    )
    grouped["pv_utilization_deficit_pct_2024"] = (
        100.0 - grouped["pv_utilization_rate_pct_2024"]
    )
    grouped["utilization_rate_change_pctpt"] = (
        grouped["pv_utilization_rate_pct_2024"]
        - grouped["pv_utilization_rate_pct_2023"]
    )
    return grouped


def build_validation() -> tuple[pd.DataFrame, pd.DataFrame]:
    layer = province_layer()
    if FLEET_VALIDATION_CSV.exists():
        fleet = pd.read_csv(FLEET_VALIDATION_CSV, encoding="utf-8-sig")
        keep = [
            "province",
            "resource_band",
            "twin_kwh_per_kwp",
            "fleet_hours",
            "implied_system_loss_pct",
        ]
        layer = layer.merge(fleet[keep], on="province", how="left")
        corr = layer["pv_utilization_deficit_pct_2024"].corr(
            layer["implied_system_loss_pct"]
        )
    else:
        corr = float("nan")
    national = load_source()
    national = national[national["province"] == "全国"].iloc[0]
    summary = pd.DataFrame(
        [
            {
                "check": "official NEA PV utilization-rate layer",
                "n": int(len(layer)),
                "national_rate_2024_pct": float(
                    national["pv_utilization_rate_pct_2024"]
                ),
                "min_rate_2024_pct": float(layer["pv_utilization_rate_pct_2024"].min()),
                "max_rate_2024_pct": float(layer["pv_utilization_rate_pct_2024"].max()),
                "median_rate_2024_pct": float(
                    layer["pv_utilization_rate_pct_2024"].median()
                ),
                "deficit_vs_fleet_loss_r": float(corr),
                "lowest_region": str(
                    layer.sort_values("pv_utilization_rate_pct_2024").iloc[0][
                        "province"
                    ]
                ),
                "highest_region_count": int(
                    (layer["pv_utilization_rate_pct_2024"] == 100.0).sum()
                ),
            }
        ]
    )
    return layer, summary


def write_markdown(layer: pd.DataFrame, summary: pd.DataFrame, path: Path = OUT_MD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s: dict[str, Any] = summary.iloc[0].to_dict()
    bottom = layer.sort_values("pv_utilization_rate_pct_2024").head(6)
    lines = [
        "# SI PV Utilization External Validation",
        "",
        "Last updated: 2026-07-01",
        "",
        "Validation status: location-resolved official PV generation-utilization layer available.",
        "",
        "This appendix adds an external official PV operation layer from the National Energy Administration. The source is the 2024 National renewable power development monitoring and evaluation result, Table 4. It reports 2023 and 2024 PV generation utilization rates by region. The layer has a location axis and is independent of the model.",
        "",
        "Source URL: `https://www.nea.gov.cn/20251113/cc1fb0298a2944f8bd5441f67c9be9b3/c.html`",
        "",
        "| Check | Value |",
        "| --- | ---: |",
        f"| Province-level rows after aggregating Inner Mongolia grid regions | {int(s['n'])} |",
        f"| National 2024 PV generation utilization rate | {s['national_rate_2024_pct']:.1f} percent |",
        f"| Median province-level 2024 utilization rate | {s['median_rate_2024_pct']:.1f} percent |",
        f"| Lowest province-level 2024 utilization rate | {s['min_rate_2024_pct']:.1f} percent |",
        f"| Regions at 100 percent utilization | {int(s['highest_region_count'])} |",
        "",
        "Lowest utilization regions:",
        "",
        "| Province | Reporting regions | 2023 rate | 2024 rate | 2024 deficit |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in bottom.iterrows():
        lines.append(
            "| "
            f"{row['province']} | "
            f"{row['reporting_regions']} | "
            f"{row['pv_utilization_rate_pct_2023']:.1f} | "
            f"{row['pv_utilization_rate_pct_2024']:.1f} | "
            f"{row['pv_utilization_deficit_pct_2024']:.1f} |"
        )
    lines += [
        "",
        "Interpretation:",
        "",
        "This layer validates a grid-operation component of PV generation, not clean device physics. It should be used to explain where observed PV output is affected by curtailment and grid absorption. It should not be used as a replacement for province-level monthly PV generation or plant-level generation records.",
        "",
        "The layer closes the location-resolved official PV operation evidence gap. The CTGR operating-region layer adds a PV-specific absolute generation sample. A complete government province-level PV generation inventory remains a stronger future source target.",
        "",
        "Machine-readable outputs: `outputs/si_pv_utilization_external_validation.csv` and `outputs/si_pv_utilization_external_validation_summary.csv`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    layer, summary = build_validation()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    layer.to_csv(OUT_CSV, index=False, encoding="utf-8")
    summary.to_csv(OUT_SUMMARY, index=False, encoding="utf-8")
    write_markdown(layer, summary)
    return layer, summary


def main() -> int:
    layer, summary = run()
    s = summary.iloc[0]
    print(f"PV utilization external layer written to {OUT_CSV} and {OUT_MD}.")
    print(
        f"Rows: {len(layer)}; national utilization: "
        f"{s['national_rate_2024_pct']:.1f}%; lowest region: {s['lowest_region']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
