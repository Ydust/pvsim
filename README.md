# Photovoltaic simulation

Current manuscript revision: 10 October 2026, 369 Chinese modelling regions.

| Directory | Contents |
|---|---|
| `code` | Physical and financial models, checks and the existing plotting notebook |
| `inputs` | Input data, original source records and archived comparison results |
| `outputs` | Current Figures 1–5, five source workbooks and numerical check records |
| `environment` | Python setup, exact versions and hash-checked runtime mappings |

Use 64-bit Python 3.12.14. From the project directory:

```powershell
powershell -ExecutionPolicy Bypass -File environment/setup.ps1
powershell -ExecutionPolicy Bypass -File ./run.ps1 --support
powershell -ExecutionPolicy Bypass -File ./plot.ps1
```

The default run reconstructs cost–lifetime boundaries, regional technology choices, policy transitions and generation contributions from the current physical-state inputs, then renders the five current main figures. `--support` also renders the complete response comparison and standalone auxiliary figures. The current notebook cells appear first. Each run starts with a fresh ignored workspace in `environment/.runtime`; SHA-256 checks reject changed inputs.

Hourly physical simulation is a separate, longer calculation:

```powershell
./environment/.venv/Scripts/python.exe code/run_current_physics.py
./environment/.venv/Scripts/python.exe code/run_current_physics.py --full --workers 4
```

The first command freshly checks four anchors and reconstructs all 369 regions from the archived hourly anchor-state results. `--full` freshly simulates every anchor, 26 path states and the matched factorial response controls. The current synchronized release passed the four-anchor pilot, all-region reconstruction and complete economic/decision recomputation; it does not claim that all hourly runs were repeated during this packaging step.

`run.ps1 --archived` and the later notebook cells retain the earlier release. They are distinct from the current 369-region manuscript. Current perovskite response paths are prescribed model scenarios, not measured device-development trajectories. Cost, lifetime and the 1/5/10% classification cutoffs have their declared scenario identities. Metadata and numeric source locators are included in the input manifests.

Dependency versions: `environment/requirements.txt`, `environment/PACKAGE_VERSIONS.md` and `environment/verified_environment.json`. Current source mappings: `environment/current_figures_manifest.json` and `environment/current_physics_manifest.json`. Original directory structure is preserved.

The 10 October delivery integrates the final standalone SI numbering and manuscript captions. Figures 1–5, all numerical data, model equations and calculation/plotting code are unchanged. The final delivery also contains numbered Figure 6, the Methods module diagram. Runtime composite Figure S44 maps to final SI Figures S130–S133; paired differences are S122–S125, cross-context fields S134–S135 and cutoff sensitivity S136–S137.
