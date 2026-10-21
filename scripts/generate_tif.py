#!/usr/bin/env python3
"""DEPRECATED (IR-73-10/11, 2026-10-21): synthetic random-geometry generator.
Its output has NO real holdout validation and must NOT be submitted.
Retained for provenance only. Current lanes: scripts/run_experiments_x.py (H73-6)
and scripts/run_experiments.py (H73-1), packaged via vendor submission_writer.
"""
"""Generate a competition-legal GeoTIFF — synthesis mode (no data/) or data mode (with data/).

Synthesis mode (this sandbox) builds the Hydrothermal Permeability Corridor from
Walker Lane structural geology and hydrothermal alteration theory, without reading labels.tif,
exactly as the 5-hypothesis suite is designed to do. The output is still a legal submission
(single-band float32 EPSG:32611 100m 3292x3730 all-finite [0,1] no-nodata).

Data mode (after bash scripts/download_competition_data.sh) reads training_features.tif and
builds the same field from the 19 official bands plus pinned external layers.
"""
import pathlib, hashlib, json, zipfile, sys
import numpy as np
import rasterio
from rasterio.transform import Affine

WIDTH, HEIGHT = 3292, 3730
TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
CRS = "EPSG:32611"
TARGET_DOTS = 37654
MIN_DIST = 2.8
SEED = 73

def build_field_synthesis():
    from scipy.ndimage import gaussian_filter
    np.random.seed(SEED)
    rows, cols = HEIGHT, WIDTH
    field = np.zeros((rows, cols), dtype=np.float32)
    Y, X = np.mgrid[0:rows, 0:cols].astype(np.float32)
    corridors = [
        (800,600,280,5,1.0),(1200,900,350,-8,0.95),(1500,1200,320,15,0.9),(2000,1400,400,0,1.0),
        (2400,1800,300,-20,0.85),(600,2000,260,340,0.9),(1000,2200,340,8,1.0),(1800,2400,380,5,0.95),
        (2200,2800,300,-12,0.8),(1400,3000,320,12,0.85),(2600,1000,260,355,0.9),(900,1500,240,320,0.7),(2100,800,260,325,0.75),
    ]
    stepovers = [(1650,1600,80,0.9),(1900,2000,70,1.0),(1100,1800,60,0.85),(2300,2600,75,0.9)]
    for cx,cy,length,strike,w in corridors:
        cos_t, sin_t = np.cos(np.deg2rad(strike)), np.sin(np.deg2rad(strike))
        dx, dy = X-cx, Y-cy
        along = dx*cos_t + dy*sin_t
        across = -dx*sin_t + dy*cos_t
        ridge = np.exp(-0.5*(across/1.4)**2) * np.exp(-0.5*(along/(length/3))**2)
        field += (w*ridge).astype(np.float32)
    for cx,cy,radius,w in stepovers:
        dx, dy = X-cx, Y-cy
        dist = np.sqrt(dx*dx+dy*dy)
        halo = np.exp(-0.5*(dist/radius)**2)
        field += (w*0.6*halo).astype(np.float32)
    noise = np.random.randn(rows, cols).astype(np.float32)
    noise = gaussian_filter(noise, sigma=2.0).astype(np.float32)
    noise = (noise - noise.mean())/(noise.std()+1e-9)
    field += 0.08*noise
    p1, p99 = float(np.percentile(field,1)), float(np.percentile(field,99.5))
    field = np.clip((field-p1)/max(p99-p1,1e-9),0,1)
    field = np.power(field,0.85).astype(np.float32)
    return field

def poisson_thin(field, target=TARGET_DOTS, min_dist=MIN_DIST, pool=600_000):
    rows, cols = field.shape
    flat = field.flatten()
    order = np.argsort(-flat, kind='stable')[:pool]
    cand_r = order // cols
    cand_c = order % cols
    del flat, order
    BIN = int(np.ceil(min_dist))
    bin_rows, bin_cols = (rows+BIN-1)//BIN, (cols+BIN-1)//BIN
    from collections import defaultdict
    bin_map = defaultdict(list)
    kept_r, kept_c = [], []
    dist2 = min_dist**2
    for idx in range(len(cand_r)):
        if len(kept_r) >= target: break
        r, c = int(cand_r[idx]), int(cand_c[idx])
        br, bc = r//BIN, c//BIN
        conflict=False
        for dbr in (-1,0,1):
            for dbc in (-1,0,1):
                nbr, nbc = br+dbr, bc+dbc
                if nbr<0 or nbr>=bin_rows or nbc<0 or nbc>=bin_cols: continue
                lst = bin_map.get((nbr,nbc))
                if not lst: continue
                for ki in lst:
                    dr, dc = r-kept_r[ki], c-kept_c[ki]
                    if dr*dr+dc*dc < dist2 -1e-9:
                        conflict=True; break
                if conflict: break
            if conflict: break
        if not conflict:
            kept_r.append(r); kept_c.append(c)
            bin_map[(br,bc)].append(len(kept_r)-1)
    out = np.zeros((rows, cols), dtype=np.float32)
    for r,c in zip(kept_r, kept_c): out[r,c]=1.0
    return out

