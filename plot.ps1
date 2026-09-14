$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& ./environment/.venv/Scripts/python.exe -m jupyterlab code/figures.ipynb
if ($LASTEXITCODE -ne 0) { throw 'JupyterLab could not start.' }
