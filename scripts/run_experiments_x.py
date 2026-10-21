#!/usr/bin/env python3
"""GEMSDOE73 session-2 preregistered experiment suite (X1/X2/X3, H73-6).

Frozen in registry/preregistration_x.json BEFORE this script was run.
Reuses the shared vendor evaluator/folds/writer tooling unchanged
(gems57-pooled-hide-v2); catalogue-based quantities derive only from
visible faults; visible faults masked pixel-exactly by the evaluator.
Writes evidence/*_x.json and .cache/work_x/{components_x,dots_x}.npz.
Memory-lean (3 GB sandbox): float32 throughout, arrays freed as consumed.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout, grid as grid_mod, holdout, metric  # noqa: E402
from gems73 import surface as S  # noqa: E402
from gems73 import surface_x as SX  # noqa: E402
from gems73.emit import greedy_dots  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
REFS = ROOT / ".cache" / "refs"
WORK = ROOT / ".cache" / "work_x"
WORK.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"
EV.mkdir(parents=True, exist_ok=True)
BUDGET = 37654
t0 = time.time()


def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)


def dump(name: str, obj) -> None:
    (EV / name).write_text(json.dumps(obj, indent=2) + "\n")
    log("wrote evidence/" + name)


def read_dots(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        a = s.read(1)
    return np.isfinite(a) & (a > 0.5)


g = grid_mod.load_grid(DATA)
foot, cat = g.footprint, g.catalogue
log(f"grid footprint={int(foot.sum())} catalogue={int(cat.sum())}")
dcat = ndimage.distance_transform_edt(~cat)

# H19-5 support + H33 champion (controls / references only, never inputs)
h19_5_support = read_dots(DATA / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
h33_static = read_dots(REFS / "h33_champion.tif")
log(f"h19 support={int(h19_5_support.sum())} h33={int(h33_static.sum())} h33_in_h19_exceptions={int((h33_static & ~h19_5_support).sum())}")

# ---------------------------------------------------------------- components
cache = WORK / "components_x.npz"
if cache.exists():
    z = np.load(cache)
    comp = {k: z[k] for k in z.files}
    log("reused cached components_x")
else:
    base = S.build_components(DATA, foot, log=log)
    comp = dict(scarp_n=base["scarp_n"], pied_soft=base["pied_soft"],
                substep=base["substep"], chain=base["chain"], lidar_valid=base["lidar_valid"])
    del base
    comp["ridge"] = SX.ridge_soft_nms(comp["scarp_n"], foot)
    log(f"ridge built: frac full-value={(comp['ridge'] == comp['scarp_n'])[foot].mean():.3f}")
    comp.update(SX.build_witness(DATA, foot, log=log))
    np.savez_compressed(cache, **comp)
    log("components_x built + cached")

surfaces = {e: SX.make_surface_x(comp["scarp_n"], comp["ridge"], comp["witness"],
                                 comp["pied_soft"], e) for e in ("X1", "X2", "X3")}
for e, s in surfaces.items():
    log(f"surface {e}: mean={float(s[foot].mean()):.4f} p99={float(np.percentile(s[foot], 99)):.4f}")

# ---------------------------------------------------------------- folds (shared, identical to session-1)
folds, quad = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
hidden_all = folds[0]["hidden_all"]
visible = folds[0]["visible"]
withheld = int(hidden_all.sum())
log(f"holdout withheld={withheld} visible={int(visible.sum())}")
dvis = ndimage.distance_transform_edt(~visible)
a_allowed = foot.copy()
for f in folds:
    r = f["region"]
    a_allowed[r] = foot[r] & (~f["masked_known"][r]) & (dvis[r] > 2.0)
del dvis, quad

# ---------------------------------------------------------------- leakage canaries
rng = np.random.default_rng(7)
neg_pool = np.flatnonzero(foot & (dcat > 5.0))
neg_idx = rng.choice(neg_pool, 200_000, replace=False)
del neg_pool
pos_cat = np.flatnonzero(cat)
pos_hid = np.flatnonzero(hidden_all)


def _auc(pos, neg):
    pos = np.asarray(pos, float); neg = np.asarray(neg, float)
    pos = pos[np.isfinite(pos)]; neg = neg[np.isfinite(neg)]
    if pos.size < 10 or neg.size < 10 or np.ptp(np.concatenate([pos, neg])) == 0:
        return None
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    return float(roc_auc_score(y, np.concatenate([pos, neg])))


canaries = {"evidence_class": "HOLDOUT-DTI canary (single-feature AUC; gate symmetric AUC <= 0.90)",
            "lane": "H73-6 session-2", "n_neg_sample": int(neg_idx.size),
            "n_pos_catalogue": int(pos_cat.size), "n_pos_withheld": int(pos_hid.size), "channels": {}}


def canary(name: str, arr: np.ndarray):
    flat = np.asarray(arr).ravel()
    a_cat = _auc(flat[pos_cat], flat[neg_idx])
    a_hid = _auc(flat[pos_hid], flat[neg_idx])
    sym = None if (a_cat is None or a_hid is None) else max(a_cat, 1 - a_cat, a_hid, 1 - a_hid)
    canaries["channels"][name] = {"auc_catalogue": a_cat, "auc_withheld": a_hid,
                                  "symmetric_auc": sym, "pass": bool(sym is not None and sym <= 0.90)}
    log(f"canary {name}: cat={a_cat} hid={a_hid} sym={sym}")


for band, nm in [(3, "band03_tmi_hg"), (5, "band05_iso_grav_slope"), (12, "band12_det_elev"),
                 (15, "band15_depth_to_base"), (19, "band19_det_elev_slope")]:
    canary(nm, S.official_band(DATA, band))
lid = DATA / "external/lidar_scarp_features_u8.tif"
for band, nm in [(1, "lidar_ex_max"), (3, "lidar_step_max"), (6, "lidar_downface_max"),
                 (7, "lidar_upface_max"), (8, "lidar_cross_max")]:
    canary(nm, S.read_band(lid, band).astype(np.float32))
canary("ext_uk_raw", S.read_band(DATA / "external/geodawn_extensions_u8.tif", 2).astype(np.float32))
for nm in ("scarp_n", "pied_soft", "ridge", "witness", "uk_grad_n", "grav_slope_n"):
    canary(f"derived_{nm}", comp[nm])
for e in ("X1", "X2", "X3"):
    canary(f"surface_{e}", surfaces[e])
canaries["all_pass"] = all(c["pass"] for c in canaries["channels"].values())
canaries["max_symmetric_auc"] = max(c["symmetric_auc"] for c in canaries["channels"].values())
dump("canaries_x.json", canaries)

# ---------------------------------------------------------------- emissions (fold-fair + production)
prod_allowed = foot & (dcat > 2.0)
arms: dict[str, np.ndarray] = {}
prod_dots: dict[str, np.ndarray] = {}
for e in ("X1", "X2", "X3"):
    arms[e] = greedy_dots(surfaces[e], a_allowed, BUDGET).astype(np.float32)
    log(f"{e} fold-fair dots={int(arms[e].sum())}")
    prod_dots[e] = greedy_dots(surfaces[e], prod_allowed, BUDGET)
    log(f"{e} production dots={int(prod_dots[e].sum())} on_catalogue={int((prod_dots[e] & cat).sum())}")
support_surf = h19_5_support.astype(np.float32)
arms["h33_analogue_foldfair"] = greedy_dots(support_surf, a_allowed & h19_5_support, BUDGET).astype(np.float32)
del support_surf
log(f"h33 analogue fold-fair dots={int(arms['h33_analogue_foldfair'].sum())}")
rng_surf = np.random.default_rng(73).random(surfaces["X1"].shape, dtype=np.float32)
arms["random_control"] = greedy_dots(rng_surf, a_allowed, BUDGET).astype(np.float32)
del rng_surf
arms["h33_static_reference"] = h33_static.astype(np.float32)

# ---------------------------------------------------------------- pooled hide-and-recover
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
summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=73073, candidate="X1")
summary["per_fold"] = per_fold
summary["fold_receipts"] = [f["receipt"] for f in folds]
summary["lane"] = "H73-6 session-2 (X1/X2/X3)"
dump("holdout_x_all_arms.json", summary)
scores = {k: v["dti"] for k, v in summary["scores"].items()}
log("HOLDOUT-DTI pooled:", {k: round(v, 4) for k, v in scores.items()})

best_e = max(("X1", "X2", "X3"), key=lambda e: scores[e])
if best_e != "X1":
    summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=73073, candidate=best_e)
    summary["per_fold"] = per_fold
    summary["fold_receipts"] = [f["receipt"] for f in folds]
    summary["lane"] = "H73-6 session-2 (X1/X2/X3)"
    dump("holdout_x_all_arms.json", summary)
delta = summary["paired_differences"]["h33_analogue_foldfair"]
beats_control = bool(delta["delta"] > 0 and delta["ci95"][0] > 0)
log(f"best={best_e} delta vs control={delta['delta']:.4f} CI={delta['ci95']} beats={beats_control}")
dump("holdout_x_paired.json", summary)

# ---------------------------------------------------------------- SGMC piedmont proxy (report only)
sg = S.read_band(DATA / "external/derived_sgmc_faults_100m_u8.tif", 1) > 0
slope = S.official_band(DATA, 19)
depth = S.official_band(DATA, 15)
pied_hard = foot & (depth >= 250) & (slope <= float(np.nanpercentile(slope[cat], 80)))
del slope, depth
sg_pied = sg & (dcat > 3.0) & pied_hard
proxy = {"evidence_class": "PROXY-DTI (SGMC off-catalogue piedmont subset; report only, never used for selection)",
         "truth_pixels": int(sg_pied.sum()), "piedmont_domain_pixels": int(pied_hard.sum()), "dti": {}}
for name, dd in [("h33_champion", h33_static)] + [(e, prod_dots[e]) for e in ("X1", "X2", "X3")]:
    proxy["dti"][name] = metric.dti_binary(dd, sg_pied, valid=foot & ~cat)["dti"]
dump("proxy_sgmc_piedmont_x.json", proxy)
del sg, sg_pied, pied_hard

selection = {
    "lane": "H73-6 session-2",
    "best_experiment": best_e,
    "best_holdout_dti": scores[best_e],
    "control_holdout_dti": scores["h33_analogue_foldfair"],
    "random_holdout_dti": scores["random_control"],
    "all_scores": scores,
    "paired_delta_vs_control": delta,
    "beats_control_ci_excluding_0": beats_control,
    "canaries_all_pass": canaries["all_pass"],
    "canaries_max_symmetric_auc": canaries["max_symmetric_auc"],
    "production_dots": int(prod_dots[best_e].sum()),
    "evaluator_version": "gems57-pooled-hide-v2",
    "withheld_positive_pixels": withheld,
    "runtime_s": round(time.time() - t0, 1),
}
dump("selection_x.json", selection)

np.savez_compressed(WORK / "dots_x.npz",
                    **{f"prod_{e}": prod_dots[e] for e in prod_dots},
                    surf_best=surfaces[best_e], best=np.array([best_e]))
log(f"saved dots_x.npz best={best_e}")
log("DONE", selection)
