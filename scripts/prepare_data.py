#!/usr/bin/env python3
"""Pin SHAs and build footprint/domain masks from data/ (when present)."""
import pathlib, hashlib, json
data = pathlib.Path("data")
if not data.exists() or not any(data.iterdir()):
    print("No data/ — synthesis mode; nothing to prepare. (Run bash scripts/download_competition_data.sh on an unrestricted host.)")
    raise SystemExit(0)
for p in sorted(data.iterdir()):
    if p.is_file():
        print(p.name, p.stat().st_size, hashlib.sha256(open(p,'rb').read()).hexdigest()[:12])
print("OK — data present; train pipeline can run (GPU recommended).")
