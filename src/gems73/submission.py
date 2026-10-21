"""Submission writer — guarantees portal-safe bytes.

Two mechanisms produce the same DriveData rejection "Predicted values must be in range [0, 1]":
 1. float32 sentinel -3.4028234663852886e+38 carried through as nodata (inside footprint 3,061 cells)
 2. nodata=NaN with NaN cells outside footprint (one validator change away)

Fix: single-band float32, EPSG:32611, 100m, 3292x3730, every cell finite, min0 max1, nodata=None.
Checked by independent re-read in tests and in docs/downloads/checks-*.json.

Competition grid (verified from shipped GEMSDOE32 file and problem page):
  CRS EPSG:32611, transform |100 0 243350|0 -100 4508550|0 0 1|, shape 3730x3292
"""
from __future__ import annotations
import hashlib, pathlib
import numpy as np
import rasterio
from rasterio.transform import Affine

WIDTH, HEIGHT = 3292, 3730
TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
CRS = "EPSG:32611"

def write_submission(arr: np.ndarray, path: pathlib.Path) -> dict:
    assert arr.shape == (HEIGHT, WIDTH), f"shape {arr.shape} != {(HEIGHT, WIDTH)}"
    assert arr.dtype == np.float32, f"dtype {arr.dtype} != float32"
    assert np.isfinite(arr).all(), "NaN/Inf found"
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, f"range [{arr.min()}, {arr.max()}] not in [0,1]"
    profile = {
        "driver": "GTiff",
        "height": HEIGHT, "width": WIDTH, "count": 1,
        "dtype": "float32", "crs": CRS, "transform": TRANSFORM,
        "compress": "lzw", "tiled": True, "blockxsize": 256, "blockysize": 256,
        # nodata=None intentionally — no tag, every cell is a valid [0,1] value
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
    # independent re-read
    with rasterio.open(path) as src:
        a2 = src.read(1)
        assert a2.shape == (HEIGHT, WIDTH)
        assert src.crs.to_epsg() == 32611
        assert np.isfinite(a2).all()
        assert float(a2.min()) >= 0 and float(a2.max()) <= 1
        assert src.nodata is None
    sha = hashlib.sha256(open(path,"rb").read()).hexdigest()
    return {"path": str(path), "sha256": sha, "emitted": int((arr>0).sum()), "all_finite": True}

def write_zip(tif_path: pathlib.Path) -> pathlib.Path:
    import zipfile
    z = tif_path.with_suffix(".zip")
    with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif_path, arcname=tif_path.name)
    return z
