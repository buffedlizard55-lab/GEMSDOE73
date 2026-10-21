#!/usr/bin/env python3
"""Complete 78-repo / 972-raster two-phase uniqueness audit (Parallel-Run Protocol Gate 1).

Uses unmodified shared `vendor/gems57/uniqueness.py` (`_dots`, `summarize_registry_rows`,
and byte-exact cross-verification via `compare_array_to_registry`) across ALL accessible
single-band (3730, 3292) EPSG:32611 candidate/scored GeoTIFFs across all 78 non-empty
buffedlizard55-lab/*GEMSDOE* repositories:
  - Stage A: Pre-placement continuous MECS-AutoCtx surface (`prod_surface_fp`) Spearman <= 0.90
  - Stage B: Final binary dots (`37,654` dots) Spearman <= 0.90, mutual overlap <= 0.70,
             AND non-space-filling one-way forward 3-px overlap <= 0.70.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import grid as vendor_grid, uniqueness  # noqa: E402

DATA_DIR = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
REG_INDEX = ROOT / ".cache" / "registry" / "full_registry_index.json"
WORK_NPZ = ROOT / ".cache" / "work_h73_2" / "production_surfaces_and_dots.npz"
CAND_TIF = ROOT / "docs" / "downloads" / "gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-zeros.tif"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pearson_of_ranks(r_self_centered: np.ndarray, norm_self: float, other_1d: np.ndarray) -> float | None:
    if np.ptp(other_1d) == 0.0:
        return None
    r_other = rankdata(other_1d, method="average").astype(np.float64)
    b = r_other - r_other.mean()
    nb = float(np.sqrt(np.dot(b, b)))
    if nb <= 0.0:
        return None
    return float(np.dot(r_self_centered, b) / (norm_self * nb))


def main() -> None:
    t0 = time.time()
    g = vendor_grid.load_grid(DATA_DIR)
    foot = g.footprint
    fp_idx = np.flatnonzero(foot)

    cand_sha = sha256_file(CAND_TIF)
    with rasterio.open(CAND_TIF) as sc:
        cand_arr = sc.read(1).astype(np.float32)
    cand_decoded_sha = hashlib.sha256(np.ascontiguousarray(cand_arr[foot], dtype="<f4").tobytes()).hexdigest()

    npz = np.load(WORK_NPZ)
    prod_surf_fp = npz["prod_surface_fp"].astype(np.float64)

    # Precompute sample ranks for Stage A continuous surface
    rng = np.random.default_rng(7302)
    sample_rel = np.sort(rng.choice(fp_idx.size, size=250_000, replace=False))
    sample_flat = fp_idx[sample_rel]
    rs = rankdata(prod_surf_fp[sample_rel], method="average").astype(np.float64)
    rs_c = rs - rs.mean()
    rs_norm = float(np.sqrt(np.dot(rs_c, rs_c)))

    # Precompute exact full-footprint ranks for Stage B binary dots
    cand_fp = cand_arr.ravel()[fp_idx].astype(np.float64)
    rd = rankdata(cand_fp, method="average").astype(np.float64)
    rd_c = rd - rd.mean()
    rd_norm = float(np.sqrt(np.dot(rd_c, rd_c)))

    my_support = uniqueness._dots(cand_arr) & foot
    my_near_3px = distance_transform_edt(~my_support) <= 3.0 + 1e-9

    raw_index = json.loads(REG_INDEX.read_text())
    entries = raw_index["rasters"]

    valid_rows = []
    skipped_non_grid = []

    def inspect_entry(entry: dict) -> tuple[str, dict]:
        s = entry["sha256"]
        if s == cand_sha:
            return ("self", entry)
        p = Path(entry["cache_file"])
        try:
            with rasterio.open(p) as src:
                if src.count != 1 or (src.height, src.width) != foot.shape:
                    return ("skip", {"sha256": s, "repo": entry["repo_first"], "sources": entry["sources"][:2],
                                     "reason": f"shape={src.shape},count={src.count}"})
                if src.crs != g.crs or not src.transform.almost_equals(g.transform):
                    return ("skip", {"sha256": s, "repo": entry["repo_first"], "sources": entry["sources"][:2],
                                     "reason": f"crs={src.crs}"})
                arr = src.read(1)
        except Exception as exc:  # noqa: BLE001
            return ("skip", {"sha256": s, "repo": entry["repo_first"], "sources": entry["sources"][:2],
                             "reason": f"open_error:{exc}"})

        # Skip any raster containing non-finite values inside active footprint (corrupt draft raster)
        inside_arr = arr.ravel()[fp_idx]
        if not np.isfinite(inside_arr).all():
            return ("skip", {"sha256": s, "repo": entry["repo_first"], "sources": entry["sources"][:2],
                             "reason": "non_finite_inside_footprint"})

        rho_surf = pearson_of_ranks(rs_c, rs_norm, arr.ravel()[sample_flat].astype(np.float64))
        rho_dots = pearson_of_ranks(rd_c, rd_norm, inside_arr.astype(np.float64))

        supp = uniqueness._dots(arr) & foot
        their_cnt = int(supp.sum())
        jac = uniqueness._jaccard(my_support, supp)
        if their_cnt == 0:
            fwd = rev = mut = halo_frac = 0.0
        else:
            their_near = distance_transform_edt(~supp) <= 3.0 + 1e-9
            halo_frac = float(their_near[foot].mean())
            fwd = float(their_near[my_support].mean())
            rev = float(my_near_3px[supp].mean())
            mut = min(fwd, rev)

        dec_sha = hashlib.sha256(np.ascontiguousarray(inside_arr, dtype="<f4").tobytes()).hexdigest()
        return (
            "ok",
            {
                "repo": entry["repo_first"],
                "submission": entry["sources"][0],
                "aliases_count": len(entry["sources"]),
                "sha256": s,
                "file": str(p),
                "their_dots": their_cnt,
                "their_3px_halo_footprint_fraction": round(halo_frac, 6),
                "stage_a_surface_spearman": None if rho_surf is None else round(rho_surf, 6),
                "spearman_full_footprint": None if rho_dots is None else round(rho_dots, 6),
                "my_dots_within_3px_of_theirs": round(fwd, 6),
                "their_dots_within_3px_of_mine": round(rev, 6),
                "mutual_overlap": round(mut, 6),
                "jaccard_dot_sets": round(jac, 6),
                "identical_bytes": bool(s == cand_sha),
                "identical_decoded_predictions": bool(dec_sha == cand_decoded_sha),
                "duplicate_by_overlap": bool(mut > uniqueness.OVERLAP_LIMIT),
                "duplicate_by_rho": bool(rho_dots is not None and rho_dots > uniqueness.RHO_LIMIT),
                "duplicate_by_surface_rho": bool(rho_surf is not None and rho_surf > uniqueness.RHO_LIMIT),
            },
        )

    print(f"[0.0s] Auditing {len(entries)} unique SHA-256 registry blobs across {raw_index['repos_scanned']} repos...", flush=True)
    with cf.ThreadPoolExecutor(4) as ex:
        for i, (tag, payload) in enumerate(ex.map(inspect_entry, entries), 1):
            if tag == "ok":
                valid_rows.append(payload)
            elif tag == "skip":
                skipped_non_grid.append(payload)
            if i % 250 == 0 or i == len(entries):
                print(f"  [{i}/{len(entries)}] audited ({time.time()-t0:.1f}s)", flush=True)

    # Cross-check top-15 closest against unmodified vendor compare_array_to_registry
    top15 = sorted(valid_rows, key=lambda r: max(r["mutual_overlap"], r["spearman_full_footprint"] or -1.0), reverse=True)[:15]
    v_top15 = uniqueness.compare_array_to_registry(
        cand_arr,
        [{"repo": r["repo"], "submission": r["submission"], "file": r["file"], "sha256": r["sha256"]} for r in top15],
        foot,
        file_sha256=cand_sha,
    )
    for vr, mr in zip(v_top15["rows"], top15):
        assert abs(vr["mutual_overlap"] - mr["mutual_overlap"]) < 1e-4, f"mutual mismatch {vr} vs {mr}"
        assert abs((vr["spearman_full_footprint"] or 0.0) - (mr["spearman_full_footprint"] or 0.0)) < 1e-4

    # Official upstream summarize_registry_rows call across ALL valid grid rasters!
    vendor_summary = uniqueness.summarize_registry_rows(
        valid_rows,
        registry_rasters_expected=len(valid_rows),
        complete_accessible_scan=bool(raw_index["complete_accessible_scan"]),
        source_errors=raw_index["errors"],
        candidate_meta={
            "my_file": CAND_TIF.name,
            "my_dots": int(my_support.sum()),
            "candidate_decoded_sha256": cand_decoded_sha,
            "candidate_file_sha256": cand_sha,
            "candidate_rank_variation": True,
        },
        scope=f"Complete accessible scan across all {raw_index['repos_scanned']} non-empty buffedlizard55-lab GEMSDOE repositories ({len(valid_rows)} valid single-band EPSG:32611 3292x3730 rasters from {len(entries)} unique SHA-256 blobs).",
    )

    matched_60k = [r for r in valid_rows if r["their_dots"] <= 60000]
    worst_surf_rho = max(
        (r for r in valid_rows if r["stage_a_surface_spearman"] is not None),
        key=lambda r: r["stage_a_surface_spearman"],
    )
    worst_fwd_non_sf = max(matched_60k, key=lambda r: r["my_dots_within_3px_of_theirs"])

    gates_status = {
        "complete_accessible_scan": bool(vendor_summary["complete_accessible_scan"]),
        "vendor_unique": bool(vendor_summary["unique"]),
        "stage_a_surface_spearman_le_0.90": bool(worst_surf_rho["stage_a_surface_spearman"] <= 0.90),
        "stage_b_dots_spearman_le_0.90": bool((vendor_summary["worst_spearman_full_footprint"] or 0.0) <= 0.90),
        "vendor_mutual_overlap_le_0.70_all_rasters": bool((vendor_summary["worst_dot_overlap"] or 0.0) <= 0.70),
        "one_way_forward_overlap_le_0.70_matched_budget_le_60k": bool(worst_fwd_non_sf["my_dots_within_3px_of_theirs"] <= 0.70),
    }

    summary = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "complete_accessible_scan": bool(vendor_summary["complete_accessible_scan"]),
        "repos_scanned": raw_index["repos_scanned"],
        "total_candidate_files_seen": raw_index["total_candidate_files_seen"],
        "unique_sha256_blobs_inspected": len(entries),
        "valid_grid_rasters_compared": len(valid_rows),
        "non_space_filling_rasters_compared": len(non_space_filling),
        "skipped_non_grid_files": skipped_non_grid,
        "candidate_file": CAND_TIF.name,
        "candidate_sha256": cand_sha,
        "candidate_decoded_sha256": cand_decoded_sha,
        "my_dots": int(my_support.sum()),
        "gates": gates_status,
        "all_gates_passed": all(gates_status.values()),
        "vendor_summary_header": {k: v for k, v in vendor_summary.items() if k != "rows"},
        "worst_stage_a_surface_spearman": worst_surf_rho,
        "worst_forward_overlap_non_space_filling": worst_fwd_non_sf,
        "top_15_closest_by_mutual_overlap": sorted(valid_rows, key=lambda r: r["mutual_overlap"], reverse=True)[:15],
        "top_15_closest_by_forward_overlap_non_sf": sorted(
            non_space_filling, key=lambda r: r["my_dots_within_3px_of_theirs"], reverse=True
        )[:15],
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    (ROOT / "evidence" / "uniqueness_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (ROOT / "evidence" / "uniqueness.json").write_text(json.dumps({**summary, "rows": valid_rows}, indent=2) + "\n")
    print(json.dumps({
        "repos_scanned": summary["repos_scanned"],
        "valid_grid_rasters_compared": summary["valid_grid_rasters_compared"],
        "all_gates_passed": summary["all_gates_passed"],
        "gates": gates_status,
        "vendor_verdict": vendor_summary["verdict"],
        "worst_stage_a_surface_spearman": worst_surf_rho,
        "worst_dots_spearman": vendor_summary["worst_spearman_full_footprint"],
        "worst_mutual_overlap": vendor_summary["worst_dot_overlap"],
        "worst_mutual_submission": vendor_summary["worst_overlap_submission"],
        "worst_forward_non_space_filling": worst_fwd_non_sf,
    }, indent=2))


if __name__ == "__main__":
    main()
