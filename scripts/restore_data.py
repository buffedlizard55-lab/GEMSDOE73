#!/usr/bin/env python3
"""Restore and SHA-256 verify the core DrivenData DOE GEMS competition rasters into `.cache/data`.

Also ensures `data/bridge/{existing_faults,labels,sample_submission}.tif` are present and verified.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".cache" / "data"
BRIDGE = ROOT / "data" / "bridge"

PINS = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}

SOURCES = {
    "training_features.tif": (
        "GEMSDOE",
        "c0c06ac82178f26b94fce3397036ef8f12a2f3a0",
        [f"data/bridge/gems-geodawn-numerical-features.tif.part-00{i}" for i in range(5)],
    ),
    "existing_faults.tif": (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        ["data/bridge/existing_faults.tif"],
    ),
    "sample_submission.tif": (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        ["data/bridge/sample_submission.tif"],
    ),
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_members(repo: str, ref: str, members: list[str], out_path: Path) -> None:
    url = f"https://codeload.github.com/buffedlizard55-lab/{repo}/tar.gz/{ref}"
    wanted = set(members)
    chunks: dict[str, Path] = {}
    tmp_dir = out_path.parent / "_tmp_extract"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "gems73-restore"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
                if rel in wanted:
                    part_file = tmp_dir / Path(rel).name
                    src = tf.extractfile(member)
                    assert src is not None
                    with part_file.open("wb") as out:
                        shutil.copyfileobj(src, out, 1 << 20)
                    chunks[rel] = part_file
                    if len(chunks) == len(wanted):
                        break
    missing = [m for m in members if m not in chunks]
    if missing:
        raise FileNotFoundError(f"Missing members {missing} from {repo}@{ref}")
    tmp_out = out_path.with_suffix(".assembling")
    with tmp_out.open("wb") as out:
        for m in members:
            with chunks[m].open("rb") as src:
                shutil.copyfileobj(src, out, 1 << 20)
            chunks[m].unlink(missing_ok=True)
    tmp_out.replace(out_path)
    shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    BRIDGE.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, dict] = {}
    for name, expected in PINS.items():
        target = DATA / name
        bridge_file = BRIDGE / name
        if not (target.is_file() and sha(target) == expected):
            if bridge_file.is_file() and sha(bridge_file) == expected:
                shutil.copy2(bridge_file, target)
            else:
                repo, ref, parts = SOURCES[name]
                extract_members(repo, ref, parts, target)
        got = sha(target)
        ok = got == expected
        if not ok:
            raise RuntimeError(f"SHA-256 mismatch for {name}: got {got}, expected {expected}")
        if name in ("existing_faults.tif", "sample_submission.tif"):
            if not (bridge_file.is_file() and sha(bridge_file) == expected):
                shutil.copy2(target, bridge_file)
            if name == "existing_faults.tif":
                lbl = BRIDGE / "labels.tif"
                if not (lbl.is_file() and sha(lbl) == expected):
                    shutil.copy2(target, lbl)
                lbl_cache = DATA / "labels.tif"
                if not (lbl_cache.is_file() and sha(lbl_cache) == expected):
                    shutil.copy2(target, lbl_cache)
        receipt[name] = {
            "sha256": got,
            "expected": expected,
            "bytes": target.stat().st_size,
            "ok": ok,
        }
    (ROOT / "evidence" / "restore_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
