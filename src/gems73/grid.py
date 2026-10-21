"""Competition grid geometry, footprint, raster IO.

All geometry is taken from the competition rasters themselves
(byte-verified against the owner-mirror manifest):

    EPSG:32611 (UTM 11N), 100 m, width 3292 x height 3730,
    origin (243350, 4508550), transform [100,0,243350, 0,-100,4508550],
    feature nodata -3.4028234663852886e+38, footprint 5,167,373 px
    (measured from sample_submission.tif), sample_submission sha256
    2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc.

Every value here is verified line-by-line; see docs/sources.html.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import numpy as np
import rasterio
from rasterio.transform import Affine

# Official grid constants — verified from sample_submission.tif (GEMSDOE24 mirror)
WIDTH = 3292
HEIGHT = 3730
CRS = "EPSG:32611"
TRANSFORM = Affine(100.0, 0.0, 243350.0,
                   0.0, -100.0, 4508550.0)
NODATA_F32 = np.float32(-3.4028234663852886e38)
SAMPLE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
LABELS_SHA256 = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"
FOOTPRINT_PX = 5167373  # measured: np.isfinite(sample_submission).sum()
POSITIVE_PX = 60988     # measured: (labels >=1).sum()


def get_template_meta() -> dict:
    return dict(driver="GTiff", dtype="float32", count=1,
                crs=CRS, transform=TRANSFORM,
                width=WIDTH, height=HEIGHT, nodata=np.nan)


def read_footprint(sample_path: str | Path) -> np.ndarray:
    with rasterio.open(sample_path) as src:
        a = src.read(1)
    return np.isfinite(a)


def read_labels(labels_path: str | Path) -> np.ndarray:
    with rasterio.open(labels_path) as src:
        a = src.read(1)
    return a >= 1


def write_submission(mask: np.ndarray, template_path: str | Path,
                     out_path: str | Path, footprint: np.ndarray | None = None,
                     outside: str = "zeros") -> Path:
    """Write a portal-safe GeoTIFF on the exact template grid.

    outside='zeros' → all 12,279,160 cells finite in [0,1], nodata=None (portal-safe)
    outside='nan'   → NaN outside footprint, nodata=NaN (competition spec)
    """
    with rasterio.open(template_path) as src:
        profile = src.profile.copy()
        profile.update(dtype=rasterio.float32, count=1, compress="deflate", tiled=True)
        if outside == "zeros":
            profile.update(nodata=None)
        else:
            profile.update(nodata=np.nan)

    out = np.asarray(mask, dtype=np.float32)
    assert out.shape == (HEIGHT, WIDTH), f"shape {out.shape} != {(HEIGHT, WIDTH)}"

    if footprint is not None:
        inside = out[footprint]
        assert np.isfinite(inside).all(), "non-finite inside footprint"
        assert (inside >= 0).all() and (inside <= 1).all(), "value outside [0,1] inside footprint"
        if outside == "zeros":
            out = np.where(footprint, out, np.float32(0.0))
        else:
            out = np.where(footprint, out, np.float32(np.nan))
        # Ensure zeros variant is fully finite and in range
        if outside == "zeros":
            assert np.isfinite(out).all() and (out >= 0).all() and (out <= 1).all()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out, 1)
    return out_path


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
