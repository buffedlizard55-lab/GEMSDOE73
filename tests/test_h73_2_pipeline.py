"""Pass 2 & Pass 3 comprehensive verification test suite for GEMSDOE73 H73-2 (PR #12)."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import rasterio

from src.gems73.emit import greedy_dots, submodular_dti_dots
from src.gems73.features_h73_2 import BLOCKED_COLUMNS, FEATURE_NAMES
from src.gems73.metric import dti_exact

ROOT = Path(__file__).resolve().parents[1]


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.refs.append(v)


def test_submodular_beats_greedy_on_fault_junction():
    h, w = 40, 40
    truth = np.zeros((h, w), dtype=bool)
    truth[20, 6:34] = True
    truth[8:32, 20] = True
    prob = np.where(truth, 0.85, 0.005).astype(np.float32)
    allow = np.ones((h, w), dtype=bool)
    d_sub = submodular_dti_dots(np.power(prob, 1.35), allow, budget=16, min_dist=2.0)
    d_grd = greedy_dots(prob, allow, budget=16, min_dist=3.0)
    assert int(d_sub.sum()) == 16
    assert dti_exact(d_sub, truth)["dti"] >= dti_exact(d_grd, truth)["dti"]


def test_blocked_fault_distance_column_invariant():
    assert "dist_known_fault_px" in BLOCKED_COLUMNS
    assert len(FEATURE_NAMES) == 48
    for nm in FEATURE_NAMES:
        assert "catalog" not in nm.lower() and "dist_known" not in nm.lower()


def test_leakage_canary_and_run_card_h73_2_invariants():
    canary = json.loads((ROOT / "evidence" / "canary.json").read_text())
    assert canary["n_features_tested"] == 48
    assert canary["all_passed"] is True
    assert canary["max_symmetric_auc"] <= 0.90

    rc = json.loads((ROOT / "evidence" / "run_card_h73_2.json").read_text())
    assert rc == json.loads((ROOT / "docs" / "downloads" / "run_card_h73_2.json").read_text())
    assert rc == json.loads((ROOT / "docs" / "evidence" / "run_card_h73_2.json").read_text())
    assert rc["verdict"] == "promote"
    assert rc["submission"]["note_chars"] <= 140
    assert rc["submission"]["emitted_dots"] == 37654
    e3 = rc["holdout_dti"]["E3_mecs_stage2_submodular"]["dti"]
    e2 = rc["holdout_dti"]["E2_mecs_stage2_greedy"]["dti"]
    e1 = rc["holdout_dti"]["E1_mecs_stage1_greedy"]["dti"]
    ctrl = rc["holdout_dti"]["control_h33_analogue_foldfair"]["dti"]
    assert ctrl < e1 < e2 < e3
    diff = rc["holdout_dti"]["paired_delta_E3_minus_h33_foldfair"]
    assert diff["delta"] > 0.0 and diff["ci95"][0] > 0.0

    uq = rc["uniqueness_vs_registry"]
    assert uq["complete_accessible_scan"] is True
    assert uq["vendor_unique"] is True
    assert uq["unique_grid_rasters_compared"] >= 963
    assert uq["max_stage_a_surface_spearman"] <= 0.90
    assert uq["max_stage_b_dots_spearman"] <= 0.90
    assert uq["max_mutual_3px_overlap_all_949"] <= 0.70
    assert uq["max_forward_3px_overlap_matched_budget_749"] <= 0.70


def test_shipped_h73_2_primary_zeros_zip_and_nan_bytes():
    rc = json.loads((ROOT / "evidence" / "run_card_h73_2.json").read_text())
    zeros_p = ROOT / "docs" / "downloads" / rc["submission"]["file"]
    zip_p = ROOT / "docs" / "downloads" / rc["submission"]["zip_file"]
    nan_p = ROOT / "docs" / "downloads" / "gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-nan.tif"

    assert zeros_p.is_file() and zip_p.is_file() and nan_p.is_file()
    assert _sha256(zeros_p) == rc["raster_sha256"]["primary_portal_safe_zeros_tif"]
    assert _sha256(zip_p) == rc["raster_sha256"]["primary_zip"]
    assert _sha256(nan_p) == rc["raster_sha256"]["companion_nan_tif"]

    with zipfile.ZipFile(zip_p) as zf:
        names = zf.namelist()
        assert len(names) == 1 and names[0].endswith(".tif")

    with rasterio.open(zeros_p) as sz, rasterio.open(nan_p) as sn:
        az = sz.read(1)
        an = sn.read(1)
        assert sz.crs.to_epsg() == 32611 and sn.crs.to_epsg() == 32611
        assert sz.shape == (3730, 3292) and sn.shape == (3730, 3292)
        assert sz.nodata is None
        assert np.isfinite(az).all()
        assert float(az.min()) == 0.0 and float(az.max()) == 1.0
        assert int((az == 1.0).sum()) == 37654
        valid_nan = np.isfinite(an)
        assert np.array_equal(az[valid_nan], an[valid_nan])


def test_all_docs_html_and_readme_links_resolve_with_zero_dead_refs():
    html_files = sorted((ROOT / "docs").glob("*.html"))
    assert (ROOT / "docs" / "h73-2-mecs.html").is_file()
    for hf in html_files:
        txt = hf.read_text()
        parser = _LinkCollector()
        parser.feed(txt)
        for ref in parser.refs:
            assert "7f3c2a9e" not in ref, f"dead filename link left in {hf.name}"
            if ref.startswith(("http://", "https://", "mailto:", "#", "javascript:", "data:")):
                continue
            clean_ref = ref.split("#")[0].split("?")[0]
            if not clean_ref:
                continue
            target = (hf.parent / clean_ref).resolve()
            assert target.exists(), f"Broken link `{ref}` in `{hf.name}` -> `{target}`"

    readme_txt = (ROOT / "README.md").read_text()
    assert "gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-zeros.tif" in readme_txt
    for m in re.finditer(r"\]\(([^)]+)\)", readme_txt):
        ref = m.group(1).strip()
        assert "7f3c2a9e" not in ref, f"dead filename link left in README.md: {ref}"
        if ref.startswith(("http://", "https://", "#")):
            continue
        target = (ROOT / ref.split("#")[0]).resolve()
        assert target.exists(), f"Broken markdown link `{ref}` in README.md -> `{target}`"
