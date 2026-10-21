#!/usr/bin/env python3
"""H73-2 diagnostic: do local proxies rank OWNER-REPORT live scores?

For every restored scored raster with a live score in the brief's ledger,
compute static DTI vs (a) full catalogue, (b) SGMC off-catalogue (d>3),
(c) SGMC off-catalogue piedmont subset, and Spearman vs live.  Analysis
only - never used to build or select the GEMSDOE73 surface.
"""
import json, os, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage
from scipy.stats import spearmanr
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "src"))
from gems57 import grid as grid_mod, metric
from gems73 import surface as S
DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))
SCORED = [
 ("h19_5", DATA/"scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif", 0.1922),
 ("h19_4", DATA/"scored/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif", 0.1894),
 ("h16_1", DATA/"scored/gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif", 0.1855),
 ("d1_5", DATA/"scored/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
 ("d2_8", DATA/"scored/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
 ("topogap_d1_5", DATA/"scored/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449),
 ("lattice", DATA/"scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif", 0.0904),
 ("hedge", DATA/"scored/8GEMSDOE_Hedge-v2_submission.tif", 0.1563),
 ("ctxridge", DATA/"scored/gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif", 0.1280),
 ("dottedridge", DATA/"scored/gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif", 0.1839),
 ("ens12", DATA/"scored/gemsdoe-ens12-adopted-7f00890a.tif", 0.1563),
 ("placeholder", DATA/"scored/gemsdoe9-PLACEHOLDER-2314b599.tif", 0.0107),
 ("h33_champion", Path("/home/user/refs/g32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"), 0.2778),
]
g = grid_mod.load_grid(DATA); foot, cat = g.footprint, g.catalogue
dcat = ndimage.distance_transform_edt(~cat)
sg = S.read_band(DATA/"external/derived_sgmc_faults_100m_u8.tif",1) > 0
slope = S.official_band(DATA,19); depth = S.official_band(DATA,15)
pied = foot & (depth>=250) & (slope <= float(np.nanpercentile(slope[cat],80)))
truths = {"catalogue": (cat, foot), "sgmc_off": (sg & (dcat>3), foot & ~cat),
          "sgmc_pied": (sg & (dcat>3) & pied, foot & ~cat)}
rows=[]
for name, p, live in SCORED:
    with rasterio.open(p) as s: a=s.read(1)
    dots = np.isfinite(a) & (a>0.5)
    row={"name":name,"live_owner_report":live,"dots":int(dots.sum())}
    for tn,(t,v) in truths.items(): row[tn]=metric.dti_binary(dots,t,valid=v)["dti"]
    rows.append(row); print(row, flush=True)
live=np.array([r["live_owner_report"] for r in rows])
corr={tn: float(spearmanr(live,[r[tn] for r in rows]).statistic) for tn in truths}
out={"evidence_class":"MEASURED-HERE proxies vs OWNER-REPORT live scores (no organizer receipts in this repo)",
     "n":len(rows),"rows":rows,"spearman_vs_live":corr,
     "reading":"Static catalogue DTI ranks the live champion near-last (B2 prune); treat every local proxy as a screen, not evidence of live gain."}
(ROOT/"evidence"/"instrument_calibration.json").write_text(json.dumps(out,indent=2)+"\n")
print(corr)
