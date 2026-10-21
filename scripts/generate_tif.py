#!/usr/bin/env python3
"""Reproduce the GEMSDOE73 validated GeoTIFF submission from verified inputs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "scripts/prepare_data.py")], check=True)
    return subprocess.run([sys.executable, str(ROOT / "scripts/run_gems73_experiments.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
