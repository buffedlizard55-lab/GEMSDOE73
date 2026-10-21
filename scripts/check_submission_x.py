#!/usr/bin/env python3
"""Independent re-read validator for the H73-6 GeoTIFF (shared vendor validate).

Answers the portal error 'Predicted values must be in range [0, 1]' from the
written bytes: all 12,279,160 cells finite in [0,1], nodata=None,
CRS/shape/transform identical to the sample submission.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, validate  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
sel = json.loads((ROOT / "evidence/selection_x.json").read_text())
ARM = sel["best_experiment"].lower()
CAND = ROOT / "docs/downloads" / f"gems73-h73-6-traceloc-{ARM}-37654dots-20261021.tif"

g = grid_mod.load_grid(DATA)
receipt = validate.validate(CAND, g.footprint, g.catalogue)
with rasterio.open(DATA / "sample_submission.tif") as s:
    receipt["sample_template"] = {"crs": str(s.crs), "shape": [s.height, s.width],
                                  "transform": list(tuple(s.transform)[:6]), "dtype": s.dtypes[0]}
receipt["crs_shape_transform_match_sample"] = bool(
    receipt["meta"]["crs"] == receipt["sample_template"]["crs"]
    and receipt["meta"]["shape"] == receipt["sample_template"]["shape"]
    and receipt["meta"]["transform"] == receipt["sample_template"]["transform"])
validate.assert_submittable(receipt)
assert receipt["crs_shape_transform_match_sample"]
(ROOT / "evidence/validator_x.json").write_text(json.dumps(receipt, indent=2) + "\n")
(ROOT / "docs/downloads/validator_h73-6.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"sha256": receipt["sha256"], "all_checks_passed": receipt["all_checks_passed"],
                  "min": receipt["min"], "max": receipt["max"], "n_nan": receipt["n_nan"],
                  "dots": receipt["emitted_positive_pixels"],
                  "match_sample": receipt["crs_shape_transform_match_sample"]}, indent=2))
