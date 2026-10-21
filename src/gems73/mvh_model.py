"""H73-MVH Dual Metric-Direct LightGBM Ensemble & Two-Head R=300 m Submodular DTI Allocator.

Strict 0-bit fold isolation guarantee:
  For every holdout fold ``fold_q``, ``fit_and_predict_for_single_fold(..., fold_q)`` receives ONLY
  ``(X_stat, fp, fold_q["visible"], fold_q["masked_known"], fold_q["block"])`` — ``fold_q["withheld"]``
  is NEVER passed to or accessible inside any training, calibration, or allocation routine.
  To prevent in-sample tree confidence on training pixels from stealing global dot budget away from
  the held-out block ``fold_q["block"]``, training-region posteriors are CDF-aligned to the held-out
  block marginal posterior distribution using only unlabelled predictions.
"""
from __future__ import annotations

import gc
import heapq
import sys
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label as ndi_label, maximum_filter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import metric  # noqa: E402
from .mvh_features import STRUCT3, compute_visible_network_mechanics  # noqa: E402


def align_in_sample_to_oof_cdf(
    scores_fp: np.ndarray,
    is_oof_fp: np.ndarray,
) -> np.ndarray:
    """Align marginal score quantiles on training pixels to the held-out ``is_oof_fp`` marginal CDF
    so global 37,654-dot allocation suffers zero in-sample confidence inflation."""
    out = scores_fp.astype(np.float32, copy=True)
    ins = ~is_oof_fp
    if is_oof_fp.sum() > 500 and ins.sum() > 500:
        qg = np.linspace(0.0, 1.0, 2001)
        sq = np.quantile(scores_fp[ins], qg)
        dq = np.quantile(scores_fp[is_oof_fp], qg)
        out[ins] = np.interp(scores_fp[ins], sq, dq).astype(np.float32)
    return out


def align_lidar_gap_quantiles(
    prob_fp: np.ndarray,
    has_lidar_fp: np.ndarray,
) -> np.ndarray:
    """Align non-LiDAR gap-tile posteriors to the LiDAR marginal quantile distribution."""
    out = prob_fp.astype(np.float32, copy=True)
    m_lid = has_lidar_fp
    m_gap = ~has_lidar_fp
    if m_lid.sum() > 500 and m_gap.sum() > 500:
        qg = np.linspace(0.0, 1.0, 2001)
        sq = np.quantile(prob_fp[m_gap], qg)
        dq = np.quantile(prob_fp[m_lid], qg)
        out[m_gap] = np.interp(prob_fp[m_gap], sq, dq).astype(np.float32)
    return out


