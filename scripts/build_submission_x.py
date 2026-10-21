#!/usr/bin/env python3
"""Package H73-6 selected production dots via the shared vendor writer.

Fail-closed (vendor submission_writer): no clipping/repair, refuses to
overwrite, validates on-disk TIFF + one-TIFF ZIP before committing.
Verdict (promote/negative) lives in the run card/site, not in this script.
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
sel = json.loads((ROOT / "evidence/selection_x.json").read_text())
ARM = sel["best_experiment"].lower()
NAME = f"gems73-h73-6-traceloc-{ARM}-37654dots-20261021"
NOTE = (f"G73 H73-6 {ARM.upper()} traceloc NMS+UK/grav witness 37654 dots; "
        f"HOLDOUT {sel['best_holdout_dti']:.4f} vs ctrl {sel['control_holdout_dti']:.4f} NEGATIVE")
assert len(NAME) <= 140 and len(NOTE) <= 140, (len(NAME), len(NOTE))

g = grid_mod.load_grid(DATA)
z = np.load(ROOT / ".cache/work_x/dots_x.npz")
dots = np.asarray(z[f"prod_{sel['best_experiment']}"], bool)
pred = np.where(g.footprint, dots.astype(np.float32), np.float32(0.0))
assert int((pred > 0).sum()) == 37654
assert not np.any((pred > 0) & g.catalogue)

out = ROOT / "docs/downloads" / f"{NAME}.tif"
receipt = submission_writer.write_submission(
    out, pred, DATA / "sample_submission.tif", g.footprint,
    note=NOTE, name=NAME, catalogue=g.catalogue,
    metadata={"experiment": sel["best_experiment"], "lane": "H73-6", "selection": sel,
              "verdict": "negative (failed preregistered holdout gate)",
              "download_ok": True, "submit_recommended": False})
print(json.dumps({"file": receipt["file"], "sha256": receipt["sha256"],
                  "bytes": receipt["bytes"], "name": NAME, "note": NOTE,
                  "note_chars": len(NOTE)}, indent=2))
