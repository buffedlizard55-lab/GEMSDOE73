"""H73-2 MECS-AutoCtx: Two-Stage Multi-Expert Corroborated Steerable Wash-Bridge &
En-Echelon Stepover Auto-Context Engine.

Strictly leakage-free two-stage architecture:
  1. Stage 1 fits four specialized LightGBM classifiers (`M_morph`, `M_subsurf`,
     `M_hydro`, `M_joint`) on strictly held-in spatial training tiles with zero
     catalogue-distance features (`distance_to_catalogue` excluded at every stage).
  2. Within any training pool, 3-tile buffered spatial cross-fitting produces out-of-fold
     Stage-1 probabilities matching the exact out-of-fold distribution seen on target
     regions (outer holdout folds or full cross-fitted production map).
  3. Per-domain uniform percentile calibration maps each expert probability onto `[0, 1]`
     and exponential tail odds `u_e = -log(1 - clip(q_e, 0, 0.9995))`, from which fast
     steerable 2D operators extract 14 structural topology & wash/stepover bridge features:
       - 4 uniform expert quantiles `(q_morph, q_subsurf, q_hydro, q_joint)`
       - 2nd-highest independent physics quantile `corrob_2nd = sort(q_morph, q_subsurf, q_hydro)[1]`
       - Subsurface-to-surface dominance ratio `q_subsurf - q_morph` (blind intrabasin fault indicator)
       - Steerable line persistence across 12 azimuths at 600 m and 1.8 km with perpendicular
         flank suppression (both on `u_joint` and purely subsurface `u_subsurf`)
       - Bilateral Holocene wash-bridge operator `max_theta sqrt(U_ahead(d) * U_behind(d))` at
         `d in {600 m, 1200 m}` across active alluvial fans/washes where local scarps are erased
       - En-echelon relay-ramp stepover operator `max_{theta, s in +-1} sqrt(U_{+L,+s*delta} * U_{-L,-s*delta})`
         at `(L=700 m, delta=300 m)` targeting dilatational geothermal stepovers (Faulds & Hinz 2015)
       - 300 m Tversky kernel-convolved expected TP density `K_300m * u_joint`
       - Cover thickness & multi-sensor witness context `(basement_depth_log, multisensor_witness)`
  4. Stage 2 combines Stage-1 + steerable topology features via shallow regularized GBDT + L2
     logistic blend to emit calibrated fault probability surfaces for E1, E2, and E3.
"""
from __future__ import annotations

import gc

import lightgbm as lgb
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression

from .emit import KERNEL_300M
from .features import IDX_HYDRO, IDX_JOINT, IDX_MORPH, IDX_SUBSURF, fast_pct_rank_1d

STAGE2_FEATURE_NAMES: tuple[str, ...] = (
    "q_morph",
    "q_subsurf",
    "q_hydro",
    "q_joint",
    "corrob_2nd_family",
    "blind_subsurf_excess",
    "worm_joint_600m",
    "worm_joint_1800m",
    "worm_subsurf_1600m",
    "wash_bridge_600m",
    "wash_bridge_1200m",
    "stepover_relay_700m",
    "kernel300_local_mass",
    "cover_depth_log",
)

AZIMUTHS_12: tuple[float, ...] = tuple(float(k * 15.0) for k in range(12))


def rank_calibrate_domain(scores: np.ndarray) -> np.ndarray:
    """Map arbitrary continuous scores inside a spatial domain to `(0, 1)` uniform ranks."""
    return fast_pct_rank_1d(scores)


def _sample_train_indices(y_pool: np.ndarray, max_neg: int = 160_000, seed: int = 73) -> tuple[np.ndarray, float]:
    pos = np.flatnonzero(y_pool > 0)
    neg = np.flatnonzero(y_pool == 0)
    rng = np.random.default_rng(seed)
    if neg.size > max_neg:
        neg_sub = np.sort(rng.choice(neg, size=max_neg, replace=False))
        neg_weight = float(neg.size) / float(max_neg)
    else:
        neg_sub = neg
        neg_weight = 1.0
    idx = np.concatenate([pos, neg_sub])
    return idx, neg_weight


