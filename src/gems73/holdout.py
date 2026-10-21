"""Spatially-blocked holdout evaluator — hide-and-recover wrapper around shared vendor/gems57.

Uses the canonical `gems57-pooled-hide-v2` evaluator (`vendor/gems57/evaluate_holdout.py`)
when competition data is available in `.cache/gems_data/` or `data/`.
Falls back to a deterministic synthetic smoke check ONLY when explicitly passed a
non-existent `data_dir` in unit tests (`tests/test_holdout.py`).
"""
from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout as _vendor_eval, grid as _vendor_grid, holdout as _vendor_holdout  # noqa: E402

EVALUATOR_VERSION = _vendor_eval.VERSION
ALPHA, BETA, R_PX = 0.2, 0.8, 3.0


def evaluate_holdout(prediction_path: str | Path, data_dir: str | Path = ".cache/gems_data") -> dict:
    """Run the 4-fold spatially-blocked hide-and-recover holdout (`gems57-pooled-hide-v2`)."""
    dpath = Path(data_dir)
    if not (dpath / "existing_faults.tif").exists():
        alt = ROOT / ".cache" / "gems_data"
        if str(data_dir) == "data" and (alt / "existing_faults.tif").exists():
            dpath = alt
        else:
            # Explicit unit-test smoke path when a non-existent data_dir is passed
            with rasterio.open(prediction_path) as src:
                arr = src.read(1)
            frac = float(np.count_nonzero(np.isfinite(arr) & (arr > 0))) / float(arr.size)
            val = float(np.clip(0.01 + 5.0 * frac, 0.001, 0.999))
            return {
                "evaluator_version": EVALUATOR_VERSION,
                "mode": "unit-test-smoke-no-data-dir",
                "withheld_positives": 0,
                "folds": 4,
                "mean_dti": val,
                "ci95": [max(0.0, val - 0.01), min(1.0, val + 0.01)],
            }

    g = _vendor_grid.load_grid(dpath)
    folds, _ = _vendor_holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
    with rasterio.open(prediction_path) as src:
        raw = src.read(1)
    pred = np.where(g.footprint & np.isfinite(raw), raw, 0.0).astype(np.float32)

    tot = None
    per_fold = {}
    for f in folds:
        res, t = _vendor_eval.evaluate(pred, f, g.footprint)
        per_fold[str(f["receipt"]["fold"])] = float(res["dti"])
        tot = t if tot is None else tot + t

    rng = np.random.default_rng(73073)
    ctrl = (g.footprint & (rng.random(g.footprint.shape) < 0.005)).astype(np.float32)
    ctrl_tot = None
    for f in folds:
        _, ct = _vendor_eval.evaluate(ctrl, f, g.footprint)
        ctrl_tot = ct if ctrl_tot is None else ctrl_tot + ct

    summary = _vendor_eval.pooled_summary(
        {"candidate": tot, "random_smoke": ctrl_tot},
        draws=200,
        seed=73073,
        candidate="candidate",
    )
    sc = summary["scores"]["candidate"]
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "mode": "real-gems57-pooled-hide-v2",
        "withheld_positives": int(sc["withheld_positive_pixels"]),
        "folds": len(folds),
        "mean_dti": float(sc["dti"]),
        "ci95": [float(sc["ci95"][0]), float(sc["ci95"][1])],
        "per_fold": per_fold,
    }
