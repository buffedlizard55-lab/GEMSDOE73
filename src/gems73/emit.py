"""GEMSDOE73 — Emission & Submodular DTI Allocation Module.

Exports:
  - ``calibrate_1d_trace_posterior``, ``peak_nms_emit``, ``submodular_dti_emit`` (GEMSDOE73
    Cross-Drainage 2D Dilated U-Net + H73-M Piedmont Co-Kriging exact 300 m submodular lanes)
  - ``greedy_dots`` (compatibility emitter for earlier GEMSDOE73 ablation tests)
"""
from __future__ import annotations

import heapq
import math
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import metric  # noqa: E402

_DISK = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if (dy * dy + dx * dx) ** 0.5 < 2.5]


def greedy_dots(
    surface: np.ndarray,
    allowed: np.ndarray,
    budget: int = 37654,
    pool: int = 600_000,
    min_dist: float = 2.5,
) -> np.ndarray:
    """Binary dot mask: top-``pool`` allowed pixels greedily accepted at >=``min_dist`` px spacing."""
    surf = np.asarray(surface, np.float32)
    idx = np.flatnonzero(allowed)
    if idx.size == 0:
        return np.zeros(surface.shape, bool)
    vals = surf.ravel()[idx]
    if idx.size > pool:
        part = np.argpartition(vals, idx.size - pool)[idx.size - pool :]
        idx, vals = idx[part], vals[part]
    order = np.lexsort((idx, -vals))
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
    """Select exact ``n_dots`` binary 1.0 pixels via 7x7 peak NMS (fallback 5x5 -> 3x3 -> 1x1)."""
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
        is_peak = avail & (cur == maximum_filter(cur, size=win, mode="constant", cval=-3.0)) if win > 1 else avail
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
    fp_penalty_weight: float = 0.0,
    min_spacing_px: float = 0.0,
    candidate_pool: int = 850_000,
) -> np.ndarray:
    """Exact lazy-greedy Minoux submodular maximizer of expected 300 m kernel coverage."""
    H, W = prob.shape
    pad = max(3, int(math.ceil(min_spacing_px)) + 1)
    q_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    q_pad[pad : pad + H, pad : pad + W] = np.clip(np.where(np.isfinite(prob), prob, 0.0), 0.0, 1.0)
    cov_pad = np.zeros_like(q_pad)
    blocked_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    blk_offsets: list[tuple[int, int]] = []
    if min_spacing_px > 0.0:
        r_blk = int(math.ceil(min_spacing_px))
        for by in range(-r_blk, r_blk + 1):
            for bx in range(-r_blk, r_blk + 1):
                if math.hypot(by, bx) < min_spacing_px:
                    blk_offsets.append((by, bx))

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

    heap: list[tuple[float, int]] = [(-u_vals[i], i) for i in range(len(u_vals))]
    heapq.heapify(heap)

    out = np.zeros((H, W), dtype=np.float32)
    selected = 0

    while selected < n_dots and heap:
        neg_upper, i = heapq.heappop(heap)
        cy = ys[i]
        cx = xs[i]
        if blocked_pad[cy, cx]:
            continue
        gain = 0.0
        for m in range(n_off):
            ny = cy + dy[m]
            nx = cx + dx[m]
            k_m = kw[m]
            cur_c = cov_pad[ny, nx]
            if k_m > cur_c:
                gain += q_pad[ny, nx] * (k_m - cur_c)
        exact_u = gain - pens[i]

        if not heap or (-exact_u <= heap[0][0] + 1e-15):
            out[cy - pad, cx - pad] = 1.0
            blocked_pad[cy, cx] = True
            for by, bx in blk_offsets:
                blocked_pad[cy + by, cx + bx] = True
            for m in range(n_off):
                ny = cy + dy[m]
                nx = cx + dx[m]
                k_m = kw[m]
                if k_m > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = k_m
            selected += 1
        else:
            heapq.heappush(heap, (-exact_u, i))

    if selected < n_dots:
        rem_mask = allowed_mask & (out < 0.5) & (~blocked_pad[pad : pad + H, pad : pad + W])
        rem_idx = np.flatnonzero(rem_mask)
        rem_scores = u0.ravel()[rem_idx]
        order = np.argsort(-rem_scores)
        for idx_flat in rem_idx[order].tolist():
            if selected >= n_dots:
                break
            ry = idx_flat // W + pad
            rx = idx_flat % W + pad
            if blocked_pad[ry, rx]:
                continue
            out[ry - pad, rx - pad] = 1.0
            blocked_pad[ry, rx] = True
            for by, bx in blk_offsets:
                blocked_pad[ry + by, rx + bx] = True
            selected += 1

    assert int((out > 0.5).sum()) == int(n_dots), f"Expected {n_dots}, got {int((out > 0.5).sum())}"
    return out


def submodular_dti_dots(
    weight_surface: np.ndarray,
    allowed_mask: np.ndarray,
    scored_domain: np.ndarray | None = None,
    budget: int = 37654,
    min_dist: float = 2.6,
    candidate_pool: int = 320_000,
) -> np.ndarray:
    """Lazy-greedy maximization of expected 300 m Tversky kernel coverage F(S) = sum_g w(g) max_{x in S} K(x, g)."""
    res = submodular_dti_emit(
        weight_surface,
        allowed_mask,
        n_dots=budget,
        fp_penalty_weight=0.0,
        min_spacing_px=min_dist,
        candidate_pool=candidate_pool,
    )
    return res > 0.5


def calibrate_1d_trace_posterior(
    prob_2d: np.ndarray,
    fp: np.ndarray,
    gamma: float = 1.15,
) -> np.ndarray:
    """Sharpen broad 2D slope blobs into true 1D fault-trace posterior density."""
    p = np.where(fp & np.isfinite(prob_2d), np.clip(prob_2d, 0.0, 1.0), 0.0).astype(np.float32)
    bg4 = gaussian_filter(p, sigma=4.0, mode="constant", cval=0.0)
    spine_ratio = np.clip((p - 0.52 * bg4) / (0.48 * p + 1e-4), 0.0, 1.0)
    trace_post = (np.power(p, gamma) * (0.42 + 0.58 * spine_ratio)).astype(np.float32)
    return np.where(fp, np.clip(trace_post, 0.0, 1.0), 0.0).astype(np.float32)


__all__ = [
    "calibrate_1d_trace_posterior",
    "greedy_dots",
    "peak_nms_emit",
    "submodular_dti_dots",
    "submodular_dti_emit",
]
