#!/usr/bin/env python3
"""Verify restored competition & external data in .cache/gems_data/ and link into data/.

Ensures any script reading either `.cache/gems_data/` or `data/` finds all SHA-256
verified rasters without duplicating 500+ MB inside the git working tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
DATA_DIR = ROOT / "data"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-only", action="store_true", help="Verify hashes and symlinks without building feature memmap")
    args = ap.parse_args()

    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    if not (CACHE_DIR / "training_features.tif").exists():
        import subprocess
        import sys
        subprocess.run([sys.executable, str(ROOT / "scripts" / "restore_data.py"), "--group", "all"], check=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    verified = 0
    for entry in manifest["files"]:
        src = CACHE_DIR / entry["dest"]
        if not src.exists():
            raise SystemExit(f"Missing restored file: {src}")
        got = sha256_file(src)
        if got != entry["sha256"]:
            raise SystemExit(f"SHA-256 mismatch on {src}: {got} != {entry['sha256']}")
        dst = DATA_DIR / entry["dest"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() and not dst.is_symlink():
            rel = os.path.relpath(src, dst.parent)
            dst.symlink_to(rel)
        verified += 1

    print(f"OK — verified {verified}/{len(manifest['files'])} SHA-256-pinned files in {CACHE_DIR} (linked in {DATA_DIR}).")
    if not args.verify_only:
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        sys.path.insert(0, str(ROOT / "vendor"))
        from gems57 import grid as grid_mod
        from gems73.features import build_feature_memmap
        g = grid_mod.load_grid(CACHE_DIR)
        mmap_path = ROOT / ".cache" / "work" / "h73m_features_fp.f32"
        X, names, _, meta = build_feature_memmap(mmap_path, g.footprint, g.transform, CACHE_DIR)
        print(f"OK — feature memmap ready: shape={X.shape}, features={len(names)}, footprint_px={meta['n_footprint_pixels']}")


if __name__ == "__main__":
    main()
