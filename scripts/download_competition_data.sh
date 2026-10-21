#!/usr/bin/env bash
set -euo pipefail
# Download competition data — requires DrivenData login (not available in sandbox).
# Run this on any unrestricted machine with a valid login into data/.
echo "This script documents the manual step. In sandbox, dropbox is TLS-blocked and DrivenData requires auth."
echo "Steps on your machine:"
echo "  1. Log into https://www.drivendata.org/competitions/306/competition-doe-gems/data/"
echo "  2. Download: training_features.tif, labels.tif (==existing_faults.tif), sample_submission.tif, 1m_DEM_links.csv"
echo "  3. Mirror dropbox extras (also login-free on unrestricted hosts):"
echo "     https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=1"
echo "     https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=1"
echo "     https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=1"
echo "  4. Place into data/ and run: python scripts/prepare_data.py"
echo "  5. Then: python scripts/generate_tif.py (data mode) and python scripts/validate_tif.py"

mkdir -p data
# Attempt direct fetch (will fail in sandbox due TLS block, but succeeds on normal hosts):
for url in \
  "https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=1" \
  "https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=1" \
  "https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=1"
do
  echo "Trying $url ..."
  curl -k -L -o "data/$(basename ${url%%\?*})" "$url" || echo "  -> failed (expected in sandbox)"
done
ls -lh data/ || true
