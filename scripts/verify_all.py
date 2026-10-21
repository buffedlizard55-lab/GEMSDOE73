#!/usr/bin/env python3
"""Master Pass-3 verification harness across all GEMSDOE73 lanes & PR #12 (`H73-2`)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    print("1. Running FULL multi-lane pytest verification suite across ALL tests in `tests/`...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=ROOT, check=True)

    print("2. Verifying cryptographic hashes of PR #12 (`H73-2`) artifacts...")
    rc = json.loads((ROOT / "evidence" / "run_card_h73_2.json").read_text())
    p_zeros = ROOT / "docs" / "downloads" / rc["submission"]["file"]
    p_zip = ROOT / "docs" / "downloads" / rc["submission"]["zip_file"]
    p_nan = ROOT / "docs" / "downloads" / "gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-nan.tif"

    assert sha256(p_zeros) == rc["raster_sha256"]["primary_portal_safe_zeros_tif"]
    assert sha256(p_zip) == rc["raster_sha256"]["primary_zip"]
    assert sha256(p_nan) == rc["raster_sha256"]["companion_nan_tif"]

    print("ALL MULTI-LANE + PR #12 VERIFICATION GATES PASSED 100%!")


if __name__ == "__main__":
    main()
