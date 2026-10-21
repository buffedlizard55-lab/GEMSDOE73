#!/usr/bin/env python3
"""Verify competition & public USGS/DOE external rasters, check SHA-256 digests, and write data/prepared_manifest.json."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def resolve_data_root() -> Path:
    env = os.environ.get("GEMS_DATA_DIR")
    if env and Path(env).exists():
        return Path(env)
    if (ROOT / "data" / "training_features.tif").exists():
        return ROOT / "data"
    return ROOT / ".cache" / "gems_data"


def main() -> None:
    t0 = time.time()
    droot = resolve_data_root()
    man = json.loads((ROOT / "registry" / "data_manifest.json").read_text())

    verified = []
    for entry in man["files"]:
        p = droot / entry["dest"]
        if not p.exists():
            sys.exit(f"Missing required file {p}. Run `bash scripts/download_competition_data.sh` first.")
        got_sha = sha256_file(p)
        if got_sha != entry["sha256"]:
            sys.exit(f"SHA-256 mismatch for {entry['dest']}: {got_sha} != {entry['sha256']}")
        info = {
            "id": entry["id"],
            "dest": entry["dest"],
            "group": entry["group"],
            "bytes": p.stat().st_size,
            "sha256": got_sha,
            "status": "VERIFIED",
        }
        if p.suffix.lower() in {".tif", ".tiff"} and entry["group"] in {"core", "external"}:
            with rasterio.open(p) as src:
                assert src.shape == (3730, 3292), f"Unexpected grid shape for {p}: {src.shape}"
                assert str(src.crs) == "EPSG:32611", f"Unexpected CRS for {p}: {src.crs}"
                info["shape"] = list(src.shape)
                info["crs"] = str(src.crs)
                info["count"] = src.count
                info["dtype"] = src.dtypes[0]
        verified.append(info)

    with rasterio.open(droot / "sample_submission.tif") as s_sub, rasterio.open(droot / "labels.tif") as s_lab:
        sub_arr = s_sub.read(1)
        lab_arr = s_lab.read(1)
        footprint = np.isfinite(sub_arr)
        sub_pos = (sub_arr > 0) & footprint
        lab_pos = (lab_arr > 0) & footprint

    with rasterio.open(droot / "external" / "lidar_scarp_features_u8.tif") as s_lid:
        lid_valid = (s_lid.read(12) > 0) & footprint

    with rasterio.open(droot / "external" / "topo_10m_derived_100m_u8.tif") as s_t10:
        t10_valid = (s_t10.read(1) > 0) & footprint

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_root": str(droot),
        "verified_files_count": len(verified),
        "grid": {
            "crs": "EPSG:32611",
            "shape": [3730, 3292],
            "pixel_m": 100.0,
            "footprint_pixels": int(footprint.sum()),
            "outside_pixels": int((~footprint).sum()),
            "catalogue_positive_pixels": int(lab_pos.sum()),
            "sample_submission_equals_catalogue": bool(np.array_equal(sub_pos, lab_pos)),
        },
        "sensor_coverage": {
            "lidar_1m_valid_pixels": int(lid_valid.sum()),
            "lidar_1m_valid_fraction": round(float(lid_valid.sum() / footprint.sum()), 6),
            "lidar_1m_gap_pixels": int((footprint & ~lid_valid).sum()),
            "dem_10m_valid_pixels": int(t10_valid.sum()),
            "dem_10m_valid_fraction": round(float(t10_valid.sum() / footprint.sum()), 6),
        },
        "files": verified,
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "prepared_manifest.json").write_text(json.dumps(out, indent=2) + "\n")
    (ROOT / "evidence" / "data_verification.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"Prepared & verified {len(verified)} files in {out['elapsed_seconds']}s | "
        f"footprint={out['grid']['footprint_pixels']:,} | catalogue={out['grid']['catalogue_positive_pixels']:,} | "
        f"1m-LiDAR={out['sensor_coverage']['lidar_1m_valid_fraction']*100:.2f}% | "
        f"10m-DEM={out['sensor_coverage']['dem_10m_valid_fraction']*100:.2f}%"
    )


if __name__ == "__main__":
    main()
