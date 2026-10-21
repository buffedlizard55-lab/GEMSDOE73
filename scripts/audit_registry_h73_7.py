#!/usr/bin/env python3
"""Uniqueness audit (parallel-run protocol rule 1) for the H73-7 candidate.

Stage A (pre-placement surface): Spearman of the H73-7 production surface vs
every registry raster on a fixed 200k-pixel footprint sample (seed 3).
Stage B (final dots): shared vendor compare_array_to_registry (full-footprint
Spearman + 3 px forward/reverse/mutual dot overlap) vs the same registry.

Registry scope = docs/downloads of the sibling clones fetched this session
(GEMSDOE32, GEMSDOE28, GEMSDOE70, 19GEMSDOE, GEMSDOE25, GEMSDOE36), the
hash-pinned scored mirrors, and this repo's own previously published
rasters, deduplicated by file SHA-256, candidate excluded. Accessible scan,
not a complete organizer registry — recorded in the output (IR-73-07).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, uniqueness  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
sel = json.loads((ROOT / "evidence" / "selection_h73-7.json").read_text())
CAND = ROOT / "docs" / "downloads" / f"gems73-h73-7-hardfault-pu-{sel['best_experiment'].lower()}-37654dots-20261021.tif"
REFS_ROOT = Path("/home/user/refs")
REFS = [REFS_ROOT / r / "docs" / "downloads" for r in
        ("GEMSDOE32", "GEMSDOE28", "GEMSDOE70", "19GEMSDOE", "GEMSDOE25", "GEMSDOE36")]
REFS += [DATA / "scored", ROOT / "docs" / "downloads"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


g = grid_mod.load_grid(DATA)
foot = g.footprint
cand_sha = sha(CAND)

seen: dict[str, dict] = {}
n_files = 0
for d in REFS:
    if not d.exists():
        print("missing registry dir:", d, flush=True)
        continue
    for p in sorted(d.glob("*.tif")):
        n_files += 1
        digest = sha(p)
        if digest == cand_sha:
            continue
        if digest not in seen:
            repo = p.parent.parent.parent.name if "refs" in str(p) else (
                "GEMSDOE73(self)" if str(ROOT) in str(p) else "scored-mirrors")
            seen[digest] = {"repo": repo, "submission": p.name,
                            "file": str(p), "sha256": digest, "aliases": 0}
        else:
            seen[digest]["aliases"] += 1
records = list(seen.values())
print(f"registry files seen={n_files} unique-by-sha256={len(records)} (candidate excluded)", flush=True)

# ---- Stage A: production surface, sampled Spearman
surf = np.load(ROOT / ".cache" / "work7" / "surf_production.npy").astype(np.float32)
rng = np.random.default_rng(3)
fp_idx = np.flatnonzero(foot)
sample = rng.choice(fp_idx, 200_000, replace=False)
mine_s = surf.ravel()[sample].astype(float)
stage_a = []
for r in records:
    try:
        with rasterio.open(r["file"]) as s:
            if s.count != 1 or (s.height, s.width) != surf.shape:
                stage_a.append({**r, "error": "grid/band mismatch"})
                continue
            a = s.read(1)
        tv = np.nan_to_num(a.ravel()[sample].astype(float), nan=0.0)
        rho = float(spearmanr(mine_s, tv).statistic) if np.ptp(tv) > 0 else None
        stage_a.append({**r, "spearman_sample200k": rho})
    except Exception as e:  # noqa: BLE001
        stage_a.append({**r, "error": str(e)})
ok_a = [r for r in stage_a if r.get("spearman_sample200k") is not None]
worst_a = max(ok_a, key=lambda r: r["spearman_sample200k"]) if ok_a else None
print("stage A worst:", worst_a, flush=True)

# ---- Stage B: vendor full-footprint compare on final dots
with rasterio.open(CAND) as s:
    cand_arr = s.read(1).astype(np.float32)
index = [{"repo": r["repo"], "submission": r["submission"], "file": r["file"], "sha256": r["sha256"]}
         for r in records]
result_b = uniqueness.compare_array_to_registry(cand_arr, index, foot, file_sha256=cand_sha)
rows_b = result_b.get("rows", [])
ok_b = [r for r in rows_b if "error" not in r]


def worst(rows, key):
    vals = [r for r in rows if r.get(key) is not None]
    return max(vals, key=lambda r: r[key]) if vals else None


# champion-specific row (must be identifiable whatever the vendor summary says)
champ = [r for r in ok_b if "e5eb6e7e" in r.get("submission", "")]
own = [r for r in ok_b if r.get("repo") == "GEMSDOE73(self)"]

out = {
    "evidence_class": "REGISTRY-MEASUREMENT (accessible scan, not a complete organizer registry)",
    "lane": "H73-7",
    "candidate_file": CAND.name, "candidate_sha256": cand_sha,
    "registry_files_seen": n_files, "registry_unique_by_sha256": len(records),
    "stage_A_surface_sampled_spearman": {
        "sample_pixels": 200_000, "seed": 3, "worst": worst_a, "rows": stage_a,
        "max_rho": worst_a["spearman_sample200k"] if worst_a else None,
        "pass_le_0.90": bool(worst_a and worst_a["spearman_sample200k"] <= 0.90)},
    "stage_B_final_dots_vendor_full": {
        "summary": {k: v for k, v in result_b.items() if k != "rows"},
        "rows": rows_b,
        "worst_spearman": worst(ok_b, "spearman_full_footprint"),
        "worst_forward_overlap": worst(ok_b, "my_dots_within_3px_of_theirs"),
        "worst_mutual_overlap": worst(ok_b, "mutual_overlap"),
        "vs_h33_champion_rows": champ,
        "vs_own_repo_previous_rasters": own,
        "errors": [r for r in rows_b if "error" in r]},
}
wb = out["stage_B_final_dots_vendor_full"]
out["gates"] = {
    "surface_rho_le_0.90": out["stage_A_surface_sampled_spearman"]["pass_le_0.90"],
    "dots_rho_le_0.90": bool(wb["worst_spearman"] and (wb["worst_spearman"]["spearman_full_footprint"] or 0) <= 0.90),
    "mutual_overlap_le_0.70": bool(wb["worst_mutual_overlap"] and (wb["worst_mutual_overlap"]["mutual_overlap"] or 0) <= 0.70),
}
out["gates"]["all_pass"] = all(out["gates"].values())
(ROOT / "evidence" / "uniqueness_h73-7.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"gates": out["gates"],
                  "worst_mutual": wb["worst_mutual_overlap"],
                  "worst_forward": wb["worst_forward_overlap"],
                  "champion_rows": champ, "own_rows": own}, indent=2))
print("wrote evidence/uniqueness_h73-7.json")