def _fit_single_lgbm(
    X_fp: np.ndarray,
    cols: list[int],
    y_fp: np.ndarray,
    train_fp_pos: np.ndarray,
    seed: int = 73,
    num_leaves: int = 63,
    n_estimators: int = 260,
) -> lgb.LGBMClassifier:
    y_pool = y_fp[train_fp_pos]
    sub_rel, _ = _sample_train_indices(y_pool, max_neg=150_000, seed=seed)
    chosen = train_fp_pos[sub_rel]
    X_tr = np.asarray(X_fp[chosen][:, cols], dtype=np.float32)
    y_tr = y_fp[chosen].astype(np.int32)
    clf = lgb.LGBMClassifier(
        n_estimators=n_estimators,
        learning_rate=0.055,
        num_leaves=num_leaves,
        max_bin=127,
        min_child_samples=100,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_alpha=2.0,
        reg_lambda=8.0,
        random_state=seed,
        n_jobs=2,
        verbose=-1,
    )
    clf.fit(X_tr, y_tr)
    return clf


def fit_stage1_experts(
    X_fp: np.ndarray,
    y_fp: np.ndarray,
    train_fp_pos: np.ndarray,
    seed: int = 73,
) -> dict[str, lgb.LGBMClassifier]:
    return {
        "morph": _fit_single_lgbm(X_fp, IDX_MORPH, y_fp, train_fp_pos, seed=seed + 1, num_leaves=47, n_estimators=220),
        "subsurf": _fit_single_lgbm(X_fp, IDX_SUBSURF, y_fp, train_fp_pos, seed=seed + 2, num_leaves=47, n_estimators=220),
        "hydro": _fit_single_lgbm(X_fp, IDX_HYDRO, y_fp, train_fp_pos, seed=seed + 3, num_leaves=31, n_estimators=160),
        "joint": _fit_single_lgbm(X_fp, IDX_JOINT, y_fp, train_fp_pos, seed=seed + 4, num_leaves=63, n_estimators=280),
    }


def predict_stage1_quantiles(
    models: dict[str, lgb.LGBMClassifier],
    X_fp: np.ndarray,
    eval_fp_pos: np.ndarray,
) -> dict[str, np.ndarray]:
    cols_map = {
        "morph": IDX_MORPH,
        "subsurf": IDX_SUBSURF,
        "hydro": IDX_HYDRO,
        "joint": IDX_JOINT,
    }
    out: dict[str, np.ndarray] = {}
    n = eval_fp_pos.size
    step = 350_000
    for name, cols in cols_map.items():
        p = np.empty(n, dtype=np.float32)
        for s in range(0, n, step):
            sl = eval_fp_pos[s : s + step]
            X_ev = np.asarray(X_fp[sl][:, cols], dtype=np.float32)
            p[s : s + step] = models[name].predict_proba(X_ev)[:, 1].astype(np.float32)
            del X_ev
        out[name] = rank_calibrate_domain(p)
        del p
    return out


