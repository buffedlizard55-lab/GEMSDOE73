#!/usr/bin/env python3
"""Package the H73-7 production dots as the GEMSDOE73 lane GeoTIFF.

Reads evidence/selection_h73-7.json (written by run_experiments_h73_7.py)
and .cache/work7/surf_production.npy (selected recipe retrained on the full
catalogue). Emits 37,654 greedy dots (2.5 px spacing, >2.0 px from the full
catalogue) and writes tif+zip+json through the shared vendor
submission_writer verbatim (fail-closed; validates on-disk bytes).

The scientific verdict (promote/negative) is decided by
evidence/run_card_h73-7.json AFTER the uniqueness audit; this script only
builds the file whose submission note already carries the honest holdout
comparison so the note can never over-claim.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, submission_writer  # noqa: E402
from gems73.emit import greedy_dots  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
WORK = ROOT / ".cache" / "work7"
BUDGET = 37654

sel = json.loads((ROOT / "evidence" / "selection_h73-7.json").read_text())
best = sel["best_experiment"]
beats = sel["beats_control_ci_excluding_0"]
NAME = f"gems73-h73-7-hardfault-pu-{best.lower()}-37654dots-20261021"
verdict_word = "beat ctrl, selector review" if beats else "NEGATIVE, selector review only"
NOTE = (f"G73 H73-7 {best} hard-fault PU-HGB 37654 dots; HOLDOUT-DTI "
        f"{sel['best_holdout_dti']:.4f} vs ctrl {sel['control_holdout_dti']:.4f} - {verdict_word}")
assert len(NAME) <= 140 and len(NOTE) <= 140, (len(NAME), len(NOTE))

g = grid_mod.load_grid(DATA)
dcat = ndimage.distance_transform_edt(~g.catalogue)
prod_allowed = g.footprint & (dcat > 2.0)
surf = np.load(WORK / "surf_production.npy")
dots = greedy_dots(surf, prod_allowed, BUDGET)
assert int(dots.sum()) == BUDGET, int(dots.sum())
assert float(dcat[dots].min()) > 2.0
assert not np.any(dots & g.catalogue)
np.savez_compressed(WORK / "dots_production.npz", dots=dots)

pred = np.where(g.footprint, dots.astype(np.float32), np.float32(0.0))
out = ROOT / "docs" / "downloads" / f"{NAME}.tif"
receipt = submission_writer.write_submission(
    out, pred, DATA / "sample_submission.tif", g.footprint,
    note=NOTE, name=NAME, catalogue=g.catalogue,
    metadata={"lane": "H73-7", "experiment": best, "selection": sel,
              "production_caveat": ("HOLDOUT-DTI describes the fold-fair twin of this "
                                    "recipe (visible-catalogue training); production bytes "
                                    "come from the same recipe retrained on the full catalogue."),
              "download_ok": True,
              "submit_recommended": None,  # decided by run card after uniqueness audit
              })
print(json.dumps({"file": receipt["file"], "sha256": receipt["sha256"],
                  "bytes": receipt["bytes"], "name": NAME, "note": NOTE,
                  "note_chars": len(NOTE), "dots": int(dots.sum())}, indent=2))
