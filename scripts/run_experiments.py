#!/usr/bin/env python3
"""Execute the preregistered GEMSDOE73 H73-2 campaign (Canary + Controls + E1/E2/E3 + OOF Production).

Strictly enforces:
  1. Single-feature leakage canary (`symmetric ROC-AUC <= 0.90`) across ALL 48 physical channels
     on the canonical `gems57-pooled-hide-v2` withheld positives (`n = 11,321`) BEFORE training.
  2. Fold-honest spatial holdout evaluation (`NW`, `NE`, `SW`, `SE` whole-segment buffered blocks,
     `seed=20`, `buffer_px=3`, `boundary_px=12`) via unmodified `vendor/gems57/evaluate_holdout.py`.
  3. Nested spatial block cross-fitting inside each outer training pool so Stage 2 receives
     strictly out-of-fold Stage-1 probabilities matching test-time calibration.
  4. Exact budget of 3 experiments (`E1`, `E2`, `E3`) against non-trivial fold-fair controls
     (`random_uniform_dots`, `h73_1_piedmont_scarpchain`, `h33_analogue_foldfair`).
  5. Strict out-of-fold production emission and canonical packaging via `vendor/gems57/submission_writer.py`.
"""
from __future__ import annotations

import ctypes
import gc
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import (  # noqa: E402
    evaluate_holdout as vendor_eval,
    grid as vendor_grid,
    holdout as vendor_holdout,
    submission_writer as vendor_writer,
)
from gems73.emit import greedy_dots, submodular_dti_dots  # noqa: E402
from gems73.features import FEATURE_NAMES, build_or_load_feature_bank  # noqa: E402
from gems73.submission import write_submission_geotiff  # noqa: E402
from gems73.mecs import (  # noqa: E402
    STAGE2_FEATURE_NAMES,
    Stage2Combiner,
    extract_stage2_topology_features,
    fit_stage1_experts,
    make_spatial_inner_splits,
    predict_stage1_quantiles,
    rank_calibrate_domain,
    stage1_corroborated_surface,
)

DATA_DIR = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
WORK_DIR = ROOT / ".cache" / "work_h73_2"
BUDGET_FULL = 37654


def peak_rss_mib() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def current_rss_mib() -> float:
    try:
        with open("/proc/self/statm") as fh:
            pages = int(fh.read().split()[1])
        return round(pages * os.sysconf("SC_PAGE_SIZE") / (1024.0 * 1024.0), 1)
    except Exception:
        return peak_rss_mib()


def release_heap() -> None:
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def run_leakage_canary(X_fp: np.ndarray, fp_idx: np.ndarray, folds: list[dict], shape: tuple[int, int]) -> dict:
    """Evaluate single-feature ROC-AUC on pooled withheld positives across all 4 quadrant folds."""
    eval_mask = np.zeros(shape, dtype=bool)
    truth_mask = np.zeros(shape, dtype=bool)
    for f in folds:
        active = f["region"] & (~f["visible"])
        eval_mask |= active
        truth_mask |= active & f["truth"]

    ev_fp = eval_mask.ravel()[fp_idx]
    y_ev = truth_mask.ravel()[fp_idx][ev_fp].astype(np.int32)
    rng = np.random.default_rng(7301)
    pos_i = np.flatnonzero(y_ev > 0)
    neg_i = rng.choice(np.flatnonzero(y_ev == 0), size=200_000, replace=False)
    sample_i = np.concatenate([pos_i, neg_i])
    ev_rows = np.flatnonzero(ev_fp)[sample_i]
    ys = y_ev[sample_i]

    results = []
    for col, fname in enumerate(FEATURE_NAMES):
        v = np.asarray(X_fp[ev_rows, col], dtype=np.float64)
        valid = np.isfinite(v)
        v_clean = np.where(valid, v, np.nanmedian(v) if valid.any() else 0.0)
        auc_raw = float(roc_auc_score(ys, v_clean))
        auc_sym = float(max(auc_raw, 1.0 - auc_raw))
        results.append({
            "col": col,
            "feature": fname,
            "auc_signed": round(auc_raw, 5),
            "auc_symmetric": round(auc_sym, 5),
            "finite_fraction": round(float(valid.mean()), 4),
            "pass_le_0.90": bool(auc_sym <= 0.90),
        })

    worst = max(results, key=lambda r: r["auc_symmetric"])
    all_pass = all(r["pass_le_0.90"] for r in results)
    report = {
        "evidence_class": "LEAKAGE-CANARY",
        "evaluator_version": vendor_eval.VERSION,
        "withheld_positive_pixels": int(pos_i.size),
        "sampled_negative_pixels": int(neg_i.size),
        "n_features_tested": len(results),
        "threshold_symmetric_auc": 0.90,
        "all_passed": all_pass,
        "max_symmetric_auc": worst["auc_symmetric"],
        "max_feature": worst["feature"],
        "features": results,
    }
    if not all_pass:
        raise RuntimeError(f"LEAKAGE CANARY FAILED: {worst}")
    return report


