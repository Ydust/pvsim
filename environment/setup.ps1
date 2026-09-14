$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDirectory
py -3.12 -m venv environment/.venv
if ($LASTEXITCODE -ne 0) { throw 'Install 64-bit Python 3.12 before running setup.' }
& ./environment/.venv/Scripts/python.exe -m pip install -r environment/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
& ./environment/.venv/Scripts/python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
& ./environment/.venv/Scripts/python.exe -m ipykernel install --sys-prefix --name python3 --display-name 'Python 3 (PV simulation)'
if ($LASTEXITCODE -ne 0) { throw 'Notebook kernel setup failed.' }