def make_nested_hide_draws(
    train_faults_2d: np.ndarray,
    fp: np.ndarray,
    hide_fracs: tuple[float, ...] = (0.45, 0.45, 0.22, 0.22),
    buffer_px: float = 3.0,
    seed: int = 7300,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create whole-component nested hide draws ``(sub_visible_2d, sub_withheld_2d)`` with
    a ``3.0 px`` feature collar across sparse (45%) and dense (22%) hide regimes."""
    comp, count = ndi_label(train_faults_2d & fp, structure=STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=count + 1)
    ids = np.flatnonzero(sizes[1:] > 0) + 1
    draws: list[tuple[np.ndarray, np.ndarray]] = []
    total_px = float((train_faults_2d & fp).sum())
    for k, hfrac in enumerate(hide_fracs):
        rng = np.random.default_rng(seed + 97 * k)
        perm = rng.permutation(ids)
        cum = np.cumsum(sizes[perm])
        cut = int(np.searchsorted(cum, hfrac * total_px)) + 1
        chosen = perm[: min(cut, perm.size)]
        sub_hid = np.isin(comp, chosen) & train_faults_2d & fp
        collar = distance_transform_edt(~sub_hid) <= buffer_px
        sub_vis = train_faults_2d & (~collar) & fp
        draws.append((sub_vis, sub_hid))
    return draws


def _fit_dual_heads(
    X_tr_trace: np.ndarray,
    y_tr_trace: np.ndarray,
    w_tr_trace: np.ndarray,
    X_tr_kern: np.ndarray,
    y_tr_kern: np.ndarray,
    w_tr_kern: np.ndarray,
    seed: int,
) -> tuple[lgb.LGBMClassifier, lgb.LGBMRegressor]:
    clf = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=320,
        num_leaves=63,
        learning_rate=0.055,
        min_child_samples=55,
        subsample_for_bin=180_000,
        colsample_bytree=0.82,
        subsample=0.85,
        subsample_freq=1,
        reg_alpha=1.5,
        reg_lambda=3.0,
        n_jobs=-1,
        random_state=seed,
        verbose=-1,
    )
    clf.fit(X_tr_trace, y_tr_trace, sample_weight=w_tr_trace)

    reg_k = lgb.LGBMRegressor(
        objective="cross_entropy",
        n_estimators=280,
        num_leaves=47,
        learning_rate=0.055,
        min_child_samples=70,
        subsample_for_bin=180_000,
        colsample_bytree=0.82,
        subsample=0.85,
        subsample_freq=1,
        reg_alpha=1.5,
        reg_lambda=3.5,
        n_jobs=-1,
        random_state=seed + 500,
        verbose=-1,
    )
    reg_k.fit(X_tr_kern, y_tr_kern, sample_weight=w_tr_kern)
    return clf, reg_k


def fit_and_predict_static_fold(
    X_stat: np.memmap,
    fp: np.ndarray,
    visible_2d: np.ndarray,
    block_2d: np.ndarray,
    aux: dict[str, np.ndarray],
    seed: int = 7310,
) -> tuple[np.ndarray, np.ndarray]:
    """0-bit leak-free single-fold fit & predict for Exp 73-1 (static physical + vent stack only)."""
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    slope_fp = aux["slope_fp"]
    has_lidar_fp = aux["has_lidar_fp"]
    pied_w = (1.0 + 1.15 * np.clip(1.0 - slope_fp / 10.0, 0.0, 1.0)).astype(np.float32)

    # Exclude entire held-out block PLUS a 30 px (3.0 km) spatial buffer around it!
    excl_2d = binary_dilation(block_2d, iterations=30)
    in_tr = (~excl_2d).ravel()[fp_idx]
    is_oof = block_2d.ravel()[fp_idx]

    d_fp = distance_transform_edt(~(visible_2d & fp)).ravel()[fp_idx].astype(np.float32)
    rng = np.random.default_rng(seed)

    pos_idx = np.flatnonzero(in_tr & (d_fp == 0.0))
    neg_pool = np.flatnonzero(in_tr & (d_fp > 3.5))
    neg_a = np.sort(rng.choice(neg_pool, size=min(240_000, neg_pool.size), replace=False))

    idx_a = np.concatenate([pos_idx, neg_a])
    y_a = np.concatenate([np.ones(pos_idx.size, np.int32), np.zeros(neg_a.size, np.int32)])
    w_a = np.concatenate([pied_w[pos_idx], np.ones(neg_a.size, np.float32)])
    X_a = np.ascontiguousarray(X_stat[:, idx_a].T, dtype=np.float32)

    halo_pool = np.flatnonzero(in_tr & (d_fp < 3.0))
    halo_idx = halo_pool if halo_pool.size <= 160_000 else np.sort(rng.choice(halo_pool, 160_000, replace=False))
    neg_b = np.sort(rng.choice(neg_pool, size=min(190_000, neg_pool.size), replace=False))
    idx_b = np.concatenate([halo_idx, neg_b])
    y_b = np.concatenate([np.clip(1.0 - d_fp[halo_idx] / 3.0, 0.0, 1.0), np.zeros(neg_b.size, np.float32)])
    w_b = np.concatenate([pied_w[halo_idx], np.ones(neg_b.size, np.float32)])
    X_b = np.ascontiguousarray(X_stat[:, idx_b].T, dtype=np.float32)

    clf, reg_k = _fit_dual_heads(X_a, y_a, w_a, X_b, y_b, w_b, seed=seed)
    del X_a, X_b, y_a, y_b, w_a, w_b
    gc.collect()

    p_tr = np.zeros(n_fp, dtype=np.float32)
    q_kn = np.zeros(n_fp, dtype=np.float32)
    chunk = 450_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        xb = np.ascontiguousarray(X_stat[:, s:e].T, dtype=np.float32)
        p_tr[s:e] = clf.predict_proba(xb)[:, 1].astype(np.float32)
        q_kn[s:e] = np.clip(reg_k.predict(xb), 0.0, 1.0).astype(np.float32)
    del clf, reg_k
    gc.collect()

    p_tr = align_in_sample_to_oof_cdf(align_lidar_gap_quantiles(p_tr, has_lidar_fp), is_oof)
    q_kn = align_in_sample_to_oof_cdf(align_lidar_gap_quantiles(q_kn, has_lidar_fp), is_oof)
    return p_tr, q_kn


def fit_and_predict_nested_bridge_fold(
    X_stat: np.memmap,
    fp: np.ndarray,
    visible_2d: np.ndarray,
    block_2d: np.ndarray,
    aux: dict[str, np.ndarray],
    seed: int = 7350,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """0-bit leak-free single-fold fit & predict for Exp 73-2 & Exp 73-3.

    Returns ``(p_tr_fp, q_kn_fp, mech_vis_fp, imp_clf, imp_reg)`` where:
      - ``clf, reg_k`` are trained strictly outside ``binary_dilation(block_2d, 30)`` on K=4 nested
        whole-component hide draws of ``visible_2d & (~excl_2d)``.
      - ``mech_vis_fp`` is ``compute_visible_network_mechanics(visible_2d, fp, aux)``.
      - Training-region predictions are CDF-aligned to the held-out ``block_2d`` distribution so
        global dot allocation suffers zero in-sample confidence inflation.
    """
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    n_stat = X_stat.shape[0]
    n_tot = n_stat + 12
    slope_fp = aux["slope_fp"]
    has_lidar_fp = aux["has_lidar_fp"]
    pied_w = (1.0 + 1.15 * np.clip(1.0 - slope_fp / 10.0, 0.0, 1.0)).astype(np.float32)

    excl_2d = binary_dilation(block_2d, iterations=30)
    in_tr = (~excl_2d).ravel()[fp_idx]
    is_oof = block_2d.ravel()[fp_idx]

    # Restrict visible training faults strictly to the training domain outside the 3.0 km buffer!
    train_vis_only = visible_2d & (~excl_2d) & fp
    nested = make_nested_hide_draws(
        train_vis_only,
        fp,
        hide_fracs=(0.45, 0.45, 0.22, 0.22),
        buffer_px=3.0,
        seed=seed,
    )

    tr_xa, tr_ya, tr_wa = [], [], []
    tr_xb, tr_yb, tr_wb = [], [], []
    rng = np.random.default_rng(seed + 17)

    for sub_vis, sub_hid in nested:
        mech_d = compute_visible_network_mechanics(sub_vis, fp, aux)
        d_hid = distance_transform_edt(~(sub_hid & fp)).ravel()[fp_idx].astype(np.float32)
        d_sv = distance_transform_edt(~(sub_vis & fp)).ravel()[fp_idx].astype(np.float32)

        # Match evaluation domain exactly: candidate domain is clean outside sub_vis 2.5 px collar!
        act_tr = in_tr & (d_sv > 2.5)
        p_i = np.flatnonzero(act_tr & (d_hid == 0.0))
        n_pool = np.flatnonzero(act_tr & (d_hid > 3.5))
        n_i = np.sort(rng.choice(n_pool, size=min(62_000, n_pool.size), replace=False))

        ia = np.concatenate([p_i, n_i])
        xa = np.empty((ia.size, n_tot), dtype=np.float32)
        xa[:, :n_stat] = X_stat[:, ia].T
        xa[:, n_stat:] = mech_d[:, ia].T
        tr_xa.append(xa)
        tr_ya.append(np.concatenate([np.ones(p_i.size, np.int32), np.zeros(n_i.size, np.int32)]))
        tr_wa.append(np.concatenate([pied_w[p_i], np.ones(n_i.size, np.float32)]))

        h_pool = np.flatnonzero(act_tr & (d_hid < 3.0))
        h_i = h_pool if h_pool.size <= 45_000 else np.sort(rng.choice(h_pool, 45_000, replace=False))
        nb_i = np.sort(rng.choice(n_pool, size=min(55_000, n_pool.size), replace=False))
        ib = np.concatenate([h_i, nb_i])
        xb = np.empty((ib.size, n_tot), dtype=np.float32)
        xb[:, :n_stat] = X_stat[:, ib].T
        xb[:, n_stat:] = mech_d[:, ib].T
        tr_xb.append(xb)
        tr_yb.append(np.concatenate([np.clip(1.0 - d_hid[h_i] / 3.0, 0.0, 1.0), np.zeros(nb_i.size, np.float32)]))
        tr_wb.append(np.concatenate([pied_w[h_i], np.ones(nb_i.size, np.float32)]))
        del mech_d

    X_a = np.concatenate(tr_xa, axis=0)
    y_a = np.concatenate(tr_ya, axis=0)
    w_a = np.concatenate(tr_wa, axis=0)
    del tr_xa, tr_ya, tr_wa

    X_b = np.concatenate(tr_xb, axis=0)
    y_b = np.concatenate(tr_yb, axis=0)
    w_b = np.concatenate(tr_wb, axis=0)
    del tr_xb, tr_yb, tr_wb
    gc.collect()

    clf, reg_k = _fit_dual_heads(X_a, y_a, w_a, X_b, y_b, w_b, seed=seed + 31)
    imp_clf = clf.booster_.feature_importance(importance_type="gain").astype(np.float64)
    imp_reg = reg_k.booster_.feature_importance(importance_type="gain").astype(np.float64)
    del X_a, X_b, y_a, y_b, w_a, w_b
    gc.collect()

    mech_vis = compute_visible_network_mechanics(visible_2d, fp, aux)
    p_tr = np.zeros(n_fp, dtype=np.float32)
    q_kn = np.zeros(n_fp, dtype=np.float32)
    chunk = 420_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        xb = np.empty((e - s, n_tot), dtype=np.float32)
        xb[:, :n_stat] = X_stat[:, s:e].T
        xb[:, n_stat:] = mech_vis[:, s:e].T
        p_tr[s:e] = clf.predict_proba(xb)[:, 1].astype(np.float32)
        q_kn[s:e] = np.clip(reg_k.predict(xb), 0.0, 1.0).astype(np.float32)

    del clf, reg_k
    gc.collect()

    p_tr = align_in_sample_to_oof_cdf(align_lidar_gap_quantiles(p_tr, has_lidar_fp), is_oof)
    q_kn = align_in_sample_to_oof_cdf(align_lidar_gap_quantiles(q_kn, has_lidar_fp), is_oof)
    return p_tr, q_kn, mech_vis, imp_clf, imp_reg


def fit_and_predict_production_oof(
    X_stat: np.memmap,
    fp: np.ndarray,
    full_catalogue_2d: np.ndarray,
    folds: list[dict[str, Any]],
    aux: dict[str, np.ndarray],
    seed_base: int = 7500,
    log=print,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Strict 4-quadrant out-of-fold full-footprint posterior prediction for live submission packaging.

    For each spatial quadrant ``fold["block"]``, trains strictly outside ``binary_dilation(block, 30)``
    on nested hide draws of ``full_catalogue_2d & (~excl)``, and predicts strictly on ``fold["block"]``
    using an ensemble of full-catalogue mechanics + 2 sparse sub-network draws so both gap bridges and
    junction-splay continuations fire cleanly across all 4 quadrants.
    """
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    n_stat = X_stat.shape[0]
    n_tot = n_stat + 12
    slope_fp = aux["slope_fp"]
    has_lidar_fp = aux["has_lidar_fp"]
    pied_w = (1.0 + 1.15 * np.clip(1.0 - slope_fp / 10.0, 0.0, 1.0)).astype(np.float32)

    mech_full = compute_visible_network_mechanics(full_catalogue_2d, fp, aux)
    sub_draws = make_nested_hide_draws(
        full_catalogue_2d, fp, hide_fracs=(0.18, 0.18), buffer_px=3.0, seed=seed_base + 900
    )
    mech_subs = [compute_visible_network_mechanics(sv, fp, aux) for sv, _ in sub_draws]

    prod_p = np.zeros(n_fp, dtype=np.float32)
    prod_q = np.zeros(n_fp, dtype=np.float32)
    imp_total = np.zeros(n_tot, dtype=np.float64)

    for q_id, fold in enumerate(folds):
        block_2d = fold["block"]
        excl_2d = binary_dilation(block_2d, iterations=30)
        in_tr = (~excl_2d).ravel()[fp_idx]
        oof_mask = block_2d.ravel()[fp_idx]

        train_cat = full_catalogue_2d & (~excl_2d) & fp
        nested = make_nested_hide_draws(
            train_cat, fp, hide_fracs=(0.40, 0.25, 0.20, 0.15), buffer_px=3.0, seed=seed_base + 77 * q_id
        )
        tr_xa, tr_ya, tr_wa = [], [], []
        tr_xb, tr_yb, tr_wb = [], [], []
        rng = np.random.default_rng(seed_base + 13 * q_id)

        for sub_vis, sub_hid in nested:
            mech_d = compute_visible_network_mechanics(sub_vis, fp, aux)
            d_hid = distance_transform_edt(~(sub_hid & fp)).ravel()[fp_idx].astype(np.float32)
            d_sv = distance_transform_edt(~(sub_vis & fp)).ravel()[fp_idx].astype(np.float32)
            act_tr = in_tr & (d_sv > 2.5)

            p_i = np.flatnonzero(act_tr & (d_hid == 0.0))
            n_pool = np.flatnonzero(act_tr & (d_hid > 3.5))
            n_i = np.sort(rng.choice(n_pool, size=min(62_000, n_pool.size), replace=False))
            ia = np.concatenate([p_i, n_i])
            xa = np.empty((ia.size, n_tot), dtype=np.float32)
            xa[:, :n_stat] = X_stat[:, ia].T
            xa[:, n_stat:] = mech_d[:, ia].T
            tr_xa.append(xa)
            tr_ya.append(np.concatenate([np.ones(p_i.size, np.int32), np.zeros(n_i.size, np.int32)]))
            tr_wa.append(np.concatenate([pied_w[p_i], np.ones(n_i.size, np.float32)]))

            h_pool = np.flatnonzero(act_tr & (d_hid < 3.0))
            h_i = h_pool if h_pool.size <= 45_000 else np.sort(rng.choice(h_pool, 45_000, replace=False))
            nb_i = np.sort(rng.choice(n_pool, size=min(55_000, n_pool.size), replace=False))
            ib = np.concatenate([h_i, nb_i])
            xb = np.empty((ib.size, n_tot), dtype=np.float32)
            xb[:, :n_stat] = X_stat[:, ib].T
            xb[:, n_stat:] = mech_d[:, ib].T
            tr_xb.append(xb)
            tr_yb.append(np.concatenate([np.clip(1.0 - d_hid[h_i] / 3.0, 0.0, 1.0), np.zeros(nb_i.size, np.float32)]))
            tr_wb.append(np.concatenate([pied_w[h_i], np.ones(nb_i.size, np.float32)]))
            del mech_d

        X_a = np.concatenate(tr_xa, axis=0)
        y_a = np.concatenate(tr_ya, axis=0)
        w_a = np.concatenate(tr_wa, axis=0)
        del tr_xa, tr_ya, tr_wa
        X_b = np.concatenate(tr_xb, axis=0)
        y_b = np.concatenate(tr_yb, axis=0)
        w_b = np.concatenate(tr_wb, axis=0)
        del tr_xb, tr_yb, tr_wb
        gc.collect()

        clf, reg_k = _fit_dual_heads(X_a, y_a, w_a, X_b, y_b, w_b, seed=seed_base + 41 * q_id)
        imp_total += clf.booster_.feature_importance(importance_type="gain") + reg_k.booster_.feature_importance(
            importance_type="gain"
        )
        del X_a, X_b, y_a, y_b, w_a, w_b
        gc.collect()

        val_idx = np.flatnonzero(oof_mask)
        chunk = 420_000
        for s in range(0, val_idx.size, chunk):
            sl = val_idx[s : s + chunk]
            x_full = np.hstack([X_stat[:, sl].T, mech_full[:, sl].T])
            p_acc = 0.54 * clf.predict_proba(x_full)[:, 1]
            q_acc = 0.54 * np.clip(reg_k.predict(x_full), 0.0, 1.0)
            for ms in mech_subs:
                xs_p = np.hstack([X_stat[:, sl].T, ms[:, sl].T])
                p_acc += 0.23 * clf.predict_proba(xs_p)[:, 1]
                q_acc += 0.23 * np.clip(reg_k.predict(xs_p), 0.0, 1.0)
            prod_p[sl] = p_acc.astype(np.float32)
            prod_q[sl] = q_acc.astype(np.float32)
        del clf, reg_k
        gc.collect()
        log(f"Production OOF quadrant {q_id} complete")

    prod_p = align_lidar_gap_quantiles(prod_p, has_lidar_fp)
    prod_q = align_lidar_gap_quantiles(prod_q, has_lidar_fp)
    return prod_p, prod_q, imp_total


def fp_vec_to_grid(vec: np.ndarray, fp: np.ndarray) -> np.ndarray:
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = vec
    return out


def peak_nms_emit(
    surface: np.ndarray,
    allowed_mask: np.ndarray,
    n_dots: int = 37654,
) -> np.ndarray:
    """Exact ``n_dots`` binary {0, 1} allocation via progressive 7x7 -> 5x5 -> 3x3 peak NMS."""
    s = np.where(allowed_mask & np.isfinite(surface), surface.astype(np.float64), -1.0)
    yy, xx = np.indices(surface.shape, dtype=np.float64)
    s_tie = s + 1e-12 * (yy * 0.00029 + xx * 0.00019)

    out = np.zeros(surface.shape, dtype=np.float32)
    rem = int(n_dots)
    avail = allowed_mask & (surface > 0)
    for win in (7, 5, 3, 1):
        if rem <= 0:
            break
        cur = np.where(avail, s_tie, -2.0)
        is_peak = avail & (cur == maximum_filter(cur, size=win, mode="constant", cval=-3.0)) if win > 1 else avail
        cands = np.flatnonzero(is_peak)
        if cands.size == 0:
            continue
        sc = s_tie.ravel()[cands]
        if cands.size > rem:
            top = np.argpartition(sc, -rem)[-rem:]
            chosen = cands[top[np.argsort(-sc[top])]]
        else:
            chosen = cands[np.argsort(-sc)]
        out.ravel()[chosen] = 1.0
        avail.ravel()[chosen] = False
        rem -= int(chosen.size)
    assert int((out > 0.5).sum()) == int(n_dots)
    return out


def two_head_submodular_dti_emit(
    p_trace_2d: np.ndarray,
    q_kern_2d: np.ndarray,
    allowed_mask: np.ndarray,
    n_dots: int = 37654,
    fp_tax: float = 0.055,
    candidate_pool: int = 400_000,
) -> np.ndarray:
    """Exact lazy-greedy Two-Head R=300 m Submodular DTI Kernel Allocator."""
    H, W = p_trace_2d.shape
    pad = 3
    p_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    p_pad[pad : pad + H, pad : pad + W] = np.clip(np.nan_to_num(p_trace_2d, nan=0.0), 0.0, 1.0)
    cov_pad = np.zeros_like(p_pad)

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    init_tp = np.zeros((H, W), dtype=np.float64)
    for oy, ox, k_val in zip(dy, dx, kw):
        init_tp += k_val * p_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W]

    q_clean = np.clip(np.nan_to_num(q_kern_2d, nan=0.0), 0.0, 1.0).astype(np.float64)
    pen_arr = fp_tax * (1.0 - q_clean)
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
        _, i = heapq.heappop(heap)
        cy = ys[i]
        cx = xs[i]
        gain = 0.0
        for m in range(n_off):
            ny = cy + dy[m]
            nx = cx + dx[m]
            k_m = kw[m]
            cur_c = cov_pad[ny, nx]
            if k_m > cur_c:
                gain += p_pad[ny, nx] * (k_m - cur_c)
        exact_u = gain - pens[i]
        if not heap or (-exact_u <= heap[0][0] + 1e-15):
            out[cy - pad, cx - pad] = 1.0
            for m in range(n_off):
                ny = cy + dy[m]
                nx = cx + dx[m]
                k_m = kw[m]
                if k_m > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = k_m
            selected += 1
        else:
            heapq.heappush(heap, (-exact_u, i))

    assert selected == int(n_dots), f"Selected {selected} != {n_dots}"
    return out
