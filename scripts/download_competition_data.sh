#!/bin/bash
# Download competition data — requires DrivenData login.
# Run on any unrestricted machine with credentials, then copy data/ to the sandbox.
set -e
DATA_URL="https://www.drivendata.org/competitions/306/competition-doe-gems/data/"
echo "Download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from:"
echo "  $DATA_URL"
echo "Place them in data/ (this sandbox has data/sample_submission.tif and data/labels.tif restored from GEMSDOE24 mirror)."
echo "Also run: python scripts/prepare_data.py  # builds feature stack"
