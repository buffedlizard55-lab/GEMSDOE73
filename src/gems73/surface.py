"""H73-1 surface components (preregistered in registry/preregistration.json).

Fully unsupervised: no catalogue/SGMC training, no distance-to-catalogue
feature, no scored raster input.  Every component is a physical transform of
the hash-pinned competition / 3DEP-derivative bands.

Components
----------
scarp_n   one-sided topographic step (1 m LiDAR where valid, 100 m DEM
          Laplacian fallback elsewhere), polarity-weighted
chain     best 16-azimuth, 1.3 km straight-line occupancy of the scarp
          skeleton (en-echelon scarplet chains)
substep   subsurface-step witness: top-2 mean of basement-depth gradient,
          isostatic-gravity slope, magnetic horizontal gradient
pied_soft soft piedmont weight in [0,1]: deep basement x gentle slope x
          low 500 m relief (geometric mean)

Frozen E1 formula:
    S = sqrt(scarp_n * clip(1.4*chain,0,1)) * (0.55+0.45*substep)
        * (0.45+0.55*pied_soft)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

SENTINEL = -1e30


def read_band(path: Path, band: int) -> np.ndarray:
    with rasterio.open(path) as s:
        return s.read(band)


def official_band(data_dir: Path, band: int) -> np.ndarray:
    """One float32 official band with the -3.4e38 sentinel mapped to NaN."""
    a = read_band(data_dir / "training_features.tif", band).astype(np.float32)
    a[a < SENTINEL] = np.nan
    return a


def norm(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Percentile-clip normalisation to [0,1] using footprint p01/p99."""
    v = a[mask & np.isfinite(a)]
    lo, hi = np.percentile(v, [1.0, 99.0])
    out = np.clip((a - np.float32(lo)) / np.float32(max(hi - lo, 1e-12)), 0.0, 1.0)
    return np.nan_to_num(out, nan=0.0).astype(np.float32)


def _shift_add(acc: np.ndarray, src: np.ndarray, dy: int, dx: int) -> None:
    """acc += src shifted by (dy,dx), zero-filled (no wraparound)."""
    h, w = src.shape
    ys = slice(max(0, dy), min(h, h + dy))
    xs = slice(max(0, dx), min(w, w + dx))
    yt = slice(max(0, -dy), min(h, h - dy))
    xt = slice(max(0, -dx), min(w, w - dx))
    acc[ys, xs] += src[yt, xt]


def chain_occupancy(skeleton: np.ndarray, half_len: int = 6, n_az: int = 16) -> np.ndarray:
    """Max over azimuths of skeleton occupancy along a straight 1.3 km line."""
    sk = skeleton.astype(np.float32)
    best = np.zeros(skeleton.shape, np.float32)
    for k in range(n_az):
        theta = k * np.pi / n_az  # line azimuths are undirected: [0, pi)
        dyu, dxu = np.sin(theta), np.cos(theta)
        offsets = sorted({
            (int(round(t * dyu)), int(round(t * dxu)))
            for t in range(-half_len, half_len + 1) if t != 0
        } - {(0, 0)})
        if not offsets:
            continue
        acc = np.zeros(skeleton.shape, np.float32)
        for dy, dx in offsets:
            _shift_add(acc, sk, dy, dx)
        acc /= float(len(offsets))
        np.maximum(best, acc, out=best)
        del acc
    return best


