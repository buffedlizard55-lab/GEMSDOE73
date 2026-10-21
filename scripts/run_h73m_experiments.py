#!/usr/bin/env python3
"""GEMSDOE73 H73-M preregistered 3-experiment suite (see registry/preregistration_h73m.json).

Executes:
  1. Single-feature ROC-AUC leakage canary across all 82 physical features + 3 fold-safe
     transtensional mechanical features = 85 features (gate: symmetric AUC <= 0.90).
  2. Strict 4-quadrant Leave-One-Quadrant-Out (LOQO) training with 3.0 km (30 px) boundary
     exclusion buffer for three regime-specialized physical experts:
       - M_Q: Active Quaternary Scarp & Breakline Expert
       - M_P: Piedmont & Buried Basin-Margin Hydrothermal-Geophysical Expert
       - M_S: Piedmont-Gated Off-Catalogue Structural Expert
  3. Three preregistered experiments (M1, M2, M3) at the matched 37,654-dot budget:
       - M1: Regime-Adaptive Co-Kriged Multi-Physics Posterior + Cross-Contour Gate + 7x7 NMS
       - M2: Frozen M1 + Fold-Safe Anisotropic Transtensional Bridge Mechanics + 7x7 NMS
       - M3: Frozen M2 Posterior + Exact 300 m Submodular DTI Allocation (d_min=1.9 px)
  4. Exact multi-instrument evaluation (Instrument A `gems57-pooled-hide-v2`, plus report-only
     Instruments C_pied and B') with 1,000-draw paired 20 km spatial-cluster bootstrap.
"""
from __future__ import annotations

import datetime as dt
import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import binary_erosion, distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout, grid as grid_mod, holdout, metric  # noqa: E402
from gems73.emit import greedy_dots, peak_nms_emit, submodular_dti_emit  # noqa: E402
from gems73.features_h73m import (  # noqa: E402
    build_feature_memmap,
    compute_fold_safe_transtensional_mechanics,
)

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
WORK = ROOT / ".cache" / "work"
WORK.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"
EV.mkdir(parents=True, exist_ok=True)
BUDGET = 37654
t0 = time.monotonic()


def log(*a: Any) -> None:
    print(f"[{time.monotonic() - t0:6.1f}s]", *a, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def dump(name: str, obj: Any) -> None:
    (EV / name).write_text(json.dumps(obj, indent=2) + "\n")
    log("wrote evidence/" + name)


def quantile_align_by_quadrant(
    raw_prob_fp: np.ndarray,
    has_lidar_fp: np.ndarray,
    quad_fp: np.ndarray,
) -> np.ndarray:
    """Match non-LiDAR probability distribution within each quadrant to LiDAR tail percentiles."""
    out = raw_prob_fp.astype(np.float32, copy=True)
    q_grid = np.linspace(0.0, 1.0, 2001)
    for q_id in range(4):
        m_lid = (quad_fp == q_id) & has_lidar_fp
        m_gap = (quad_fp == q_id) & (~has_lidar_fp)
        if m_lid.sum() > 100 and m_gap.sum() > 100:
            src_q = np.quantile(raw_prob_fp[m_gap], q_grid)
            dst_q = np.quantile(raw_prob_fp[m_lid], q_grid)
            out[m_gap] = np.interp(raw_prob_fp[m_gap], src_q, dst_q).astype(np.float32)
    return out


def _gather_cols(X: np.memmap, cols: list[int], row_idx: np.ndarray) -> np.ndarray:
    """Gather `(len(row_idx), len(cols))` float32 matrix without copying full 1.7 GB memmap."""
    out = np.empty((row_idx.size, len(cols)), dtype=np.float32)
    for j, c in enumerate(cols):
        out[:, j] = X[c, row_idx]
    return out


def predict_oof_quadrants(
    X: np.memmap,
    y_fp: np.ndarray,
    eligible_neg_fp: np.ndarray,
    quad_fp: np.ndarray,
    buffer_excl_fp: np.ndarray,
    seed_base: int,
    max_neg: int = 180_000,
    pos_weight_fp: np.ndarray | None = None,
    feature_cols: list[int] | None = None,
) -> np.ndarray:
    """Strict 4-quadrant out-of-fold ensemble training with 3.0 km boundary buffer."""
    n_fp = X.shape[1]
    oof = np.zeros(n_fp, dtype=np.float32)
    chunk_sz = 650_000
    cols = feature_cols if feature_cols is not None else list(range(X.shape[0]))

    for q_id in range(4):
        in_train_q = (quad_fp != q_id) & (~buffer_excl_fp)
        pos_idx = np.flatnonzero(in_train_q & y_fp)
        neg_pool = np.flatnonzero(in_train_q & eligible_neg_fp & (~y_fp))
        rng = np.random.default_rng(seed_base + 101 * q_id)
        if neg_pool.size > max_neg:
            neg_idx = np.sort(rng.choice(neg_pool, size=max_neg, replace=False))
        else:
            neg_idx = neg_pool
        tr_idx = np.concatenate([pos_idx, neg_idx])
        y_tr = np.concatenate(
            [np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)]
        )
        sw_tr = None
        if pos_weight_fp is not None:
            sw_tr = np.concatenate(
                [pos_weight_fp[pos_idx].astype(np.float32), np.ones(neg_idx.size, dtype=np.float32)]
            )
        X_tr = _gather_cols(X, cols, tr_idx)

        clf = HistGradientBoostingClassifier(
            max_iter=195,
            max_leaf_nodes=47,
            min_samples_leaf=70,
            learning_rate=0.055,
            l2_regularization=3.2,
            random_state=seed_base + q_id * 19 + 1,
        )
        clf.fit(X_tr, y_tr, sample_weight=sw_tr)
        del X_tr, y_tr, sw_tr
        gc.collect()

        val_idx = np.flatnonzero(quad_fp == q_id)
        preds_q = np.empty(val_idx.size, dtype=np.float32)
        for s in range(0, val_idx.size, chunk_sz):
            sl = val_idx[s : s + chunk_sz]
            xb = _gather_cols(X, cols, sl)
            preds_q[s : s + chunk_sz] = clf.predict_proba(xb)[:, 1].astype(np.float32)
            del xb
        oof[val_idx] = preds_q
        del clf, preds_q
        gc.collect()

    return oof


