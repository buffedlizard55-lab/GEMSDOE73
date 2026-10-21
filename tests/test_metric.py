"""Metric tests against the current src.gems73.metric API.

Repaired 2026-10-21 (IR-73-09): the merged file previously contained two
concatenated test modules, the second importing a ``dti_fast`` that the
PR#1+#2 library consolidation no longer exports, so ``pytest`` failed at
collection on main. Rewritten once, against the exported API
(``dti_exact``, ``dti_binary``, ``kernel``, ``marginal_bar``).
"""
import numpy as np

from src.gems73.metric import ALPHA, BETA, RADIUS_PX, dti_binary, dti_exact, kernel, marginal_bar


def test_worked_example():
    # Official problem page 967 worked example: TP=3.00 FP=1.89 FN=2.00 -> 0.60
    tp, fp, fn = 3.0, 1.89, 2.0
    assert abs(tp / (tp + ALPHA * fp + BETA * fn) - 0.60) < 0.005  # page rounds to 2dp; exact = 0.6027


def test_kernel():
    assert kernel(0) == 1.0
    assert kernel(RADIUS_PX) == 0.0
    assert abs(kernel(np.hypot(2, 2)) - (1 - 2 * np.sqrt(2) / 3)) < 1e-9
    assert kernel(100.0) == 0.0


def test_perfect_prediction_scores_one():
    truth = np.zeros((15, 15), bool)
    truth[7, 3:12] = True
    out = dti_exact(truth.astype(float), truth)
    assert abs(out["dti"] - 1.0) < 1e-9  # EPS=1e-12 in the denominator
    assert out["fp"] == 0.0 and out["fn"] == 0.0


def test_empty_prediction_scores_zero():
    truth = np.zeros((10, 10), bool)
    truth[5, 5] = True
    assert dti_exact(np.zeros((10, 10)), truth)["dti"] == 0.0
    assert dti_binary(np.zeros((10, 10), bool), truth)["dti"] == 0.0


def test_offset_dot_gets_kernel_credit():
    pred = np.zeros((20, 20), float)
    truth = np.zeros((20, 20), bool)
    truth[10, 10] = True
    pred[10, 11] = 1.0  # distance 1 px -> credit k = 1 - 1/3
    out = dti_exact(pred, truth)
    assert abs(out["tp"] - (1 - 1 / 3)) < 1e-12
    assert 0.0 < out["dti"] < 1.0


def test_binary_matches_exact_for_binary_input():
    rng = np.random.default_rng(0)
    truth = rng.random((30, 30)) < 0.05
    pred_b = rng.random((30, 30)) < 0.05
    a = dti_binary(pred_b, truth)
    b = dti_exact(pred_b.astype(float), truth)
    assert abs(a["dti"] - b["dti"]) < 1e-12


def test_out_of_range_prediction_rejected():
    truth = np.zeros((5, 5), bool)
    truth[2, 2] = True
    bad = np.zeros((5, 5))
    bad[0, 0] = 1.5
    try:
        dti_exact(bad, truth)
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_marginal_bar():
    # A non-redundant dot improves DTI iff its credit k > alpha * DTI.
    assert marginal_bar(0.2778) == ALPHA * 0.2778
    assert abs(marginal_bar(0.2778) - 0.05556) < 1e-9
