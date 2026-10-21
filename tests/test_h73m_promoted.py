"""End-to-end verification tests for the promoted GEMSDOE73 H73-M M3 submission and Run Card."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import grid as grid_mod  # noqa: E402
from gems73.emit import submodular_dti_emit  # noqa: E402


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_submodular_dti_emit_respects_min_spacing():
    rng = np.random.default_rng(73)
    prob = rng.random((80, 80), dtype=np.float32) * 0.6
    allowed = np.ones((80, 80), dtype=bool)
    dots = submodular_dti_emit(prob, allowed, n_dots=120, fp_penalty_weight=0.04, min_spacing_px=3.0)
    assert int((dots > 0.5).sum()) == 120
    pts = np.column_stack(np.nonzero(dots > 0.5))
    tree = cKDTree(pts)
    dists, _ = tree.query(pts, k=2)
    assert float(dists[:, 1].min()) >= 3.0 - 1e-6


def test_promoted_h73m_submission_and_nan_companion():
    tif_zeros = ROOT / "docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif"
    tif_nan = ROOT / "docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif"
    zip_zeros = ROOT / "docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.zip"
    assert tif_zeros.is_file() and tif_nan.is_file() and zip_zeros.is_file()

    with rasterio.open(tif_zeros) as src:
        assert src.count == 1 and src.dtypes[0] == "float32"
        assert (src.height, src.width) == (3730, 3292)
        assert src.crs.to_epsg() == 32611
        assert src.nodata is None
        arr_z = src.read(1)

    assert np.isfinite(arr_z).all()
    assert float(arr_z.min()) == 0.0 and float(arr_z.max()) == 1.0
    assert int((arr_z > 0.5).sum()) == 37654
    assert set(np.unique(arr_z).tolist()) == {0.0, 1.0}

    with rasterio.open(tif_nan) as src_n:
        assert src_n.count == 1 and src_n.dtypes[0] == "float32"
        assert (src_n.height, src_n.width) == (3730, 3292)
        assert src_n.crs.to_epsg() == 32611
        arr_n = src_n.read(1)

    data_dir = ROOT / ".cache" / "gems_data"
    if (data_dir / "sample_submission.tif").is_file():
        g = grid_mod.load_grid(data_dir)
        assert not np.any((arr_z > 0) & (~g.footprint))
        assert not np.any((arr_z > 0) & g.catalogue)
        assert np.isfinite(arr_n[g.footprint]).all()
        assert np.isnan(arr_n[~g.footprint]).all()
        assert np.array_equal(arr_z[g.footprint], arr_n[g.footprint])

    # Verify minimum inter-dot spacing >= 3.0 px across all 37,654 emitted dots
    pts = np.column_stack(np.nonzero(arr_z > 0.5))
    tree = cKDTree(pts)
    dists, _ = tree.query(pts, k=2)
    assert float(dists[:, 1].min()) >= 3.0 - 1e-6

    # Verify ZIP roundtrip
    with zipfile.ZipFile(zip_zeros) as zf:
        assert zf.namelist() == [tif_zeros.name]
        assert zf.read(tif_zeros.name) == tif_zeros.read_bytes()


def test_run_card_and_protocol_gates():
    rc_path = ROOT / "evidence" / "run_card.json"
    reg_path = ROOT / "registry" / "run_card.json"
    assert rc_path.is_file() and reg_path.is_file()
    rc = json.loads(rc_path.read_text())
    assert rc == json.loads(reg_path.read_text())

    assert rc["verdict"] == "promote"
    assert rc["download_ok"] is True
    assert rc["submit_recommended"] is True
    assert rc["experiments_executed"] == 3
    assert 1 <= rc["submission_note_chars"] <= 140
    assert 1 <= len(rc["submission_name"]) <= 140
    assert rc["validator"]["all_checks_passed"] is True

    # Holdout gate
    h = rc["holdout_dti"]
    assert h["evidence_class"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["withheld_positive_pixels"] == 11321
    assert h["best_dti"] > h["control_dti"]
    assert h["paired_delta_vs_h33_analogue_foldfair"]["ci95"][0] > 0.0
    assert h["paired_delta_vs_h73_1_e1"]["ci95"][0] > 0.0

    # Leakage canary gate
    c = rc["leakage_canary"]
    assert c["all_pass"] is True
    assert c["total_features_audited"] == 85
    assert c["max_symmetric_auc_observed"] <= 0.90

    # Uniqueness gate
    assert rc["correlation_vs_registry"]["stage_A_pass"] is True
    assert rc["correlation_vs_registry"]["stage_B_pass"] is True
    assert rc["overlap_3px_vs_registry"]["pass_mutual_le_0.70"] is True
    assert rc["overlap_3px_vs_registry"]["pass_forward_sparse_le60k_le_0.70"] is True

    tif_zeros = ROOT / rc["submission"]["file"]
    assert _sha256(tif_zeros) == rc["raster_sha256"]