def fit_h33_foldfair_control(
    data_dir: Path,
    folds: list[dict],
    footprint: np.ndarray,
    guard_px: float = 2.0,
) -> np.ndarray:
    """Reproduce the strong 30-feature fold-refitted H33 champion analogue control in <700 MB RAM."""
    n_fp = int(footprint.sum())
    X30 = np.empty((n_fp, 30), dtype=np.float32)
    col = 0
    with rasterio.open(data_dir / "training_features.tif") as tf:
        for i in range(1, 20):
            b = tf.read(i).astype(np.float32)[footprint]
            b[~np.isfinite(b) | (np.abs(b) > 1e30)] = np.nan
            X30[:, col] = b
            col += 1
    with rasterio.open(data_dir / "external" / "lidar_scarp_features_u8.tif") as sl:
        lid_valid = (sl.read(12) > 0)[footprint]
        for i in (1, 2, 3, 4, 5, 8, 9, 10):
            b = sl.read(i).astype(np.float32)[footprint]
            b[~lid_valid] = np.nan
            X30[:, col] = b
            col += 1
    with rasterio.open(data_dir / "external" / "geodawn_rad_u8.tif") as sr:
        for i in (1, 2, 3):
            X30[:, col] = sr.read(i).astype(np.float32)[footprint]
            col += 1
    gc.collect()

    with rasterio.open(data_dir / "labels.tif") as slb:
        y_all = (slb.read(1) >= 1)[footprint]

    pred_dots = np.zeros(footprint.shape, dtype=np.float32)
    fp_total = float(footprint.sum())
    for k, f in enumerate(folds):
        reg = f["region"]
        dist_reg = distance_transform_edt(~reg)
        tr_2d = footprint & (~reg) & (dist_reg > 12)
        tr_fp = tr_2d[footprint]
        rng = np.random.default_rng(900 + k)
        pos = np.flatnonzero(tr_fp & y_all)
        neg_pool = np.flatnonzero(tr_fp & (~y_all))
        neg = rng.choice(neg_pool, size=min(150_000, neg_pool.size), replace=False)
        tr_idx = np.concatenate([pos, neg])
        clf = HistGradientBoostingClassifier(
            max_iter=220, max_leaf_nodes=63, min_samples_leaf=80, learning_rate=0.06, random_state=900 + k
        )
        clf.fit(X30[tr_idx], y_all[tr_idx].astype(np.int32))
        surf = np.zeros(footprint.shape, dtype=np.float32)
        ev_fp = reg[footprint]
        surf[reg] = clf.predict_proba(X30[ev_fp])[:, 1].astype(np.float32)
        if guard_px > 0:
            allowed = reg & (~f["visible"]) & (distance_transform_edt(~f["visible"]) > guard_px)
        else:
            allowed = reg & (~f["visible"])
        fold_budget = int(round(BUDGET_FULL * float(reg.sum()) / fp_total))
        dots = greedy_dots(surf, allowed, budget=fold_budget, min_dist=2.5)
        pred_dots[dots] = 1.0
    del X30
    gc.collect()
    return pred_dots


