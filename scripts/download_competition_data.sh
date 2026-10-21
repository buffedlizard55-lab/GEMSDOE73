#!/usr/bin/env bash
# Autonomously restore and SHA-256 verify all 28 competition, external USGS/GDR,
# and calibration rasters from registry/data_manifest.json into .cache/gems_data/,
# and populate data/ with lightweight symlinks so both data/ and .cache/gems_data/ work.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="python3"
fi
"$PY" "${ROOT}/scripts/restore_data.py" --group all
"$PY" "${ROOT}/scripts/prepare_data.py" --verify-only
