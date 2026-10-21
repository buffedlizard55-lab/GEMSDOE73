"""Holdout verification tests — verifies genuine pixel scoring via vendor/gems57/evaluate_holdout.py
(replaces the hardcoded 0.1112 stub documented in IR-73-11).
"""
import numpy as np
import pytest
from pathlib import Path
from src.gems73.holdout import EVALUATOR_VERSION, evaluate_holdout
from vendor.gems57 import evaluate_holdout as vendor_eval


def test_vendor_holdout_algebra_on_synthetic_quadrant():
    h, w = 80, 80
    fp = np.ones((h, w), dtype=bool)
    truth = np.zeros((h, w), dtype=bool)
    truth[20:60, 40] = True
    fold = {
        "region": fp,
        "truth": truth,
        "visible": np.zeros((h, w), dtype=bool),
        "receipt": {"fold": "SYNTH"},
    }
    pred_hit = np.zeros((h, w), dtype=np.float32)
    pred_hit[20:60, 40] = 1.0
    pred_miss = np.zeros((h, w), dtype=np.float32)
    pred_miss[20:60, 5] = 1.0
    r_hit, _ = vendor_eval.evaluate(pred_hit, fold, fp)
    r_miss, _ = vendor_eval.evaluate(pred_miss, fold, fp)
    assert r_hit["dti"] == pytest.approx(1.0, abs=1e-6)
    assert r_miss["dti"] == pytest.approx(0.0, abs=1e-6)


def test_holdout_real_rasters_if_restored():
    data_dir = Path(".cache/gems_data")
    if not (data_dir / "existing_faults.tif").exists():
        pytest.skip("Real competition rasters not yet restored into .cache/gems_data")
    cand = "docs/downloads/gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-zeros.tif"
    res = evaluate_holdout(cand, data_dir=data_dir)
    assert res["evaluator_version"] == EVALUATOR_VERSION
    assert 0.0 < res["mean_dti"] < 1.0
    assert len(res["ci95"]) == 2
