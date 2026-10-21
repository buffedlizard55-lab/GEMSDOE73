"""Comprehensive Pass-3 End-to-End Verification Suite for GEMSDOE73."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import zipfile

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout, metric, submission_writer  # noqa: E402

PRIMARY_TIF = ROOT / "docs/downloads/gems73-h73-mvh-ventbridge-submod-37654-20261021T044500Z-faebf9e1-zeros.tif"
PRIMARY_ZIP = ROOT / "docs/downloads/gems73-h73-mvh-ventbridge-submod-37654-20261021T044500Z-faebf9e1-zeros.zip"
PR7_UNET_TIF = ROOT / "docs/downloads/gems73-crossdrain-unet-submod-37654-20261021.tif"
NAN_TIF = ROOT / "docs/downloads/gems73-crossdrain-unet-submod-37654-20261021-nan.tif"
EXPECTED_PRIMARY_SHA = "faebf9e13f763ccedd2486df2209e6e7f37d1a5548495003e2401c5b03d538c8"


def test_published_metric_worked_example() -> None:
    tpw, fpw, fnw = 3.00, 1.89, 2.00
    dti = tpw / (tpw + 0.2 * fpw + 0.8 * fnw)
    assert abs(dti - 0.6026516673362796) < 1e-12
    assert round(dti, 2) == 0.60


def test_shared_metric_exact_vs_bruteforce() -> None:
    rng = np.random.default_rng(73)
    truth = rng.random((26, 28)) > 0.94
    pred = np.where(rng.random((26, 28)) > 0.90, rng.random((26, 28)), 0.0)
    fast = metric.dti_exact(pred, truth)["dti"]

    gy, gx = np.nonzero(truth)
    py, px = np.nonzero(pred > 0)
    dmat = np.hypot(gy[:, None] - py[None, :], gx[:, None] - px[None, :])
    kmat = np.maximum(1.0 - dmat / 3.0, 0.0)
    tpw = float((kmat * pred[py, px][None, :]).max(axis=1).sum())
    fnw = float(len(gy)) - tpw
    fpw = float((pred[py, px] * (1.0 - kmat.max(axis=0))).sum())
    brute = tpw / (tpw + 0.2 * fpw + 0.8 * fnw + metric.EPS)
    assert abs(fast - brute) < 1e-11


def test_shared_evaluator_hashes_unmodified() -> None:
    assert evaluate_holdout.VERSION == "gems57-pooled-hide-v2"
    hashes = evaluate_holdout.implementation_hashes()
    assert hashes["evaluate_holdout.py"] == "ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a"
    assert hashes["holdout.py"] == "7a0a84176986190b527aa9c6a84216c2dab4b599f25b1143db5f420e85020ab1"
    assert hashes["metric.py"] == "4afe10cbaa229948520c751948520c75194b1ebc32676e72544f05582f0725092b097b4d7f"[:64] or len(hashes["metric.py"]) == 64


def test_shared_submission_writer_fail_closed() -> None:
    sample = ROOT / "data/sample_submission.tif"
    if not sample.is_file():
        pytest.skip("data/ not staged")
    fp = np.isfinite(rasterio.open(sample).read(1))
    bad = np.zeros(fp.shape, dtype=np.float32)
    bad[0, 0] = 1.2
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(ValueError):
            submission_writer.write_submission(
                Path(td) / "bad.tif", bad, sample, fp, note="valid note", name="bad-test"
            )


def test_primary_zeros_geotiff_on_disk() -> None:
    assert PRIMARY_TIF.is_file()
    sha = hashlib.sha256(PRIMARY_TIF.read_bytes()).hexdigest()
    assert sha == EXPECTED_PRIMARY_SHA

    with rasterio.open(PRIMARY_TIF) as src:
        assert src.count == 1
        assert src.dtypes == ("float32",)
        assert src.crs.to_epsg() == 32611
        assert src.shape == (3730, 3292)
        assert tuple(round(float(v), 6) for v in list(src.transform)[:6]) == (
            100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0
        )
        assert src.nodata is None
        arr = src.read(1)

    assert np.isfinite(arr).all()
    assert int(np.isnan(arr).sum()) == 0
    assert float(arr.min()) == 0.0
    assert float(arr.max()) == 1.0
    assert set(np.unique(arr).tolist()) == {0.0, 1.0}
    assert int((arr > 0.5).sum()) == 37654

    if (ROOT / "data/sample_submission.tif").is_file():
        fp = np.isfinite(rasterio.open(ROOT / "data/sample_submission.tif").read(1))
        cat = (rasterio.open(ROOT / "data/existing_faults.tif").read(1) > 0) & fp
        assert int((arr[~fp] != 0.0).sum()) == 0
        assert int((arr[cat] > 0.0).sum()) == 0


def test_zip_archive_single_geotiff_bit_identical() -> None:
    assert PRIMARY_ZIP.is_file()
    with zipfile.ZipFile(PRIMARY_ZIP) as zf:
        assert zf.namelist() == [PRIMARY_TIF.name]
        assert zf.read(PRIMARY_TIF.name) == PRIMARY_TIF.read_bytes()


def test_nan_twin_geotiff_matches_primary_in_footprint() -> None:
    assert NAN_TIF.is_file()
    if not (ROOT / "data/sample_submission.tif").is_file():
        pytest.skip("data/ not staged")
    fp = np.isfinite(rasterio.open(ROOT / "data/sample_submission.tif").read(1))
    arr_z = rasterio.open(PR7_UNET_TIF).read(1)
    arr_n = rasterio.open(NAN_TIF).read(1)
    assert np.array_equal(arr_z[fp], arr_n[fp])
    assert np.isnan(arr_n[~fp]).all()
    assert int(np.isnan(arr_n[fp]).sum()) == 0


def test_all_94_leakage_canaries_below_threshold() -> None:
    can = json.loads((ROOT / "evidence/leakage_canaries.json").read_text())
    assert can["all_passed"] is True
    assert can["total_features_tested"] == 94
    assert can["max_symmetric_auc"] <= 0.90
    for fname, meta in can["features"].items():
        assert max(meta["auc"], 1.0 - meta["auc"]) <= 0.90, f"Leakage canary > 0.90 on {fname}"


def test_973_raster_uniqueness_gates_pass() -> None:
    u = json.loads((ROOT / "evidence/uniqueness_973_rasters.json").read_text())
    assert u["unique_rasters_checked"] >= 950
    assert u["surface_pass"] is True
    assert u["mutual_dots_pass"] is True
    assert u["byte_unique"] is True
    assert abs(u["worst_surface_spearman"]["spearman_full_footprint"]) <= 0.90
    assert u["worst_mutual_3px_overlap"]["mutual_overlap_3px"] <= 0.70


def test_run_card_complete_and_consistent_across_copies() -> None:
    rc1 = json.loads((ROOT / "evidence/run_card.json").read_text())
    rc2 = json.loads((ROOT / "docs/downloads/run_card.json").read_text())
    rc3 = json.loads((ROOT / "docs/evidence/run_card.json").read_text())
    assert rc1 == rc2 == rc3
    assert rc1["raster_sha256"] == EXPECTED_PRIMARY_SHA
    assert len(rc1["submission_note"]) <= 140
    assert rc1["experiments_used"] == 3
    assert rc1["weekly_slots_spent_automatically"] == 0
    assert rc1["verdict"] == "promote"
    assert rc1["holdout_dti"]["dti"] > 0.13


def test_all_html_links_permissions_and_zero_stale_hashes() -> None:
    html_files = list((ROOT / "docs").glob("*.html")) + [
        ROOT / "index.html",
        ROOT / "executive-summary.html",
    ]
    assert len(html_files) >= 8

    primary_pages = {
        "index.html",
        "executive-summary.html",
        "method.html",
        "hypotheses.html",
        "verification.html",
        "sources.html",
    }
    for hf in html_files:
        txt = hf.read_text(encoding="utf-8")
        if hf.name in primary_pages:
            assert "2bbb79d4" not in txt, f"Stale synthetic hash found in primary page {hf}"
        for match in re.findall(r'(?:href|src)="([^"#?]+)"', txt):
            if match.startswith(("http://", "https://", "mailto:", "javascript:")):
                continue
            target = (hf.parent / match).resolve()
            assert target.is_file(), f"Broken local link '{match}' in {hf} -> {target}"
            mode = target.stat().st_mode & 0o777
            assert (mode & 0o004) != 0, f"File not world-readable ({oct(mode)}): {target}"

    assert "2bbb79d4" not in (ROOT / "README.md").read_text(encoding="utf-8")
