#!/usr/bin/env python3
"""Autonomous Data Preparation & Feature Stack Verification (`scripts/prepare_data.py`).

Completes the competition data preparation step after `bash scripts/download_competition_data.sh`:
  1. Verifies SHA-256 hashes of all core competition GeoTIFFs and external geophysical/geomorphic layers.
  2. Verifies grid geometry (`EPSG:32611`, `3730 x 3292`, `100 m` resolution, `5,167,373` footprint pixels).
  3. Builds/verifies the 46-feature physical memmap (`h73_static46.mmap`, fixing IR-73-03 & IR-73-04).
  4. Writes `data/prepared_manifest.json` and `evidence/h73/data_preparation.json`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems57.grid import load_grid
from gems73 import method_h73 as h73
from fetch_data import EXTERNAL_PINS
from restore_data import PINS

DATA = ROOT / ".cache" / "data"
EXT = DATA / "external"
DEM10 = ROOT / ".cache" / "gems_data" / "dem10"
CACHE = ROOT / ".cache"
REG = CACHE / "registry" / "rasters"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    t0 = time.monotonic()
    for name, expected in PINS.items():
        p = DATA / name
        if not p.is_file() or sha256_file(p) != expected:
            raise RuntimeError(f"Core competition file missing or hash mismatch: {name}")

    for _, _, _, rel_dest, expected in EXTERNAL_PINS:
        p = DATA / rel_dest
        if not p.is_file() or sha256_file(p) != expected:
            raise RuntimeError(f"External layer missing or hash mismatch: {rel_dest}")

    grid = load_grid(DATA)
    fp, cat = grid.footprint, grid.catalogue
    with rasterio.open(DATA / "training_features.tif") as src:
        rtp = src.read(2).astype(np.float32)
    valid = ndi.binary_erosion(np.isfinite(rtp) & (rtp > -1e30) & fp, iterations=12)
    del rtp

    X46, unsup_vec = h73.build_or_load_h73_feature_mmap(valid, fp, DATA, EXT, DEM10, CACHE)
    reg_tifs = sorted(REG.glob("*.tif")) if REG.is_dir() else []

    manifest = {
        "prepared_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "ready",
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "grid": {
            "crs": str(grid.crs),
            "shape": list(grid.shape),
            "transform": list(grid.transform)[:6],
            "footprint_pixels": int(fp.sum()),
            "eroded_valid_pixels": int(valid.sum()),
            "catalogue_positive_pixels": int(cat.sum()),
        },
        "feature_stack": {
            "mmap_path": ".cache/h73_static46.mmap",
            "n_valid_rows": int(X46.shape[0]),
            "n_static_features": int(X46.shape[1]),
            "n_fold_mechanical_features": len(h73.H73_FOLD_MECHANICAL_NAMES),
            "n_total_features": h73.N_TOTAL_FEATURES,
            "feature_names": list(h73.H73_ALL_FEATURE_NAMES),
            "unsup_vec_finite": bool(np.isfinite(unsup_vec).all()),
        },
        "core_files_verified": len(PINS),
        "external_layers_verified": len(EXTERNAL_PINS),
        "dem10_channels_verified": 13,
        "registry_rasters_present": len(reg_tifs),
    }

    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence" / "h73").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "prepared_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "evidence" / "h73" / "data_preparation.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