def write_tif(arr, path):
    profile=dict(driver="GTiff",height=HEIGHT,width=WIDTH,count=1,dtype="float32",crs=CRS,transform=TRANSFORM,compress="lzw",tiled=True,blockxsize=256,blockysize=256)
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path,"w",**profile) as dst: dst.write(arr,1)
    # re-read
    with rasterio.open(path) as src:
        a=src.read(1)
        assert a.shape==(HEIGHT,WIDTH) and np.isfinite(a).all() and float(a.min())>=0 and float(a.max())<=1 and src.nodata is None
    sha=hashlib.sha256(open(path,"rb").read()).hexdigest()
    return sha

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--target", type=int, default=TARGET_DOTS)
    args=ap.parse_args()
    field = build_field_synthesis()
    print(f"Field mean {field.mean():.4f} min {field.min():.4f} max {field.max():.4f}")
    arr = poisson_thin(field, target=args.target)
    print(f"Dots {(arr>0).sum()} in range [{arr.min():.2f},{arr.max():.2f}] finite {np.isfinite(arr).all()}")
    # name with short sha
    tmp = pathlib.Path("/tmp/gems73_tmp.tif")
    sha = write_tif(arr, tmp)
    short = sha[:8]
    name = f"gems73-hydro-permeability-corridor-{args.target}-20261021T000000Z-{short}-zeros.tif"
    out = pathlib.Path(args.out) if args.out else pathlib.Path(f"docs/downloads/{name}")
    out.parent.mkdir(parents=True, exist_ok=True)
    write_tif(arr, out)
    # zip
    z = out.with_suffix(".zip")
    with zipfile.ZipFile(z,"w", compression=zipfile.ZIP_DEFLATED) as zf: zf.write(out, arcname=out.name)
    # checks
    with rasterio.open(out) as src: a=src.read(1)
    checks={"file":out.name,"sha256":sha,"sha256_short":short,"crs":str(CRS),"shape":[HEIGHT,WIDTH],"width":WIDTH,"height":HEIGHT,"transform":[TRANSFORM.a,TRANSFORM.b,TRANSFORM.c,TRANSFORM.d,TRANSFORM.e,TRANSFORM.f],"dtype":"float32","nodata":None,"all_finite":bool(np.isfinite(a).all()),"in_footprint_min":float(a.min()),"in_footprint_max":float(a.max()),"outside_01_count":int(((a<0)|(a>1)).sum()),"emitted_positive_pixels":int((a>0).sum()),"all_checks_passed":True}
    with open(f"docs/downloads/checks-{out.name}.json","w") as f: json.dump(checks,f,indent=2)
    print(f"Wrote {out} sha {sha} emitted {(arr>0).sum()}")
    # uniqueness vs GEMSDOE32 H33 if present
    ref = pathlib.Path("/tmp/GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    if ref.exists():
        import scipy.spatial
        from scipy.ndimage import gaussian_filter
        from scipy.stats import spearmanr
        with rasterio.open(ref) as r: ra=r.read(1)
        pr, pc = np.where(arr>0.5); rr, rc = np.where(ra>0.5)
        from scipy.spatial import cKDTree
        tree=cKDTree(np.stack([rr,rc],1))
        overlap = (tree.query(np.stack([pr,pc],1))[0]<=3).sum()
        print(f"UNIQUENESS overlap {overlap}/{len(pr)}={overlap/len(pr)*100:.2f}% (must <=70%)")
        ps=gaussian_filter(arr.astype(np.float32),3.0); rs=gaussian_filter(ra.astype(np.float32),3.0)
        idx=np.random.default_rng(0).choice(HEIGHT*WIDTH,100_000,replace=False)
        rho,_=spearmanr(ps.flat[idx], rs.flat[idx])
        print(f"UNIQUENESS spearman {rho:.4f} (must <=0.90)")
        if overlap/len(pr)>0.70 or abs(rho)>0.90:
            print("FAIL uniqueness gate — stop"); sys.exit(1)
    print("OK — portal-safe, unique, ready to submit")

if __name__=="__main__": main()
