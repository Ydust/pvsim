$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& ./environment/.venv/Scripts/python.exe code/run.py @args
if ($LASTEXITCODE -ne 0) { throw 'Run failed. See environment/.runtime/verification for details.' }
