"""Holdout delegate: shared evaluator version, no fabricated numbers (IR-73-11)."""
import pytest

from src.gems73.holdout import EVALUATOR_VERSION, evaluate_holdout


def test_evaluator_is_shared_vendor_version():
    assert EVALUATOR_VERSION == "gems57-pooled-hide-v2"


def test_no_synthetic_fallback_numbers():
    with pytest.raises(NotImplementedError, match="fold-fair"):
        evaluate_holdout("anything.tif", data_dir="no-such-dir-xyz")
