# pvsim — Physics-Validated PV Digital Twin For PV Geography

**A research-grade photovoltaic simulation framework for modern silicon, perovskite and tandem comparisons.**
The current manuscript branch uses a Python physics core to study field-yield geography,
mechanisms, economic timing and land-based deployment in China. The legacy Unity twin is
kept for visualization and regression context.

[![tests](https://img.shields.io/badge/tests-63%2F63%20passing-brightgreen)]()
[![pvlib agreement](https://img.shields.io/badge/pvlib%20agreement-0.0007%25-brightgreen)]()
[![license](https://img.shields.io/badge/license-MIT-blue)]()
[![python](https://img.shields.io/badge/python-3.12-blue)]()
[![Unity](https://img.shields.io/badge/Unity-6000.4-black)]()

---

## Why this exists

The manuscript asks a specific device-to-system question: where does a single-junction
perovskite field advantage survive once modern silicon, spectral response, operating
temperature, cost timing and deployment geography are evaluated together? This repository
provides:

1. A **unified single-diode physics layer** (De Soto + Lambert-W) implemented identically in
   Python (research) and C# (Unity), verified by a regression harness to **< 0.001 %** numerical
   agreement on Pmp/Voc/Isc/FF across STC, hot, cold and low-light conditions.
2. **Five manuscript layers** stacked on the same physics, from numerical validation to
   geographic inversion, mechanisms, market rulers, economics and deployment mismatch.
3. **Versioned China inputs**: PVGIS TMY provincial anchors, ERA5-Land 0.1 degree grid
   layer with 94,998 land cells, GEM operating PV plant context, national PV capacity
   closure to 886.6 GW and provincial fleet-hour anchoring.
4. **Reproducibility gates**: 63 tests, pvlib benchmark, Crossref reference audit,
   source-data audit gate and generated manuscript review HTML.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5  Portfolio / Lifecycle    LCOE, replacement, carbon │
│  Layer 4  National geography       GeoJSON 387 GW            │
│  Layer 3  City operation           PVGIS real TMY (12 cities)│
│  Layer 2  System level             Inverter, clipping, losses│
│  Layer 1  Cell physics             De Soto + Lambert-W       │
└─────────────────────────────────────────────────────────────┘
              ↓                              ↓
         Python  pvsim/             Unity 3D  unity/PvCompare/
              ↘                            ↙
                 Verified to 0.0007 %
```

| Layer | Python module | Unity / C# counterpart |
|---|---|---|
| 1 — physics | `pvsim.cell`, `pvsim.materials` | `SingleDiodeModel.cs`, `LambertW.cs` |
| 2 — system  | `pvsim.system`, `pvsim.module`, `pvsim.temperature`, `pvsim.optics`, `pvsim.spectral` | `SystemModel.cs`, `SimulationController.cs` |
| 3 — city    | `pvsim.weather`, `pvsim.cities` | `DayPlayer.cs`, JSON via `PvDataLoader.cs` |
| 4 — geo     | `scripts.map_pv_*`, GeoJSON parsing | — (visual map only on Python side) |
| 5 — lifecycle | `pvsim.degradation`, `pvsim.lcoe`, `pvsim.tandem`, `pvsim.policy_data` | — |

---

## Quick install

```bash
git clone https://github.com/<your-org>/pvsim.git
cd pvsim
conda create -n pvsim -c conda-forge --override-channels -y python=3.12 pip
conda activate pvsim
pip install -r requirements.txt
pytest tests/ -v               # 63 tests, expect all passing
```

> On Windows mixed conda + PyPI numpy/scipy can break BLAS — keep the whole
> scientific stack from pip. Use `requirements-lock.txt` for exact reproduction
> of the verified environment.

---

## Quick start — 60 seconds

```bash
# 1.  Regenerate the five current manuscript main figures
python -m scripts.fig_main1_inversion
python -m scripts.fig_main2_mechanisms
python -m scripts.fig_yield_segmentation
python -m scripts.fig_economics_timing
python -m scripts.fig_main5_deployment

# 2.  Validate physics core against pvlib
python -m scripts.validate_against_pvlib

# 3.  Run the source-data audit gate
python -m scripts.source_audit_gate

# 4.  Build the manuscript review HTML files
python -m scripts.make_review_html
```

For the Unity 3D twin:

```bash
# After installing Unity 6000.4 LTS (free Personal licence is fine):
python -m scripts.export_unity_data           # writes Assets/StreamingAssets/pvdata.json
# Open  unity/PvCompare  in Unity Hub.
# In the Editor menu:  PvSim  →  Build scene  →  press ▶
```

---

## Validation

| Test | Result | Script |
|---|---|---|
| Physics core vs `pvlib.calcparams_desoto` + `singlediode` | **0.0007 %** worst-case deviation across 32 (tech × condition × metric) cases | `scripts/validate_against_pvlib.py` |
| Python → C# digital twin | **0.0000 %** deviation on STC Pmp/Voc/Isc/FF/η | `unity/_verify/Program.cs` + `Assets/Editor/PvSelfTest.cs` |
| Unit tests | **63 / 63 passing** | `tests/` |
| Source-data audit gate | **0 missing provenance fields, 62 row-level official records complete** | `scripts/source_audit_gate.py` |
| External validation audit | **NEA spatial PV operation layer and CTGR spatial PV absolute generation sample available** | `scripts/external_validation_audit.py` |
| Release manifest | **complete file-level SHA256 manifest** | `scripts/release_manifest.py` |
| Current manuscript device set | modern c-Si 22 %, perovskite 19.3 %, tandem 28.3 % | `scripts/fig_yield_segmentation.py` |

---

## What you get out of the box

**Current manuscript main figures** (`outputs/figures/`):

| File | Theme |
|---|---|
| `NEWFig1_inversion.png` | Geographic inversion and grid pattern |
| `NEWFig2_mechanisms.png` | Temperature and spectral mechanisms |
| `NEWFig3_segmentation.png` | STC, per-kWp and per-area market rulers |
| `NEWFig4_economics_timing.png` | Economic timing and lifetime gate |
| `NEWFig5_deployment.png` | Land-based deployment decision plane |

Legacy figures and animations remain in `outputs/figures/` and `outputs/animations/`
as supporting material and historical exploration products.

**Review files**:

| File | Role |
|---|---|
| `docs/PAPER_C_draft.md` | English manuscript draft |
| `docs/PAPER_C_draft_zh.md` | Chinese review draft |
| `docs/SUPPORTING_INFORMATION_DRAFT.md` | SI structure and evidence map |
| `docs/PAPER_C_review_en.html` | Embedded-figure English review page |
| `docs/PAPER_C_review_zh.html` | Embedded-figure Chinese review page |

**A Unity scene** (`unity/PvCompare/`) the user can drag/play: four input sliders
(irradiance, ambient T, wind, age), city dropdown, real-time I-V/P-V plots, real 3D PV
arrays (procedural c-Si grid / perovskite thin-film textures), moving sun, grass + sky.

---

## Project layout

```
pvsim/                       — physics + data modules (15 files)
scripts/                     — analysis & figure generators (24 files)
tests/                       — pytest CI tests
data/tmy_cache/              — PVGIS TMY cache (auto-populated on first run)
outputs/                     — generated figures, animations, reports
unity/PvCompare/             — Unity 6000.4 project (C# mirror + scene)
unity/_verify/               — standalone .NET 8 console that re-checks
                               Python ↔ C# physics equality
docs/                        — extended documentation
```

---

## Reproducing the paper

The active manuscript figures can be regenerated with:

```bash
python -m scripts.fig_main1_inversion
python -m scripts.fig_main2_mechanisms
python -m scripts.fig_yield_segmentation
python -m scripts.fig_economics_timing
python -m scripts.fig_main5_deployment
python -m scripts.make_review_html
```

First-time PVGIS calls require internet; subsequent runs use `data/tmy_cache/`.

---

## Citing

If this software is useful in your research, please cite the companion tool paper
and the software DOI:

```bibtex
@article{pvsim2026,
  title  = {pvsim: a physics-validated open digital-twin framework for
            photovoltaic technology comparison},
  author = {<your name(s)>},
  journal = {SoftwareX (submitted)},
  year   = {2026}
}
@software{pvsim_v1,
  title  = {pvsim — Python + Unity digital twin for PV technology comparison},
  author = {<your name(s)>},
  year   = {2026},
  doi    = {10.5281/zenodo.<placeholder>},
  url    = {https://github.com/<your-org>/pvsim}
}
```

A machine-readable `CITATION.cff` is provided at the repository root.

---

## License

MIT.  See `LICENSE`.

---

## Acknowledgements

- Real PV/coal/transmission geographies from [Global Energy Monitor](https://globalenergymonitor.org).
- Typical meteorological year via [PVGIS](https://re.jrc.ec.europa.eu/api/).
- Single-diode reference implementation from [pvlib python](https://pvlib-python.readthedocs.io/).
- Tandem cost baseline from Cordell, Woodhouse, Warren, *Joule* 2025 (OSTI 2481281).
