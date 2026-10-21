"""Comprehensive Verification Test Suite for GEMSDOE73 Lane H73."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SUB_NAME = "gems73-h73-piedmont-corrob-submod300-37654-20261021"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_run_card_and_11_gates() -> None:
    rc_path = ROOT / "run_card.json"
    ev_rc_path = ROOT / "evidence" / "h73" / "run_card.json"
    assert rc_path.is_file() and ev_rc_path.is_file()
    rc = json.loads(rc_path.read_text())
    assert rc == json.loads(ev_rc_path.read_text())

    assert rc["verdict"] == "promote"
    assert rc["download_and_submit_ok"] is True
    assert rc["submission_name"] == SUB_NAME
    assert 1 <= len(rc["submission_note"]) <= 140
    assert rc["note_length_chars"] == len(rc["submission_note"])
    assert rc["budget"]["experiments_run"] == 3
    assert rc["budget"]["experiments_allowed"] == 3

    gates = rc["promotion_gates"]
    assert len(gates) == 11
    for g_name, g_val in gates.items():
        assert g_val is True, f"Promotion gate failed: {g_name}"


def test_geotiff_range_0_1_and_no_nans() -> None:
    rc = json.loads((ROOT / "run_card.json").read_text())
    expected_sha = rc["raster_sha256"]

    paths = [
        ROOT / "docs" / "downloads" / f"{SUB_NAME}-zeros.tif",
        ROOT / "docs" / "downloads" / f"{SUB_NAME}.tif",
        ROOT / "submissions" / f"{SUB_NAME}-zeros.tif",
        ROOT / "submissions" / f"{SUB_NAME}.tif",
    ]
    for p in paths:
        assert p.is_file(), f"Missing GeoTIFF: {p}"
        assert sha256_file(p) == expected_sha

    with rasterio.open(paths[0]) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert str(src.crs) == "EPSG:32611"
        assert (src.height, src.width) == (3730, 3292)
        assert list(src.transform)[:6] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
        arr = src.read(1)

    assert np.isfinite(arr).all(), "GeoTIFF contains NaN or Inf!"
    assert int(np.isnan(arr).sum()) == 0
    assert int(np.isinf(arr).sum()) == 0
    assert float(arr.min()) == 0.0
    assert float(arr.max()) == 1.0
    uniq = np.unique(arr)
    assert np.array_equal(uniq, np.array([0.0, 1.0], dtype=np.float32))
    assert int((arr == 1.0).sum()) == 37654

    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as csrc:
        cat = csrc.read(1) > 0
    assert int(((arr > 0) & cat).sum()) == 0, "Positive dots overlap mapped catalogue!"

    zip_path = ROOT / "docs" / "downloads" / f"{SUB_NAME}-zeros.zip"
    assert zip_path.is_file()
    assert sha256_file(zip_path) == rc["downloads"]["primary_zip_sha256"]
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert f"{SUB_NAME}-zeros.tif" in names


def test_leakage_canaries_and_uniqueness() -> None:
    canary = json.loads((ROOT / "evidence" / "h73" / "feature_leakage_canary.json").read_text())
    assert canary["n_features_audited"] == 49
    assert canary["all_clean"] is True
    assert canary["max_symmetric_auc_instrument_a_fold0"] <= 0.90
    assert canary["max_symmetric_auc_instrument_b_prime"] <= 0.90

    uq = json.loads((ROOT / "evidence" / "h73" / "uniqueness_audit.json").read_text())
    assert uq["all_pass"] is True
    sp = uq["surface_pre_placement"]
    df = uq["dots_final"]
    assert sp["registry_rasters_checked"] == 80
    assert sp["unique"] is True
    assert abs(sp["worst_spearman_full_footprint"]) <= 0.90
    assert df["registry_rasters_checked"] == 80
    assert df["unique"] is True
    assert abs(df["worst_spearman_full_footprint"]) <= 0.90
    assert df["worst_mutual_overlap"] <= 0.70
    assert df["worst_non_lattice_forward_overlap"] <= 0.70


def test_docs_and_readme_deliverables() -> None:
    for rel in (
        "README.md",
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/h33-autopsy.html",
        "docs/hypotheses-and-ablation.html",
        "docs/audit-and-sources.html",
        "docs/preregistration-h73.md",
        "docs/h33-forensic-autopsy.md",
    ):
        p = ROOT / rel
        assert p.is_file(), f"Missing documentation file: {rel}"
        txt = p.read_text()
        assert SUB_NAME in txt, f"{SUB_NAME} missing from {rel}"

    readme = (ROOT / "README.md").read_text()
    assert "YES, OK TO DOWNLOAD & SUBMIT" in readme
    assert "PARALLEL-RUN PROTOCOL" in readme
    assert "HOLDOUT-DTI" in readme
    assert "ORGANIZER-CONFIRMED" in readme
