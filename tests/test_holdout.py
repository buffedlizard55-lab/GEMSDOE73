"""Holdout guard: the legacy gems73.holdout shim must never fabricate a score.

Repaired 2026-10-21 (IR-73-11): previously this test asserted the old
synthetic-demo constants (mean DTI 0.1112 with no data present), which is
exactly the failure mode that produced a false "promote" verdict. The real
instrument is vendor gems57-pooled-hide-v2, exercised end-to-end by
scripts/run_experiments*.py against restored data.
"""
import pytest

from src.gems73.holdout import EVALUATOR_VERSION, evaluate_holdout


def test_holdout_shim_refuses_to_invent_numbers():
    with pytest.raises(RuntimeError, match="no synthetic fallback"):
        evaluate_holdout("anything.tif", data_dir="no-such-dir-xyz")


def test_evaluator_version_points_at_shared_instrument():
    assert "gems57-pooled-hide-v2" in EVALUATOR_VERSION
