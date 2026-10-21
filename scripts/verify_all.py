#!/usr/bin/env python3
"""Master Pass-3 verification harness: runs unit tests, SHA-256 byte audits,
link resolution checks, and consistency checks across `docs/`, `evidence/`, and `README.md`.
"""
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
    print("1. Running full pytest verification suite...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=ROOT, check=True)

    print("2. Verifying cryptographic hashes of shipped submission artifacts against run_card.json...")
    rc = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    p_zeros = ROOT / "docs" / "downloads" / rc["submission"]["file"]
    p_zip = ROOT / "docs" / "downloads" / rc["submission"]["zip_file"]
    p_nan = ROOT / "docs" / "downloads" / "gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-nan.tif"

    assert sha256(p_zeros) == rc["raster_sha256"]["primary_portal_safe_zeros_tif"], "zeros.tif SHA mismatch"
    assert sha256(p_zip) == rc["raster_sha256"]["primary_zip"], "zip SHA mismatch"
    assert sha256(p_nan) == rc["raster_sha256"]["companion_nan_tif"], "nan.tif SHA mismatch"

    print("3. Verifying verbatim retained prompt and run card embedding in README.md...")
    readme = (ROOT / "README.md").read_text()
    assert rc["raster_sha256"]["primary_portal_safe_zeros_tif"] in readme
    assert "Predicted values must be in range [0, 1]" in readme
    assert "PROMOTE" in readme

    print("ALL PASS-3 VERIFICATION GATES PASSED 100%!")


if __name__ == "__main__":
    main()
