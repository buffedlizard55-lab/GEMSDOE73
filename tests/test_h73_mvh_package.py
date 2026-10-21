"""Comprehensive verification tests for promoted H73-MVH package, protocol gates, and GitHub Pages site."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from src.gems73.mvh_features import FORBIDDEN_POINT_COLUMNS
from src.gems73.mvh_model import two_head_submodular_dti_emit

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for ch in iter(lambda: fh.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def test_forbidden_point_columns_locked():
    assert "dist_known_fault_px" in FORBIDDEN_POINT_COLUMNS
    assert "known_fault" in FORBIDDEN_POINT_COLUMNS
    assert "label" in FORBIDDEN_POINT_COLUMNS


def test_two_head_submodular_allocator_exact_budget_and_binary_range():
    rng = np.random.default_rng(73)
    p = rng.uniform(0.0, 0.8, size=(48, 48)).astype(np.float32)
    q = rng.uniform(0.0, 0.8, size=(48, 48)).astype(np.float32)
    allow = np.ones((48, 48), dtype=bool)
    allow[:4, :] = False
    out = two_head_submodular_dti_emit(p, q, allow, n_dots=75, fp_tax=0.05)
    assert out.dtype == np.float32
    assert out.shape == (48, 48)
    assert np.isfinite(out).all()
    assert set(np.unique(out).tolist()) == {0.0, 1.0}
    assert int((out > 0.5).sum()) == 75
    assert int(out[~allow].sum()) == 0


def test_promoted_geotiff_and_zip_portal_safety_and_hashes():
    rc = json.loads((ROOT / "evidence/run_card.json").read_text())
    assert rc == json.loads((ROOT / "registry/run_card.json").read_text())
    assert rc == json.loads((ROOT / "docs/evidence/run_card.json").read_text())

    assert rc["verdict"] == "promote"
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is True
    assert 0 < len(rc["submission_note_lte_140_chars"]) <= 140
    assert rc["primary_score"]["pooled_dti"] > rc["primary_score"]["h33_analogue_control_dti"]
    assert rc["primary_score"]["paired_delta_ci95"][0] > 0.0
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["max_symmetric_auc_observed"] <= 0.90
    assert rc["uniqueness"]["complete_accessible_scan"] is True
    assert rc["uniqueness"]["repos_scanned"] >= 83
    assert rc["uniqueness"]["unique_rasters_audited"] >= 984
    assert rc["uniqueness"]["vendor_gems57_duplicate_count"] == 0
    assert rc["uniqueness"]["max_abs_spearman_stage_a_surface"] <= 0.90
    assert rc["uniqueness"]["max_abs_spearman_stage_b_dots"] <= 0.90
    assert rc["uniqueness"]["max_vendor_mutual_min_3px_overlap_all_984"] <= 0.70

    art = rc["artifact"]
    tif_path = ROOT / "docs" / art["download_url_tif"]
    zip_path = ROOT / "docs" / art["download_url_zip"]
    assert tif_path.is_file() and zip_path.is_file()
    assert _sha256(tif_path) == art["raster_sha256"]
    assert _sha256(zip_path) == art["zip_sha256"]

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.testzip() is None
        assert hashlib.sha256(zf.read(tif_path.name)).hexdigest() == art["raster_sha256"]

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert ds.nodata is None
        arr = ds.read(1)

    assert arr.size == 12_279_160
    assert np.isfinite(arr).all()
    assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
    assert int((arr > 0.5).sum()) == 37_654
    assert set(np.unique(arr).tolist()) == {0.0, 1.0}


def test_all_github_pages_links_assets_and_zero_stale_hashes():
    rc = json.loads((ROOT / "evidence/run_card.json").read_text())
    fn = rc["artifact"]["submission_filename"]
    sha = rc["artifact"]["raster_sha256"]

    readme = (ROOT / "README.md").read_text()
    assert fn in readme and sha in readme
    assert "7f3c2a9e" not in readme

    html_files = sorted((ROOT / "docs").glob("*.html"))
    assert len(html_files) >= 10

    for idx_page in ("index.html", "executive-summary.html"):
        txt = (ROOT / "docs" / idx_page).read_text()
        assert fn in txt and sha in txt
        assert "VERDICT: PROMOTE" in txt
        assert "OK TO DOWNLOAD: YES" in txt
        assert "RECOMMENDED TO SUBMIT: YES" in txt

    href_re = re.compile(r'(?:href|src)="([^"#?]+)"')
    for hp in html_files:
        txt = hp.read_text()
        if hp.name != "irregularities.html":
            assert "7f3c2a9e" not in txt, f"Stale hash found in {hp}"
        for target in href_re.findall(txt):
            if target.startswith(("http://", "https://", "mailto:", "javascript:", "data:")):
                continue
            resolved = (ROOT / "docs" / target).resolve()
            assert resolved.is_file() and resolved.stat().st_size > 0, f"Broken link {target} in {hp.name}"
