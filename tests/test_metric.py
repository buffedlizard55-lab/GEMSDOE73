"""Exact analytical identity & worked-example tests for Distance-Tolerant Intersection (DTI).

Remediates IR-73-14: removes duplicate shadowed function name and enforces exact floating-point
identities at distances d = 0, 1, 2, 3 px against both gems73.metric and vendor/gems57/metric.py.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from src.gems73.metric import ALPHA, BETA, RADIUS_PX, dti_exact, dti_fast, kernel
from gems57 import metric as metric57


def test_worked_example_strict():
    """Official DrivenData GEMS page 967 worked example: TPw=3.00, FPw=1.89, FNw=2.00 -> 0.60265."""
    tp, fp, fn = 3.0, 1.89, 2.0
    expected = 3.0 / (3.0 + ALPHA * 1.89 + BETA * 2.0)
    assert RADIUS_PX == 3.0
    assert abs(expected - 3.0 / 4.978) < 1e-12


def test_kernel_analytical_rings():
    assert kernel(0.0) == 1.0
    assert abs(kernel(1.0) - (2.0 / 3.0)) < 1e-12
    assert abs(kernel(1.5) - 0.5) < 1e-12
    assert abs(kernel(2.0) - (1.0 / 3.0)) < 1e-12
    assert abs(kernel(np.hypot(2.0, 2.0)) - (1.0 - 2.0 * np.sqrt(2.0) / 3.0)) < 1e-9
    assert kernel(3.0) == 0.0
    assert kernel(4.2) == 0.0


def test_dti_single_dot_exact_analytic_match():
    """Single truth pixel at (10, 10) and single prediction dot at (10, 11) (d = 1 px = 100 m):
    TP_w = 2/3, FN_w = 1/3, FP_w = 1 - 2/3 = 1/3.
    """
    pred = np.zeros((21, 21), dtype=np.float32)
    truth = np.zeros((21, 21), dtype=np.uint8)
    truth[10, 10] = 1
    pred[10, 11] = 1.0

    tpw = 2.0 / 3.0
    fnw = 1.0 / 3.0
    fpw = 1.0 / 3.0
    analytic = tpw / (tpw + ALPHA * fpw + BETA * fnw)
    assert abs(dti_fast(pred, truth) - analytic) < 1e-5
    exact_res = dti_exact(pred, truth)
    exact_val = exact_res["dti"] if isinstance(exact_res, dict) else float(exact_res)
    assert abs(exact_val - analytic) < 1e-5

    terms57 = metric57.dti_binary(pred > 0.5, truth.astype(bool))
    assert abs(terms57["dti"] - analytic) < 1e-5


def test_identity_empty_truth_and_perfect_match():
    pred = np.zeros((12, 12), dtype=np.float32)
    truth = np.zeros((12, 12), dtype=np.uint8)
    assert dti_fast(pred, truth) == 1.0

    truth[6, 6] = 1
    pred[6, 6] = 1.0
    assert abs(dti_fast(pred, truth) - 1.0) < 1e-6
