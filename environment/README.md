# Python environment

Verified on 64-bit Windows with Python 3.12.14. The complete exact-version lock is `requirements.txt`; `setup.ps1` creates `.venv` and runs the dependency check. `verified_environment.json` records the actual environment used for the current five-figure and hourly-pilot verification.

`current_figures_manifest.json` and `current_physics_manifest.json` record source files, generated runtime paths and SHA-256 hashes. The existing `layout.json` remains the archived-release mapping. Generated workspaces under `.runtime` are ignored by Git and recreated for each current run. `SHA256SUMS.txt` inventories this release; its own hash is deliberately omitted.
