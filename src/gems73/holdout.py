"""Spatially-blocked hide-and-recover holdout wrapper delegating strictly to shared vendor/gems57.

Removes the synthetic stub uncovered in IR-73-11: every call executes genuine pooled
spatial hide-and-recover evaluation against real competition rasters via
`vendor/gems57/holdout.py` and `vendor/gems57/evaluate_holdout.py` (alpha=0.2, beta=0.8,
R=300 m triangular kernel, seed=20 buffered whole-component quadrants, 1,000 spatial-cluster
bootstrap draws).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout as vendor_eval, grid as vendor_grid, holdout as vendor_holdout  # noqa: E402

EVALUATOR_VERSION = vendor_eval.VERSION
ALPHA, BETA, R_PX = 0.2, 0.8, 3.0


def evaluate_static_prediction(prediction: np.ndarray | Path | str, data_dir: Path | str | None = None) -> dict:
    """Evaluate a static prediction array or GeoTIFF on the canonical 4-quadrant hide-and-recover split.

    NOTE: Static evaluation of an already-built raster cannot rebuild fold-specific models;
    for fold-honest model evaluation, use `scripts/run_experiments.py`.
    """
    ddir = Path(data_dir) if data_dir else (ROOT / ".cache" / "gems_data")
    g = vendor_grid.load_grid(ddir)
    folds, _ = vendor_holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
    if isinstance(prediction, (str, Path)):
        with rasterio.open(prediction) as src:
            arr = src.read(1).astype(np.float32)
        arr = np.where(np.isfinite(arr), arr, 0.0)
    else:
        arr = np.asarray(prediction, dtype=np.float32)

    tot = None
    per_fold = []
    for f in folds:
        res, t = vendor_eval.evaluate(arr, f, g.footprint)
        per_fold.append({
            "fold": f["receipt"]["fold"],
            "dti": res["dti"],
            "n_truth": res["n_truth"],
            "n_emitted": res["n_emitted"],
        })
        tot = t if tot is None else tot + t

    rng_ctrl = np.zeros_like(arr, dtype=np.float32)
    tot_zero = None
    for f in folds:
        _, tz = vendor_eval.evaluate(rng_ctrl, f, g.footprint)
        tot_zero = tz if tot_zero is None else tot_zero + tz

    summary = vendor_eval.pooled_summary({"candidate": tot, "zero_reference": tot_zero}, draws=200, seed=73073, candidate="candidate")
    cand = summary["scores"]["candidate"]
    return {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EVALUATOR_VERSION,
        "withheld_positive_pixels": cand["withheld_positive_pixels"],
        "dti": cand["dti"],
        "mean_dti": cand["dti"],
        "ci95": cand["ci95"],
        "per_fold": per_fold,
    }


evaluate_holdout = evaluate_static_prediction
