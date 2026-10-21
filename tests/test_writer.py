"""Writer produces portal-safe bytes (real src API, session-2 IR-73-09 fix).

Builds a minimal template GeoTIFF on the pinned grid in a temp dir, writes
via src.gems73.submission.write_submission_geotiff, and re-reads the bytes:
all-finite, [0,1], nodata=None for the zeros variant — the exact properties
that answer the portal error "Predicted values must be in range [0, 1]".
"""
import pathlib
import tempfile

import numpy as np
import rasterio

from src.gems73.grid import CRS, HEIGHT, TRANSFORM, WIDTH
from src.gems73.submission import validate_submission_geotiff, write_submission_geotiff


def _template(path: pathlib.Path) -> pathlib.Path:
    profile = dict(driver="GTiff", dtype="float32", count=1, crs=CRS,
                   transform=TRANSFORM, width=WIDTH, height=HEIGHT, nodata=np.nan)
    arr = np.full((HEIGHT, WIDTH), np.nan, np.float32)
    arr[100:300, 100:300] = 0.0  # finite footprint patch
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
    return path


def test_write_all_finite_zeros_variant():
    with tempfile.TemporaryDirectory() as td:
        tpl = _template(pathlib.Path(td) / "tpl.tif")
        arr = np.zeros((HEIGHT, WIDTH), np.float32)
        arr[150, 150] = 1.0
        arr[200, 200] = 0.5
        out = pathlib.Path(td) / "out.tif"
        info = write_submission_geotiff(arr, tpl, out, outside_mode="zeros")
        assert info["emitted_dots"] == 2
        rep = validate_submission_geotiff(out, tpl, strict_whole_array_finite=True)
        assert rep.passed, rep.to_dict()
        with rasterio.open(out) as src:
            assert src.nodata is None
            assert src.crs.to_epsg() == 32611
            a = src.read(1)
        assert np.isfinite(a).all() and float(a.min()) >= 0.0 and float(a.max()) <= 1.0


def test_nan_variant_finite_inside_footprint():
    with tempfile.TemporaryDirectory() as td:
        tpl = _template(pathlib.Path(td) / "tpl.tif")
        arr = np.zeros((HEIGHT, WIDTH), np.float32)
        arr[150, 150] = 1.0
        out = pathlib.Path(td) / "out_nan.tif"
        write_submission_geotiff(arr, tpl, out, outside_mode="nan")
        with rasterio.open(out) as src:
            a = src.read(1)
        inside = a[100:300, 100:300]
        assert np.isfinite(inside).all() and float(inside.min()) >= 0.0 and float(inside.max()) <= 1.0
        assert np.isnan(a[0, 0])
