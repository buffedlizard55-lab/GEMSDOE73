"""Frozen dotted emission (registry/preregistration.json).

Score-ordered greedy selection with a 2.5 px minimum spacing.  Rationale
(official metric, alpha=0.2, R=3 px): a dot spacing of ~2.5 px leaves any
point of a covered trace within ~1.25 px of a dot (kernel credit >= ~0.58)
while paying the 0.2-per-dot false-positive tax only once per ~6 px of
trace instead of once per pixel.
"""
from __future__ import annotations

import numpy as np

# offsets with Euclidean distance < 2.5 px (the blocking disk, incl. centre)
_DISK = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3)
         if (dy * dy + dx * dx) ** 0.5 < 2.5]


def greedy_dots(surface: np.ndarray, allowed: np.ndarray, budget: int = 37654,
                pool: int = 600_000) -> np.ndarray:
    """Binary dot mask: top-`pool` allowed pixels by surface (ties by flat
    index), greedily accepted if no accepted dot within <2.5 px."""
    surf = np.asarray(surface, np.float32)
    idx = np.flatnonzero(allowed)
    if idx.size == 0:
        return np.zeros(surface.shape, bool)
    vals = surf.ravel()[idx]
    if idx.size > pool:
        part = np.argpartition(vals, idx.size - pool)[idx.size - pool:]
        idx, vals = idx[part], vals[part]
    order = np.lexsort((idx, -vals))  # surface desc, flat index asc
    idx = idx[order]
    h, w = surface.shape
    ys = (idx // w).astype(np.int64)
    xs = (idx % w).astype(np.int64)
    blocked = np.zeros(surface.shape, bool)
    dots = np.zeros(surface.shape, bool)
    n = 0
    for y, x in zip(ys.tolist(), xs.tolist()):
        if blocked[y, x]:
            continue
        dots[y, x] = True
        n += 1
        if n >= budget:
            break
        for dy, dx in _DISK:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
    return dots
