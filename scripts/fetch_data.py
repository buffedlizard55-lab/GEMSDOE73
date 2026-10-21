#!/usr/bin/env python3
"""Fetch and SHA-256 verify all public external geophysical, geomorphic, fluvial, and geothermal layers.

Fixes IR-73-03 (the truncated 58-hex SHA-256 pin for `lidar_scarp_features.json` in `GEMSDOE70/scripts/fetch_data.py`
is restored to its full 64-hex SHA-256 `9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41`).
All large rasters are stored in `.cache/data/external` and `.cache/gems_data` (git-ignored).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST_GEMS = ROOT / ".cache" / "gems_data"
DEST_DATA = ROOT / ".cache" / "data"

EXTERNAL_PINS = [
    # USGS 3DEP 1m LiDAR scarp features + quantisation metadata (IR-73-03 full 64-hex pin fixed)
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/lidar_scarp_features_u8.tif",
        "external/lidar_scarp_features_u8.tif",
        "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    ),
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/lidar_scarp_features.json",
        "external/lidar_scarp_features.json",
        "9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41",
    ),
    # USGS GeoDAWN radiometrics (K, Th, U, TC) & upward-continuation 150m extensions
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/geodawn_rad_u8.tif",
        "external/geodawn_rad_u8.tif",
        "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
    ),
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/geodawn_extensions_u8.tif",
        "external/geodawn_extensions_u8.tif",
        "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
    ),
    # DOE GDR #1391 geothermal springs/wells, volcanic vents, 2m probes, sinter/tufa
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/gdr_wellspring_in_footprint.csv",
        "external/gdr_wellspring_in_footprint.csv",
        "122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea",
    ),
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/gdr_volcanic_vents_in_footprint.csv",
        "external/gdr_volcanic_vents_in_footprint.csv",
        "f91bafbaccaaf2754e71d60434fc0f9eb2c7b880c6e714883f4974542ff6a0bf",
    ),
    (
        "GEMSDOE30",
        "HEAD",
        "data/external/derived_gdr_2m_probes_100m_u8.tif",
        "external/derived_gdr_2m_probes_100m_u8.tif",
        "7ac3cfdf2412f7f8a8b82d928115888c510f106f0254fb0b3988448db2f3b6ec",
    ),
    (
        "GEMSDOE30",
        "HEAD",
        "data/external/derived_gdr_paleo_100m_u8.tif",
        "external/derived_gdr_paleo_100m_u8.tif",
        "d6a3609bd7943fa5f1126a3cc688441aeceee261a76cd6a90a206830400066a4",
    ),
    # US Census TIGER road distance de-confounder & EarthMRI 1m Openness/LRM
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/audit_sources/tiger_road_distance_m.tif",
        "external/tiger_road_distance_m.tif",
        "e5350423508968fa2d32b0a6ae0d3fb4ae3ea645e3b8736f0c8e7ad9ff2f2988",
    ),
    (
        "19GEMSDOE",
        "HEAD",
        "evidence/ci/dem1m_high_prior_openness_lrm.npz",
        "external/dem1m_high_prior_openness_lrm.npz",
        "62f27929747ad3c35be4dd3e0257b0bde7d7bea8566474956e1711269ad451fe",
    ),
    # USGS 3DEP 10m derived stack, fluvial chi/ksn stack, SGMC faults, and raw GDR archives from 60GEMSDOE
    (
        "60GEMSDOE",
        "HEAD",
        "data/external/topo_10m_derived_100m_u8.tif",
        "external/topo_10m_derived_100m_u8.tif",
        "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
    ),
    (
        "60GEMSDOE",
        "HEAD",
        "data/external/dem10_chi_100m_i16.tif",
        "external/dem10_chi_100m_i16.tif",
        "8897ba9c30ef1cd7ad5f23c16c6dfd7bb070e7e757f36fd9486eb45edfd973a5",
    ),
    (
        "60GEMSDOE",
        "HEAD",
        "data/external/dem10_chi_100m_u8.tif",
        "external/dem10_chi_100m_u8.tif",
        "e8830ba6f0bb99f525266b1b3a483b0722d25cd4758c2bbccc6e7f54eb6b1b6a",
    ),
    (
        "60GEMSDOE",
        "HEAD",
        "data/external/sgmc_faults_100m.tif",
        "external/sgmc_faults_100m.tif",
        "26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c",
    ),
    (
        "60GEMSDOE",
        "HEAD",
        "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip",
        "external/2m_temperature_probe_INGENIOUS_regional_data.zip",
        "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3",
    ),
    (
        "60GEMSDOE",
        "HEAD",
        "data/external/paleo_geothermal_regional.zip",
        "external/paleo_geothermal_regional.zip",
        "faffcf697f32dbbf6cbb317cd1effb3e305538ce38eb239d72d0c6fa071e91ca",
    ),
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/derived_sgmc_faults_100m_u8.tif",
        "external/derived_sgmc_faults_100m_u8.tif",
        "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
    ),
]

DEM10_REPO = "GEMSDOE10"
DEM10_TAG = "ext/dem10-36343078537"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_many(repo: str, ref: str, wanted: dict[str, Path]) -> None:
    if not wanted:
        return
    url = f"https://codeload.github.com/buffedlizard55-lab/{repo}/tar.gz/{ref}"
    req = urllib.request.Request(url, headers={"User-Agent": "gems73-fetch-data"})
    with urllib.request.urlopen(req, timeout=240) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                parts = member.name.split("/", 1)
                rel = parts[1] if len(parts) > 1 else parts[0]
                if rel in wanted:
                    dest = wanted[rel]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    fh = tf.extractfile(member)
                    if fh is not None:
                        tmp = dest.with_suffix(dest.suffix + ".tmp")
                        with tmp.open("wb") as out:
                            for chunk in iter(lambda: fh.read(1 << 20), b""):
                                out.write(chunk)
                        tmp.replace(dest)


def main() -> int:
    by_repo_ref: dict[tuple[str, str], dict[str, Path]] = defaultdict(dict)
    for repo, ref, src_path, rel_dest, expected in EXTERNAL_PINS:
        target = DEST_DATA / rel_dest
        alt_target = DEST_GEMS / rel_dest
        if target.exists() and sha256_file(target) == expected:
            if not alt_target.exists():
                alt_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, alt_target)
            continue
        if alt_target.exists() and sha256_file(alt_target) == expected:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(alt_target, target)
            continue
        by_repo_ref[(repo, ref)][src_path] = target

    for (repo, ref), mapping in by_repo_ref.items():
        print(f"[fetch] Streaming {len(mapping)} external layer(s) from {repo}@{ref[:10]}...", flush=True)
        extract_many(repo, ref, mapping)

    verified_ext = {}
    for repo, ref, src_path, rel_dest, expected in EXTERNAL_PINS:
        target = DEST_DATA / rel_dest
        if not target.exists():
            raise FileNotFoundError(f"Missing external layer {rel_dest}")
        got = sha256_file(target)
        if got != expected:
            raise RuntimeError(f"SHA256 mismatch for {rel_dest}: {got} vs {expected}")
        alt_target = DEST_GEMS / rel_dest
        if not alt_target.exists():
            alt_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, alt_target)
        verified_ext[rel_dest] = {"sha256": got, "bytes": target.stat().st_size, "repo": repo, "ref": ref}

    dem10_dir = DEST_GEMS / "dem10"
    dem10_dir.mkdir(parents=True, exist_ok=True)
    man_file = dem10_dir / "manifest.json"
    if not man_file.exists():
        extract_many(DEM10_REPO, DEM10_TAG, {"manifest.json": man_file})
    manifest = json.loads(man_file.read_text())
    need_dem10 = {}
    for ch in manifest["channels"]:
        p = dem10_dir / f"{ch}.f32.npy"
        want = manifest["channel_stats"][ch]["sha256"]
        if not (p.exists() and sha256_file(p) == want):
            need_dem10[f"{ch}.f32.npy"] = p
    if need_dem10:
        print(f"[fetch] Streaming {len(need_dem10)} USGS 3DEP 10m DEM channels from {DEM10_REPO}@{DEM10_TAG}...", flush=True)
        extract_many(DEM10_REPO, DEM10_TAG, need_dem10)
    for ch in manifest["channels"]:
        p = dem10_dir / f"{ch}.f32.npy"
        want = manifest["channel_stats"][ch]["sha256"]
        if sha256_file(p) != want:
            raise RuntimeError(f"10m DEM channel SHA mismatch: {ch}")

    print(
        f"[ok] All {len(EXTERNAL_PINS)} external layers + {len(manifest['channels'])} 10m DEM channels SHA-256 verified.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