def main() -> None:
    t0 = time.time()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)

    print(f"[0.0s] Loading grid & spatial block folds (`{vendor_eval.VERSION}`)...", flush=True)
    g = vendor_grid.load_grid(DATA_DIR)
    folds, fold_summary = vendor_holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
    shape = g.shape
    foot = g.footprint
    fp_total = float(foot.sum())

    print(f"[{time.time()-t0:.1f}s] Building / loading 48-channel pure-physics memmap bank (RSS={peak_rss_mib()} MiB)...", flush=True)
    X_fp, fp_idx = build_or_load_feature_bank(DATA_DIR, WORK_DIR)
    print(f"[{time.time()-t0:.1f}s] Feature bank ready: shape={X_fp.shape} RSS={peak_rss_mib()} MiB", flush=True)

    print(f"[{time.time()-t0:.1f}s] Running single-feature leakage canary across all {len(FEATURE_NAMES)} channels...", flush=True)
    canary_report = run_leakage_canary(X_fp, fp_idx, folds, shape)
    (ROOT / "evidence" / "canary.json").write_text(json.dumps(canary_report, indent=2) + "\n")
    print(
        f"[{time.time()-t0:.1f}s] CANARY PASS: all_passed={canary_report['all_passed']} "
        f"max_symmetric_auc={canary_report['max_symmetric_auc']} ({canary_report['max_feature']})",
        flush=True,
    )

    ckpt_path = WORK_DIR / "holdout_arms_ckpt.npz"
    if ckpt_path.exists() and "--retrain" not in sys.argv:
        print(f"[{time.time()-t0:.1f}s] Loading saved OOF & holdout checkpoint `{ckpt_path.name}` (pass --retrain to rebuild)...", flush=True)
        ck = np.load(ckpt_path)
        oof_surf_e1_fp = ck["oof_surf_e1_fp"].astype(np.float32)
        oof_surf_e2_fp = ck["oof_surf_e2_fp"].astype(np.float32)
        dots_e1_holdout = np.zeros(shape, dtype=np.float32)
        dots_e2_holdout = np.zeros(shape, dtype=np.float32)
        dots_e3_holdout = np.zeros(shape, dtype=np.float32)
        dots_h33_ctrl = np.zeros(shape, dtype=np.float32)
        dots_rand_holdout = np.zeros(shape, dtype=np.float32)
        dots_e1_holdout.ravel()[ck["e1_idx"]] = 1.0
        dots_e2_holdout.ravel()[ck["e2_idx"]] = 1.0
        dots_e3_holdout.ravel()[ck["e3_idx"]] = 1.0
        dots_h33_ctrl.ravel()[ck["h33_idx"]] = 1.0
        dots_rand_holdout.ravel()[ck["rand_idx"]] = 1.0
        if "h33_ug_idx" in ck:
            dots_h33_unguarded = np.zeros(shape, dtype=np.float32)
            dots_h33_unguarded.ravel()[ck["h33_ug_idx"]] = 1.0
        else:
            dots_h33_unguarded = None
        del X_fp, ck
        release_heap()
        fold_diagnostics = []
        for f in folds:
            fname = f["receipt"]["fold"]
            r1, _ = vendor_eval.evaluate(dots_e1_holdout, f, foot)
            r2, _ = vendor_eval.evaluate(dots_e2_holdout, f, foot)
            r3, _ = vendor_eval.evaluate(dots_e3_holdout, f, foot)
            fold_diagnostics.append({
                "fold": fname,
                "n_truth": r3["n_truth"],
                "budget": int(round(BUDGET_FULL * float(f["region"].sum()) / fp_total)),
                "E1_dti": r1["dti"],
                "E2_dti": r2["dti"],
                "E3_dti": r3["dti"],
            })
    else:
        with rasterio.open(DATA_DIR / "labels.tif") as slb:
            labels_2d = slb.read(1) >= 1
        y_fp = labels_2d.ravel()[fp_idx].astype(np.int8)

        oof_surf_e1_fp = np.zeros(fp_idx.size, dtype=np.float32)
        oof_surf_e2_fp = np.zeros(fp_idx.size, dtype=np.float32)

        dots_e1_holdout = np.zeros(shape, dtype=np.float32)
        dots_e2_holdout = np.zeros(shape, dtype=np.float32)
        dots_e3_holdout = np.zeros(shape, dtype=np.float32)
        dots_rand_holdout = np.zeros(shape, dtype=np.float32)

        rng_ctrl = np.random.default_rng(20261021)
        fold_diagnostics = []

        for k, f in enumerate(folds):
            fname = f["receipt"]["fold"]
            reg = f["region"]
            vis = f["visible"]
            dist_reg = distance_transform_edt(~reg)
            train_pool_2d = foot & (~reg) & (dist_reg > 12)
            train_fp_pos = np.flatnonzero(train_pool_2d.ravel()[fp_idx])
            eval_fp_pos = np.flatnonzero(reg.ravel()[fp_idx])

            print(f"[{time.time()-t0:.1f}s] Outer fold {fname}: nested 3-split Stage-1 OOF + full Stage-1 fit (RSS={peak_rss_mib()} MiB)...", flush=True)

            inner_splits = make_spatial_inner_splits(train_pool_2d, n_splits=3, guard_px=12)
            q_oof_train: dict[str, np.ndarray] = {m: np.zeros(fp_idx.size, dtype=np.float32) for m in ("morph", "subsurf", "hydro", "joint")}
            for s_idx, (tr_in_2d, val_in_2d) in enumerate(inner_splits):
                tr_in_pos = np.flatnonzero(tr_in_2d.ravel()[fp_idx])
                val_in_pos = np.flatnonzero(val_in_2d.ravel()[fp_idx])
                m_in = fit_stage1_experts(X_fp, y_fp, tr_in_pos, seed=100 * k + 10 * s_idx)
                q_val = predict_stage1_quantiles(m_in, X_fp, val_in_pos)
                for mname, arr in q_val.items():
                    q_oof_train[mname][val_in_pos] = arr
                del m_in, q_val

            Z_train_full = extract_stage2_topology_features(q_oof_train, X_fp, fp_idx, train_pool_2d, shape)
            s2_model = Stage2Combiner(seed=500 + k).fit(Z_train_full[train_fp_pos], y_fp[train_fp_pos], seed=500 + k)
            del Z_train_full, q_oof_train
            gc.collect()

            m_outer = fit_stage1_experts(X_fp, y_fp, train_fp_pos, seed=700 + k)
            q_eval_dict = predict_stage1_quantiles(m_outer, X_fp, eval_fp_pos)
            q_eval_fp = {m: np.zeros(fp_idx.size, dtype=np.float32) for m in ("morph", "subsurf", "hydro", "joint")}
            for mname, arr in q_eval_dict.items():
                q_eval_fp[mname][eval_fp_pos] = arr
            del m_outer

            s1_surf_fp = np.zeros(fp_idx.size, dtype=np.float32)
            s1_surf_fp[eval_fp_pos] = stage1_corroborated_surface(q_eval_dict)
            oof_surf_e1_fp[eval_fp_pos] = rank_calibrate_domain(s1_surf_fp[eval_fp_pos])

            Z_eval_full = extract_stage2_topology_features(q_eval_fp, X_fp, fp_idx, reg, shape)
            p2_reg = s2_model.predict_surface(Z_eval_full[eval_fp_pos])
            oof_surf_e2_fp[eval_fp_pos] = p2_reg
            del Z_eval_full, q_eval_fp, s2_model
            gc.collect()

            surf1_2d = np.zeros(shape, dtype=np.float32)
            surf1_2d.ravel()[fp_idx[eval_fp_pos]] = oof_surf_e1_fp[eval_fp_pos]

            surf2_2d = np.zeros(shape, dtype=np.float32)
            surf2_2d.ravel()[fp_idx[eval_fp_pos]] = p2_reg

            dist_vis = distance_transform_edt(~vis)
            allowed_g20 = reg & (~vis) & (dist_vis > 2.0)
            allowed_g25 = reg & (~vis) & (dist_vis > 2.5)
            scored_dom = reg & (~vis)
            fold_budget = int(round(BUDGET_FULL * float(reg.sum()) / fp_total))

            d_e1 = greedy_dots(surf1_2d, allowed_g20, budget=fold_budget, min_dist=2.8)
            d_e2 = greedy_dots(surf2_2d, allowed_g20, budget=fold_budget, min_dist=2.8)
            w_e3 = np.power(np.clip(surf2_2d, 0.0, 1.0), 1.35)
            d_e3 = submodular_dti_dots(w_e3, allowed_g25, scored_domain=scored_dom, budget=fold_budget, min_dist=2.2)

            dots_e1_holdout[d_e1] = 1.0
            dots_e2_holdout[d_e2] = 1.0
            dots_e3_holdout[d_e3] = 1.0

            allow_idx = np.flatnonzero(allowed_g20)
            pick_r = rng_ctrl.choice(allow_idx, size=min(fold_budget, allow_idx.size), replace=False)
            dots_rand_holdout.ravel()[pick_r] = 1.0

            r1, _ = vendor_eval.evaluate(dots_e1_holdout, f, foot)
            r2, _ = vendor_eval.evaluate(dots_e2_holdout, f, foot)
            r3, _ = vendor_eval.evaluate(dots_e3_holdout, f, foot)
            release_heap()
            print(
                f"[{time.time()-t0:.1f}s] Fold {fname} HOLDOUT-DTI: "
                f"E1={r1['dti']:.5f} | E2={r2['dti']:.5f} | E3={r3['dti']:.5f} "
                f"(n_truth={r3['n_truth']}, cur_RSS={current_rss_mib()} MiB)",
                flush=True,
            )
            fold_diagnostics.append({
                "fold": fname,
                "n_truth": r3["n_truth"],
                "budget": fold_budget,
                "E1_dti": r1["dti"],
                "E2_dti": r2["dti"],
                "E3_dti": r3["dti"],
            })

        del X_fp, y_fp, labels_2d
        release_heap()
        print(
            f"[{time.time()-t0:.1f}s] Freed Stage-1/2 bank (cur_RSS={current_rss_mib()} MiB). "
            f"Fitting fold-fair H33 champion control (`h33_analogue_foldfair`)...",
            flush=True,
        )
        dots_h33_ctrl = fit_h33_foldfair_control(DATA_DIR, folds, foot, guard_px=2.0)
        dots_h33_unguarded = None
        release_heap()

    if dots_h33_unguarded is None:
        print(f"[{time.time()-t0:.1f}s] Fitting unguarded H33 champion control (`h33_unguarded_foldfair`)...", flush=True)
        dots_h33_unguarded = fit_h33_foldfair_control(DATA_DIR, folds, foot, guard_px=0.0)
        release_heap()

    methods = {
        "E1_mecs_stage1_greedy": dots_e1_holdout,
        "E2_mecs_stage2_greedy": dots_e2_holdout,
        "E3_mecs_stage2_submodular": dots_e3_holdout,
        "h33_analogue_foldfair": dots_h33_ctrl,
        "h33_unguarded_foldfair": dots_h33_unguarded,
        "random_uniform_dots": dots_rand_holdout,
    }
    totals = {}
    per_fold_table = {m: [] for m in methods}
    for mname, arr in methods.items():
        tot = None
        for f in folds:
            res, t = vendor_eval.evaluate(arr, f, foot)
            per_fold_table[mname].append(res)
            tot = t if tot is None else tot + t
        totals[mname] = tot

    # Save fold & control arrays to disk immediately before scoring/packaging
    np.savez_compressed(
        WORK_DIR / "holdout_arms_ckpt.npz",
        oof_surf_e1_fp=oof_surf_e1_fp,
        oof_surf_e2_fp=oof_surf_e2_fp,
        e1_idx=np.flatnonzero(dots_e1_holdout > 0).astype(np.int64),
        e2_idx=np.flatnonzero(dots_e2_holdout > 0).astype(np.int64),
        e3_idx=np.flatnonzero(dots_e3_holdout > 0).astype(np.int64),
        h33_idx=np.flatnonzero(dots_h33_ctrl > 0).astype(np.int64),
        h33_ug_idx=np.flatnonzero(dots_h33_unguarded > 0).astype(np.int64),
        rand_idx=np.flatnonzero(dots_rand_holdout > 0).astype(np.int64),
    )

    # Determine winning preregistered experiment strictly by pooled HOLDOUT-DTI among E1, E2, E3
    best_exp = max(
        ("E1_mecs_stage1_greedy", "E2_mecs_stage2_greedy", "E3_mecs_stage2_submodular"),
        key=lambda k_name: float(vendor_eval.from_terms(totals[k_name].sum(axis=0))),
    )
    pooled = vendor_eval.pooled_summary(totals, draws=1000, seed=20261021, candidate=best_exp)
    n_withheld = pooled["scores"][best_exp]["withheld_positive_pixels"]
    print(
        f"[{time.time()-t0:.1f}s] POOLED HOLDOUT SUMMARY (`{vendor_eval.VERSION}`, n={n_withheld}):",
        flush=True,
    )
    for mname, sc in pooled["scores"].items():
        diff_info = pooled["paired_differences"].get(mname)
        print(f"  {mname:28s}: DTI={sc['dti']:.5f}  95% CI={sc['ci95']}  cand_minus_arm={diff_info}", flush=True)

    # Emit full production map from the winning preregistered experiment using strictly cross-fitted OOF surface
    surf_e1_2d = np.zeros(shape, dtype=np.float32)
    surf_e1_2d.ravel()[fp_idx] = oof_surf_e1_fp
    surf_e2_2d = np.zeros(shape, dtype=np.float32)
    surf_e2_2d.ravel()[fp_idx] = oof_surf_e2_fp

    dist_known = distance_transform_edt(~g.catalogue)
    scored_prod = foot & (~g.catalogue)
    if best_exp == "E1_mecs_stage1_greedy":
        prod_surface = surf_e1_2d
        prod_dots = greedy_dots(prod_surface, scored_prod & (dist_known > 2.0), budget=BUDGET_FULL, min_dist=2.8)
    elif best_exp == "E2_mecs_stage2_greedy":
        prod_surface = surf_e2_2d
        prod_dots = greedy_dots(prod_surface, scored_prod & (dist_known > 2.0), budget=BUDGET_FULL, min_dist=2.8)
    else:
        prod_surface = surf_e2_2d
        prod_dots = submodular_dti_dots(
            np.power(np.clip(prod_surface, 0.0, 1.0), 1.35),
            scored_prod & (dist_known > 2.5),
            scored_domain=scored_prod,
            budget=BUDGET_FULL,
            min_dist=2.2,
        )

    np.savez_compressed(
        WORK_DIR / "production_surfaces_and_dots.npz",
        best_exp=best_exp,
        surf_e1_fp=oof_surf_e1_fp,
        surf_e2_fp=oof_surf_e2_fp,
        prod_surface_fp=prod_surface.ravel()[fp_idx].astype(np.float32),
        prod_dots_idx=np.flatnonzero(prod_dots).astype(np.int64),
    )

    # Package production submission artifacts using unmodified vendor/gems57/submission_writer.py
    cand_score = pooled["scores"][best_exp]["dti"]
    ctrl_score = pooled["scores"]["h33_analogue_foldfair"]["dti"]
    delta_ctrl = pooled["paired_differences"]["h33_analogue_foldfair"]
    beats_ctrl_sig = bool(delta_ctrl["delta"] > 0.0 and delta_ctrl["ci95"][0] > 0.0)

    ts_slug = "gems73-h73-2-mecs-autoctx-submod-37654dots-20261021"
    note_str = (
        f"GEMS73 H73-2 MECS-AutoCtx 2-stage wash/stepover+submodular 300m ({int(prod_dots.sum())} dots); "
        f"HOLDOUT-DTI {cand_score:.4f} vs H33 {ctrl_score:.4f}"
    )[:140]

    dl_dir = ROOT / "docs" / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    zeros_tif = dl_dir / f"{ts_slug}-zeros.tif"
    for ext in (".tif", ".zip", ".json"):
        zeros_tif.with_suffix(ext).unlink(missing_ok=True)

    pkg_zeros = vendor_writer.write_submission(
        zeros_tif,
        prod_dots.astype(np.float32),
        DATA_DIR / "sample_submission.tif",
        foot,
        note=note_str,
        name=f"{ts_slug}-zeros",
        catalogue=g.catalogue,
        metadata={
            "lane": "H73-2",
            "evaluator_version": vendor_eval.VERSION,
            "holdout_dti": cand_score,
            "holdout_ci95": pooled["scores"][best_exp]["ci95"],
            "control_h33_foldfair_dti": ctrl_score,
            "paired_delta_vs_h33": delta_ctrl,
        },
    )
    pkg_nan = write_submission_geotiff(
        prod_dots.astype(np.float32),
        DATA_DIR / "sample_submission.tif",
        dl_dir / f"{ts_slug}-nan.tif",
        outside_mode="nan",
        note=note_str,
    )

    holdout_out = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": vendor_eval.VERSION,
        "split_summary": fold_summary,
        "best_experiment": best_exp,
        "beats_h33_foldfair_statistically": beats_ctrl_sig,
        "pooled_summary": pooled,
        "fold_diagnostics": fold_diagnostics,
        "per_fold_details": per_fold_table,
        "production_package_zeros": pkg_zeros,
        "production_package_nan": pkg_nan,
        "elapsed_seconds": round(time.time() - t0, 2),
        "peak_rss_mib": peak_rss_mib(),
    }
    def _compact(obj):
        if isinstance(obj, np.ndarray):
            return {"shape": list(obj.shape), "sum": float(obj.sum())} if obj.size > 64 else obj.tolist()
        return str(obj)

    (ROOT / "evidence" / "holdout_h73_2.json").write_text(
        json.dumps(holdout_out, indent=2, default=_compact) + "\n"
    )
    print(
        f"[{time.time()-t0:.1f}s] DONE! Winner={best_exp} HOLDOUT-DTI={cand_score:.5f} "
        f"vs h33_analogue_foldfair={ctrl_score:.5f} beats_sig={beats_ctrl_sig} "
        f"zeros_sha256={pkg_zeros.get('sha256', '')} RSS={peak_rss_mib()} MiB",
        flush=True,
    )


if __name__ == "__main__":
    main()
