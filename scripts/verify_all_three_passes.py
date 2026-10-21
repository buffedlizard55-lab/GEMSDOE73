#!/usr/bin/env python3
"""Independent 3-Pass End-to-End Verification Suite for GEMSDOE73 (Lane H73-MCSC).

Executes Pass 1 (GeoTIFF, Math, Canary & Uniqueness Integrity), Pass 2 (Cross-File Link,
SHA-256, Evidence Label & Documentation Audit), and Pass 3 (Pytest, Permissions & Git Hygiene).
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]


def pass1_scientific_and_geotiff_audit() -> dict:
    rc = json.loads((ROOT / "evidence" / "run_card_mcsc.json").read_text())
    rc_reg = json.loads((ROOT / "registry" / "run_card_mcsc.json").read_text())
    rc_doc = json.loads((ROOT / "docs" / "evidence" / "run_card_mcsc.json").read_text())
    rc_dl = json.loads((ROOT / "docs" / "downloads" / "run_card_mcsc.json").read_text())
    assert rc == rc_reg == rc_doc == rc_dl, "run_card_mcsc.json copies out of sync"

    assert rc["verdict"] == "promote"
    assert rc["note_length"] <= 140 and len(rc["note"]) == rc["note_length"]
    assert rc["leakage_canary"]["all_pass"] is True
    assert rc["leakage_canary"]["max_symmetric_auc_stage1"] <= 0.90
    assert rc["leakage_canary"]["max_symmetric_auc_stage2"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["all_uniqueness_gates_passed"] is True
    assert rc["correlation_overlap_vs_registry"]["max_abs_spearman_surface"]["value"] <= 0.90
    assert rc["correlation_overlap_vs_registry"]["max_3px_overlap_vs_sparse_submissions"]["value"] <= 0.70

    ho = rc["holdout_dti"]
    assert ho["pooled_dti"] == 0.109514
    assert ho["beats_h33_foldfair_ci95_gt_0"] is True
    assert ho["beats_h33_far_gt_1km_ci95_gt_0"] is True
    assert ho["beats_d28_ci95_gt_0"] is True
    assert ho["beats_prior_gemsdoe73_pr3_0_0548"] is True

    p_tif = ROOT / rc["deliverables"]["primary_zeros_tif"]["path"]
    n_tif = ROOT / rc["deliverables"]["companion_nan_tif"]["path"]
    z_pkg = ROOT / rc["deliverables"]["zip_bundle"]["path"]
    for p, key in ((p_tif, "primary_zeros_tif"), (n_tif, "companion_nan_tif"), (z_pkg, "zip_bundle")):
        assert p.is_file(), f"Missing {p}"
        assert hashlib.sha256(p.read_bytes()).hexdigest() == rc["deliverables"][key]["sha256"]
        assert p.stat().st_size == rc["deliverables"][key]["size_bytes"]
        mode = stat.S_IMODE(p.stat().st_mode)
        assert (mode & 0o444) == 0o444, f"File {p} is not world-readable: {oct(mode)}"

    with zipfile.ZipFile(z_pkg) as zf:
        assert p_tif.name in zf.namelist()
        assert hashlib.sha256(zf.read(p_tif.name)).hexdigest() == rc["raster_sha256"]

    with rasterio.open(ROOT / ".cache/gems_data/sample_submission.tif") as s_tpl, rasterio.open(
        ROOT / ".cache/gems_data/existing_faults.tif"
    ) as s_cat:
        foot = np.isfinite(s_tpl.read(1))
        cat = s_cat.read(1) > 0
        dcat = ndi.distance_transform_edt(~cat)

    with rasterio.open(p_tif) as src:
        assert str(src.crs) == "EPSG:32611"
        assert (src.height, src.width) == (3730, 3292)
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.nodata is None
        arr = src.read(1)
        assert np.all(np.isfinite(arr))
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert int((arr == 1.0).sum()) == 37654
        assert int((arr == 0.0).sum()) + 37654 == arr.size
        assert int(arr[~foot].sum()) == 0
        assert int(arr[cat].sum()) == 0
        assert int(arr[dcat <= 2.0].sum()) == 0

    return {"pass1": "ALL_CHECKS_PASSED", "sha256": rc["raster_sha256"], "dots": 37654}


def pass2_cross_file_docs_and_links_audit() -> dict:
    rc = json.loads((ROOT / "evidence" / "run_card_mcsc.json").read_text())
    sha = rc["raster_sha256"]
    readme = (ROOT / "README.md").read_text()
    assert "Maximize" in readme and "Own the Outcome" in readme
    assert sha in readme
    assert rc["submission_name"] in readme
    assert rc["note"] in readme
    for tag in ("HOLDOUT-DTI", "ORGANIZER-CONFIRMED", "OWNER-REPORT"):
        assert tag in readme, f"Missing required evidence/status label {tag} in README.md"

    irr = (ROOT / "docs" / "irregularities.md").read_text()
    for code in ("IR-73-15", "IR-73-16"):
        assert code in irr, f"Missing {code} in docs/irregularities.md"

    checked_links = 0
    html_files = sorted((ROOT / "docs").glob("*.html"))
    for hf in html_files:
        if hf.name == "404.html":
            continue
        txt = hf.read_text()
        if hf.name in ("index.html", "executive-summary.html", "h73-mcsc.html"):
            assert sha in txt, f"H73-MCSC SHA-256 missing on {hf.name}"
        for target in re.findall(r'(?:href|src)="([^"#?]+)"', txt):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (hf.parent / target).resolve()
            assert resolved.is_file() and resolved.stat().st_size > 0, f"Broken link {target} in {hf.name} -> {resolved}"
            checked_links += 1

    return {"pass2": "ALL_CHECKS_PASSED", "html_pages_verified": len(html_files) - 1, "local_links_verified": checked_links}


def pass3_tests_and_git_hygiene_audit() -> dict:
    res = subprocess.run([str(ROOT / ".venv/bin/pytest"), "-q"], cwd=ROOT, capture_output=True, text=True, check=True)
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True).strip()
    assert branch == "arena/53d58648-gemsdoe73", f"Unexpected branch {branch}"
    status_lines = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines()
    total_delta_bytes = 0
    for ln in status_lines:
        rel = ln[3:].strip().split(" -> ")[-1]
        assert not rel.startswith((".cache/", ".venv/")), f"Forbidden path in git status: {rel}"
        if rel.startswith("data/"):
            assert rel.endswith(".json") and (ROOT / rel).stat().st_size < 100_000, f"Large/binary file in data/: {rel}"
        p = ROOT / rel
        if p.is_file():
            total_delta_bytes += p.stat().st_size
    assert total_delta_bytes < 15 * 1024 * 1024, f"Tracked delta too large: {total_delta_bytes}"
    return {
        "pass3": "ALL_CHECKS_PASSED",
        "branch": branch,
        "pytest_summary": res.stdout.strip().splitlines()[-1],
        "changed_or_new_files_bytes": total_delta_bytes,
    }


def main() -> None:
    p1 = pass1_scientific_and_geotiff_audit()
    p2 = pass2_cross_file_docs_and_links_audit()
    p3 = pass3_tests_and_git_hygiene_audit()
    print(json.dumps({"PASS_1": p1, "PASS_2": p2, "PASS_3": p3}, indent=2))


if __name__ == "__main__":
    main()
