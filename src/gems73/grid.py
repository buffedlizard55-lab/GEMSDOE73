"""Competition grid constants (verified 2026-10-21 from GEMSDOE32 shipped file)."""
from affine import Affine

WIDTH, HEIGHT = 3292, 3730
CRS = "EPSG:32611"
TRANSFORM_TUPLE = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
TRANSFORM = Affine(*TRANSFORM_TUPLE)


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
        profile.update(dtype=rasterio.float32, count=1, compress="deflate", tiled=True, blockxsize=256, blockysize=256)
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
