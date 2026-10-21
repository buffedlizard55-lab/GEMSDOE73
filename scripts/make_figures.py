#!/usr/bin/env python3
"""Overview map: E1 dots vs catalogue vs champion (downsampled, for the site)."""
import os, sys
from pathlib import Path
import numpy as np, rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT/".cache"/"gems_data"))
def dots(p):
    with rasterio.open(p) as s: a=s.read(1)
    return np.isfinite(a)&(a>0.5)
with rasterio.open(DATA/"labels.tif") as s: lab=s.read(1)
foot, cat = lab>=0, lab==1
e1 = dots(ROOT/"docs/downloads/gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif")
h33 = dots("/home/user/refs/g32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
f=4  # 4x block max-pool for display
def pool(m):
    h,w=m.shape; return m[:h//f*f,:w//f*f].reshape(h//f,f,w//f,f).max(axis=(1,3))
img=np.zeros((*pool(foot).shape,3),dtype=np.float32)+0.08
img[pool(foot)]=[0.16,0.17,0.19]
img[pool(cat)]=[0.55,0.55,0.55]
both=pool(e1)&pool(h33); img[pool(h33)]=[0.95,0.55,0.10]; img[pool(e1)]=[0.10,0.75,0.95]; img[both]=[0.95,0.95,0.95]
plt.figure(figsize=(9,10)); plt.imshow(img, interpolation="nearest")
plt.title("GEMSDOE73 H73-1 E1 dots (cyan) vs H33 champion (orange), catalogue (grey)\nwhite = both within same 400 m display cell; 17.7% of E1 dots lie within 300 m of an H33 dot", fontsize=9, color="white")
plt.axis("off"); plt.tight_layout()
out=ROOT/"docs/assets"; out.mkdir(parents=True,exist_ok=True)
plt.savefig(out/"fig_e1_vs_h33.png",dpi=130,facecolor="#111111"); print(out/"fig_e1_vs_h33.png")
