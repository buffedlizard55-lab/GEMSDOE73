#!/usr/bin/env python3
"""Package the preregistered H73-M M3 production dots as the primary GEMSDOE73 GeoTIFF.

Uses the shared `vendor/gems57/submission_writer.py` verbatim (fail-closed: no clipping
or silent repair; validates the on-disk `.tif` and single-member `.zip` before committing).
Also writes the `-nan.tif` companion (NaN outside footprint, identical inside footprint)
for completeness.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import grid as grid_mod, submission_writer  # noqa: E402
from gems73.grid import write_submission as write_grid_submission  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
NAME = "gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros"
NOTE = (
    "G73 H73-M M3 3-expert LOQO piedmont co-kriging + wing-bridge + dmin3 submod, "
    "37654 off-cat dots; HOLDOUT-DTI 0.1224 vs ctrl 0.0939"
)
assert len(NAME) <= 140 and len(NOTE) <= 140, (len(NAME), len(NOTE))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    g = grid_mod.load_grid(DATA)
    z = np.load(ROOT / ".cache" / "work" / "h73m_dots.npz")
    dots = np.asarray(z["prod_M3"], bool)
    pred = np.where(g.footprint, dots.astype(np.float32), np.float32(0.0))
    assert int((pred > 0).sum()) == 37654
    assert not np.any((pred > 0) & g.catalogue)

    out_tif = ROOT / "docs" / "downloads" / f"{NAME}.tif"
    for p in (out_tif, out_tif.with_suffix(".zip"), out_tif.with_suffix(".json")):
        if p.exists():
            p.unlink()

    sel = json.loads((ROOT / "evidence" / "selection_h73m.json").read_text())
    receipt = submission_writer.write_submission(
        out_tif,
        pred,
        DATA / "sample_submission.tif",
        g.footprint,
        note=NOTE,
        name=NAME,
        catalogue=g.catalogue,
        metadata={
            "experiment": "M3",
            "lane": "H73-M",
            "selection": sel,
            "verdict": "promote",
            "download_ok": True,
            "submit_recommended": True,
        },
    )

    # Also write the NaN-outside companion for users who want the spec NaN-outside twin
    nan_tif = ROOT / "docs" / "downloads" / "gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif"
    write_grid_submission(
        pred, DATA / "sample_submission.tif", nan_tif, footprint=g.footprint, outside="nan"
    )
    receipt["nan_companion_file"] = nan_tif.name
    receipt["nan_companion_sha256"] = sha256_file(nan_tif)
    receipt["nan_companion_bytes"] = nan_tif.stat().st_size
    out_tif.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
    for p in (out_tif, out_tif.with_suffix(".zip"), out_tif.with_suffix(".json"), nan_tif):
        os.chmod(p, 0o644)

    (ROOT / "evidence" / "validator_h73m.json").write_text(
        json.dumps(receipt["validator"], indent=2) + "\n"
    )
    (ROOT / "docs" / "downloads" / "validator_h73m.json").write_text(
        json.dumps(receipt["validator"], indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "file": receipt["file"],
                "sha256": receipt["sha256"],
                "bytes": receipt["bytes"],
                "zip_file": receipt["zip_file"],
                "zip_sha256": receipt["zip_sha256"],
                "nan_companion_file": receipt["nan_companion_file"],
                "nan_companion_sha256": receipt["nan_companion_sha256"],
                "name": NAME,
                "note": NOTE,
                "note_chars": len(NOTE),
                "all_checks_passed": receipt["validator"]["all_checks_passed"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
