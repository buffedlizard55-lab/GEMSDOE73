#!/usr/bin/env python3
"""Synchronize and SHA-256 index every accessible single-band 3730x3292 EPSG:32611
prediction GeoTIFF across all public buffedlizard55-lab GEMSDOE repositories.

Uses zero-rate-limit ``https://codeload.github.com`` streaming tarballs plus all
locally restored reference rasters, storing deduplicated rasters in
``.cache/registry_rasters/<sha256>.tif`` and writing the full manifest to
``evidence/registry_inventory.json``.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.grid import TRANSFORM  # noqa: E402

CACHE_DIR = ROOT / ".cache" / "registry_rasters"
OUT_INDEX = ROOT / "evidence" / "registry_inventory.json"

NON_SUBMISSION_BASENAMES = {
    "existing_faults.tif",
    "labels.tif",
    "sample_submission.tif",
    "example_submission.tif",
    "training_features.tif",
    "gems-geodawn-numerical-features.tif",
    "lidar_scarp_features_u8.tif",
    "geodawn_rad_u8.tif",
    "geodawn_extensions_u8.tif",
    "derived_sgmc_faults_100m.tif",
    "derived_sgmc_faults_100m_u8.tif",
    "sgmc_faults_100m.tif",
    "dem10_chi_100m_i16.tif",
    "dem10_chi_100m_sig_i32.tif",
    "dem10_chi_100m_u8.tif",
    "topo_10m_derived_100m_u8.tif",
    "derived_gdr_2m_probes_100m_u8.tif",
    "derived_gdr_paleo_100m_u8.tif",
    "derived_gdr_qfaults_v2_100m_u8.tif",
    "derived_gdr_volcanics_100m_u8.tif",
    "qfaults_prior_u8.tif",
    "tiger_road_distance_m.tif",
    "blm_closed_claim_distance_m.tif",
    "acquisition_block_id_100m.tif",
    "template-mask.tif",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_valid_grid_raster(path: Path) -> bool:
    try:
        with rasterio.open(path) as src:
            return (
                src.count == 1
                and src.shape == (3730, 3292)
                and src.crs is not None
                and src.crs.to_epsg() == 32611
                and src.transform == TRANSFORM
            )
    except Exception:
        return False


def list_gems_repos() -> list[str]:
    out = subprocess.check_output(
        [
            "gh",
            "api",
            "--paginate",
            "users/buffedlizard55-lab/repos?per_page=100",
            "--jq",
            ".[].name",
        ],
        text=True,
    )
    repos = sorted({line.strip() for line in out.splitlines() if "GEMSDOE" in line.upper()})
    return repos


def fetch_repo_tifs(repo: str) -> tuple[str, str, list[tuple[str, bytes]], str | None]:
    url = f"https://codeload.github.com/buffedlizard55-lab/{repo}/tar.gz/HEAD"
    req = urllib.request.Request(url, headers={"User-Agent": "gemsdoe73-audit/1.0"})
    found: list[tuple[str, bytes]] = []
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                for m in tf:
                    if not m.isfile() or m.size > 60_000_000:
                        continue
                    low = m.name.lower()
                    if not (low.endswith(".tif") or low.endswith(".tiff")):
                        continue
                    rel = m.name.split("/", 1)[1] if "/" in m.name else m.name
                    base = Path(rel).name
                    if base in NON_SUBMISSION_BASENAMES or base.startswith("."):
                        continue
                    if "/bridge/" in rel or "/external/" in rel or "/raw/" in rel:
                        continue
                    f = tf.extractfile(m)
                    if f is not None:
                        found.append((rel, f.read()))
    except urllib.error.HTTPError as e:
        if e.code in (404, 409):
            return repo, "empty_or_missing", [], None
        return repo, "error", [], f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return repo, "error", [], str(e)
    return repo, "ok", found, None


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    repos = list_gems_repos()
    print(f"Discovered {len(repos)} GEMSDOE repositories on GitHub", flush=True)

    by_sha: dict[str, dict] = {}
    repo_status: list[dict] = []
    errors: list[str] = []

    def ingest_bytes(repo: str, rel: str, data: bytes) -> None:
        digest = sha256_bytes(data)
        dst = CACHE_DIR / f"{digest}.tif"
        if not dst.exists():
            dst.write_bytes(data)
        if not is_valid_grid_raster(dst):
            return
        src_tag = f"{repo}:{rel}"
        if digest not in by_sha:
            by_sha[digest] = {
                "sha256": digest,
                "repo_first": repo,
                "cache_file": str(dst.relative_to(ROOT)),
                "bytes": len(data),
                "sources": [src_tag],
            }
        elif src_tag not in by_sha[digest]["sources"]:
            by_sha[digest]["sources"].append(src_tag)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(fetch_repo_tifs, r) for r in repos]
        for fut in concurrent.futures.as_completed(futs):
            repo, st, items, err = fut.result()
            repo_status.append({"repo": repo, "status": st, "tifs_found": len(items), "error": err})
            if err:
                errors.append(f"{repo}: {err}")
            for rel, b in items:
                ingest_bytes(repo, rel, b)

    # Also include local scored mirrors in .cache/gems_data/scored
    scored_dir = ROOT / ".cache" / "gems_data" / "scored"
    if scored_dir.exists():
        for p in sorted(scored_dir.glob("*.tif")):
            ingest_bytes("local_scored_mirror", p.name, p.read_bytes())

    rasters = sorted(by_sha.values(), key=lambda r: (r["repo_first"], r["sources"][0], r["sha256"]))
    for r in rasters:
        r["sources"].sort()

    payload = {
        "schema_version": 1,
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repos_discovered": len(repos),
        "repos": sorted(repo_status, key=lambda x: x["repo"]),
        "unique_rasters": len(rasters),
        "complete_accessible_scan": len(errors) == 0,
        "errors": errors,
        "rasters": rasters,
    }
    OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_INDEX.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        f"Indexed {len(rasters)} unique valid 3730x3292 EPSG:32611 rasters across "
        f"{len(repos)} repos (errors={len(errors)}, complete={len(errors) == 0})",
        flush=True,
    )


if __name__ == "__main__":
    main()
