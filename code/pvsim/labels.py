"""Read text labels shared with model input and reference tables."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _labels() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    candidates = (
        root / 'data/source_tables/model_text.csv',
        root.parent / 'inputs/data/source_tables/model_text.csv',
    )
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise FileNotFoundError('Model text table was not found.')
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    result = {row['label_id']: row['text'] for row in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate model text identifiers.')
    return result


def label(identifier: str) -> str:
    return _labels()[identifier]
