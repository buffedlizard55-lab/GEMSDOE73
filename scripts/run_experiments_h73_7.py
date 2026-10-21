#!/usr/bin/env python3
"""GEMSDOE73 lane H73-7 experiment suite (registry/preregistration_h73-7.json).

Fold-fair hard-fault PU ranker (HistGradientBoosting) vs the shared
gems57-pooled-hide-v2 hide-and-recover instrument. Reuses, without forking:
vendor/gems57/{grid,holdout,evaluate_holdout,metric}.py and
src/gems73/{surface,emit}.py. Maximum 3 experiments (E1/E2/E3), preregistered.

Outputs: evidence/{canaries_h73-7,holdout_h73-7,selection_h73-7}.json and
.cache/work7/{components.npz, surf_*.npy, dots_*.npz, models}. Production
surface (selected recipe retrained on the full catalogue) is written to
.cache/work7/surf_production.npy for scripts/build_submission_h73_7.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
from scipy import ndimage
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout, grid as grid_mod, holdout, metric  # noqa: E402
from gems73 import surface as S  # noqa: E402
from gems73.emit import greedy_dots  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
WORK = ROOT / ".cache" / "work7"
WORK.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"
BUDGET = 37654
SEED_TRAIN = 7307
N_NEG = 250_000
t0 = time.time()


def log(*a):
    print(f"[{time.time()-t0:8.1f}s]", *a, flush=True)


def dump(name: str, obj) -> None:
    (EV / name).write_text(json.dumps(obj, indent=2) + "\n")
    log("wrote evidence/" + name)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# --------------------------------------------------------------------- channels
# (name, file key, band) — physical per-pixel transforms only; no catalogue-derived
# channel, no scored raster, no SGMC. Official band names are read from the
# GeoTIFF band descriptions of training_features.tif itself.
TF = DATA / "training_features.tif"
LID = DATA / "external" / "lidar_scarp_features_u8.tif"
RAD = DATA / "external" / "geodawn_rad_u8.tif"
EXT = DATA / "external" / "geodawn_extensions_u8.tif"

OFFICIAL = [  # 1-based band -> short name (from band descriptions, verified this session)
    (1, "mag_anom"), (2, "rtp"), (3, "tmi_hg"), (4, "geod_2ndinv"),
    (5, "iso_grav_anom_slope"), (6, "tc"), (7, "geod_shearrate"),
    (8, "geod_dilaterate"), (9, "tmi_vg"), (10, "deq_n100a15"),
    (11, "iso_grav_anom_vg"), (12, "det_elev"), (13, "iso_grav_anom"),
    (14, "tmi"), (15, "depth_to_base_surf"), (16, "ieq_n100a15"),
    (17, "cond_surf"), (18, "iso_grav_anom_hg"), (19, "det_elev_slope"),
]
LIDAR = [(1, "ex_max"), (2, "ex_mean"), (3, "step_max"), (4, "lapneg_max"),
         (5, "lappos_max"), (6, "downface_max"), (7, "upface_max"),
         (8, "cross_max"), (9, "relief"), (10, "coh100")]  # excl. 11 strike (circular), 12 valid (coverage)
RADIO = [(RAD, 1, "K"), (RAD, 2, "Th"), (RAD, 3, "U"), (RAD, 4, "TC"),
         (EXT, 1, "ThK"), (EXT, 2, "UK"), (EXT, 3, "UTh"), (EXT, 4, "TMI_up150")]
COMP_NAMES = ["scarp_n", "chain", "substep", "pied_soft"]

CHANNELS_FULL: list[tuple[str, str]] = []   # (channel name, group)
for _, n in OFFICIAL:
    CHANNELS_FULL.append((f"off_{n}", "official"))
for _, n in LIDAR:
    CHANNELS_FULL.append((f"lid_{n}", "lidar"))
for _, _, n in RADIO:
    CHANNELS_FULL.append((f"rad_{n}", "radiometric"))
for n in COMP_NAMES:
    CHANNELS_FULL.append((f"cmp_{n}", "component"))
assert len(CHANNELS_FULL) == 41, len(CHANNELS_FULL)
IDX_E3 = [i for i, (_, grp) in enumerate(CHANNELS_FULL) if grp in ("official", "radiometric")]
assert len(IDX_E3) == 27

SENTINEL = -1e30


def read_channel_flat(idx: int, flat_idx: np.ndarray, comp: dict) -> np.ndarray:
    """Values of channel `idx` at flat pixel indices (full-band read, then index)."""
    name, grp = CHANNELS_FULL[idx]
    if grp == "component":
        return comp[name[4:]].ravel()[flat_idx].astype(np.float32)
    if grp == "official":
        band = OFFICIAL[idx][0]
        with rasterio.open(TF) as s:
            a = s.read(band).astype(np.float32)
        a[a < SENTINEL] = np.nan
        return a.ravel()[flat_idx]
    if grp == "lidar":
        band = LIDAR[idx - 19][0]
        with rasterio.open(LID) as s:
            a = s.read(band).astype(np.float32)
        return a.ravel()[flat_idx]
    path, band, _ = RADIO[idx - 29]
    with rasterio.open(path) as s:
        a = s.read(band).astype(np.float32)
    a[a == 0.0] = np.nan  # uint8 stacks declare nodata=0.0
    return a.ravel()[flat_idx]


def read_channel_window(idx: int, r0: int, r1: int, comp: dict,
                        handles: dict) -> np.ndarray:
    name, grp = CHANNELS_FULL[idx]
    if grp == "component":
        return comp[name[4:]][r0:r1].astype(np.float32)
    win = Window(0, r0, 3292, r1 - r0)
    if grp == "official":
        a = handles["tf"].read(OFFICIAL[idx][0], window=win).astype(np.float32)
        a[a < SENTINEL] = np.nan
        return a
    if grp == "lidar":
        return handles["lid"].read(LIDAR[idx - 19][0], window=win).astype(np.float32)
    path, band, _ = RADIO[idx - 29]
    a = handles[str(path)].read(band, window=win).astype(np.float32)
    a[a == 0.0] = np.nan
    return a


def norm01_vals(vals: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return np.clip((vals - lo) / max(hi - lo, 1e-12), 0.0, 1.0)


def fit_model(X, y, w):
    m = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
        min_samples_leaf=40, l2_regularization=1.0,
        early_stopping=False, random_state=SEED_TRAIN)
    m.fit(X, y, sample_weight=w)
    return m


def predict_surface(model, cols: list[int], comp: dict, shape) -> np.ndarray:
    """Chunked full-grid prediction (200-row blocks) -> float32 surface."""
    surf = np.zeros(shape, np.float32)
    handles = {"tf": rasterio.open(TF), "lid": rasterio.open(LID),
               str(RAD): rasterio.open(RAD), str(EXT): rasterio.open(EXT)}
    try:
        for r0 in range(0, shape[0], 200):
            r1 = min(shape[0], r0 + 200)
            X = np.empty(((r1 - r0) * shape[1], len(cols)), np.float32)
            for j, ci in enumerate(cols):
                X[:, j] = read_channel_window(ci, r0, r1, comp, handles).ravel()
            surf[r0:r1] = model.predict_proba(X)[:, 1].reshape(r1 - r0, shape[1])
            del X
    finally:
        for h in handles.values():
            h.close()
    return surf


# --------------------------------------------------------------------- grid/folds
g = grid_mod.load_grid(DATA)
foot, cat = g.footprint, g.catalogue
log(f"grid footprint={int(foot.sum())} catalogue={int(cat.sum())}")

folds, quad = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
hidden_all = folds[0]["hidden_all"]
visible = folds[0]["visible"]
withheld = int(hidden_all.sum())
log(f"holdout withheld={withheld} visible={int(visible.sum())}")
if withheld != 11321:
    raise SystemExit(f"STOP: withheld {withheld} != 11321 (control reproduction precondition)")

dvis = ndimage.distance_transform_edt(~visible)
dcat = ndimage.distance_transform_edt(~cat)
a_allowed = foot.copy()
for f in folds:
    r = f["region"]
    a_allowed[r] = foot[r] & (~f["masked_known"][r]) & (dvis[r] > 2.0)
prod_allowed = foot & (dcat > 2.0)

# --------------------------------------------------------------------- components
cache = WORK / "components.npz"
if cache.exists():
    z = np.load(cache)
    comp = {k: z[k] for k in COMP_NAMES}
    log("reused cached H73-1 components")
else:
    full = S.build_components(DATA, foot, log=log)
    comp = {k: full[k] for k in COMP_NAMES}
    np.savez_compressed(cache, **comp)
    log("components built + cached")

# --------------------------------------------------------------------- samples
rng = np.random.default_rng(SEED_TRAIN)
pos_idx_vis = np.flatnonzero(visible & foot)
neg_pool_vis = np.flatnonzero(foot & (dvis > 5.0))
neg_idx = rng.choice(neg_pool_vis, N_NEG, replace=False)
sample_idx = np.concatenate([pos_idx_vis, neg_idx])
y = np.concatenate([np.ones(pos_idx_vis.size, np.int8), np.zeros(neg_idx.size, np.int8)])
log(f"train sample: pos(visible)={pos_idx_vis.size} neg={neg_idx.size} "
    f"(neg pool >5px from VISIBLE only; hidden contamination is the PU setting)")

# hardness percentiles from footprint (physical bands only, label-blind)
fp_sample = np.random.default_rng(11).choice(np.flatnonzero(foot), 300_000, replace=False)


def pct01_99(vals):
    v = vals[np.isfinite(vals)]
    return float(np.percentile(v, 1.0)), float(np.percentile(v, 99.0))


step_ch = 19 + 2    # lid_step_max -> LIDAR list position 2 (band 3)
depth_ch = 14       # off_depth_to_base_surf (band 15 -> position 14)
slope_ch = 18       # off_det_elev_slope (band 19 -> position 18)

X_cache = WORK / "sample_matrix.npz"
if X_cache.exists():
    z = np.load(X_cache)
    X = z["X"]
    assert np.array_equal(z["sample_idx"], sample_idx)
    lo_step, hi_step, lo_dep, hi_dep, lo_slo, hi_slo = [float(v) for v in z["hard_pct"]]
    log("reused cached sample matrix", X.shape)
else:
    X = np.empty((sample_idx.size, 41), np.float32)
    for ci in range(41):
        X[:, ci] = read_channel_flat(ci, sample_idx, comp)
    lo_step, hi_step = pct01_99(read_channel_flat(step_ch, fp_sample, comp))
    lo_dep, hi_dep = pct01_99(read_channel_flat(depth_ch, fp_sample, comp))
    lo_slo, hi_slo = pct01_99(read_channel_flat(slope_ch, fp_sample, comp))
    np.savez_compressed(X_cache, X=X, sample_idx=sample_idx,
                        hard_pct=np.array([lo_step, hi_step, lo_dep, hi_dep, lo_slo, hi_slo]))
    log("sample matrix built", X.shape)

hard = (1 - norm01_vals(np.nan_to_num(X[:, step_ch], nan=lo_step), lo_step, hi_step)
        + norm01_vals(np.nan_to_num(X[:, depth_ch], nan=lo_dep), lo_dep, hi_dep)
        + 1 - norm01_vals(np.nan_to_num(X[:, slope_ch], nan=hi_slo), lo_slo, hi_slo)) / 3.0
w_hard = np.where(y == 1, 1.0 + 2.0 * hard, 1.0).astype(np.float64)
w_flat = np.ones_like(w_hard)
log(f"hardness: pos mean={float(hard[y==1].mean()):.3f} p10={float(np.percentile(hard[y==1],10)):.3f} "
    f"p90={float(np.percentile(hard[y==1],90)):.3f}; weight range "
    f"[{float(w_hard.min()):.2f},{float(w_hard.max()):.2f}]")

# --------------------------------------------------------------------- canaries
rng_c = np.random.default_rng(7)
neg_pool_c = np.flatnonzero(foot & (dcat > 5.0))
neg_idx_c = rng_c.choice(neg_pool_c, 200_000, replace=False)
pos_cat = np.flatnonzero(cat)
pos_hid = np.flatnonzero(hidden_all)


def _auc(pos, neg):
    pos = np.asarray(pos, float); neg = np.asarray(neg, float)
    pos = pos[np.isfinite(pos)]; neg = neg[np.isfinite(neg)]
    if pos.size < 10 or neg.size < 10 or np.ptp(np.concatenate([pos, neg])) == 0:
        return None
    yy = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    return float(roc_auc_score(yy, np.concatenate([pos, neg])))


canaries = {"evidence_class": "HOLDOUT-DTI canary (single-feature AUC; gate symmetric AUC <= 0.90)",
            "lane": "H73-7", "n_neg_sample": int(neg_idx_c.size),
            "n_pos_catalogue": int(pos_cat.size), "n_pos_withheld": int(pos_hid.size),
            "note": "Diagnostic negatives >5 px from the FULL catalogue (same protocol as evidence/canaries.json); training negatives use visible-only distance.",
            "channels": {}}
all_idx_c = np.concatenate([pos_cat, pos_hid, neg_idx_c])
for ci, (name, grp) in enumerate(CHANNELS_FULL):
    vals = read_channel_flat(ci, all_idx_c, comp)
    v_cat = vals[:pos_cat.size]
    v_hid = vals[pos_cat.size:pos_cat.size + pos_hid.size]
    v_neg = vals[pos_cat.size + pos_hid.size:]
    a_cat, a_hid = _auc(v_cat, v_neg), _auc(v_hid, v_neg)
    sym = None if (a_cat is None or a_hid is None) else max(a_cat, 1 - a_cat, a_hid, 1 - a_hid)
    canaries["channels"][name] = {"group": grp, "auc_catalogue": a_cat, "auc_withheld": a_hid,
                                  "symmetric_auc": sym,
                                  "pass": bool(sym is not None and sym <= 0.90)}
    log(f"canary {name}: sym={sym}")
canaries["all_pass"] = all(c["pass"] for c in canaries["channels"].values())
canaries["max_symmetric_auc"] = max(c["symmetric_auc"] for c in canaries["channels"].values())
dump("canaries_h73-7.json", canaries)
if not canaries["all_pass"]:
    raise SystemExit("STOP: leakage canary failed (symmetric AUC > 0.90)")

# --------------------------------------------------------------------- experiments
EXPERIMENTS = {
    "E1": dict(cols=list(range(41)), weights="hard"),
    "E2": dict(cols=list(range(41)), weights="flat"),
    "E3": dict(cols=IDX_E3, weights="hard"),
}
surfaces: dict[str, np.ndarray] = {}
for name, cfg in EXPERIMENTS.items():
    sp = WORK / f"surf_{name}.npy"
    if sp.exists():
        surfaces[name] = np.load(sp)
        log(f"{name}: reused cached surface")
        continue
    w = w_hard if cfg["weights"] == "hard" else w_flat
    model = fit_model(X[:, cfg["cols"]], y, w)
    log(f"{name}: model fitted ({cfg['weights']} weights, {len(cfg['cols'])} channels)")
    surf = predict_surface(model, cfg["cols"], comp, foot.shape)
    surf[~foot] = 0.0
    np.save(sp, surf)
    surfaces[name] = surf
    log(f"{name}: surface predicted, range [{float(surf.min()):.4f},{float(surf.max()):.4f}]")

# fold-fair + production-candidate dot fields (production retrain happens after selection)
arms: dict[str, np.ndarray] = {}
for e in EXPERIMENTS:
    arms[e] = greedy_dots(surfaces[e], a_allowed, BUDGET).astype(np.float32)
    log(f"{e} fold-fair dots={int(arms[e].sum())}")

def read_dots(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        a = s.read(1)
    return np.isfinite(a) & (a > 0.5)

h19_5_support = read_dots(DATA / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
h33_path = Path("/home/user/refs/GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
h33_static = read_dots(h33_path)
arms["h33_analogue_foldfair"] = greedy_dots(
    h19_5_support.astype(np.float32), a_allowed & h19_5_support, BUDGET).astype(np.float32)
log(f"h33 analogue fold-fair dots={int(arms['h33_analogue_foldfair'].sum())}")
rng_surf = np.random.default_rng(73).random(foot.shape, dtype=np.float32)
arms["random_control"] = greedy_dots(rng_surf, a_allowed, BUDGET).astype(np.float32)
arms["h33_static_reference"] = h33_static.astype(np.float32)

forensic = {
    "evidence_class": "MEASURED-HERE from hash-pinned bytes (H73-7 session re-verification)",
    "counts": {"h33_champion": int(h33_static.sum()),
               "h19_5_support": int(h19_5_support.sum())},
    "h33_file_sha256": sha256_file(h33_path),
    "h33_min_distance_to_catalogue_px": float(dcat[h33_static].min()),
    "static_dti_vs_full_catalogue": {
        "h33_champion": metric.dti_binary(h33_static, cat, valid=foot)["dti"]},
}
dump("forensic_h73-7.json", forensic)

# --------------------------------------------------------------------- holdout scoring
terms: dict[str, np.ndarray] = {}
per_fold: dict[str, list] = {}
for name, pred in arms.items():
    tot = None
    per_fold[name] = []
    for f in folds:
        res, t = evaluate_holdout.evaluate(pred, f, foot)
        per_fold[name].append({"fold": f["receipt"]["fold"], "dti": res["dti"],
                               "n_truth": res["n_truth"], "n_emitted": res["n_emitted"]})
        tot = t if tot is None else tot + t
    terms[name] = tot
    log(f"arm {name} evaluated")

ctrl_dti = float(evaluate_holdout.from_terms(terms["h33_analogue_foldfair"].sum(axis=0)))
log(f"CONTROL REPRODUCTION: h33_analogue_foldfair pooled DTI={ctrl_dti:.6f} (target 0.093861)")
if abs(ctrl_dti - 0.09386085313581098) > 0.002:
    raise SystemExit("STOP: control reproduction failed; do not interpret experiments")

summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=73073, candidate="E1")
summary["per_fold"] = per_fold
summary["fold_receipts"] = [f["receipt"] for f in folds]
scores = {k: v["dti"] for k, v in summary["scores"].items()}
log("HOLDOUT-DTI pooled:", {k: round(v, 4) for k, v in scores.items()})

best_e = max(EXPERIMENTS, key=lambda e: scores[e])
if best_e != "E1":
    summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=73073, candidate=best_e)
    summary["per_fold"] = per_fold
    summary["fold_receipts"] = [f["receipt"] for f in folds]
    scores = {k: v["dti"] for k, v in summary["scores"].items()}
summary["lane"] = "H73-7"
summary["selected_experiment"] = best_e
dump("holdout_h73-7.json", summary)

delta = summary["paired_differences"]["h33_analogue_foldfair"]
beats = bool(delta["delta"] > 0 and delta["ci95"][0] > 0)
log(f"best={best_e} delta vs control={delta['delta']:.4f} CI={delta['ci95']} beats={beats}")

selection = {
    "lane": "H73-7",
    "best_experiment": best_e,
    "best_holdout_dti": scores[best_e],
    "best_holdout_ci95": summary["scores"][best_e]["ci95"],
    "control_holdout_dti": scores["h33_analogue_foldfair"],
    "control_reproduction_target": 0.09386085313581098,
    "paired_delta_vs_control": delta,
    "beats_control_ci_excluding_0": beats,
    "random_holdout_dti": scores["random_control"],
    "canaries_all_pass": canaries["all_pass"],
    "canaries_max_symmetric_auc": canaries["max_symmetric_auc"],
    "evaluator_version": "gems57-pooled-hide-v2",
    "withheld_positive_pixels": withheld,
    "all_scores": scores,
    "runtime_s": round(time.time() - t0, 1),
}
dump("selection_h73-7.json", selection)

# --------------------------------------------------------------------- production twin
# Selected recipe retrained on the FULL catalogue (preregistered production rule).
# Requires a second sample matrix (positives = all catalogue px; negatives >5 px
# from the full catalogue, same seed/size/formula).
cfg = EXPERIMENTS[best_e]
prod_surf_path = WORK / "surf_production.npy"
if not prod_surf_path.exists():
    rng_p = np.random.default_rng(SEED_TRAIN)
    pos_full = np.flatnonzero(cat & foot)
    neg_full_pool = np.flatnonzero(foot & (dcat > 5.0))
    neg_full = rng_p.choice(neg_full_pool, N_NEG, replace=False)
    sidx = np.concatenate([pos_full, neg_full])
    yy = np.concatenate([np.ones(pos_full.size, np.int8), np.zeros(neg_full.size, np.int8)])
    Xp = np.empty((sidx.size, len(cfg["cols"])), np.float32)
    hard_cols = {}
    for j, ci in enumerate(cfg["cols"]):
        col = read_channel_flat(ci, sidx, comp)
        Xp[:, j] = col
        if ci in (step_ch, depth_ch, slope_ch):
            hard_cols[ci] = col
    for ci in (step_ch, depth_ch, slope_ch):
        if ci not in hard_cols:
            hard_cols[ci] = read_channel_flat(ci, sidx, comp)
    hp = (1 - norm01_vals(np.nan_to_num(hard_cols[step_ch], nan=lo_step), lo_step, hi_step)
          + norm01_vals(np.nan_to_num(hard_cols[depth_ch], nan=lo_dep), lo_dep, hi_dep)
          + 1 - norm01_vals(np.nan_to_num(hard_cols[slope_ch], nan=hi_slo), lo_slo, hi_slo)) / 3.0
    wp = (np.where(yy == 1, 1.0 + 2.0 * hp, 1.0) if cfg["weights"] == "hard"
          else np.ones(yy.size))
    model_p = fit_model(Xp, yy, wp.astype(np.float64))
    surf_p = predict_surface(model_p, cfg["cols"], comp, foot.shape)
    surf_p[~foot] = 0.0
    np.save(prod_surf_path, surf_p)
    del Xp, surf_p
    log("production surface predicted (full-catalogue twin)")
else:
    log("production surface already cached")

np.savez_compressed(WORK / "dots_foldfair.npz",
                    **{f"foldfair_{e}": arms[e] > 0 for e in EXPERIMENTS})
(WORK / "DONE").write_text(json.dumps(selection, indent=2) + "\n")
log("DONE", selection)
