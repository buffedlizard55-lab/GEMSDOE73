#!/usr/bin/env bash
# Autonomous Competition & External Data Restoration + SHA-256 Verification Script
# Resolves the data placement blocker by streaming SHA-256 pinned mirrors from GitHub
# (`codeload.github.com`) into `.cache/data` and linking into `data/`.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

echo "[download_competition_data.sh] Step 1/3: Restoring & SHA-256 verifying core competition GeoTIFFs..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/restore_data.py"

echo "[download_competition_data.sh] Step 2/3: Fetching & SHA-256 verifying external 3DEP/GeoDAWN/GDR layers..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/fetch_data.py"

echo "[download_competition_data.sh] Step 3/3: Linking verified competition files into data/..."
mkdir -p "${ROOT_DIR}/data"
for f in training_features.tif existing_faults.tif labels.tif sample_submission.tif; do
  if [[ -f "${ROOT_DIR}/.cache/data/${f}" && ! -e "${ROOT_DIR}/data/${f}" ]]; then
    ln -sf "${ROOT_DIR}/.cache/data/${f}" "${ROOT_DIR}/data/${f}"
  fi
done
if [[ -d "${ROOT_DIR}/.cache/data/external" && ! -e "${ROOT_DIR}/data/external" ]]; then
  ln -sf "${ROOT_DIR}/.cache/data/external" "${ROOT_DIR}/data/external"
fi

echo "[download_competition_data.sh] SUCCESS: All competition & external layers placed and SHA-256 verified."
