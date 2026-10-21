#!/usr/bin/env bash
# Restore and SHA-256 verify all core competition rasters, public USGS/DOE external layers,
# and historical scored reference artifacts via zero-rate-limit codeload tar streams, linking into data/.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
if [ ! -x "${PY}" ]; then
  PY="python3"
fi
exec "${PY}" "${ROOT}/scripts/restore_data.py" --group all --link-data "$@"
