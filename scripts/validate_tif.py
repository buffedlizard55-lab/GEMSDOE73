#!/usr/bin/env python3
"""Validate both all-finite primary GeoTIFFs and official NaN-outside twin GeoTIFFs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import validate as shared_validate  # noqa: E402


def verify_path(path: Path, fp: np.ndarray | None, cat: np.ndarray | None) -> dict:
    with rasterio.open(path) as src:
        arr = src.read(1)
        crs_ok = src.crs is not None and src.crs.to_epsg() == 32611
        shape_ok = src.shape == (3730, 3292)
        dtype_ok = src.count == 1 and src.dtypes[0] == "float32"
        tf = tuple(round(float(v), 6) for v in list(src.transform)[:6])
        tf_ok = tf == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        nodata = src.nodata

    is_nan_twin = path.name.endswith("-nan.tif")
    if is_nan_twin and fp is not None:
        in_ok = bool(np.isfinite(arr[fp]).all() and arr[fp].min() >= 0.0 and arr[fp].max() <= 1.0)
        out_ok = bool(np.isnan(arr[~fp]).all())
        pos_px = int((arr[fp] > 0.5).sum())
        cat_px = int((arr[cat] > 0.5).sum()) if cat is not None else 0
        ok = crs_ok and shape_ok and dtype_ok and tf_ok and in_ok and out_ok and cat_px == 0
    else:
        fin_ok = bool(np.isfinite(arr).all() and nodata is None)
        rng_ok = bool(float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0)
        pos_px = int((arr > 0.5).sum())
        cat_px = int((arr[cat] > 0.5).sum()) if cat is not None else 0
        out_zero = bool((arr[~fp] == 0.0).all()) if fp is not None else True
        ok = crs_ok and shape_ok and dtype_ok and tf_ok and fin_ok and rng_ok and out_zero and cat_px == 0
        if (ROOT / "data/sample_submission.tif").is_file():
            rep = shared_validate.validate(path)
            ok = ok and bool(rep["all_checks_passed"])

    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "file": str(path),
        "mode": "nan-outside-official-twin" if is_nan_twin else "all-finite-zeros-primary",
        "sha256": sha,
        "emitted_positive_pixels": pos_px,
        "on_catalogue_pixels": cat_px,
        "ok": ok,
    }


def main() -> int:
    fp = cat = None
    if (ROOT / "data/sample_submission.tif").is_file():
        fp = np.isfinite(rasterio.open(ROOT / "data/sample_submission.tif").read(1))
    if (ROOT / "data/existing_faults.tif").is_file() and fp is not None:
        cat = (rasterio.open(ROOT / "data/existing_faults.tif").read(1) > 0) & fp

    targets = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "docs/downloads").glob("*.tif"))
    assert targets, "No GeoTIFF files found to validate!"
    for p in targets:
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as zf:
                names = zf.namelist()
                assert len(names) == 1 and names[0].endswith(".tif"), f"Invalid zip {p}: {names}"
                print(f"[PASS] ZIP {p.name}: contains single GeoTIFF {names[0]} ({len(zf.read(names[0])):,} bytes)")
            continue
        res = verify_path(p, fp, cat)
        status = "PASS" if res["ok"] else "FAIL"
        print(
            f"[{status}] {p.name} ({res['mode']}) | dots={res['emitted_positive_pixels']:,} | "
            f"on_cat={res['on_catalogue_pixels']} | sha256={res['sha256'][:16]}..."
        )
        if not res["ok"]:
            return 2
    print("ALL VALIDATION CHECKS PASSED!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
