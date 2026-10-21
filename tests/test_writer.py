"""Writer tests against the merged src.gems73.submission API.

History: IR-73-09 — the original file imported `write_submission/WIDTH/...`
from `src.gems73.submission`, which never existed there, so pytest failed at
collection. The H73-7 session first rewrote it against `src.gems73.grid`;
the parallel-lane merge then reduced `grid.py` to constants, so this final
form tests the surviving writer/validator pair in
`src.gems73.submission` (`write_submission_geotiff` /
`validate_submission_geotiff`), including the strip-template tile fix
(blockxsize/blockysize=256; the real sample template is strip-organized).
"""
import pathlib
import tempfile

import numpy as np
import rasterio
from rasterio.transform import Affine

from src.gems73.submission import validate_submission_geotiff, write_submission_geotiff

H, W = 3730, 3292
TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def _make_strip_template(path: pathlib.Path) -> pathlib.Path:
    """Strip-organized template like the real sample_submission.tif."""
    profile = dict(driver="GTiff", dtype="float32", count=1, crs="EPSG:32611",
                   transform=TRANSFORM, width=W, height=H, nodata=np.nan, tiled=False)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.zeros((H, W), np.float32), 1)
    return path


def test_write_zeros_variant_is_portal_safe_from_strip_template():
    arr = np.zeros((H, W), dtype=np.float32)
    arr[100, 100] = 1.0
    arr[200, 200] = 0.5
    with tempfile.TemporaryDirectory() as td:
        tpl = _make_strip_template(pathlib.Path(td) / "template.tif")
        out = pathlib.Path(td) / "out.tif"
        info = write_submission_geotiff(arr, tpl, out, outside_mode="zeros")
        assert info["emitted_dots"] == 2
        report = validate_submission_geotiff(out, tpl, strict_whole_array_finite=True)
        assert report.passed, report.to_dict()
        with rasterio.open(out) as src:
            assert src.nodata is None
            assert src.crs.to_epsg() == 32611
            a = src.read(1)
        assert np.isfinite(a).all()
        assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0


def test_validator_rejects_out_of_range():
    arr = np.zeros((H, W), dtype=np.float32)
    with tempfile.TemporaryDirectory() as td:
        tpl = _make_strip_template(pathlib.Path(td) / "template.tif")
        bad = pathlib.Path(td) / "bad.tif"
        profile = dict(driver="GTiff", dtype="float32", count=1, crs="EPSG:32611",
                       transform=TRANSFORM, width=W, height=H)
        arr[0, 0] = 1.5
        with rasterio.open(bad, "w", **profile) as dst:
            dst.write(arr, 1)
        report = validate_submission_geotiff(bad, tpl, strict_whole_array_finite=True)
        assert not report.passed