def fast_proxy_eval_with_folds(
    pred_arms: dict[str, np.ndarray],
    truth_mask: np.ndarray,
    active_mask: np.ndarray,
    folds: list[dict[str, Any]],
    block_side: int = 200,
    draws: int = 1000,
    seed: int = 73073,
    candidate_key: str = "M3",
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Bit-exact fast evaluation matching `evaluate_holdout.evaluate` & `pooled_summary`."""
    H, W = truth_mask.shape
    ncols = (W + block_side - 1) // block_side
    nrows = (H + block_side - 1) // block_side
    n_blocks = ncols * nrows

    union_reg = np.zeros_like(active_mask, dtype=bool)
    for f in folds:
        union_reg |= f["region"]
    eval_domain = active_mask & union_reg

    truth_act = eval_domain & truth_mask
    q_truth = np.maximum(1.0 - distance_transform_edt(~truth_act) / metric.RADIUS_PX, 0.0)
    ty, tx = np.nonzero(truth_act)
    t_bids = (ty // block_side) * ncols + (tx // block_side)

    terms_by_arm: dict[str, np.ndarray] = {}
    fold_rows_by_arm: dict[str, list[dict[str, Any]]] = {k: [] for k in pred_arms}

    for arm_name, pred in pred_arms.items():
        dots = eval_domain & (pred >= 0.5)
        q_pred = (
            np.maximum(1.0 - distance_transform_edt(~dots) / metric.RADIUS_PX, 0.0)
            if dots.any()
            else np.zeros((H, W), dtype=np.float64)
        )
        covers = q_pred[ty, tx]

        terms = np.zeros((n_blocks, 4), dtype=np.float64)
        terms[:, 0] = np.bincount(t_bids, weights=covers, minlength=n_blocks)
        terms[:, 2] = np.bincount(t_bids, weights=1.0 - covers, minlength=n_blocks)
        terms[:, 3] = np.bincount(t_bids, weights=np.ones(ty.size), minlength=n_blocks)

        py, px = np.nonzero(dots)
        p_bids = (py // block_side) * ncols + (px // block_side)
        terms[:, 1] = np.bincount(p_bids, weights=1.0 - q_truth[py, px], minlength=n_blocks)
        terms_by_arm[arm_name] = terms

        for f in folds:
            f_reg = eval_domain & f["region"]
            f_t = f_reg & truth_mask
            fty, ftx = np.nonzero(f_t)
            f_cov = q_pred[fty, ftx]
            tp_f = float(f_cov.sum())
            fn_f = float(fty.size) - tp_f
            f_dots = f_reg & (pred >= 0.5)
            fp_f = float((1.0 - q_truth[f_dots]).sum())
            dti_f = tp_f / (tp_f + metric.ALPHA * fp_f + metric.BETA * fn_f + metric.EPS)
            fold_rows_by_arm[arm_name].append(
                {
                    "fold": f["receipt"]["fold"],
                    "dti": dti_f,
                    "tp": tp_f,
                    "fp": fp_f,
                    "fn": fn_f,
                    "n_truth": int(fty.size),
                    "n_emitted": int(f_dots.sum()),
                }
            )

    summary = evaluate_holdout.pooled_summary(
        terms_by_arm, draws=draws, seed=seed, candidate=candidate_key
    )
    summary["bootstrap"]["seed"] = seed
    summary["implementation_sha256"] = evaluate_holdout.implementation_hashes()
    return summary, fold_rows_by_arm


def main() -> int:
    os.environ["GEMS_DATA"] = str(DATA)
    g = grid_mod.load_grid(DATA)
    fp = g.footprint
    cat = g.catalogue
    fp_idx = np.flatnonzero(fp)

    valid0 = fp.copy()
    with rasterio.open(DATA / "training_features.tif") as ds_tf:
        for b_idx in (12, 2, 15, 19):
            arr_b = ds_tf.read(b_idx).astype(np.float32)
            valid0 &= np.isfinite(arr_b) & (arr_b > -1e30)
        depth_arr = ds_tf.read(15).astype(np.float32)
    valid = binary_erosion(valid0, iterations=12)

    folds, _ = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
    withheld = int(folds[0]["hidden_all"].sum())
    log(f"Loaded grid & 4 spatial folds (footprint={int(fp.sum()):,}, withheld={withheld:,})")

    mmap_path = WORK / "h73m_features_fp.f32"
    X, feat_names, has_lidar_fp, feat_meta = build_feature_memmap(
        mmap_path, fp, g.transform, DATA
    )
    log(f"Feature stack ready: {X.shape[0]} features x {X.shape[1]:,} footprint cells")

    # Compute strictly fold-safe transtensional mechanics on holdout folds & production catalogue
    a_active = np.zeros(fp.shape, dtype=bool)
    a_truth = np.zeros(fp.shape, dtype=bool)
    tip_fold = np.zeros(fp.shape, dtype=np.float32)
    wing_fold = np.zeros(fp.shape, dtype=np.float32)
    rel_fold = np.zeros(fp.shape, dtype=np.float32)
    for f in folds:
        act = valid & f["region"] & (~f["masked_known"])
        a_active |= act
        a_truth |= act & f["truth"]
        tf_f, wf_f, rf_f = compute_fold_safe_transtensional_mechanics(f["visible"])
        tip_fold[f["region"]] = tf_f[f["region"]]
        wing_fold[f["region"]] = wf_f[f["region"]]
        rel_fold[f["region"]] = rf_f[f["region"]]

    # 1. Single-feature leakage canaries across all 85 features (both catalogue & withheld)
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    canary_path = EV / "canaries_h73m.json"
    if canary_path.is_file():
        canaries = json.loads(canary_path.read_text())
        assert canaries.get("all_pass") is True and canaries.get("total_features_audited") == 85
        log(f"Reused verified {canaries['total_features_audited']} leakage canaries from {canary_path} (max sym AUC = {canaries['max_symmetric_auc']:.4f} <= 0.90)")
    else:
        rng_can = np.random.default_rng(73001)
        neg_pool_fp = np.flatnonzero((d_cat.ravel()[fp_idx] > 5.0) & (~a_truth.ravel()[fp_idx]))
        neg_c = np.sort(rng_can.choice(neg_pool_fp, size=200_000, replace=False))
        pos_cat_c = np.flatnonzero(cat.ravel()[fp_idx])
        pos_hid_c = np.flatnonzero(a_truth.ravel()[fp_idx])

        def _calc_auc(pos_idx_sub: np.ndarray, neg_idx_sub: np.ndarray, vec_fp: np.ndarray) -> float:
            p_v = vec_fp[pos_idx_sub]
            n_v = vec_fp[neg_idx_sub]
            p_v = p_v[np.isfinite(p_v)]
            n_v = n_v[np.isfinite(n_v)]
            y = np.concatenate([np.ones(p_v.size), np.zeros(n_v.size)])
            return float(roc_auc_score(y, np.concatenate([p_v, n_v])))

        canaries = {
            "evidence_class": "HOLDOUT-DTI canary (single-feature ROC-AUC on catalogue and withheld holdout; gate symmetric AUC <= 0.90)",
            "n_neg_sample": int(neg_c.size),
            "n_pos_catalogue": int(pos_cat_c.size),
            "n_pos_withheld": int(pos_hid_c.size),
            "channels": {},
        }
        for j, fname in enumerate(feat_names):
            col = np.asarray(X[j, :], dtype=np.float64)
            auc_cat = _calc_auc(pos_cat_c, neg_c, col)
            auc_hid = _calc_auc(pos_hid_c, neg_c, col)
            sym = max(auc_cat, 1.0 - auc_cat, auc_hid, 1.0 - auc_hid)
            passed = bool(sym <= 0.90)
            assert passed, f"LEAKAGE CANARY FAILED on {fname}: sym={sym:.4f}"
            canaries["channels"][fname] = {
                "auc_catalogue": round(auc_cat, 6),
                "auc_withheld": round(auc_hid, 6),
                "symmetric_auc": round(sym, 6),
                "pass": passed,
            }

        for mname, marr in (
            ("fold_safe_tip_lobe", tip_fold),
            ("fold_safe_wing_bridge", wing_fold),
            ("fold_safe_relay_annulus", rel_fold),
        ):
            col = marr.ravel()[fp_idx].astype(np.float64)
            auc_cat = _calc_auc(pos_cat_c, neg_c, col)
            auc_hid = _calc_auc(pos_hid_c, neg_c, col)
            sym = max(auc_cat, 1.0 - auc_cat, auc_hid, 1.0 - auc_hid)
            passed = bool(sym <= 0.90)
            assert passed, f"LEAKAGE CANARY FAILED on {mname}: sym={sym:.4f}"
            canaries["channels"][mname] = {
                "auc_catalogue": round(auc_cat, 6),
                "auc_withheld": round(auc_hid, 6),
                "symmetric_auc": round(sym, 6),
                "pass": passed,
            }

        canaries["all_pass"] = all(c["pass"] for c in canaries["channels"].values())
        canaries["max_symmetric_auc"] = max(c["symmetric_auc"] for c in canaries["channels"].values())
        canaries["total_features_audited"] = len(canaries["channels"])
        dump("canaries_h73m.json", canaries)
        log(f"All {canaries['total_features_audited']} leakage canaries PASSED (max sym AUC = {canaries['max_symmetric_auc']:.4f} <= 0.90)")

    # 2. Construct 4-quadrant geometry & 30 px (3.0 km) boundary exclusion buffer
    quad_2d = np.full(fp.shape, -1, dtype=np.int8)
    for q_idx, f in enumerate(folds):
        quad_2d[f["region"]] = q_idx
    nw_reg = folds[0]["region"]
    row_split = int(np.where(nw_reg.any(axis=1))[0].max())
    col_split = int(np.where(nw_reg.any(axis=0))[0].max())
    yy, xx = np.indices(fp.shape)
    boundary_excl_2d = (np.abs(yy - row_split) <= 15) | (np.abs(xx - col_split) <= 15)
    del yy, xx
    quad_fp = quad_2d.ravel()[fp_idx]
    boundary_excl_fp = boundary_excl_2d.ravel()[fp_idx]

    with rasterio.open(DATA / "external" / "sgmc_faults_100m.tif") as ds_sg:
        sgmc = (ds_sg.read(1) > 0) & fp
    with rasterio.open(DATA / "external" / "topo_10m_derived_100m_u8.tif") as ds_t10:
        rel10_u8 = ds_t10.read(5).astype(np.float32)
        slp10_u8 = ds_t10.read(1).astype(np.float32)

    allowed_offcat = fp & (~cat)
    emit_allowed_offcat = allowed_offcat & (d_cat > 2.0)

    # Spatially varying Piedmont & Range-Front Transition Regime Weight pi_pied in [0, 1]
    rel_p85_cat = float(np.nanpercentile(rel10_u8[cat], 85.0))
    rel_p75_cat = float(np.nanpercentile(rel10_u8[cat], 75.0))
    slp_p80_cat = float(np.nanpercentile(slp10_u8[cat], 80.0))

    depth_clean = np.where(np.isfinite(depth_arr) & (depth_arr > -1e30), depth_arr, 0.0).astype(np.float32)
    pi_depth = np.clip((depth_clean - 80.0) / 350.0, 0.0, 1.0)
    pi_rel = np.clip(1.0 - rel10_u8 / (rel_p85_cat * 1.35 + 1.0), 0.0, 1.0)
    pi_slp = np.clip(1.0 - slp10_u8 / (slp_p80_cat * 1.35 + 1.0), 0.0, 1.0)
    pi_pied_2d = np.sqrt(pi_depth * (0.55 * pi_rel + 0.45 * pi_slp)).astype(np.float32)
    pi_pied_fp = pi_pied_2d.ravel()[fp_idx]

    # Cross-Contour & Multi-Line Corroboration Factor (rejects isolated pluvial shoreline benches)
    shore_idx = feat_names.index("pluvial_shoreline_elev_dist_m")
    cross_idx = feat_names.index("cross_contour_scarp_index")
    hydro_idx = feat_names.index("hydrothermal_strain_conduit")
    chain_idx = feat_names.index("scarp_chain_occ_16az")
    shore_d_fp = np.asarray(X[shore_idx, :], dtype=np.float32)
    cross_fp = np.asarray(X[cross_idx, :], dtype=np.float32)
    hydro_fp = np.asarray(X[hydro_idx, :], dtype=np.float32)
    chain_fp = np.asarray(X[chain_idx, :], dtype=np.float32)

    # Attenuate pixels sitting right on Lahontan/Bonneville highstand contours (<= 8 m) UNLESS cross-contour or hydrothermal
    shore_gate_fp = np.where(
        (shore_d_fp < 8.0) & (cross_fp < np.percentile(cross_fp, 60.0)) & (hydro_fp < np.percentile(hydro_fp, 65.0)),
        0.78,
        1.0,
    ).astype(np.float32)
    corrob_boost_fp = (
        shore_gate_fp * (0.90 + 0.12 * np.clip(chain_fp * 1.5, 0.0, 1.0) + 0.08 * np.clip(hydro_fp * 2.0, 0.0, 1.0))
    ).astype(np.float32)

    # Targets for the 3 LOQO experts (strictly held-in quadrants only)
    y_quat_fp = cat.ravel()[fp_idx]
    neg_quat_fp = (d_cat.ravel()[fp_idx] > 3.0) & (~sgmc.ravel()[fp_idx])

    # Expert 2 (M_P): Piedmont & Hydrothermal Quaternary Expert (4.5x weight on piedmont/hydrothermal traces)
    w_pied_quat_fp = (1.0 + 3.5 * pi_pied_fp + 1.5 * np.clip(hydro_fp * 2.0, 0.0, 1.0)).astype(np.float32)

    # Expert 3 (M_S): Piedmont-Gated Off-Catalogue Structural Expert (4.5x in piedmont, 0.30x in steep mountain bedrock)
    y_struct_2d = sgmc & (~cat) & (d_cat >= 2.5)
    w_struct_2d = np.where(
        (rel10_u8 <= rel_p85_cat) & (depth_clean >= 130.0),
        4.2,
        np.where((rel10_u8 > rel_p85_cat * 1.4) & (depth_clean < 60.0), 0.35, 1.0),
    ).astype(np.float32)
    y_struct_fp = y_struct_2d.ravel()[fp_idx]
    w_struct_fp = w_struct_2d.ravel()[fp_idx]
    neg_struct_fp = (~sgmc).ravel()[fp_idx] & (d_cat.ravel()[fp_idx] > 2.5)

    # Evaluation truth sets for report-only proxy instruments
    b_prime = sgmc & (~cat) & (d_cat >= 3.0)
    c_pied = (
        sgmc
        & (~cat)
        & (d_cat > 2.5)
        & (rel10_u8 <= rel_p75_cat)
        & (slp10_u8 <= slp_p80_cat)
        & (depth_clean >= 250.0)
    )
    del depth_arr, depth_clean, rel10_u8, slp10_u8
    gc.collect()

    oof_cache = WORK / "h73m_oof_experts.npz"
    q_cache = WORK / "h73m_oof_q.npy"
    p_cache = WORK / "h73m_oof_p.npy"
    s_cache = WORK / "h73m_oof_s.npy"
    if oof_cache.is_file():
        zc = np.load(oof_cache)
        oof_q_raw = zc["oof_q_raw"]
        oof_p_raw = zc["oof_p_raw"]
        oof_s_raw = zc["oof_s_raw"]
        log(f"Loaded cached 3-expert LOQO predictions from {oof_cache}")
    else:
        if q_cache.is_file():
            oof_q_raw = np.load(q_cache)
            log("Loaded cached LOQO Expert 1 (M_Q)")
        else:
            log("Training LOQO Expert 1 (M_Q: Active Quaternary Scarp & Breakline Expert)...")
            oof_q_raw = predict_oof_quadrants(
                X, y_quat_fp, neg_quat_fp, quad_fp, boundary_excl_fp, seed_base=7310
            )
            np.save(q_cache, oof_q_raw)
        if p_cache.is_file():
            oof_p_raw = np.load(p_cache)
            log("Loaded cached LOQO Expert 2 (M_P)")
        else:
            log("Training LOQO Expert 2 (M_P: Piedmont & Buried Hydrothermal-Geophysical Expert)...")
            oof_p_raw = predict_oof_quadrants(
                X,
                y_quat_fp,
                neg_quat_fp,
                quad_fp,
                boundary_excl_fp,
                seed_base=7320,
                pos_weight_fp=w_pied_quat_fp,
            )
            np.save(p_cache, oof_p_raw)
        if s_cache.is_file():
            oof_s_raw = np.load(s_cache)
            log("Loaded cached LOQO Expert 3 (M_S)")
        else:
            log("Training LOQO Expert 3 (M_S: Piedmont-Gated Off-Catalogue Structural Expert)...")
            oof_s_raw = predict_oof_quadrants(
                X,
                y_struct_fp,
                neg_struct_fp,
                quad_fp,
                boundary_excl_fp,
                seed_base=7330,
                pos_weight_fp=w_struct_fp,
            )
            np.save(s_cache, oof_s_raw)
        np.savez_compressed(oof_cache, oof_q_raw=oof_q_raw, oof_p_raw=oof_p_raw, oof_s_raw=oof_s_raw)
        log(f"Saved 3-expert LOQO predictions to {oof_cache}")

    oof_q_cal = quantile_align_by_quadrant(oof_q_raw, has_lidar_fp, quad_fp)
    oof_p_cal = quantile_align_by_quadrant(oof_p_raw, has_lidar_fp, quad_fp)
    oof_s_cal = quantile_align_by_quadrant(oof_s_raw, has_lidar_fp, quad_fp)

    # Load H73-1 fold-fair E1 if cached, or compute from H73-1 components
    h73_1_comp_cache = WORK / "components.npz"
    if not h73_1_comp_cache.exists():
        from gems73 import surface as S_h73_1
        comp1 = S_h73_1.build_components(DATA, fp, log=log)
        np.savez_compressed(h73_1_comp_cache, **comp1)
    else:
        z1 = np.load(h73_1_comp_cache)
        comp1 = {k: z1[k] for k in ("scarp_n", "chain", "substep", "pied_soft", "lidar_valid")}
    from gems73 import surface as S_h73_1
    surf_h73_1_e1 = S_h73_1.make_surface(comp1, "E1")
    s_h73_1_tail = (np.clip((surf_h73_1_e1 - 0.90) / 0.10, 0.0, 1.0) ** 2).astype(np.float32)

    # Regime-Adaptive Co-Kriging Posterior (M1 surface):
    # In range-front / moderate relief (pi_pied -> 0): 0.42 M_Q + 0.24 M_P + 0.34 M_S
    # In deep alluvial piedmont (pi_pied -> 1):        0.20 M_Q + 0.34 M_P + 0.46 M_S
    w_q = 0.42 - 0.22 * pi_pied_fp
    w_p = 0.24 + 0.10 * pi_pied_fp
    w_s = 0.34 + 0.12 * pi_pied_fp
    cokrig_fp = ((w_q * oof_q_cal + w_p * oof_p_cal + w_s * oof_s_cal) * corrob_boost_fp).astype(np.float32)

    surf_m1 = np.zeros(fp.shape, dtype=np.float32)
    surf_m1.ravel()[fp_idx] = np.clip(cokrig_fp, 0.0, 1.0)

    # Fold-fair allowed mask on Instrument A (prunes only d_vis <= 2.0 px around visible faults)
    a_emit_allowed = fp.copy()
    for f in folds:
        d_vis_f = distance_transform_edt(~f["visible"]).astype(np.float32)
        a_emit_allowed[f["region"]] = (
            fp[f["region"]] & (~f["masked_known"][f["region"]]) & (d_vis_f[f["region"]] > 2.0)
        )

    # =========================================================================
    # EXPERIMENT M1: Regime-Adaptive Co-Kriged Multi-Physics + 7x7 Peak NMS
    # =========================================================================
    log("Running Experiment M1 (Regime-Adaptive Co-Kriging + Cross-Contour Gate + 7x7 NMS)...")
    dots_m1_A = peak_nms_emit(surf_m1, a_emit_allowed, n_dots=BUDGET)
    dots_m1_off = peak_nms_emit(surf_m1, emit_allowed_offcat, n_dots=BUDGET)

    # =========================================================================
    # EXPERIMENT M2: Frozen M1 + Fold-Safe Anisotropic Transtensional Mechanics + 7x7 NMS
    # =========================================================================
    log("Running Experiment M2 (Frozen M1 + Fold-Safe Anisotropic Transtensional Bridge + 7x7 NMS)...")
    mech_mult_A = (
        1.0 + 0.26 * tip_fold + 0.22 * wing_fold + 0.26 * rel_fold + 0.20 * s_h73_1_tail
    ).astype(np.float32)
    surf_m2_A = np.clip(surf_m1 * mech_mult_A, 0.0, 1.0).astype(np.float32)

    tip_cat, wing_cat, rel_cat = compute_fold_safe_transtensional_mechanics(cat)
    mech_mult_off = (
        1.0 + 0.26 * tip_cat + 0.22 * wing_cat + 0.26 * rel_cat + 0.20 * s_h73_1_tail
    ).astype(np.float32)
    surf_m2_off = np.clip(surf_m1 * mech_mult_off, 0.0, 1.0).astype(np.float32)

    dots_m2_A = peak_nms_emit(surf_m2_A, a_emit_allowed, n_dots=BUDGET)
    dots_m2_off = peak_nms_emit(surf_m2_off, emit_allowed_offcat, n_dots=BUDGET)

    # =========================================================================
    # EXPERIMENT M3: Frozen M2 Posterior + Radius-Matched (d_min=3.0 px) Submodular DTI Allocation
    # =========================================================================
    log("Running Experiment M3 (Frozen M2 Posterior + Exact 300 m Submodular DTI Allocation, d_min=3.0 px)...")
    a_masked_known = np.zeros(fp.shape, dtype=bool)
    for f in folds:
        a_masked_known[f["region"]] = f["masked_known"][f["region"]]
    post_m3_A = np.where(fp & (~a_masked_known), surf_m2_A ** 0.75, 0.0).astype(np.float32)
    dots_m3_A = submodular_dti_emit(
        post_m3_A, a_emit_allowed, n_dots=BUDGET, fp_penalty_weight=0.04, min_spacing_px=3.0
    )

    post_m3_off = np.where(fp & (~cat), surf_m2_off ** 0.75, 0.0).astype(np.float32)
    dots_m3_off = submodular_dti_emit(
        post_m3_off, emit_allowed_offcat, n_dots=BUDGET, fp_penalty_weight=0.04, min_spacing_px=3.0
    )

    # Controls on Instrument A
    with rasterio.open(DATA / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif") as s:
        h19_5_support = np.isfinite(s.read(1)) & (s.read(1) > 0.5)
    h33_analogue_foldfair = greedy_dots(
        h19_5_support.astype(np.float32), a_emit_allowed & h19_5_support, BUDGET
    ).astype(np.float32)

    h33_path = Path("/home/user/refs/g32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    with rasterio.open(h33_path) as s:
        h33_static = np.where(fp & np.isfinite(s.read(1)), s.read(1), 0.0).astype(np.float32)

    rng_ctrl = np.random.default_rng(73099)
    ctrl_noise = np.zeros(fp.shape, dtype=np.float32)
    ctrl_noise[fp] = rng_ctrl.random(int(fp.sum()), dtype=np.float32)
    random_ctrl_A = greedy_dots(ctrl_noise, a_emit_allowed, BUDGET).astype(np.float32)
    random_ctrl_off = peak_nms_emit(ctrl_noise, emit_allowed_offcat, n_dots=BUDGET)

    dots_h73_1_A = greedy_dots(surf_h73_1_e1, a_emit_allowed, BUDGET).astype(np.float32)
    dots_h73_1_off = greedy_dots(surf_h73_1_e1, emit_allowed_offcat, BUDGET).astype(np.float32)

    # Save surfaces & production dots to .cache/work/h73m_dots.npz
    np.savez_compressed(
        WORK / "h73m_dots.npz",
        prod_M1=(dots_m1_off > 0.5),
        prod_M2=(dots_m2_off > 0.5),
        prod_M3=(dots_m3_off > 0.5),
        surf_M1=surf_m1,
        surf_M2_off=surf_m2_off,
    )

    # =========================================================================
    # Evaluate on Primary Instrument A (`gems57-pooled-hide-v2`, 11,321 withheld px)
    # =========================================================================
    log("Evaluating all arms on Primary Instrument A (gems57-pooled-hide-v2)...")
    arms_A = {
        "M3": dots_m3_A,
        "M2": dots_m2_A,
        "M1": dots_m1_A,
        "h33_analogue_foldfair": h33_analogue_foldfair,
        "H73_1_E1_foldfair": dots_h73_1_A,
        "random_control": random_ctrl_A,
        "M3_offcat_static": dots_m3_off,
        "h33_static_reference": h33_static,
    }
    # Verify bit-exact equivalence between fast_proxy_eval_with_folds and vendor evaluate_holdout.evaluate on M3
    tot_m3_exact = None
    for f in folds:
        _, t_f = evaluate_holdout.evaluate(dots_m3_A, f, valid)
        tot_m3_exact = t_f if tot_m3_exact is None else tot_m3_exact + t_f

    summary_A_init, per_fold_A = fast_proxy_eval_with_folds(
        arms_A, a_truth, a_active, folds, draws=1000, seed=73073, candidate_key="M3"
    )
    dti_m3_exact = float(evaluate_holdout.from_terms(tot_m3_exact.sum(axis=0)))
    assert abs(summary_A_init["scores"]["M3"]["dti"] - dti_m3_exact) < 1e-12, (
        summary_A_init["scores"]["M3"]["dti"],
        dti_m3_exact,
    )

    best_m = max(("M1", "M2", "M3"), key=lambda m: summary_A_init["scores"][m]["dti"])
    if best_m == "M3":
        summary_A = summary_A_init
    else:
        summary_A, per_fold_A = fast_proxy_eval_with_folds(
            arms_A, a_truth, a_active, folds, draws=1000, seed=73073, candidate_key=best_m
        )
    summary_A["per_fold"] = per_fold_A
    summary_A["fold_receipts"] = [f["receipt"] for f in folds]
    dump("holdout_h73m_instrument_A.json", summary_A)

    scores_A = {k: round(v["dti"], 4) for k, v in summary_A["scores"].items()}
    log("HOLDOUT-DTI Instrument A:", scores_A)

    # =========================================================================
    # Evaluate on Report-Only Proxy Instruments C_pied and B'
    # =========================================================================
    log("Evaluating on Report-Only Proxy Instruments C_pied and B'...")
    arms_off = {
        "M3": dots_m3_off,
        "M2": dots_m2_off,
        "M1": dots_m1_off,
        "h33_champion": h33_static,
        "H73_1_E1": dots_h73_1_off,
        "random_control": random_ctrl_off,
    }
    p9_path = Path("/home/user/refs/g70/docs/downloads/gems70-p5-multiphysics-submodular-37654-20261020.tif")
    p8_path = Path("/home/user/refs/g70/docs/downloads/gems70-p5-dual-submod300-oof38k-20261020.tif")
    if p9_path.exists():
        with rasterio.open(p9_path) as s:
            arms_off["gems70_p9_piedmont"] = np.where(fp & np.isfinite(s.read(1)), s.read(1), 0.0).astype(np.float32)
    if p8_path.exists():
        with rasterio.open(p8_path) as s:
            arms_off["gems70_p8_oof38k"] = np.where(fp & np.isfinite(s.read(1)), s.read(1), 0.0).astype(np.float32)

    summary_Cpied, folds_Cpied = fast_proxy_eval_with_folds(
        arms_off, c_pied, valid & allowed_offcat, folds, draws=1000, seed=73074, candidate_key=best_m
    )
    summary_Cpied["per_fold"] = folds_Cpied
    summary_Cpied["evidence_class"] = "PROXY-DTI (SGMC off-catalogue piedmont subset; report-only, never used for feature training)"
    dump("proxy_h73m_instrument_Cpied.json", summary_Cpied)
    log("PROXY-DTI Instrument C_pied:", {k: round(v["dti"], 4) for k, v in summary_Cpied["scores"].items()})

    summary_Bprime, folds_Bprime = fast_proxy_eval_with_folds(
        arms_off, b_prime, valid & allowed_offcat, folds, draws=1000, seed=73075, candidate_key=best_m
    )
    summary_Bprime["per_fold"] = folds_Bprime
    summary_Bprime["evidence_class"] = "PROXY-DTI (SGMC off-catalogue d>=3 px; report-only)"
    dump("proxy_h73m_instrument_Bprime.json", summary_Bprime)
    log("PROXY-DTI Instrument B':", {k: round(v["dti"], 4) for k, v in summary_Bprime["scores"].items()})

    delta_ctrl = summary_A["paired_differences"]["h33_analogue_foldfair"]
    delta_h73_1 = summary_A["paired_differences"]["H73_1_E1_foldfair"]
    delta_static = summary_A["paired_differences"]["h33_static_reference"]
    beats_ctrl = bool(delta_ctrl["delta"] > 0 and delta_ctrl["ci95"][0] > 0)

    selection = {
        "lane": "H73-M",
        "best_experiment": best_m,
        "best_holdout_dti": summary_A["scores"][best_m]["dti"],
        "best_holdout_ci95": summary_A["scores"][best_m]["ci95"],
        "h33_analogue_foldfair_dti": summary_A["scores"]["h33_analogue_foldfair"]["dti"],
        "h33_analogue_foldfair_ci95": summary_A["scores"]["h33_analogue_foldfair"]["ci95"],
        "h73_1_e1_foldfair_dti": summary_A["scores"]["H73_1_E1_foldfair"]["dti"],
        "random_control_dti": summary_A["scores"]["random_control"]["dti"],
        "paired_delta_vs_h33_analogue_foldfair": delta_ctrl,
        "paired_delta_vs_h73_1_e1": delta_h73_1,
        "paired_delta_vs_h33_static": delta_static,
        "beats_control_ci_excluding_0": beats_ctrl,
        "canaries_all_pass": canaries["all_pass"],
        "max_canary_symmetric_auc": canaries["max_symmetric_auc"],
        "c_pied_dti": summary_Cpied["scores"][best_m]["dti"],
        "c_pied_ci95": summary_Cpied["scores"][best_m]["ci95"],
        "c_pied_paired_vs_h33": summary_Cpied["paired_differences"]["h33_champion"],
        "b_prime_dti": summary_Bprime["scores"][best_m]["dti"],
        "b_prime_ci95": summary_Bprime["scores"][best_m]["ci95"],
        "b_prime_paired_vs_h33": summary_Bprime["paired_differences"]["h33_champion"],
        "production_dots": int((dots_m3_off > 0.5).sum()),
        "evaluator_version": evaluate_holdout.VERSION,
        "withheld_positive_pixels": summary_A["scores"][best_m]["withheld_positive_pixels"],
        "runtime_s": round(time.monotonic() - t0, 1),
    }
    dump("selection_h73m.json", selection)
    log("SELECTION SUMMARY:", json.dumps(selection, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
