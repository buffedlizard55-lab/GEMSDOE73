#!/usr/bin/env bash
set -euo pipefail
# Autonomous zero-manual-input competition & auxiliary public geoscience data restoration.
# Streams SHA-256 pinned split archives via codeload.github.com and verifies every byte.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 scripts/prepare_data.py
