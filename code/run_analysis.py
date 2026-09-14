"""Run supported entry points and compare their tables with reference outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pandas as pd


ROOT = Path(__file__).resolve().parent
TASKS = [
    ("policy", ["release/policy/run.py"], "release/policy/deliverables/Source_Data", "Figure5_final", ROOT),
    ("policy_sensitivity", ["release/policy_sensitivity/run.py"], "release/policy_sensitivity/deliverables/Source_Data", "Figure5_final", ROOT),
    ("parameter_stress", ["release/parameter_stress/run.py"], "release/parameter_stress/deliverables/Source_Data", "Parameters", ROOT),
    ("boundaries", ["release/boundaries/run.py"], "release/boundaries/deliverables/Source_Data", "Parameters", ROOT),
    ("revision_quick", ["-m", "scripts.reviewer_revision_analysis", "quick"], "outputs/reviewer_revision_20260910", "Revision_S7_35", ROOT),
    ("revision_aggregate", ["-m", "scripts.reviewer_revision_analysis", "aggregate"], "outputs/reviewer_revision_20260910", "Revision_S7_35", ROOT),
    ("annual_policy", ["-m", "scripts.annual_policy_robustness"], "outputs/annual_policy_robustness_20260910", "Annual_policy_S7_36", ROOT),
    ("field_validation", ["scripts/field_validation_20260910.py", "--project-root", ".", "--output", "outputs/field_validation_reproduced"], "outputs/field_validation_reproduced", "Validation_S7_32", ROOT),
    ("hzb_validation", ["hzb_response_20260910/analyse.py"], "hzb_response_20260910/Source_Data", "Validation_S7_33", ROOT / "external_validation/hzb"),
]


def main() -> int:
    restore = subprocess.run([sys.executable, str(ROOT / "restore_large_files.py")])
    if restore.returncode:
        return restore.returncode
    requested = set(sys.argv[1:])
    names = {task[0] for task in TASKS}
    if requested - names:
        raise ValueError(f"Unknown task(s): {sorted(requested - names)}")
    selected = [task for task in TASKS if not requested or task[0] in requested]
    verification = ROOT / "verification/github_run"
    verification.mkdir(parents=True, exist_ok=True)
    results = []
    for name, args, generated, expected, cwd in selected:
        print(f"Running {name}", flush=True)
        output_dir = cwd / generated
        before = {path: path.stat().st_mtime_ns for path in output_dir.rglob("*.csv")} if output_dir.exists() else {}
        started = time.monotonic()
        with (verification / f"{name}.log").open("w", encoding="utf-8") as log:
            process = subprocess.run(
                [sys.executable, *args], cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(cwd), "MPLBACKEND": "Agg"},
            )
        result = {"task": name, "exit_code": process.returncode, "seconds": round(time.monotonic() - started, 2), "comparisons": []}
        references = {path.name: path for path in (ROOT / "reference_outputs" / expected).rglob("*.csv")}
        if process.returncode == 0:
            for output in sorted(output_dir.rglob("*.csv")):
                if output.name not in references or before.get(output) == output.stat().st_mtime_ns:
                    continue
                comparison = {"file": output.name, "reference": str(references[output.name].relative_to(ROOT))}
                try:
                    actual = pd.read_csv(output)
                    reference = pd.read_csv(references[output.name])
                    pd.testing.assert_frame_equal(actual, reference, check_dtype=False, check_exact=False, rtol=1e-10, atol=1e-7)
                    comparison.update(matches=True, rows=len(actual))
                except Exception as error:
                    comparison.update(matches=False, error=str(error))
                result["comparisons"].append(comparison)
        result["passed"] = process.returncode == 0 and bool(result["comparisons"]) and all(item["matches"] for item in result["comparisons"])
        results.append(result)
        print(f"{name}: {'PASS' if result['passed'] else 'FAIL'}; compared {len(result['comparisons'])} tables", flush=True)
    report = {
        "python": sys.version,
        "tolerance": {"rtol": 1e-10, "atol": 1e-7},
        "tasks": results,
        "all_passed": all(result["passed"] for result in results),
    }
    (verification / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
