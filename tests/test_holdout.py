"""Holdout smoke — synthetic demo path runs without data/."""
from src.gems73.holdout import evaluate_holdout, EVALUATOR_VERSION

def test_holdout_synthetic():
    res = evaluate_holdout("docs/downloads/gems73-hydro-permeability-corridor-37654-20261021T000000Z-2bbb79d4-zeros.tif", data_dir="no-such-dir-xyz")
    assert res["evaluator_version"]==EVALUATOR_VERSION
    assert res["mean_dti"]>0 and res["mean_dti"]<1
    assert len(res["ci95"])==2
