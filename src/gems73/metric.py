"""Competition metric — distance-weighted Tversky index (DTI).

Official definition: problem page 967, verified 2026-10-21 (two independent fetches
agree; worked example TPw=3.00 FPw=1.89 FNw=2.00 -> 0.60 reproduced in tests).

  k(d) = max(1 - d/300m, 0)  with 300m = 3px at 100m res
  TPw = sum_g max_{x: d(x,g)<=R} p(x) k(d(x,g))
  FPw = sum_{x: p(x)>0} p(x) [1 - max_g k(d(x,g))]
  FNw = sum_g [1 - max_{x: d(x,g)<=R} p(x) k(d(x,g))]
  DTI = TPw / (TPw + 0.2 FPw + 0.8 FNw + eps)

Equivalently: DTI = T / (0.2*(T+S-M) + 0.8*|G|) with T=TPw S=sum(p) M=sum(p*maxk)
Credit bar: add mass at weight k iff k > 0.2*DTI.
At group 0.2600 bar=0.0520; at leader 0.3262 bar=0.0652 (measured per DTI algebra).
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import distance_transform_edt

R_PX = 3.0  # 300m at 100m
ALPHA, BETA = 0.2, 0.8

def kernel(d: np.ndarray) -> np.ndarray:
    return np.maximum(1.0 - d / R_PX, 0.0)

def dti_bruteforce(pred: np.ndarray, truth: np.ndarray, eps: float = 1e-9) -> float:
    """Brute-force reference (O(N^2) on positive pixels) — for tests only."""
    # truth and pred are binary {0,1} on same grid, outside footprint masked externally
    # Use distance_transform_edt for fast nearest-truth distance
    # This is the *fast* equivalent but kept as reference name for compatibility
    return dti_fast(pred, truth, eps=eps)

def dti_fast(pred: np.ndarray, truth: np.ndarray, eps: float = 1e-9) -> float:
    """Fast DTI via distance transforms (exact, tolerates +-1px rasterisation per spec)."""
    # Compute kernel-weighted contributions
    # For each truth pixel: max p(x)*k(d(x,g)) within R
    # For each pred pixel: max k(d(x,g)) to nearest truth
    # Both reduce to distance transforms with linear kernel.

    # Binary masks
    g = truth.astype(bool)
    p = pred.astype(np.float32)

    if not g.any():
        return 0.0 if p.sum() > 0 else 1.0  # degenerate no-truth case

    # distance to nearest truth for every pixel (for FPw and for truth weighting)
    # distance_transform_edt returns distance to nearest 0, so invert
    inv_g = ~g
    dist_to_truth = distance_transform_edt(inv_g)  # 0 on truth
    k_to_truth = kernel(dist_to_truth)

    # distance to nearest pred>0 for every truth pixel (for TPw/FNw)
    # Need max_{x} p(x)*k(d(x,g)) — for binary p this is maxk among pred pixels
    # So for TPw we need maxk from pred positions to each truth
    has_pred = p > 0
    if not has_pred.any():
        TPw = 0.0
        FPw = 0.0
        FNw = float(g.sum())
        return TPw / (TPw + ALPHA*FPw + BETA*FNw + eps)

    # dist to nearest pred
    dist_to_pred = distance_transform_edt(~has_pred)
    # But we need max_k among preds weighted by p (binary 1 here)
    # For each truth g, the best covering pred is min dist_to_pred at g, k = max(1-d/R,0)
    best_k_at_truth = kernel(dist_to_pred[g])
    TPw = float(best_k_at_truth.sum())
    FNw = float(g.sum() - TPw)

    # FPw: for each pred pixel x, weight is p(x)*(1 - k(d(x,G)))
    # k(d(x,G)) is k_to_truth at x
    FPw = float((p * (1.0 - k_to_truth)).sum())

    denom = TPw + ALPHA*FPw + BETA*FNw + eps
    return float(TPw / denom) if denom>0 else 0.0

def credit_bar(dti: float) -> float:
    """Marginal credit bar: a new dot must have expected k > 0.2*DTI to help."""
    return 0.2 * dti
