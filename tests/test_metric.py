"""Metric checks for the src implementation (official page 967 values).

Session-2 fix (IR-73-09): the previous revision concatenated two test
modules, redefined test_worked_example, and imported a non-existent
``dti_fast``. Replaced with tests against the actual src API; the shared
vendor metric is cross-checked in tests/test_metric_and_submission.py.
"""
import numpy as np

from src.gems73.metric import ALPHA, BETA, RADIUS_PX, dti_binary, dti_exact, kernel, marginal_bar


def test_worked_example():
    # Official page 967: TPw=3.00 FPw=1.89 FNw=2.00 -> 0.60 (page rounding)
    dti = 3.0 / (3.0 + ALPHA * 1.89 + BETA * 2.0)
    assert abs(dti - 0.60) < 0.005


def test_kernel_support():
    assert float(kernel(0.0)) == 1.0
    assert float(kernel(RADIUS_PX)) == 0.0
    assert float(kernel(1.5)) == 0.5
    assert abs(float(kernel(np.hypot(2, 2))) - (1 - 2 * np.sqrt(2) / 3)) < 1e-9


def test_exact_vs_binary_and_bounds():
    truth = np.zeros((20, 20), bool)
    truth[4:16, 10] = True
    pred = np.zeros((20, 20), np.float32)
    pred[5:15, 11] = 1.0  # 1 px offset -> k = 2/3 on covered truth
    r_exact = dti_exact(pred, truth)
    r_binary = dti_binary(pred > 0, truth)
    assert 0.0 < r_exact["dti"] < 1.0
    assert abs(r_exact["dti"] - r_binary["dti"]) < 1e-9
    assert r_exact["n_truth"] == 12


def test_perfect_and_empty():
    truth = np.zeros((10, 10), bool)
    truth[5, 2:8] = True
    perfect = truth.astype(np.float32)
    assert abs(dti_exact(perfect, truth)["dti"] - 1.0) < 1e-9
    assert dti_exact(np.zeros((10, 10), np.float32), truth)["dti"] == 0.0


def test_marginal_bar():
    # Non-redundant dot helps iff k > alpha*DTI (vendor metric derivation)
    assert marginal_bar(0.2778) == ALPHA * 0.2778
    assert abs(marginal_bar(0.2778) - 0.05556) < 1e-9
