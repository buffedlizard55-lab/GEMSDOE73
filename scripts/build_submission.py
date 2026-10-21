#!/usr/bin/env python3
"""Package the preregistered H73-1 E1 production dots as the GEMSDOE73 GeoTIFF.

Uses the shared vendor submission_writer verbatim (fail-closed: no clipping
or repair; validates the on-disk TIFF and one-TIFF ZIP before committing).
The scientific verdict (promote/negative) is recorded in the run card and on
the site; this script only guarantees a format-valid, range-[0,1] file.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, submission_writer  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
NAME = "gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021"
NOTE = ("G73 H73-1 E1 piedmont scarp-chain unsupervised 37654 dots; "
        "HOLDOUT-DTI 0.0548 vs ctrl 0.0939 - NEGATIVE, selector review only")
assert len(NAME) <= 140 and len(NOTE) <= 140, (len(NAME), len(NOTE))

g = grid_mod.load_grid(DATA)
z = np.load(ROOT / ".cache" / "work" / "dots.npz")
dots = np.asarray(z["prod_E1"], bool)
pred = np.where(g.footprint, dots.astype(np.float32), np.float32(0.0))
assert int((pred > 0).sum()) == 37654
assert not np.any((pred > 0) & g.catalogue)

out = ROOT / "docs" / "downloads" / f"{NAME}.tif"
sel = json.loads((ROOT / "evidence" / "selection.json").read_text())
receipt = submission_writer.write_submission(
    out, pred, DATA / "sample_submission.tif", g.footprint,
    note=NOTE, name=NAME, catalogue=g.catalogue,
    metadata={"experiment": "E1", "lane": "H73-1", "selection": sel,
              "verdict": "negative (failed preregistered holdout gate)",
              "download_ok": True, "submit_recommended": False})
# submission_writer also writes NAME.zip and NAME.json beside the TIFF
print(json.dumps({"file": receipt["file"], "sha256": receipt["sha256"],
                  "bytes": receipt["bytes"], "name": NAME, "note_chars": len(NOTE)}, indent=2))
