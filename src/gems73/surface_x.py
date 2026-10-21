"""H73-6 surface components (preregistered in registry/preregistration_x.json).

Lane (single method paragraph): trace-localised, independently-corroborated
scarps. Reuses session-1 components (`surface.build_components`: scarp_n,
pied_soft) unchanged; adds exactly two new transforms:

ridge_soft_nms  orientation non-maximum suppression of scarp_n on its own
                structure tensor (8-direction quantised); off-ridge pixels
                keep 0.25*scarp_n so ranking degrades softly instead of
                starving low-scarp folds.
witness         max(U/K gradient ridge, isostatic-gravity slope ridge),
                normalised to [0,1], max-filtered radius 2 px (200 m);
                surface factor 0.35+0.65*witness (never hard-zero).

Frozen surfaces:
    X1 = ridge * (0.35+0.65*w) * (0.45+0.55*pied_soft)
    X2 = ridge * (0.45+0.55*pied_soft)
    X3 = scarp_n * (0.35+0.65*w) * (0.45+0.55*pied_soft)
No catalogue/SGMC training, no distance-to-catalogue feature, no scored
raster input. All arrays float32 on the 3730x3292 competition grid.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import ndimage

from .surface import norm, official_band, read_band

OFF_RIDGE_FACTOR = np.float32(0.25)
WITNESS_FLOOR, WITNESS_GAIN = np.float32(0.35), np.float32(0.65)


def _shift(a: np.ndarray, dy: int, dx: int, fill: float = -1.0) -> np.ndarray:
    """Return `a` shifted by (dy,dx) with constant fill (no wraparound)."""
    out = np.full(a.shape, fill, dtype=a.dtype)
    h, w = a.shape
    ys = slice(max(0, dy), min(h, h + dy))
    xs = slice(max(0, dx), min(w, w + dx))
    yt = slice(max(0, -dy), min(h, h - dy))
    xt = slice(max(0, -dx), min(w, w - dx))
    out[ys, xs] = a[yt, xt]
    return out


def ridge_soft_nms(scarp_n: np.ndarray, footprint: np.ndarray,
                   sigma: float = 1.5, tensor_sigma: float = 2.0) -> np.ndarray:
    """Soft orientation-NMS ridge of the scarp field (float32 in [0,1])."""
    s = ndimage.gaussian_filter(scarp_n.astype(np.float32), sigma, mode="nearest")
    gy, gx = np.gradient(s)
    gy = gy.astype(np.float32); gx = gx.astype(np.float32)
    del s
    gxx = ndimage.gaussian_filter(gx * gx, tensor_sigma, mode="nearest")
    gyy = ndimage.gaussian_filter(gy * gy, tensor_sigma, mode="nearest")
    gxy = ndimage.gaussian_filter(gx * gy, tensor_sigma, mode="nearest")
    del gx, gy
    # Dominant gradient orientation theta in [0, pi); ridge runs perpendicular.
    theta = (0.5 * np.arctan2(2.0 * gxy, gxx - gyy)).astype(np.float32)
    del gxx, gyy, gxy
    theta = np.where(theta < 0, theta + np.float32(np.pi), theta)
    # Quantise gradient direction to 4 axes: 0=E-W, 1=NE-SW, 2=N-S, 3=NW-SE
    axis = ((theta + np.float32(np.pi / 8.0)) / np.float32(np.pi / 4.0)).astype(np.int32) % 4
    del theta
    base = scarp_n.astype(np.float32)
    is_max = np.zeros(base.shape, bool)
    for ax, (dy, dx) in enumerate(((0, 1), (-1, 1), (1, 0), (1, 1))):
        sel = axis == ax
        if not sel.any():
            continue
        n1 = _shift(base, dy, dx)
        n2 = _shift(base, -dy, -dx)
        is_max |= sel & (base >= n1) & (base >= n2)
        del n1, n2, sel
    del axis
    ridge = np.where(is_max, base, base * OFF_RIDGE_FACTOR).astype(np.float32)
    del is_max, base
    ridge[~footprint] = 0.0
    assert np.isfinite(ridge).all()
    return ridge


def build_witness(data_dir: Path, footprint: np.ndarray, log=print) -> dict[str, np.ndarray]:
    """Non-topographic corroboration field in [0,1] (see module docstring)."""
    uk_raw = read_band(data_dir / "external/geodawn_extensions_u8.tif", 2)
    uk_missing = footprint & (uk_raw == 0)
    log(f"UK zero (missing) inside footprint: {int(uk_missing.sum())} / {int(footprint.sum())}")
    uk = uk_raw.astype(np.float32)
    del uk_raw
    gy, gx = np.gradient(uk)
    del uk
    uk_grad = np.hypot(gx, gy).astype(np.float32)
    del gy, gx
    uk_grad[uk_missing] = 0.0
    uk_n = norm(uk_grad, footprint)
    del uk_grad, uk_missing
    grav_n = norm(official_band(data_dir, 5), footprint)  # iso_grav_anom_slope
    w = np.maximum(uk_n, grav_n)
    w = ndimage.maximum_filter(w, size=5, mode="nearest").astype(np.float32)
    w[~footprint] = 0.0
    assert np.isfinite(w).all()
    return dict(witness=w, uk_grad_n=uk_n, grav_slope_n=grav_n)


def make_surface_x(scarp_n: np.ndarray, ridge: np.ndarray, witness: np.ndarray,
                   pied_soft: np.ndarray, experiment: str) -> np.ndarray:
    """Frozen X1/X2/X3 surfaces from registry/preregistration_x.json."""
    pied_f = np.float32(0.45) + np.float32(0.55) * pied_soft
    wit_f = WITNESS_FLOOR + WITNESS_GAIN * witness
    if experiment == "X1":
        s = ridge * wit_f * pied_f
    elif experiment == "X2":
        s = ridge * pied_f
    elif experiment == "X3":
        s = scarp_n * wit_f * pied_f
    else:
        raise ValueError(experiment)
    return np.clip(np.nan_to_num(s, nan=0.0), 0.0, 1.0).astype(np.float32)
