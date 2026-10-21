"""Dotted emission algorithms for GEMSDOE73 (H73-1 and H73-M).

Provides:
  1. `greedy_dots`: Score-ordered greedy selection with 2.5 px minimum spacing (H73-1).
  2. `peak_nms_emit`: Deterministic 7x7 local-maximum suppression baseline (M1 & M2).
  3. `submodular_dti_emit`: Exact lazy-greedy Minoux submodular maximizer of expected
     marginal Distance-Weighted Tversky Index (DTI) coverage over the official R=300 m
     (3.0 px) triangular kernel k(d) = max(1 - d/3, 0) with optional inter-dot spacing
     guard (M3).
"""
from __future__ import annotations

import heapq
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import maximum_filter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import metric  # noqa: E402

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


def peak_nms_emit(
    surface: np.ndarray,
    allowed_mask: np.ndarray,
    n_dots: int = 37654,
) -> np.ndarray:
    """Select exact `n_dots` binary 1.0 pixels via 7x7 peak NMS (fallback 5x5 -> 3x3 -> 1x1)."""
    s = np.where(allowed_mask & np.isfinite(surface), surface.astype(np.float64), -1.0)
    yy, xx = np.indices(surface.shape, dtype=np.float64)
    s_tie = s + 1e-12 * (yy * 0.00031 + xx * 0.00017)

    out = np.zeros(surface.shape, dtype=np.float32)
    remaining = int(n_dots)
    avail = allowed_mask & (surface > 0)

    for win in (7, 5, 3, 1):
        if remaining <= 0:
            break
        cur = np.where(avail, s_tie, -2.0)
        if win > 1:
            is_peak = avail & (cur == maximum_filter(cur, size=win, mode="constant", cval=-3.0))
        else:
            is_peak = avail
        cand_idx = np.flatnonzero(is_peak)
        if cand_idx.size == 0:
            continue
        scores = s_tie.ravel()[cand_idx]
        if cand_idx.size > remaining:
            top = np.argpartition(scores, -remaining)[-remaining:]
            top = top[np.argsort(-scores[top])]
            chosen = cand_idx[top]
        else:
            chosen = cand_idx[np.argsort(-scores)]
        out.ravel()[chosen] = 1.0
        avail.ravel()[chosen] = False
        remaining -= int(chosen.size)

    assert int((out > 0.5).sum()) == int(n_dots)
    return out


def submodular_dti_emit(
    prob: np.ndarray,
    allowed_mask: np.ndarray,
    n_dots: int = 37654,
    fp_penalty_weight: float = 0.06,
    candidate_pool: int = 850_000,
    min_spacing_px: float = 0.0,
) -> np.ndarray:
    """Exact lazy-greedy Minoux submodular maximizer of expected DTI kernel coverage.

    For each cell `g` with calibrated posterior `q(g) >= 0`, adding dot `x` yields
    marginal expected weighted true-positive gain:
        dTP(x | S) = sum_{m: d_m < 3} q(x + delta_m) * max(0, k_m - C_S(x + delta_m))
    penalized by `fp_penalty_weight * (1 - max_m q(x + delta_m) * k_m)`.
    If `min_spacing_px > 0`, also enforces a hard minimum Euclidean distance between
    accepted dots so high-posterior ridges are not over-packed at sub-kernel spacing.
    """
    H, W = prob.shape
    pad = 3
    q_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    q_pad[pad : pad + H, pad : pad + W] = np.clip(
        np.where(np.isfinite(prob), prob, 0.0), 0.0, 1.0
    )
    cov_pad = np.zeros_like(q_pad)
    blocked_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool) if min_spacing_px > 0 else None
    block_offs = []
    if min_spacing_px > 0:
        r_blk = int(np.ceil(min_spacing_px))
        block_offs = [
            (by, bx)
            for by in range(-r_blk, r_blk + 1)
            for bx in range(-r_blk, r_blk + 1)
            if (by * by + bx * bx) ** 0.5 < min_spacing_px
        ]

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    init_tp = np.zeros((H, W), dtype=np.float64)
    q_self = np.zeros((H, W), dtype=np.float64)
    for oy, ox, k_val in zip(dy, dx, kw):
        sub = q_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W]
        init_tp += k_val * sub
        np.maximum(q_self, k_val * sub, out=q_self)

    pen_arr = fp_penalty_weight * (1.0 - q_self)
    u0 = init_tp - pen_arr

    valid_idx = np.flatnonzero(allowed_mask & (init_tp > 0))
    if valid_idx.size > candidate_pool:
        u_sub = u0.ravel()[valid_idx]
        keep = np.argpartition(u_sub, -candidate_pool)[-candidate_pool:]
        valid_idx = valid_idx[keep]

    ys = (valid_idx // W + pad).tolist()
    xs = (valid_idx % W + pad).tolist()
    pens = pen_arr.ravel()[valid_idx].tolist()
    u_vals = u0.ravel()[valid_idx].tolist()

    heap = [(-u_vals[i], i, 0) for i in range(len(ys))]
    heapq.heapify(heap)

    out = np.zeros((H, W), dtype=np.float32)
    selected = 0
    step = 0

    while selected < n_dots and heap:
        neg_u, idx, last_step = heapq.heappop(heap)
        cy = ys[idx]
        cx = xs[idx]
        if blocked_pad is not None and blocked_pad[cy, cx]:
            continue
        if last_step == step:
            out[cy - pad, cx - pad] = 1.0
            selected += 1
            step += 1
            for m in range(n_off):
                ny = cy + dy[m]
                nx = cx + dx[m]
                kv = kw[m]
                if kv > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = kv
            if blocked_pad is not None:
                for by, bx in block_offs:
                    blocked_pad[cy + by, cx + bx] = True
        else:
            gain = 0.0
            for m in range(n_off):
                ny = cy + dy[m]
                nx = cx + dx[m]
                rem = kw[m] - cov_pad[ny, nx]
                if rem > 0.0:
                    gain += q_pad[ny, nx] * rem
            new_u = gain - pens[idx]
            heapq.heappush(heap, (-new_u, idx, step))

    if selected < n_dots:
        rem_idx = np.flatnonzero(allowed_mask & (out < 0.5))
        rem_order = rem_idx[np.argsort(u0.ravel()[rem_idx])[::-1]]
        for flat_i in rem_order:
            if selected >= n_dots:
                break
            r0 = int(flat_i // W)
            c0 = int(flat_i % W)
            cy = r0 + pad
            cx = c0 + pad
            if blocked_pad is not None and blocked_pad[cy, cx]:
                continue
            out[r0, c0] = 1.0
            selected += 1
            if blocked_pad is not None:
                for by, bx in block_offs:
                    blocked_pad[cy + by, cx + bx] = True

    assert int((out > 0.5).sum()) == int(n_dots), f"Expected {n_dots}, got {int((out > 0.5).sum())}"
    return out
