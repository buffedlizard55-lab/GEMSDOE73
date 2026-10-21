#!/usr/bin/env python3
import pathlib, sys, json, hashlib
import numpy as np, rasterio
for p in sys.argv[1:]:
    with rasterio.open(p) as src:
        a=src.read(1)
        ok = (src.crs.to_epsg()==32611 and src.width==3292 and src.height==3730 and src.count==1 and src.dtypes[0]=='float32' and src.nodata is None and np.isfinite(a).all() and float(a.min())>=0 and float(a.max())<=1 and int(((a<0)|(a>1)).sum())==0)
        sha=hashlib.sha256(open(p,'rb').read()).hexdigest()
        print(f"{p}: {src.crs} {src.shape} {src.dtypes[0]} nodata={src.nodata} min={a.min():.2f} max={a.max():.2f} finite={np.isfinite(a).all()} emitted={(a>0).sum()} sha={sha[:8]} {'PASS' if ok else 'FAIL'}")
        if not ok: sys.exit(2)
print("All files PASS")
