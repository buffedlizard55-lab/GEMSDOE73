#!/usr/bin/env python3
"""Fetch and SHA-256-verify all accessible candidate/scored GeoTIFF rasters across
buffedlizard55-lab/*GEMSDOE* sibling repositories for Parallel-Run Protocol Gate 1.

Uses GraphQL repo listing + zero-rate-limit shallow git clones (with `.cache/registry`
blob reuse) so it never exhausts the GitHub REST API quota.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "registry"
REFS_DIR = Path("/tmp/refs")

CANDIDATE_KEYWORDS = (
    "download",
    "submission",
    "artifact",
    "candidate",
    "evidence",
    "quarantine",
    "scored",
    "calibration",
)
SKIP_INPUT_NAMES = frozenset({
    "training_features.tif",
    "gems-geodawn-numerical-features.tif",
    "labels.tif",
    "existing_faults.tif",
    "sample_submission.tif",
    "example_submission.tif",
    "lidar_scarp_features_u8.tif",
    "geodawn_rad_u8.tif",
    "geodawn_extensions_u8.tif",
    "derived_sgmc_faults_100m_u8.tif",
    "derived_sgmc_faults_100m.tif",
    "sgmc_faults_100m.tif",
    "topo_10m_derived_100m_u8.tif",
    "dem10_chi_100m_i16.tif",
    "dem10_chi_100m_u8.tif",
    "dem10_chi_100m_sig_i32.tif",
    "geodawn_dem_a2_100m.tif",
})


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha(p: Path) -> str:
    data = p.read_bytes()
    hdr = f"blob {len(data)}\0".encode()
    return hashlib.sha1(hdr + data).hexdigest()


def discover_all_gemsdoe_repos() -> list[str]:
    res = subprocess.run(
        ["gh", "repo", "list", "buffedlizard55-lab", "--limit", "200", "--json", "name,diskUsage"],
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(
        r["name"]
        for r in json.loads(res.stdout)
        if "gemsdoe" in r["name"].lower() and int(r.get("diskUsage") or 0) > 0
    )


def ensure_clone(repo: str) -> Path | None:
    if repo == "GEMSDOE73":
        return ROOT
    dest = REFS_DIR / repo
    if (dest / ".git").exists():
        return dest
    REFS_DIR.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["git", "clone", "--depth", "1", "-q", f"https://github.com/buffedlizard55-lab/{repo}.git", str(dest)],
        capture_output=True,
        text=True,
    )
    return dest if r.returncode == 0 else None


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    repos = discover_all_gemsdoe_repos()
    print(f"Syncing {len(repos)} non-empty GEMSDOE repositories via shallow git...", flush=True)

    clones: dict[str, Path] = {}
    errors: list[str] = []
    with cf.ThreadPoolExecutor(10) as ex:
        for repo, path in zip(repos, ex.map(ensure_clone, repos)):
            if path is None:
                errors.append(f"clone_failed:{repo}")
            else:
                clones[repo] = path

    by_sha: dict[str, dict] = {}
    total_files = 0
    for repo, cdir in sorted(clones.items()):
        for tif in sorted(cdir.rglob("*")):
            if not tif.is_file() or ".git" in tif.parts or ".cache" in tif.parts:
                continue
            nm = tif.name.lower()
            if not nm.endswith((".tif", ".tiff")) or nm in SKIP_INPUT_NAMES:
                continue
            rel = str(tif.relative_to(cdir))
            if not any(k in rel.lower() for k in CANDIDATE_KEYWORDS):
                continue
            total_files += 1
            bsha = git_blob_sha(tif)
            cached = CACHE / f"{bsha}.tif"
            if not cached.exists():
                shutil.copy2(tif, cached)
            csha = sha256_file(cached)
            src_label = f"{repo}:{rel}"
            if csha not in by_sha:
                by_sha[csha] = {
                    "blob": bsha,
                    "sha256": csha,
                    "cache_file": str(cached),
                    "repo_first": repo,
                    "sources": [src_label],
                }
            else:
                if src_label not in by_sha[csha]["sources"]:
                    by_sha[csha]["sources"].append(src_label)

    # Also include pinned scored calibration rasters in .cache/gems_data/scored
    scored_dir = ROOT / ".cache" / "gems_data" / "scored"
    if scored_dir.exists():
        for tif in sorted(scored_dir.glob("*.tif")):
            total_files += 1
            bsha = git_blob_sha(tif)
            cached = CACHE / f"{bsha}.tif"
            if not cached.exists():
                shutil.copy2(tif, cached)
            csha = sha256_file(cached)
            src_label = f"pinned_scored:{tif.name}"
            if csha not in by_sha:
                by_sha[csha] = {
                    "blob": bsha,
                    "sha256": csha,
                    "cache_file": str(cached),
                    "repo_first": "pinned_scored",
                    "sources": [src_label],
                }
            else:
                if src_label not in by_sha[csha]["sources"]:
                    by_sha[csha]["sources"].append(src_label)

    out_idx = {
        "complete_accessible_scan": len(errors) == 0,
        "errors": errors,
        "repos_scanned": len(clones),
        "total_candidate_files_seen": total_files,
        "unique_sha256_rasters": len(by_sha),
        "rasters": sorted(by_sha.values(), key=lambda x: (x["repo_first"], x["sources"][0])),
    }
    (CACHE / "full_registry_index.json").write_text(json.dumps(out_idx, indent=2) + "\n")
    print(
        f"COMPLETE: repos={len(clones)} errors={len(errors)} files_seen={total_files} "
        f"unique_sha256={len(by_sha)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
