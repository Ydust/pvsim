# Contributing

Thank you for considering a contribution to **pvsim**.

## Quick checklist

1. Open an issue first for non-trivial changes so we can discuss the design.
2. Fork the repository and create a topic branch from `main`.
3. Keep commits focused; write a short, descriptive subject (≤ 72 chars).
4. Add or extend a `pytest` test for any new physics, data source, or scenario.
5. Run the full local quality gate before opening a PR:

   ```bash
   pytest tests/ -v
   python -m scripts.validate_against_pvlib
   python -m scripts.calibrate
   ```

6. If you touch the C# physics in `unity/PvCompare/Assets/Scripts/`, also rebuild
   the verifier and confirm `unity/_verify` still reports zero deviation
   (requires .NET 8 SDK):

   ```bash
   cd unity/_verify
   dotnet run -c Release
   ```

7. Document any new public function / data source in its docstring with a
   literature reference where applicable.

## Physics / data changes

- Any change to material parameters (`pvsim/materials.py`), grid emission
  factors, embodied-carbon factors, or technology cost assumptions
  **must cite a published source** in the docstring or in
  `pvsim/policy_data.py`.
- Calibration changes that affect the literature-aligned temperature
  coefficients should re-run `scripts/calibrate.py` and update the reported
  numbers in `README.md` if they shift.

## Style

- Python: follow PEP 8 with 4-space indents; prefer concise, well-named
  variables over comments.
- Avoid emojis in source code.
- Keep figures self-explanatory: title with the conclusion, axis labels with
  units, and a sources / assumptions note at the bottom when external data
  are involved.

## Code of conduct

By participating you agree to interact constructively and respectfully.
We follow the [Contributor Covenant](https://www.contributor-covenant.org/)
v2.1.
