# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and adheres to
[Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-06

### Added
- Single-diode physics core with De Soto translation and Lambert-W I-V solver
  (`pvsim/cell.py`, `pvsim/materials.py`).
- System layer with Faiman cell temperature, Martin-Ruiz IAM, SPECTRL2-based
  spectral mismatch, PVWatts inverter with clipping
  (`pvsim/temperature.py`, `pvsim/optics.py`, `pvsim/spectral.py`,
  `pvsim/system.py`).
- City-scale weather pipeline (`pvsim/weather.py`) supporting synthetic
  clear-sky days, synthetic TMY year, and **real PVGIS TMY** via
  `from_pvgis_tmy`. 12 representative Chinese cities in `pvsim/cities.py`.
- National GeoJSON layers: 13 489 PV plants, 6 078 coal plants (with emission
  factors), 12 839 transmission lines, country administrative boundary.
- Lifecycle modules: multi-year degradation with three perovskite scenarios
  (`pvsim/degradation.py`), LCOE (`pvsim/lcoe.py`), I-V hysteresis
  (`pvsim/hysteresis.py`), perovskite/silicon tandem (`pvsim/tandem.py`).
- Policy / resource trajectory data with literature citations
  (`pvsim/policy_data.py`): NEA installation target, IEA grid decarbonisation,
  USGS critical metal supply, NREL Cordell 2025 tandem MSP baseline.
- 27 publication-grade figures and 12 animations under `outputs/`.
- **Unity 3D digital twin** (`unity/PvCompare/`) with bit-identical C# physics
  mirror, runtime self-test, real-time UI, and procedural PV-array visuals.
- Standalone .NET 8 console (`unity/_verify/`) re-checking Python ↔ C#
  numerical agreement on the real `SingleDiodeModel.cs` source.
- Comprehensive unit tests (`tests/test_physics.py`, 16 tests, < 1 s).
- pvlib cross-validation harness (`scripts/validate_against_pvlib.py`):
  worst-case agreement 0.0007 % over 32 (tech × condition × metric) cases.
- Portfolio optimisation v1 (`scripts/portfolio_v0.py`,
  `scripts/portfolio_v1.py`) with three-scenario Pareto sweep.
- MIT licence, CITATION.cff, `.zenodo.json`, GitHub Actions CI on three
  operating systems × three Python versions.
