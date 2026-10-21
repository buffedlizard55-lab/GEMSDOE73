#!/usr/bin/env python3
"""GEMSDOE73 preregistered experiment suite (E1/E2/E3, see registry/preregistration.json).

Steps: forensic lineage check -> H73-1 components -> leakage canaries ->
fold-fair hide-and-recover holdout (shared gems57-pooled-hide-v2) ->
SGMC-piedmont proxy (report only) -> candidate selection by the frozen rule.
Writes evidence/*.json and .cache/work/{components,surfaces,dots}.npz.
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
from scipy import ndimage
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout, grid as grid_mod, holdout, metric  # noqa: E402
from gems73 import surface as S  # noqa: E402
from gems73.emit import greedy_dots  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
WORK = ROOT / ".cache" / "work"
WORK.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"
EV.mkdir(parents=True, exist_ok=True)
BUDGET = 37654
t0 = time.time()


def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def dump(name: str, obj) -> None:
    (EV / name).write_text(json.dumps(obj, indent=2) + "\n")
    log("wrote evidence/" + name)


def read_dots(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        a = s.read(1)
    return np.isfinite(a) & (a > 0.5)


# ---------------------------------------------------------------- forensic
g = grid_mod.load_grid(DATA)
foot, cat = g.footprint, g.catalogue
log(f"grid footprint={int(foot.sum())} catalogue={int(cat.sum())}")

refs = {
    "h33_champion": Path("/home/user/refs/g32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    "d28": DATA / "scored/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
    "h19_5": DATA / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif",
}
masks = {k: read_dots(p) for k, p in refs.items()}
dcat = ndimage.distance_transform_edt(~cat)
forensic = {
    "evidence_class": "MEASURED-HERE from hash-pinned bytes",
    "counts": {k: int(v.sum()) for k, v in masks.items()},
    "on_catalogue": {k: int((v & cat).sum()) for k, v in masks.items()},
    "subset_exceptions": {
        "h33_not_in_d28": int((masks["h33_champion"] & ~masks["d28"]).sum()),
        "d28_not_in_h19_5": int((masks["d28"] & ~masks["h19_5"]).sum()),
        "h33_not_in_h19_5": int((masks["h33_champion"] & ~masks["h19_5"]).sum()),
    },
    "h33_equals_d28_minus_dcat_le2": bool(
        np.array_equal(masks["h33_champion"], masks["d28"] & (dcat > 2.0))),
    "d28_dots_dcat_le2": int((masks["d28"] & (dcat <= 2.0)).sum()),
    "static_dti_vs_full_catalogue": {
        k: metric.dti_binary(v, cat, valid=foot)["dti"] for k, v in masks.items()},
    "file_sha256": {k: sha256_file(p) for k, p in refs.items()},
}
h19_5_support = masks["h19_5"]
h33_static = masks["h33_champion"]
dump("forensic.json", forensic)
log("forensic:", forensic["subset_exceptions"], forensic["static_dti_vs_full_catalogue"])

# ---------------------------------------------------------------- components
cache = WORK / "components.npz"
if cache.exists():
    z = np.load(cache)
    comp = {k: z[k] for k in ("scarp_n", "chain", "substep", "pied_soft", "lidar_valid")}
    log("reused cached components")
else:
    comp = S.build_components(DATA, foot, log=log)
    np.savez_compressed(cache, **comp)
    log("components built + cached")
surfaces = {e: S.make_surface(comp, e) for e in ("E1", "E2", "E3")}

# ---------------------------------------------------------------- holdout folds (shared)
folds, quad = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
hidden_all = folds[0]["hidden_all"]
visible = folds[0]["visible"]
masked_known = folds[0]["masked_known"]
withheld = int(hidden_all.sum())
log(f"holdout withheld={withheld} visible={int(visible.sum())}")
dvis = ndimage.distance_transform_edt(~visible)
a_allowed = foot.copy()
for f in folds:
    r = f["region"]
    a_allowed[r] = foot[r] & (~f["masked_known"][r]) & (dvis[r] > 2.0)

# ---------------------------------------------------------------- leakage canaries
rng = np.random.default_rng(7)
neg_pool = np.flatnonzero(foot & (dcat > 5.0))
neg_idx = rng.choice(neg_pool, 200_000, replace=False)
pos_cat = np.flatnonzero(cat)
pos_hid = np.flatnonzero(hidden_all)


def auc_pair(vals_cat_pos, vals_hid_pos, vals_neg):
    def _auc(pos, neg):
        pos = np.asarray(pos, float); neg = np.asarray(neg, float)
        m = np.isfinite(pos); pos = pos[m]
        m = np.isfinite(neg); neg = neg[m]
        if pos.size < 10 or neg.size < 10 or np.ptp(np.concatenate([pos, neg])) == 0:
            return None
        y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
        return float(roc_auc_score(y, np.concatenate([pos, neg])))
    return _auc(vals_cat_pos, vals_neg), _auc(vals_hid_pos, vals_neg)


canaries = {"evidence_class": "HOLDOUT-DTI canary (single-feature AUC; gate symmetric AUC <= 0.90)",
            "n_neg_sample": int(neg_idx.size), "n_pos_catalogue": int(pos_cat.size),
            "n_pos_withheld": int(pos_hid.size), "channels": {}}


def canary(name: str, arr: np.ndarray):
    flat = np.asarray(arr).ravel()
    a_cat, a_hid = auc_pair(flat[pos_cat], flat[pos_hid], flat[neg_idx])
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
for nm in ("scarp_n", "chain", "substep", "pied_soft"):
    canary(f"derived_{nm}", comp[nm])
for e in ("E1", "E2", "E3"):
    canary(f"surface_{e}", surfaces[e])
canaries["all_pass"] = all(c["pass"] for c in canaries["channels"].values())
canaries["max_symmetric_auc"] = max(c["symmetric_auc"] for c in canaries["channels"].values())
dump("canaries.json", canaries)

# ---------------------------------------------------------------- emissions (fold-fair + production)
prod_allowed = foot & (dcat > 2.0)
arms: dict[str, np.ndarray] = {}
prod_dots: dict[str, np.ndarray] = {}
for e in ("E1", "E2", "E3"):
    arms[e] = greedy_dots(surfaces[e], a_allowed, BUDGET).astype(np.float32)
    log(f"{e} fold-fair dots={int(arms[e].sum())}")
    prod_dots[e] = greedy_dots(surfaces[e], prod_allowed, BUDGET)
    log(f"{e} production dots={int(prod_dots[e].sum())}")
support_surf = h19_5_support.astype(np.float32)
arms["h33_analogue_foldfair"] = greedy_dots(
    support_surf, a_allowed & h19_5_support, BUDGET).astype(np.float32)
log(f"h33 analogue fold-fair dots={int(arms['h33_analogue_foldfair'].sum())}")
rng_surf = np.random.default_rng(73).random(surfaces["E1"].shape, dtype=np.float32)
arms["random_control"] = greedy_dots(rng_surf, a_allowed, BUDGET).astype(np.float32)
arms["h33_static_reference"] = h33_static.astype(np.float32)
np.savez_compressed(WORK / "dots.npz",
                    **{f"prod_{e}": prod_dots[e] for e in prod_dots},
                    **{f"surf_{e}": surfaces[e] for e in surfaces})

# ---------------------------------------------------------------- Instrument A: pooled hide-and-recover
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
summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=73073, candidate="E1")
summary["per_fold"] = per_fold
summary["fold_receipts"] = [f["receipt"] for f in folds]
summary["note"] = ("candidate key 'E1' is the bootstrap reference arm only; selection below "
                   "re-runs pooled_summary with the winning experiment as candidate if E1 is not best")
dump("holdout_all_arms.json", summary)
dump("holdout_E1_paired.json", summary)  # E1-referenced paired deltas for the run card
scores = {k: v["dti"] for k, v in summary["scores"].items()}
log("HOLDOUT-DTI pooled:", {k: round(v, 4) for k, v in scores.items()})

# selection by frozen rule: best experiment vs h33_analogue_foldfair, paired CI excluding 0
best_e = max(("E1", "E2", "E3"), key=lambda e: scores[e])
if best_e != "E1":
    summary = evaluate_holdout.pooled_summary(terms, draws=1000, seed=73073, candidate=best_e)
    summary["per_fold"] = per_fold
    summary["fold_receipts"] = [f["receipt"] for f in folds]
    dump("holdout_all_arms.json", summary)
delta = summary["paired_differences"]["h33_analogue_foldfair"]
beats_control = bool(delta["delta"] > 0 and delta["ci95"][0] > 0)
log(f"best={best_e} delta vs control={delta['delta']:.4f} CI={delta['ci95']} beats={beats_control}")

# ---------------------------------------------------------------- SGMC piedmont proxy (report only)
sg = S.read_band(DATA / "external/derived_sgmc_faults_100m_u8.tif", 1) > 0
slope = S.official_band(DATA, 19)
depth = S.official_band(DATA, 15)
pied_hard = foot & (depth >= 250) & (slope <= float(np.nanpercentile(slope[cat], 80)))
sg_pied = sg & (dcat > 3.0) & pied_hard
proxy = {"evidence_class": "PROXY-DTI (SGMC off-catalogue piedmont subset; report only, never used for selection)",
         "truth_pixels": int(sg_pied.sum()), "piedmont_domain_pixels": int(pied_hard.sum()), "dti": {}}
for name, dd in [("h33_champion", h33_static)] + [(e, prod_dots[e]) for e in ("E1", "E2", "E3")]:
    proxy["dti"][name] = metric.dti_binary(dd, sg_pied, valid=foot & ~cat)["dti"]
dump("proxy_sgmc_piedmont.json", proxy)

selection = {
    "best_experiment": best_e,
    "best_holdout_dti": scores[best_e],
    "control_holdout_dti": scores["h33_analogue_foldfair"],
    "paired_delta_vs_control": delta,
    "beats_control_ci_excluding_0": beats_control,
    "canaries_all_pass": canaries["all_pass"],
    "production_dots": int(prod_dots[best_e].sum()),
    "evaluator_version": "gems57-pooled-hide-v2",
    "withheld_positive_pixels": withheld,
    "runtime_s": round(time.time() - t0, 1),
}
dump("selection.json", selection)
log("DONE", selection)
