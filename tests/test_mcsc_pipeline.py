"""Comprehensive end-to-end unit & artifact verification tests for Lane H73-MCSC."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems57 import validate as validate57
from gems73.mcsc import (
    align_quadrant_surfaces,
    compute_symmetric_canaries,
    directional_crest_sharpen,
    submodular_dti_emit,
)
from gems73.submission import validate_submission_geotiff, write_submission_geotiff


def test_non_multiple_of_16_tiled_geotiff_regression_ir73_15(tmp_path: Path):
    """Regression test for IR-73-15: width=3292 (3292 % 16 == 12) strip template written as tiled GeoTIFF."""
    tpl = tmp_path / "tpl_strip_100x52.tif"
    arr = np.zeros((100, 52), dtype=np.float32)  # 52 % 16 == 4 (mimics 3292 % 16 == 12)
    arr[10:90, 10:42] = 0.0
    arr[:10, :] = np.nan
    with rasterio.open(
        tpl,
        "w",
        driver="GTiff",
        height=100,
        width=52,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=rasterio.transform.Affine.translation(243350.0, 4508550.0) @ rasterio.transform.Affine.scale(100.0, -100.0),
        tiled=False,
    ) as dst:
        dst.write(arr, 1)

    pred = np.zeros((100, 52), dtype=np.float32)
    pred[30, 25] = 1.0

    rec_z = write_submission_geotiff(pred, tpl, tmp_path / "out-zeros.tif", outside_mode="zeros", note="test")
    rec_n = write_submission_geotiff(pred, tpl, tmp_path / "out-nan.tif", outside_mode="nan", note="test")
    assert rec_z["emitted_dots"] == 1
    assert rec_n["emitted_dots"] == 1

    with rasterio.open(tmp_path / "out-zeros.tif") as src:
        assert src.nodata is None
        d = src.read(1)
        assert np.all(np.isfinite(d))
        assert float(d.min()) == 0.0 and float(d.max()) == 1.0


def test_mcsc_core_operators():
    rng = np.random.default_rng(73)
    foot = np.ones((40, 44), dtype=bool)
    foot[:3, :] = False
    quad = np.zeros((40, 44), dtype=np.int8)
    quad[:20, 22:] = 1
    quad[20:, :22] = 2
    quad[20:, 22:] = 3

    p1 = np.clip(rng.uniform(0.01, 0.25, size=(40, 44)), 0, 1).astype(np.float32)
    p2 = np.clip(p1 * 1.5, 0, 1).astype(np.float32)
    p2[quad == 1] *= 0.4  # induce artificial inter-fold calibration drift
    aligned = align_quadrant_surfaces(p2, p1, quad, foot, w_stage2=0.72)
    assert aligned.shape == (40, 44)
    assert np.all(aligned[~foot] == 0.0)
    assert float(aligned[foot].min()) >= 0.0 and float(aligned[foot].max()) <= 1.0

    # Vertical fault trace at col=22 should sharpen cleanly above flanking apron
    ridge = np.zeros((40, 44), dtype=np.float32)
    for c in range(18, 27):
        ridge[:, c] = np.exp(-0.5 * ((c - 22) / 2.2) ** 2)
    strike = np.full((40, 44), np.pi / 2.0, dtype=np.float32)
    sharp = directional_crest_sharpen(ridge, strike, foot)
    assert float(sharp[20, 22]) > float(sharp[20, 19])

    dots = submodular_dti_emit(sharp, foot, n_dots=10, fp_penalty_weight=0.025)
    assert int((dots > 0.5).sum()) == 10
    assert set(np.unique(dots).tolist()).issubset({0.0, 1.0})


def test_symmetric_canary_detector():
    rng = np.random.default_rng(42)
    foot = np.ones((30, 30), dtype=bool)
    cat = np.zeros((30, 30), dtype=bool)
    cat[2, 2:10] = True
    hid = np.zeros((30, 30), dtype=bool)
    hid[25, 10:25] = True
    X = rng.normal(size=(900, 2)).astype(np.float32)

    clean = compute_symmetric_canaries(X, ("noise_a", "noise_b"), foot, cat, hid)
    assert clean["all_pass"] is True
    assert clean["max_symmetric_auc"] < 0.70

    X[:, 1] = -10.0 * hid.ravel().astype(np.float32)  # inverted leaky feature -> symmetric AUC == 1.0
    leaky = compute_symmetric_canaries(X, ("noise_a", "inverted_leak"), foot, cat, hid)
    assert leaky["all_pass"] is False
    assert leaky["max_symmetric_auc"] > 0.99


def test_promoted_deliverable_and_run_card_integrity():
    rc = json.loads((ROOT / "evidence" / "run_card_mcsc.json").read_text())
    assert rc == json.loads((ROOT / "registry" / "run_card_mcsc.json").read_text())
    assert rc == json.loads((ROOT / "docs" / "evidence" / "run_card_mcsc.json").read_text())
    assert rc == json.loads((ROOT / "docs" / "downloads" / "run_card_mcsc.json").read_text())
    assert rc["verdict"] == "promote"
    assert rc["leakage_canary"]["all_pass"] is True
    assert rc["leakage_canary"]["max_symmetric_auc_stage1"] <= 0.90
    assert rc["leakage_canary"]["max_symmetric_auc_stage2"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["all_uniqueness_gates_passed"] is True
    assert rc["correlation_overlap_vs_registry"]["max_abs_spearman_surface"]["value"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["max_3px_overlap_vs_sparse_submissions"]["value"] <= 0.70
    assert rc["holdout_dti"]["pooled_dti"] > 0.105
    assert rc["holdout_dti"]["beats_h33_foldfair_ci95_gt_0"] is True
    assert rc["holdout_dti"]["beats_h33_far_gt_1km_ci95_gt_0"] is True
    assert rc["holdout_dti"]["beats_d28_ci95_gt_0"] is True
    assert rc["holdout_dti"]["beats_prior_gemsdoe73_pr3_0_0548"] is True
    assert rc["note_length"] <= 140

    primary = ROOT / rc["deliverables"]["primary_zeros_tif"]["path"]
    companion = ROOT / rc["deliverables"]["companion_nan_tif"]["path"]
    zip_bundle = ROOT / rc["deliverables"]["zip_bundle"]["path"]
    assert primary.is_file() and companion.is_file() and zip_bundle.is_file()
    assert hashlib.sha256(primary.read_bytes()).hexdigest() == rc["raster_sha256"]
    assert hashlib.sha256(companion.read_bytes()).hexdigest() == rc["deliverables"]["companion_nan_tif"]["sha256"]
    assert hashlib.sha256(zip_bundle.read_bytes()).hexdigest() == rc["deliverables"]["zip_bundle"]["sha256"]

    tpl = ROOT / ".cache" / "gems_data" / "sample_submission.tif"
    cat_tif = ROOT / ".cache" / "gems_data" / "existing_faults.tif"
    with rasterio.open(tpl) as s_tpl, rasterio.open(cat_tif) as s_cat:
        foot = np.isfinite(s_tpl.read(1))
        cat = s_cat.read(1) > 0

    v57 = validate57.validate(primary, footprint=foot, catalogue=cat)
    v73 = validate_submission_geotiff(primary, tpl, strict_whole_array_finite=True)
    assert v57["all_checks_passed"] is True
    assert v73.passed is True
    assert v57["emitted_positive_pixels"] == 37654
    assert v57["on_catalogue_positive_pixels"] == 0
    assert v57["n_nan"] == 0 and v57["n_infinite"] == 0
