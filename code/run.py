"""Run the numerical calculations and reference checks."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from notebook_support import prepare_runtime

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
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
