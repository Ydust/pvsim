"""Restore files split or compressed to satisfy GitHub's browser-upload limit."""

from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "inputs/electrical_hourly_inputs.npz": "9c0548b3a4bf6ecc651d4de5a7f45d3d58689f02da4006f053b1a4c59ffd2c3b",
    "external_validation/hzb/public_field_search_round2_20260910/raw/irradiance_and_cell_temp.csv": "76c30c67fe79a47f59021655238958e619c87b617211c603bcbe7982a050304f",
    "external_validation/hzb/public_field_search_round2_20260910/raw/outdoor_mpp_d1_p1.csv": "f1631f1442be4774a055eb70301cc89ed8a10b2562c24b3782e55b892c22bce5",
    "external_validation/hzb/public_field_search_round2_20260910/raw/outdoor_mpp_d1_p2.csv": "9061afbebfb6bda8db94526dcd1d828ef61d990111bf320215606667cfb9c076",
    "external_validation/hzb/public_field_search_round2_20260910/raw/outdoor_mpp_d1_p4.csv": "959dd8f7ce5c97d0e874c668727653517b9c994c26ede1d3a74546e2c0fcbc8d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def restore_electrical_input() -> None:
    target = ROOT / "inputs/electrical_hourly_inputs.npz"
    parts = sorted((ROOT / "large_file_archives/electrical_hourly_inputs").glob("*.part*"))
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as output:
            for part in parts:
                with part.open("rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(block)


def restore_hzb_inputs() -> None:
    target_dir = ROOT / "external_validation/hzb/public_field_search_round2_20260910/raw"
    target_dir.mkdir(parents=True, exist_ok=True)
    for archive in sorted((ROOT / "large_file_archives/hzb_raw").glob("*.zip")):
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) != 1 or Path(members[0].filename).name != members[0].filename:
                raise RuntimeError(f"Unexpected archive structure: {archive}")
            target = target_dir / members[0].filename
            if not target.exists():
                bundle.extract(members[0], target_dir)


def main() -> int:
    restore_electrical_input()
    restore_hzb_inputs()
    failures = []
    for relative, expected in EXPECTED.items():
        path = ROOT / relative
        actual = sha256(path) if path.exists() else "missing"
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")
    if failures:
        print("Large-file restoration failed:\n" + "\n".join(failures))
        return 1
    print(f"PASS: restored and verified {len(EXPECTED)} large files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
