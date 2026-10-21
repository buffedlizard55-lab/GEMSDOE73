#!/usr/bin/env python3
"""Uniqueness audit (PARALLEL-RUN PROTOCOL Gate 1) for the GEMSDOE73 H73-M M3 candidate.

Audits BOTH:
  - Stage A (pre-placement continuous surface `surf_M2_off`): Spearman rank correlation
    on a fixed 200k-pixel footprint sample (seed 3) against every registry raster.
  - Stage B (final 37,654 binary dots): shared vendor `compare_array_to_registry`
    (full-footprint exact Spearman + 3 px forward/reverse/mutual dot overlap) against
    the complete accessible registry (60GEMSDOE 62-raster archive + sibling downloads
    GEMSDOE32, GEMSDOE28, GEMSDOE70, 19GEMSDOE, GEMSDOE25, GEMSDOE36, GEMSDOE63, GEMSDOE48
    + GEMSDOE73 PR #1, PR #2, PR #3 rasters + scored mirrors, deduplicated by SHA-256).
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
CAND = ROOT / "docs" / "downloads" / "gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif"
NAN_TWIN = ROOT / "docs" / "downloads" / "gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif"

REFS = [
    Path("/home/user/refs/g60/registry/rasters"),
    Path("/home/user/refs/g32/docs/downloads"),
    Path("/home/user/refs/g28/docs/downloads"),
    Path("/home/user/refs/g70/docs/downloads"),
    Path("/home/user/refs/g19/docs/downloads"),
    Path("/home/user/refs/g25/docs/downloads"),
    Path("/home/user/refs/g36/docs/downloads"),
    Path("/home/user/refs/g63/docs/downloads"),
    Path("/home/user/refs/g48/docs/downloads"),
    DATA / "scored",
    ROOT / "docs" / "downloads",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    g = grid_mod.load_grid(DATA)
    foot = g.footprint

    cand_sha = sha(CAND)
    nan_sha = sha(NAN_TWIN) if NAN_TWIN.exists() else ""

    seen: dict[str, dict] = {}
    n_files = 0
    for d in REFS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.tif")):
            n_files += 1
            digest = sha(p)
            if digest in (cand_sha, nan_sha):
                continue
            if digest not in seen:
                seen[digest] = {
                    "repo": p.parent.parent.parent.name if "downloads" in str(p) else p.parent.name,
                    "submission": p.name,
                    "file": str(p),
                    "sha256": digest,
                    "aliases": 0,
                }
            else:
                seen[digest]["aliases"] += 1

    records = list(seen.values())
    print(f"Registry files scanned={n_files}, unique external/prior rasters by sha256={len(records)}", flush=True)

    # ---- Stage A: sampled Spearman on pre-placement continuous surface (surf_M2_off)
    z = np.load(ROOT / ".cache" / "work" / "h73m_dots.npz")
    surf = np.asarray(z["surf_M2_off"], np.float32)
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
    worst_a = max(ok_a, key=lambda r: abs(r["spearman_sample200k"])) if ok_a else None
    print("Stage A worst |rho|:", worst_a, flush=True)

    # ---- Stage B: vendor full-footprint compare on final 37,654 binary dots
    with rasterio.open(CAND) as s:
        cand_arr = s.read(1).astype(np.float32)
    index = [
        {"repo": r["repo"], "submission": r["submission"], "file": r["file"], "sha256": r["sha256"]}
        for r in records
    ]
    result_b = uniqueness.compare_array_to_registry(cand_arr, index, foot, file_sha256=cand_sha)
    rows_b = result_b.get("rows", [])
    ok_b = [r for r in rows_b if "error" not in r]

    def worst(rows, key):
        vals = [r for r in rows if r.get(key) is not None]
        return max(vals, key=lambda r: r[key]) if vals else None

    sparse_b = [r for r in ok_b if r.get("their_dots", 0) <= 60_000]
    sparse_150k_b = [r for r in ok_b if r.get("their_dots", 0) <= 150_000]

    out = {
        "evidence_class": "REGISTRY-MEASUREMENT (161-raster accessible scan across 60GEMSDOE archive + 8 sibling repos + GEMSDOE73 prior lanes)",
        "candidate_file": CAND.name,
        "candidate_sha256": cand_sha,
        "registry_files_seen": n_files,
        "registry_unique_by_sha256": len(records),
        "stage_A_surface_sampled_spearman": {
            "sample_pixels": 200_000,
            "seed": 3,
            "worst": worst_a,
            "max_abs_rho": abs(worst_a["spearman_sample200k"]) if worst_a else None,
            "pass_le_0.90": bool(worst_a and abs(worst_a["spearman_sample200k"]) <= 0.90),
            "rows": stage_a,
        },
        "stage_B_final_dots_vendor_full": {
            "summary": {k: v for k, v in result_b.items() if k != "rows"},
            "worst_spearman": worst(ok_b, "spearman_full_footprint"),
            "worst_mutual_overlap": worst(ok_b, "mutual_overlap"),
            "worst_forward_sparse_le60k": worst(sparse_b, "my_dots_within_3px_of_theirs"),
            "worst_forward_sparse_le150k": worst(sparse_150k_b, "my_dots_within_3px_of_theirs"),
            "worst_forward_literal_all": worst(ok_b, "my_dots_within_3px_of_theirs"),
            "rows": rows_b,
            "errors": [r for r in rows_b if "error" in r],
        },
    }
    wb = out["stage_B_final_dots_vendor_full"]
    out["gates"] = {
        "surface_rho_le_0.90": out["stage_A_surface_sampled_spearman"]["pass_le_0.90"],
        "dots_rho_le_0.90": bool(
            wb["worst_spearman"] and abs(wb["worst_spearman"]["spearman_full_footprint"] or 0) <= 0.90
        ),
        "dots_mutual_overlap_le_0.70": bool(
            wb["worst_mutual_overlap"] and wb["worst_mutual_overlap"]["mutual_overlap"] <= 0.70
        ),
        "dots_forward_sparse_le60k_le_0.70": bool(
            wb["worst_forward_sparse_le60k"]
            and wb["worst_forward_sparse_le60k"]["my_dots_within_3px_of_theirs"] <= 0.70
        ),
        "dots_forward_literal_all_le_0.70": bool(
            wb["worst_forward_literal_all"]
            and wb["worst_forward_literal_all"]["my_dots_within_3px_of_theirs"] <= 0.70
        ),
    }
    (ROOT / "evidence" / "uniqueness_h73m.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        json.dumps(
            {
                "registry_unique_by_sha256": len(records),
                "gates": out["gates"],
                "worst_surface_rho": out["stage_A_surface_sampled_spearman"]["worst"],
                "worst_dots_rho": wb["worst_spearman"],
                "worst_mutual": wb["worst_mutual_overlap"],
                "worst_forward_sparse_le60k": wb["worst_forward_sparse_le60k"],
                "worst_forward_sparse_le150k": wb["worst_forward_sparse_le150k"],
                "worst_forward_literal_all": wb["worst_forward_literal_all"],
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
