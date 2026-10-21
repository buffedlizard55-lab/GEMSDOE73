"""Official Distance-Weighted Tversky Index (DTI) for the DOE GEMS Prize.

Verified from official competition problem description
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric
and organizer forum clarification Thread 11516.

Formulation:
  Triangular kernel k(d) = max(1 - d/R, 0), R = 300 m = 3 px at 100 m
  TP_w = sum_{g in G} max_{x:d(x,g) <=R} p(x) * k(d)
  FP_w = sum_{x:p(x)>0} p(x) * [1 - max_{g} k(d(x,g))]
  FN_w = |G| - TP_w
  DTI(α=0.2, β=0.8) = TP_w / (TP_w + 0.2*FP_w + 0.8*FN_w)
                 = T / (0.2*(T + S - M) + 0.8*|G|)
  with T=TP_w (sum over truth), S=sum p, M=sum_x p(x)*max_g k(d) (sum over
  dots). T and M are NOT interchangeable (see vendor/gems57/metric.py);
  an earlier revision collapsed them — corrected session-2, code unaffected
  (dti_exact/dti_binary compute TP/FP/FN directly).

Worked example TP=3.00 FP=1.89 FN=2.00 → 0.60 reproduced in tests.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
EPS = 1e-12


def kernel(d, radius: float = RADIUS_PX):
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / radius, 0.0)


def _offsets(radius: float = RADIUS_PX):
    r = int(np.ceil(radius))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = float(kernel(np.hypot(dy, dx), radius))
            if k > 0:
                out.append((dy, dx, k))
    return out

_OFFS = _offsets()


def dti_exact(pred, truth, valid=None, known=None, alpha=ALPHA, beta=BETA):
    pred = np.asarray(pred, float)
    truth = np.asarray(truth, bool)
    valid = np.ones(pred.shape, bool) if valid is None else np.asarray(valid, bool)
    known = np.zeros(pred.shape, bool) if known is None else np.asarray(known, bool)
    active = valid & ~known
    if pred.shape != truth.shape or valid.shape != pred.shape:
        raise ValueError("shape mismatch")
    inside = pred[active]
    if not np.isfinite(inside).all() or (inside < 0).any() or (inside > 1).any():
        raise ValueError("predictions inside scored domain must be finite in [0,1]")
    p = np.where(active & np.isfinite(pred), pred, 0.0).astype(np.float64)
    g = active & (truth > 0)
    n = int(g.sum())
    if n == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0)
    yy, xx = np.nonzero(g)
    credit = np.zeros(n, dtype=np.float64)
    H, W = p.shape
    for dy, dx, k in _OFFS:
        ny, nx = yy + dy, xx + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        credit[ok] = np.maximum(credit[ok], p[ny[ok], nx[ok]] * k)
    tp = float(credit.sum())
    fn = float(n) - tp
    d = distance_transform_edt(~g)
    fp = float((p * (1.0 - kernel(d))).sum())
    dti = tp / (tp + alpha * fp + beta * fn + EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n, dti=float(dti), coverage=tp / n if n else 0)


def dti_binary(pred_bool, truth, valid=None, known=None, alpha=ALPHA, beta=BETA):
    pred_bool = np.asarray(pred_bool, bool)
    truth = np.asarray(truth, bool)
    valid_ = np.ones(pred_bool.shape, bool) if valid is None else np.asarray(valid, bool)
    known_ = np.zeros(pred_bool.shape, bool) if known is None else np.asarray(known, bool)
    active = valid_ & ~known_
    p = pred_bool & active
    g = truth & active
    n = int(g.sum())
    if n == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0)
    if not p.any():
        return dict(tp=0.0, fp=0.0, fn=float(n), n_truth=n, dti=0.0)
    dp = distance_transform_edt(~p)
    tp = float(kernel(dp[g]).sum())
    fn = float(n) - tp
    dg = distance_transform_edt(~g)
    fp = float((1.0 - kernel(dg[p])).sum())
    dti = tp / (tp + alpha * fp + beta * fn + EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n, dti=float(dti))


def marginal_bar(current_dti: float, alpha: float = ALPHA) -> float:
    """k > alpha*DTI required for an added dot to improve DTI."""
    return alpha * current_dti


def dti_fast(pred, truth, valid=None, known=None, alpha=ALPHA, beta=BETA) -> float:
    """Fast scalar DTI wrapper; returns 1.0 when both truth and pred are empty."""
    pred_arr = np.asarray(pred, float)
    truth_arr = np.asarray(truth, bool)
    if not truth_arr.any():
        return 1.0 if not (pred_arr > 0).any() else 0.0
    return float(dti_exact(pred_arr, truth_arr, valid=valid, known=known, alpha=alpha, beta=beta)["dti"])