def build_components(data_dir: Path, footprint: np.ndarray, log=print) -> dict[str, np.ndarray]:
    """Compute the four preregistered components; returns float32 arrays."""
    ext = data_dir / "external"
    # ---- LiDAR scarp (bands: 1 ex_max, 3 step_max, 6 downface, 7 upface, 8 cross, 12 valid)
    lid = ext / "lidar_scarp_features_u8.tif"
    valid = read_band(lid, 12) > 0
    vmask = footprint & valid
    log(f"lidar valid footprint px: {int(vmask.sum())} / {int(footprint.sum())}")
    parts = []
    for b in (3, 6, 8, 1):
        parts.append(norm(read_band(lid, b).astype(np.float32), vmask))
    scarp_lid = sum(parts) / float(len(parts))
    del parts
    down = read_band(lid, 6).astype(np.float32)
    up = read_band(lid, 7).astype(np.float32)
    polarity = np.abs(down - up) / (down + up + 1.0)
    del down, up
    scarp_lid = (scarp_lid * (0.5 + 0.5 * polarity)).astype(np.float32)
    del polarity

    # ---- DEM fallback + relief (official band 12 det_elev)
    dem = official_band(data_dir, 12)
    dem0 = np.nan_to_num(dem, nan=0.0)
    lap = np.abs(ndimage.gaussian_laplace(dem0, 1.5, mode="nearest")).astype(np.float32)
    scarp_dem = norm(lap, footprint)
    del lap
    relief5 = (ndimage.maximum_filter(dem0, size=5) - ndimage.minimum_filter(dem0, size=5)).astype(np.float32)
    del dem0

    scarp = np.where(vmask, scarp_lid, scarp_dem).astype(np.float32)
    del scarp_lid, scarp_dem
    scarp_n = norm(scarp, footprint)
    del scarp

    # ---- straight-chain occupancy of the scarp skeleton
    thr = float(np.percentile(scarp_n[footprint], 90.0))
    skeleton = (scarp_n >= thr) & footprint
    log(f"scarp skeleton: thr={thr:.4f} px={int(skeleton.sum())}")
    chain = chain_occupancy(skeleton)
    del skeleton

    # ---- subsurface-step witness (top-2 mean of three normalised steps)
    depth = official_band(data_dir, 15)
    depth_s = ndimage.gaussian_filter(np.nan_to_num(depth, nan=np.nanmedian(depth[footprint])), 2.0, mode="nearest")
    gy, gx = np.gradient(depth_s)
    depth_grad_n = norm(np.hypot(gx, gy).astype(np.float32), footprint)
    del gy, gx, depth_s
    grav_n = norm(official_band(data_dir, 5), footprint)
    mag_n = norm(official_band(data_dir, 3), footprint)
    stack = np.sort(np.stack([depth_grad_n, grav_n, mag_n]), axis=0)
    substep = ((stack[1] + stack[2]) * 0.5).astype(np.float32)
    del stack, depth_grad_n, grav_n, mag_n

    # ---- soft piedmont weight
    slope = official_band(data_dir, 19)
    depth_c = np.clip(np.nan_to_num(depth, nan=0.0) / 750.0, 0.0, 1.0)
    slope_c = np.clip(1.0 - np.nan_to_num(slope, nan=20.0) / 20.0, 0.0, 1.0)
    relief_c = np.clip(1.0 - relief5 / 120.0, 0.0, 1.0)
    pied_soft = np.cbrt(depth_c * slope_c * relief_c).astype(np.float32)
    del slope, depth, depth_c, slope_c, relief_c, relief5, dem

    for name, a in (("scarp_n", scarp_n), ("chain", chain), ("substep", substep), ("pied_soft", pied_soft)):
        a[~footprint] = 0.0
        assert np.isfinite(a).all(), name
    return dict(scarp_n=scarp_n, chain=chain, substep=substep, pied_soft=pied_soft,
                lidar_valid=vmask)


def make_surface(comp: dict[str, np.ndarray], experiment: str) -> np.ndarray:
    """Frozen E1/E2/E3 surfaces from preregistration.json."""
    scarp = comp["scarp_n"]
    chain_f = np.clip(1.4 * comp["chain"], 0.0, 1.0)
    sub_f = 0.55 + 0.45 * comp["substep"]
    pied_f = 0.45 + 0.55 * comp["pied_soft"]
    if experiment == "E1":
        s = np.sqrt(scarp * chain_f) * sub_f * pied_f
    elif experiment == "E2":
        s = np.sqrt(scarp * chain_f) * sub_f
    elif experiment == "E3":
        s = scarp * pied_f
    else:
        raise ValueError(experiment)
    return np.clip(np.nan_to_num(s, nan=0.0), 0.0, 1.0).astype(np.float32)
