# Photovoltaic simulation

| Directory | Contents |
|---|---|
| `code` | Numerical models, checks and the single `figures.ipynb` plotting notebook |
| `inputs` | Model inputs, reference data and source metadata |
| `outputs` | Main-figure data: `Figure_1.xlsx` through `Figure_5.xlsx` |
| `environment` | Python setup, dependency versions and installation script |

Use 64-bit Python 3.12.14. From the project directory:

```powershell
powershell -ExecutionPolicy Bypass -File environment/setup.ps1
powershell -ExecutionPolicy Bypass -File ./run.ps1
```

Open the plotting notebook:

```powershell
powershell -ExecutionPolicy Bypass -File ./plot.ps1
```

Figures are displayed in the notebook. Runtime files are stored in `environment/.runtime`.

Dependency versions: `environment/requirements.txt` and `environment/PACKAGE_VERSIONS.md`.
