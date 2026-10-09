"""Run the numerical calculations and reference checks."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from notebook_support import prepare_runtime

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if "--archived" not in sys.argv:
        if "--current-figures" in sys.argv: sys.argv.remove("--current-figures")
        from run_current_figures import main as current_main
        return current_main()
    sys.argv.remove("--archived")
    workspace = prepare_runtime(ROOT)
    environment = {
        **os.environ,
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPATH': str(workspace),
        'MPLBACKEND': 'Agg',
    }
    return subprocess.run(
        [sys.executable, str(workspace/'run_final_results.py'), *sys.argv[1:]],
        cwd=workspace, env=environment,
    ).returncode


if __name__ == '__main__':
    raise SystemExit(main())
