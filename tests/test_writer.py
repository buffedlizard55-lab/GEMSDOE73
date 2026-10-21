"""Writer tests against the current src.gems73.grid API.

Repaired 2026-10-21 (IR-73-09): previously imported
``write_submission/WIDTH/HEIGHT/CRS/TRANSFORM`` from ``src.gems73.submission``,
which the merged library does not export (they live in ``src.gems73.grid``
and the writer there takes a template path), so pytest failed at collection
on main. Rewritten once against the real API.
"""
import pathlib
import tempfile

import numpy as np
import pytest
import rasterio

from src.gems73.grid import CRS, HEIGHT, TRANSFORM, WIDTH, write_submission


def _make_template(path: pathlib.Path) -> pathlib.Path:
    profile = dict(driver="GTiff", dtype="float32", count=1, crs=CRS,
                   transform=TRANSFORM, width=WIDTH, height=HEIGHT, nodata=np.nan)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.zeros((HEIGHT, WIDTH), np.float32), 1)
    return path


def test_write_zeros_variant_is_portal_safe():
    arr = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    arr[100, 100] = 1.0
    arr[200, 200] = 0.5
    with tempfile.TemporaryDirectory() as td:
        tpl = _make_template(pathlib.Path(td) / "template.tif")
        out = write_submission(arr, tpl, pathlib.Path(td) / "out.tif", outside="zeros")
        with rasterio.open(out) as src:
            assert src.nodata is None
            assert src.crs.to_epsg() == 32611
            assert (src.height, src.width) == (HEIGHT, WIDTH)
            a = src.read(1)
        assert np.isfinite(a).all()  # every cell finite -> cannot trip the [0,1] portal check
        assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0
        assert int((a > 0).sum()) == 2


def test_write_zeros_variant_zeroes_outside_footprint():
    arr = np.ones((HEIGHT, WIDTH), dtype=np.float32)
    footprint = np.zeros((HEIGHT, WIDTH), bool)
    footprint[10:20, 10:20] = True
    with tempfile.TemporaryDirectory() as td:
        tpl = _make_template(pathlib.Path(td) / "template.tif")
        out = write_submission(arr, tpl, pathlib.Path(td) / "out.tif",
                               footprint=footprint, outside="zeros")
        with rasterio.open(out) as src:
            a = src.read(1)
        assert int((a > 0).sum()) == 100
        assert np.isfinite(a).all()


def test_rejects_out_of_range_inside_footprint():
    arr = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    arr[0, 0] = 1.5
    footprint = np.ones((HEIGHT, WIDTH), bool)
    with tempfile.TemporaryDirectory() as td:
        tpl = _make_template(pathlib.Path(td) / "template.tif")
        with pytest.raises(AssertionError):
            write_submission(arr, tpl, pathlib.Path(td) / "bad.tif",
                             footprint=footprint, outside="zeros")