def make_spatial_inner_splits(
    train_mask_2d: np.ndarray,
    n_splits: int = 3,
    guard_px: int = 12,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Split a 2D boolean training pool into `n_splits` contiguous spatial bands with `guard_px` buffers."""
    yy, xx = np.nonzero(train_mask_2d)
    # Score along NW-SE diagonal so every split samples mountains, piedmonts, and basins fairly
    diag = (yy.astype(np.float64) / train_mask_2d.shape[0]) + (xx.astype(np.float64) / train_mask_2d.shape[1])
    cuts = np.quantile(diag, np.linspace(0.0, 1.0, n_splits + 1))
    splits = []
    for k in range(n_splits):
        lo, hi = cuts[k], cuts[k + 1]
        sel = (diag >= lo) & (diag <= hi if k == n_splits - 1 else diag < hi)
        val_m = np.zeros_like(train_mask_2d, dtype=bool)
        val_m[yy[sel], xx[sel]] = True
        dist = distance_transform_edt(~val_m)
        tr_m = train_mask_2d & (~val_m) & (dist > guard_px)
        splits.append((tr_m, val_m))
    return splits


def extract_stage2_topology_features(
    q_maps_fp: dict[str, np.ndarray],
    X_fp: np.ndarray,
    fp_idx: np.ndarray,
    domain_mask_2d: np.ndarray,
    shape: tuple[int, int],
) -> np.ndarray:
    """Compute the 14 steerable wash-bridge, en-echelon stepover & corroboration features
    strictly using probability support inside `domain_mask_2d` (zero leakage outside domain!)."""
    h, w = shape
    dom_flat = domain_mask_2d.ravel()[fp_idx]

    qm = np.where(dom_flat, q_maps_fp["morph"], 0.0).astype(np.float32)
    qs = np.where(dom_flat, q_maps_fp["subsurf"], 0.0).astype(np.float32)
    qh = np.where(dom_flat, q_maps_fp["hydro"], 0.0).astype(np.float32)
    qj = np.where(dom_flat, q_maps_fp["joint"], 0.0).astype(np.float32)

    # Exponential upper-tail odds transform: amplifies sharp >98th-percentile fault strands
    uj_fp = -np.log(1.0 - np.clip(qj, 0.0, 0.9992)).astype(np.float32)
    us_fp = -np.log(1.0 - np.clip(qs, 0.0, 0.9992)).astype(np.float32)

    uj_2d = np.zeros((h, w), dtype=np.float32)
    us_2d = np.zeros((h, w), dtype=np.float32)
    uj_2d.ravel()[fp_idx] = uj_fp
    us_2d.ravel()[fp_idx] = us_fp

    uj_sm = gaussian_filter(uj_2d, sigma=1.15).astype(np.float32)
    us_sm = gaussian_filter(us_2d, sigma=1.50).astype(np.float32)

    worm_600 = np.full((h, w), -1e9, dtype=np.float32)
    worm_1800 = np.full((h, w), -1e9, dtype=np.float32)
    worm_sub = np.full((h, w), -1e9, dtype=np.float32)
    bridge_600 = np.zeros((h, w), dtype=np.float32)
    bridge_1200 = np.zeros((h, w), dtype=np.float32)
    stepover_700 = np.zeros((h, w), dtype=np.float32)

    for deg in AZIMUTHS_12:
        th = np.deg2rad(deg)
        ux, uy = float(np.cos(th)), float(np.sin(th))
        px, py = -uy, ux

        def sh(arr: np.ndarray, along_px: float, perp_px: float = 0.0) -> np.ndarray:
            dx = int(round(along_px * ux + perp_px * px))
            dy = int(round(along_px * uy + perp_px * py))
            return np.roll(np.roll(arr, -dy, axis=0), -dx, axis=1)

        # 1. Short-scale 600 m flank-suppressed steerable line integral
        flank3 = 0.5 * (sh(uj_sm, 0.0, -3.0) + sh(uj_sm, 0.0, 3.0))
        a6 = (sh(uj_sm, -3.0) + sh(uj_sm, -1.5) + uj_sm + sh(uj_sm, 1.5) + sh(uj_sm, 3.0)) * 0.2
        np.maximum(worm_600, a6 - 0.65 * flank3, out=worm_600)

        # 2. Meso-scale 1.8 km steerable fault persistence + pure-subsurface persistence
        flank5 = 0.5 * (sh(uj_sm, 0.0, -5.0) + sh(uj_sm, 0.0, 5.0))
        a18 = (
            sh(uj_sm, -9.0) + sh(uj_sm, -6.0) + sh(uj_sm, -3.0) + uj_sm
            + sh(uj_sm, 3.0) + sh(uj_sm, 6.0) + sh(uj_sm, 9.0)
        ) / 7.0
        np.maximum(worm_1800, a18 - 0.65 * flank5, out=worm_1800)

        s16 = (sh(us_sm, -8.0) + sh(us_sm, -4.0) + us_sm + sh(us_sm, 4.0) + sh(us_sm, 8.0)) * 0.2
        flank_s = 0.5 * (sh(us_sm, 0.0, -5.0) + sh(us_sm, 0.0, 5.0))
        np.maximum(worm_sub, s16 - 0.60 * flank_s, out=worm_sub)

        # 3. Bilateral Holocene Wash-Bridge geometric mean across 1.2 km and 2.4 km wash gaps
        ahead6 = 0.5 * (sh(uj_sm, 4.0) + sh(uj_sm, 7.0))
        behind6 = 0.5 * (sh(uj_sm, -4.0) + sh(uj_sm, -7.0))
        np.maximum(bridge_600, np.sqrt(np.maximum(ahead6 * behind6, 0.0)), out=bridge_600)

        ahead12 = 0.5 * (sh(uj_sm, 9.0) + sh(uj_sm, 14.0))
        behind12 = 0.5 * (sh(uj_sm, -9.0) + sh(uj_sm, -14.0))
        np.maximum(bridge_1200, np.sqrt(np.maximum(ahead12 * behind12, 0.0)), out=bridge_1200)

        # 4. En-Echelon Dilatational Stepover / Relay-Ramp Conjugate Bridge (+-300 m offset across 1.4 km)
        for sign in (-1.0, 1.0):
            st_a = 0.5 * (sh(uj_sm, 5.0, sign * 2.0) + sh(uj_sm, 8.0, sign * 3.0))
            st_b = 0.5 * (sh(uj_sm, -5.0, -sign * 2.0) + sh(uj_sm, -8.0, -sign * 3.0))
            np.maximum(stepover_700, np.sqrt(np.maximum(st_a * st_b, 0.0)), out=stepover_700)

    # Zero 15-px outer image border wrap artifacts
    for arr in (worm_600, worm_1800, worm_sub, bridge_600, bridge_1200, stepover_700):
        arr[:15, :] = 0.0
        arr[-15:, :] = 0.0
        arr[:, :15] = 0.0
        arr[:, -15:] = 0.0

    # Exact 300 m Tversky kernel-convolved local expected coverage density
    k300 = np.zeros((h, w), dtype=np.float32)
    for dy, dx, kw in KERNEL_300M:
        sy0, sy1 = max(0, -dy), min(h, h - dy)
        sx0, sx1 = max(0, -dx), min(w, w - dx)
        k300[sy0:sy1, sx0:sx1] += kw * uj_2d[sy0 + dy : sy1 + dy, sx0 + dx : sx1 + dx]

    tri = np.stack([qm, qs, qh], axis=0)
    corrob_2nd = np.partition(tri, 1, axis=0)[1]

    Z = np.empty((fp_idx.size, len(STAGE2_FEATURE_NAMES)), dtype=np.float32)
    Z[:, 0] = qm
    Z[:, 1] = qs
    Z[:, 2] = qh
    Z[:, 3] = qj
    Z[:, 4] = corrob_2nd
    Z[:, 5] = qs - qm
    Z[:, 6] = worm_600.ravel()[fp_idx]
    Z[:, 7] = worm_1800.ravel()[fp_idx]
    Z[:, 8] = worm_sub.ravel()[fp_idx]
    Z[:, 9] = bridge_600.ravel()[fp_idx]
    Z[:, 10] = bridge_1200.ravel()[fp_idx]
    Z[:, 11] = stepover_700.ravel()[fp_idx]
    Z[:, 12] = k300.ravel()[fp_idx]
    Z[:, 13] = np.asarray(X_fp[:, 29], dtype=np.float32)  # basement_depth_log

    del uj_2d, us_2d, uj_sm, us_sm, worm_600, worm_1800, worm_sub, bridge_600, bridge_1200, stepover_700, k300
    gc.collect()
    return Z


class Stage2Combiner:
    """Shallow monotonic/regularized Stage-2 combiner preventing overfitting to spatial context."""

    def __init__(self, seed: int = 73) -> None:
        self.gbdt = lgb.LGBMClassifier(
            n_estimators=180,
            learning_rate=0.04,
            num_leaves=15,
            min_child_samples=250,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.85,
            reg_alpha=5.0,
            reg_lambda=20.0,
            random_state=seed,
            n_jobs=2,
            verbose=-1,
        )
        self.logreg = LogisticRegression(C=0.25, max_iter=300)
        self.mu_: np.ndarray | None = None
        self.sd_: np.ndarray | None = None

    def fit(self, Z_tr: np.ndarray, y_tr_all: np.ndarray, seed: int = 73) -> "Stage2Combiner":
        sub, _ = _sample_train_indices(y_tr_all, max_neg=150_000, seed=seed)
        Zs = Z_tr[sub].astype(np.float32)
        ys = y_tr_all[sub].astype(np.int32)
        self.gbdt.fit(Zs, ys)
        self.mu_ = Zs.mean(axis=0)
        self.sd_ = np.maximum(Zs.std(axis=0), 1e-5)
        Zn = np.clip((Zs - self.mu_) / self.sd_, -8.0, 8.0)
        self.logreg.fit(Zn, ys)
        return self

    def predict_surface(self, Z_ev: np.ndarray) -> np.ndarray:
        p_tree = self.gbdt.predict_proba(Z_ev.astype(np.float32))[:, 1].astype(np.float32)
        Zn = np.clip((Z_ev - self.mu_) / self.sd_, -8.0, 8.0)
        p_lin = self.logreg.predict_proba(Zn)[:, 1].astype(np.float32)
        return (0.72 * p_tree + 0.28 * p_lin).astype(np.float32)


def stage1_corroborated_surface(q_maps_fp: dict[str, np.ndarray]) -> np.ndarray:
    """E1 surface: probability-calibrated blend of the 4 Stage-1 physics experts."""
    tri = np.stack([q_maps_fp["morph"], q_maps_fp["subsurf"], q_maps_fp["hydro"]], axis=0)
    corrob2 = np.partition(tri, 1, axis=0)[1]
    score = (
        0.58 * q_maps_fp["joint"]
        + 0.16 * q_maps_fp["morph"]
        + 0.14 * q_maps_fp["subsurf"]
        + 0.04 * q_maps_fp["hydro"]
        + 0.08 * corrob2
    )
    return score.astype(np.float32)
