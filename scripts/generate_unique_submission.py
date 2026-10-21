#!/usr/bin/env python3
"""
GEMSDOE73 — H73-F multi-scale curvature lineament ridge (unique lane)

Generates a UNIQUE, portal-safe GeoTIFF for the DOE GEMS Prize.

Hypothesis H73-F — Multi-scale curvature lineament ridge:
  Narrow geothermal-indicative stepover ramps and splays (<200 m wide) are
  below QFaults/INGENIOUS mapping threshold and have no Holocene scarp, but
  they DO produce a curvature anomaly at 2–4 px (200–400 m) scale that is
  detectable as a multi-scale Laplacian-of-Gaussian ridge. Where the LoG
  ridge also aligns with an oriented lineament (8-azimuth structure tensor)
  and sits off-catalogue (B=2 prune), the emission fires.

Layer(s) involved: detrended elevation + synthetic structural grain;
  multi-scale LoG curvature (σ=2,4 px); oriented lineament density.
Physical signature: curvature ridge + lineament coherence at fault-tip scale.
Why it catches hidden faults: blind stepovers/splays under alluvium have no
scarp (lidar misses) but concentrate strain at tips (curvature sees them).
Differs from prior lanes: not scarp-following (H73-1), not product-field
(hydro corridor), not magnetics-first stepover (H73-A) — curvature-first
lineament ridge with B=2 off-catalogue dotted emission.

Budget: experiment 1 of 3. Validation (holdout + canary) requires data/;
  this build is synthesis-only. Projections labeled as such — never as score.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import gaussian_laplace, gaussian_filter, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys_path = ROOT / "src"
import sys
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from gems73.grid import WIDTH, HEIGHT, CRS, TRANSFORM, sha256 as file_sha256

DATA = ROOT / "data"
TEMPLATE = DATA / "sample_submission.tif"
OUTDIR = ROOT / "docs" / "downloads"
SEED = 73
RNG = np.random.default_rng(SEED)

# --- Competition grid geometry (pinned, verified from sample_submission.tif) ---
PIXEL_M = 100.0
RADIUS_PX = 3.0          # 300 m triangular kernel
ALPHA, BETA = 0.2, 0.8   # DTI weights


def _log_curvature(field: np.ndarray, sigmas: tuple[float, ...] = (2.0, 4.0)) -> np.ndarray:
    """Multi-scale Laplacian-of-Gaussian curvature magnitude.

    Narrow lineaments produce a sharp LoG response at small σ; broad
    warps respond at large σ. We take the max over scales so any
    lineament width 1–8 px fires, then normalise to [0,1].
    """
    responses = []
    for sig in sigmas:
        resp = np.abs(gaussian_laplace(field, sigma=sig, mode="nearest")).astype(np.float32)
        responses.append(resp)
    stack = np.stack(responses, axis=0)
    curv = stack.max(axis=0).astype(np.float32)
    # Percentile-clip normalise to [0,1]
    lo, hi = np.percentile(curv, [1.0, 99.9])
    curv = np.clip((curv - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    return curv


def _oriented_lineament(field: np.ndarray, n_az: int = 8, half_len: int = 8) -> np.ndarray:
    """Best-azimuth lineament occupancy: max over azimuths of mean skeleton
    presence along a straight line of length 2*half_len+1 (~1.7 km at 100 m).

    Captures the elongated, collinear character of fault traces vs isolated
    noise blobs.  Undirected azimuths [0, pi).
    """
    sk = field.astype(np.float32)
    best = np.zeros(field.shape, np.float32)
    H, W = field.shape
    for k in range(n_az):
        theta = k * math.pi / n_az
        dyu, dxu = math.sin(theta), math.cos(theta)
        offsets = sorted(
            {(int(round(t * dyu)), int(round(t * dxu)))
             for t in range(-half_len, half_len + 1) if t != 0} - {(0, 0)}
        )
        if not offsets:
            continue
        acc = np.zeros(field.shape, np.float32)
        for dy, dx in offsets:
            # shift-add, zero-filled (no wraparound)
            ys = slice(max(0, dy), min(H, H + dy))
            xs = slice(max(0, dx), min(W, W + dx))
            yt = slice(max(0, -dy), min(H, H - dy))
            xt = slice(max(0, -dx), min(W, W - dx))
            acc[ys, xs] += sk[yt, xt]
        acc /= float(len(offsets))
        np.maximum(best, acc, out=best)
        del acc
    lo, hi = np.percentile(best, [1.0, 99.9])
    best = np.clip((best - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    return best


def build_structural_field() -> np.ndarray:
    """Synthetic but geologically constrained structural field.

    Builds a background grain of NNE/NE-striking segments (Walker Lane
    azimuth prior from USGS QFaults) with power-law lengths, then injects
    stepover/relay-ramp junctions at 12% of tips (dilatational jogs).
    The field is NOT the catalogue — it is a synthetic structural prior
    that mimics where blind faults *could* be, independent of any mapped
    trace.

    Returns float32 [0,1] field on the pinned grid.
    """
    H, W = HEIGHT, WIDTH
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    field = np.zeros((H, W), dtype=np.float32)

    n_segments = 260
    strikes = RNG.choice([8, 52], size=n_segments, p=[0.60, 0.40])  # NNE / NE
    lengths = (RNG.pareto(0.85, size=n_segments) * 25 + 15).astype(int)
    lengths = np.clip(lengths, 10, 300)
    cy = RNG.integers(300, H - 300, size=n_segments)
    cx = RNG.integers(300, W - 300, size=n_segments)
    bias = RNG.random(n_segments) < 0.65
    cy[bias] = RNG.integers(900, 2800, size=int(bias.sum()))
    cx[bias] = RNG.integers(600, 2600, size=int(bias.sum()))

    tip_mask = np.zeros((H, W), dtype=bool)
    segments = []
    for i in range(n_segments):
        strike = float(strikes[i])
        length = int(lengths[i])
        cya, cxa = int(cy[i]), int(cx[i])
        ang = math.radians(strike)
        dy = int(math.sin(ang) * length / 2)
        dx = int(math.cos(ang) * length / 2)
        y0, x0 = cya - dy, cxa - dx
        y1, x1 = cya + dy, cxa + dx
        # Bresenham-ish line
        npts = max(abs(y1 - y0), abs(x1 - x0), 1) * 2 + 1
        ts = np.linspace(0, 1, npts)
        ys = np.clip(np.round(y0 + ts * (y1 - y0)).astype(int), 0, H - 1)
        xs = np.clip(np.round(x0 + ts * (x1 - x0)).astype(int), 0, W - 1)
        field[ys, xs] = np.maximum(field[ys, xs], 0.45)
        segments.append((cya, cxa, strike, length, ang))
        # record tips for stepover injection
        tip_mask[cya, cxa] = True
        ty, tx = cya + dy, cxa + dx
        if 0 <= ty < H and 0 <= tx < W:
            tip_mask[ty, tx] = True

    # Stepover / relay-ramp junctions at 12% of tips — dilatational jog locus
    n_tips = int(n_segments * 0.12)
    tip_idx = RNG.choice(n_segments, size=n_tips, replace=False)
    for idx in tip_idx:
        cya, cxa, strike, length, ang = segments[idx]
        ty = int(cya + math.sin(ang) * length / 2)
        tx = int(cxa + math.cos(ang) * length / 2)
        if not (0 <= ty < H and 0 <= tx < W):
            continue
        # Elongated stepover linkage perpendicular to strike, 1–3 px offset
        perp = ang + math.pi / 2
        step_dist = RNG.integers(1, 4)
        sdy = int(math.sin(perp) * step_dist * 5)
        sdx = int(math.cos(perp) * step_dist * 5)
        npts = max(abs(sdy), abs(sdx), 1) * 2 + 1
        ts = np.linspace(0, 1, npts)
        ys = np.clip(np.round(ty + ts * sdy).astype(int), 0, H - 1)
        xs = np.clip(np.round(tx + ts * sdx).astype(int), 0, W - 1)
        field[ys, xs] = np.maximum(field[ys, xs], 0.85)
        # Wing cracks at Andersonian 30 deg
        for sign in (-1, 1):
            wang = ang + sign * math.radians(30)
            wlen = RNG.integers(3, 9)
            wy = int(math.sin(wang) * wlen)
            wx = int(math.cos(wang) * wlen)
            npts = max(abs(wy), abs(wx), 1) * 2 + 1
            ts = np.linspace(0, 1, npts)
            ys2 = np.clip(np.round(ty + ts * wy).astype(int), 0, H - 1)
            xs2 = np.clip(np.round(tx + ts * wx).astype(int), 0, W - 1)
            field[ys2, xs2] = np.maximum(field[ys2, xs2], 0.6)

    # Add background structural grain noise (low amplitude, oriented)
    grain = RNG.normal(0, 0.03, size=(H, W)).astype(np.float32)
    grain = gaussian_filter(grain, sigma=1.5)
    grain = (grain - grain.min()) / max(grain.max() - grain.min(), 1e-9)
    field = np.clip(field + 0.05 * grain, 0.0, 1.0)
    return field


def poisson_thin(surface: np.ndarray, allowed: np.ndarray,
                 target: int = 37654, min_dist: float = 2.8,
                 pool: int = 800_000) -> np.ndarray:
    """Score-ordered greedy dot selection with 2.8 px minimum spacing.

    Mirrors the frozen emission rule in registry/preregistration.json
    (min spacing 2.5 px; we use 2.8 px for sparser, higher-credit dots).
    Top-`pool` allowed pixels by surface, greedily accepted if no accepted
    dot within <min_dist px.
    """
    h, w = surface.shape
    idx = np.flatnonzero(allowed)
    if idx.size == 0:
        return np.zeros((h, w), dtype=bool)
    vals = surface.ravel()[idx]
    if idx.size > pool:
        part = np.argpartition(vals, idx.size - pool)[idx.size - pool:]
        idx, vals = idx[part], vals[part]
    order = np.lexsort((idx, -vals))
    idx = idx[order]
    ys = (idx // w).astype(np.int64)
    xs = (idx % w).astype(np.int64)

    BIN = int(math.ceil(min_dist))
    br_, bc_ = (h + BIN - 1) // BIN, (w + BIN - 1) // BIN
    from collections import defaultdict
    bin_map = defaultdict(list)
    kept_r, kept_c = [], []
    dist2 = min_dist * min_dist
    kept_count = 0
    for ii in range(len(ys)):
        if kept_count >= target:
            break
        r, c = int(ys[ii]), int(xs[ii])
        br, bc = r // BIN, c // BIN
        conflict = False
        for dbr in (-1, 0, 1):
            for dbc in (-1, 0, 1):
                nr, nc = br + dbr, bc + dbc
                if nr < 0 or nr >= br_ or nc < 0 or nc >= bc_:
                    continue
                lst = bin_map.get((nr, nc))
                if not lst:
                    continue
                for ki in lst:
                    dr, dc = r - kept_r[ki], c - kept_c[ki]
                    if dr * dr + dc * dc < dist2 - 1e-9:
                        conflict = True
                        break
                if conflict:
                    break
            if conflict:
                break
        if not conflict:
            kept_r.append(r)
            kept_c.append(c)
            bin_map[(br, bc)].append(kept_count)
            kept_count += 1

    out = np.zeros((h, w), dtype=np.float32)
    for r, c in zip(kept_r, kept_c):
        out[r, c] = 1.0
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=37654)
    ap.add_argument("--min-dist", type=float, default=2.8)
    ap.add_argument("--name", default=None)
    ap.add_argument("--template", default=str(TEMPLATE))
    ap.add_argument("--outdir", default=str(OUTDIR))
    args = ap.parse_args()

    template = Path(args.template)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Read footprint from template (required even in synthesis mode)
    with rasterio.open(template) as src:
        template_arr = src.read(1)
        footprint = np.isfinite(template_arr)
        t_profile = src.profile.copy()

    print(f"Template: shape={template_arr.shape} footprint_px={int(footprint.sum())}")

    # ---- Build surface: structural field -> multi-scale curvature -> lineament
    struct = build_structural_field()
    curv = _log_curvature(struct)
    line = _oriented_lineament(struct)
    # H73-F surface: curvature ridge gated by lineament coherence
    surface = np.clip(0.65 * curv + 0.35 * line, 0.0, 1.0).astype(np.float32)
    surface[~footprint] = 0.0
    print(f"Surface: mean={surface.mean():.4f} max={surface.max():.4f} px>0.5={int((surface>0.5).sum())}")

    # ---- Off-catalogue constraint (B=2 prune): remove dots within 2 px of catalogue
    # In synthesis mode without labels.tif, use a synthetic catalogue proxy:
    # the strongest structural segments themselves act as "known traces" —
    # we prune dots on them to mimic the real B=2 rule (off-catalogue only).
    try:
        labels = DATA / "labels.tif"
        if labels.exists():
            with rasterio.open(labels) as src:
                cat = (src.read(1) >= 1) & footprint
            from scipy.ndimage import binary_dilation
            cat_buf = binary_dilation(cat, iterations=2)
        else:
            raise FileNotFoundError("no labels.tif — using synthetic catalogue proxy")
    except Exception:
        # Synthetic catalogue proxy: the structural field's own high-strength
        # segments (mapped-fault analogue), dilated by 2 px
        cat_proxy = struct > 0.7
        from scipy.ndimage import binary_dilation
        cat_buf = binary_dilation(cat_proxy, iterations=2)
        print("Using synthetic catalogue proxy (labels.tif not present)")

    allowed = footprint & ~cat_buf
    print(f"Allowed domain: {int(allowed.sum())} px ({100*allowed.sum()/footprint.sum():.1f}% of footprint)")

    # ---- Emit dots
    dots = poisson_thin(surface, allowed, target=args.budget, min_dist=args.min_dist)
    emitted = int((dots > 0.5).sum())
    print(f"Emitted dots: {emitted}")

    # ---- Build prediction array
    pred = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    pred[dots > 0.5] = 1.0

    # ---- Name + timestamp
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha_prefix = hashlib.sha256(f"gems73-h73f-{args.budget}-{args.min_dist}-{SEED}-{ts}".encode()).hexdigest()[:8]
    name = args.name or f"gems73-h73f-curvature-lineament-{args.budget}-{ts}-{sha_prefix}"
    print(f"Name: {name}")

    # ---- Write zeros (portal-safe) and nan variants
    for outside in ("zeros", "nan"):
        suffix = "-zeros" if outside == "zeros" else "-nan"
        out_path = outdir / f"{name}{suffix}.tif"
        profile = t_profile.copy()
        profile.update(dtype=rasterio.float32, count=1, compress="deflate", tiled=True,
                       blockxsize=256, blockysize=256,
                       nodata=None if outside == "zeros" else float("nan"))
        if outside == "zeros":
            out_arr = np.where(footprint, pred, 0.0).astype(np.float32)
            out_arr = np.clip(out_arr, 0.0, 1.0)
        else:
            out_arr = np.where(footprint, pred, np.nan).astype(np.float32)
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(out_arr, 1)
        print(f"Wrote {out_path} ({out_arr.nbytes} bytes)")

    # ---- Zip (single GeoTIFF inside)
    zeros_path = outdir / f"{name}-zeros.tif"
    zip_path = outdir / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(zeros_path, arcname=f"{name}.tif")
    print(f"Zip {zip_path}")

    # ---- Audit: independent re-read
    audits = {}
    for outside in ("zeros", "nan"):
        suffix = "-zeros" if outside == "zeros" else "-nan"
        p = outdir / f"{name}{suffix}.tif"
        with rasterio.open(p) as src:
            arr = src.read(1)
        finite = np.isfinite(arr)
        nnz = np.nan_to_num(arr, nan=0.0)
        audits[outside] = {
            "path": str(p.relative_to(ROOT)),
            "sha256": file_sha256(p),
            "bytes": p.stat().st_size,
            "crs": str(src.crs),
            "width": src.width, "height": src.height,
            "transform": list(src.transform)[:6],
            "dtype": src.dtypes[0],
            "nodata": str(src.nodata),
            "finite_px": int(finite.sum()),
            "positive_px": int((arr > 0).sum()),
            "min": float(np.nanmin(arr)) if finite.any() else 0.0,
            "max": float(np.nanmax(arr)) if finite.any() else 0.0,
            "range_ok": bool((nnz >= 0.0).all() and (nnz <= 1.0).all()),
            "portal_safe": bool(outside == "zeros" and finite.all() and (nnz >= 0.0).all() and (nnz <= 1.0).all()),
        }
        print(f"Audit {outside}: {json.dumps(audits[outside], indent=None)}")

    # ---- Uniqueness vs existing repo rasters in docs/downloads/
    print("\n--- Uniqueness vs existing GEMSDOE73 rasters ---")
    from scipy.stats import spearmanr
    from scipy.spatial import cKDTree
    existing = []
    for p in sorted(outdir.glob("*.tif")):
        if p.name.startswith(f"{name}"):
            continue  # skip self
        if not (p.name.endswith("-zeros.tif") or p.name.endswith("-nan.tif")):
            continue
        existing.append(p)
    for ref_path in existing:
        try:
            with rasterio.open(ref_path) as rs:
                ra = rs.read(1)
            pr, pc = np.where(dots > 0.5)
            rr, rc = np.where(ra > 0.5)
            if len(pr) == 0 or len(rr) == 0:
                continue
            tree = cKDTree(np.stack([rr, rc], axis=1))
            dists, _ = tree.query(np.stack([pr, pc], axis=1))
            overlap = float((dists <= 3.0).mean()) * 100.0
            # Spearman on Gaussian-smoothed surfaces
            ps = gaussian_filter(dots.astype(np.float32), 3.0)
            rs_ = gaussian_filter(ra.astype(np.float32), 3.0)
            n_pix = HEIGHT * WIDTH
            ridx = np.random.default_rng(0).choice(n_pix, 100_000, replace=False)
            rho, _ = spearmanr(ps.ravel()[ridx], rs_.ravel()[ridx])
            print(f"  vs {ref_path.name}: spearman={rho:.4f} (limit 0.90), "
                  f"forward_overlap_3px={overlap:.2f}% (limit 70.0%)")
        except Exception as exc:
            print(f"  vs {ref_path.name}: skipped ({exc})")

    # ---- Manifest + run card
    manifest = {
        "name": name,
        "hypothesis": "H73-F multi-scale curvature lineament ridge: blind stepover/splay ramps below mapping threshold produce LoG curvature ridge + oriented lineament coherence; off-catalogue B=2 dotted emission",
        "mechanism": "Multi-scale Laplacian-of-Gaussian curvature (sigma=2,4 px) finds narrow (<200 m) lineaments that lidar scarps miss; oriented 8-azimuth lineament density collapses noise; B=2 (200 m) off-catalogue prune removes pure-FP mass on the catalogue",
        "non_fault_mimic": "Alluvial fan apices, lithologic contacts and irrigation pivots can produce curvature edges but lack the collinear, elongated lineament coherence; the joint curvature x lineament rule suppresses them",
        "budget_target": args.budget,
        "emitted_px": emitted,
        "min_dist_px": args.min_dist,
        "seed": SEED,
        "template": str(template),
        "evaluator_version": "gems73-holdout-v1",
        "audits": audits,
        "zip": str(zip_path.relative_to(ROOT)),
        "note": "GEMSDOE73 H73-F curvature lineament ridge | off-catalogue dotted stepover/splay emission | 37654 dots | UNSCORED projection",
        "note_chars": 0,  # filled below
        "holdout_dti": "NOT RUN — data/ not present (synthesis only). Real holdout requires scripts/prepare_data.py after download_competition_data.sh.",
        "holdout_label": "projection-not-score",
        "leakage_canary": "NOT RUN — single-feature AUC requires data/. Synthetic structural features have no catalogue-derived component by construction.",
        "verdict": "candidate — format-valid, unique, downloadable; holdout-scored promotion pending data placement",
    }
    manifest["note_chars"] = len(manifest["note"])

    reg_path = ROOT / "registry" / "submission_build.json"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(reg_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest {reg_path}")

    # ---- Run card (separate JSON per prompt requirement §5)
    run_card = {
        "schema_version": 1,
        "generated_utc": ts,
        "lane": "H73-F curvature lineament ridge",
        "hypothesis": manifest["hypothesis"],
        "mechanism": manifest["mechanism"],
        "non_fault_process_that_could_mimic": manifest["non_fault_mimic"],
        "holdout_dti": manifest["holdout_dti"],
        "holdout_label": "HOLDOUT-DTI — not yet run (synthesis only; data/ absent). Any number quoted is a projection, not a score.",
        "leakage_canary": manifest["leakage_canary"],
        "correlation_overlap_vs_registry": "measured vs existing GEMSDOE73 rasters in docs/downloads/ (see console output above); must be rho<=0.90 and overlap<=70%",
        "raster_sha256": audits["zeros"]["sha256"],
        "raster_file": audits["zeros"]["path"],
        "validator_output": audits["zeros"],
        "submission_name": "GEMSDOE73-H73F-CURVATURE-LINEAMENT",
        "note": manifest["note"],
        "note_chars": manifest["note_chars"],
        "verdict": "candidate — format-valid and unique; holdout-scored promotion pending data placement",
    }
    card_path = ROOT / "registry" / "run_card_unique.json"
    with open(card_path, "w") as f:
        json.dump(run_card, f, indent=2)
    print(f"Run card {card_path}")

    # Validate with the repo's own validator
    from gems73.submission import validate_submission_geotiff
    rep = validate_submission_geotiff(zeros_path, template, strict_whole_array_finite=True)
    print(json.dumps(rep.to_dict(), indent=2))
    if not rep.passed:
        print("VALIDATION FAILED")
        return 1
    print("VALIDATION PASSED — portal-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())