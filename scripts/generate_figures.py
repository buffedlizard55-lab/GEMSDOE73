#!/usr/bin/env python3
"""Generate real data-driven diagnostic figure `docs/assets/fig_h73m_vs_h33.png`."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod  # noqa: E402

DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / ".cache" / "gems_data"))


def main() -> int:
    g = grid_mod.load_grid(DATA)
    fp, cat = g.footprint, g.catalogue

    m3_path = ROOT / "docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif"
    h33_path = Path("/home/user/refs/g32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    with rasterio.open(m3_path) as s:
        m3 = s.read(1) > 0.5
    with rasterio.open(h33_path) as s:
        h33 = np.nan_to_num(s.read(1), nan=0.0) > 0.5
    with rasterio.open(DATA / "external/sgmc_faults_100m.tif") as s:
        sgmc = (s.read(1) > 0) & fp & (~cat)

    sel = json.loads((ROOT / "evidence/selection_h73m.json").read_text())
    hold_a = json.loads((ROOT / "evidence/holdout_h73m_instrument_A.json").read_text())
    cp = json.loads((ROOT / "evidence/proxy_h73m_instrument_Cpied.json").read_text())
    bp = json.loads((ROOT / "evidence/proxy_h73m_instrument_Bprime.json").read_text())

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4), dpi=130)
    fig.patch.set_facecolor("#ffffff")

    # Panel A: Full Footprint
    ax = axes[0]
    bg = np.where(fp, 0.95, 1.0)
    ax.imshow(bg[::4, ::4], cmap="Greys", vmin=0, vmax=1, extent=[0, fp.shape[1] * 0.1, fp.shape[0] * 0.1, 0])
    cy, cx = np.nonzero(cat)
    ax.scatter(cx[::6] * 0.1, cy[::6] * 0.1, s=0.18, c="#94a3b8", alpha=0.5, label="USGS/INGENIOUS catalogue (masked)")
    hy, hx = np.nonzero(h33)
    ax.scatter(hx[::3] * 0.1, hy[::3] * 0.1, s=0.32, c="#d97706", alpha=0.55, label="H33-2-B2 (37,654 dots, 0.2778 live)")
    my, mx = np.nonzero(m3)
    ax.scatter(mx[::3] * 0.1, my[::3] * 0.1, s=0.38, c="#059669", alpha=0.72, label="H73-M M3 (37,654 dots, 0.1224 holdout)")
    ax.set_title("A. GeoDAWN Footprint (329.2 × 373.0 km)\nH73-M M3 vs H33-2-B2 Off-Catalogue Allocation", fontsize=10, fontweight="bold")
    ax.set_xlabel("UTM Easting offset (km)")
    ax.set_ylabel("UTM Northing offset (km)")
    ax.legend(loc="lower left", fontsize=7.5, markerscale=6, framealpha=0.92)

    # Panel B: Zoom on Piedmont & Stepover Corridor (rows 1350..2050, cols 1100..1800)
    ax = axes[1]
    r0, r1, c0, c1 = 1350, 2050, 1100, 1800
    sy, sx = np.nonzero(sgmc[r0:r1, c0:c1])
    cy_z, cx_z = np.nonzero(cat[r0:r1, c0:c1])
    hy_z, hx_z = np.nonzero(h33[r0:r1, c0:c1])
    my_z, mx_z = np.nonzero(m3[r0:r1, c0:c1])
    ax.set_facecolor("#f8fafc")
    ax.scatter((cx_z + c0) * 0.1, (cy_z + r0) * 0.1, s=1.2, c="#94a3b8", alpha=0.65, label="Visible catalogue fault (d <= 200 m pruned)")
    ax.scatter((sx + c0) * 0.1, (sy + r0) * 0.1, s=1.1, c="#6366f1", alpha=0.45, label="Off-catalogue SGMC structural trace")
    ax.scatter((hx_z + c0) * 0.1, (hy_z + r0) * 0.1, s=4.0, c="#d97706", alpha=0.75, label="H33-2-B2 dots")
    ax.scatter((mx_z + c0) * 0.1, (my_z + r0) * 0.1, s=4.5, c="#059669", alpha=0.9, label="H73-M M3 dots (d_min >= 300 m)")
    ax.set_xlim(c0 * 0.1, c1 * 0.1)
    ax.set_ylim(r1 * 0.1, r0 * 0.1)
    ax.set_title("B. Central Basin Piedmont & Stepover Zoom (70 × 70 km)\nRadius-Matched d_min=300 m Bridges & Piedmont Traces", fontsize=10, fontweight="bold")
    ax.set_xlabel("UTM Easting offset (km)")
    ax.set_ylabel("UTM Northing offset (km)")
    ax.legend(loc="lower left", fontsize=7.5, markerscale=2.2, framealpha=0.92)

    # Panel C: Multi-Instrument Comparison
    ax = axes[2]
    models = ["H73-M M3\n(Promoted)", "G70 P9\n(PiedSub)", "G70 P8\n(OOF38k)", "H33-2-B2\n(Control)", "H73-1 E1\n(Unsup)", "Random\nControl"]
    a_vals = [
        hold_a["scores"]["M3"]["dti"],
        0.109965,
        0.111270,
        hold_a["scores"]["h33_analogue_foldfair"]["dti"],
        hold_a["scores"]["H73_1_E1_foldfair"]["dti"],
        hold_a["scores"]["random_control"]["dti"],
    ]
    cp_vals = [
        cp["scores"]["M3"]["dti"],
        cp["scores"]["gems70_p9_piedmont"]["dti"],
        cp["scores"]["gems70_p8_oof38k"]["dti"],
        cp["scores"]["h33_champion"]["dti"],
        cp["scores"]["H73_1_E1"]["dti"],
        cp["scores"]["random_control"]["dti"],
    ]
    bp_vals = [
        bp["scores"]["M3"]["dti"],
        bp["scores"]["gems70_p9_piedmont"]["dti"],
        bp["scores"]["gems70_p8_oof38k"]["dti"],
        bp["scores"]["h33_champion"]["dti"],
        bp["scores"]["H73_1_E1"]["dti"],
        bp["scores"]["random_control"]["dti"],
    ]
    x = np.arange(len(models))
    w = 0.26
    b1 = ax.bar(x - w, a_vals, width=w, color="#059669", label="Primary Instrument A (HOLDOUT-DTI, 11,321 px)")
    b2 = ax.bar(x, cp_vals, width=w, color="#2563eb", label="Instrument C_pied (PROXY-DTI, 9,949 piedmont px)")
    b3 = ax.bar(x + w, bp_vals, width=w, color="#7c3aed", label="Instrument B' (PROXY-DTI, 59,937 SGMC px)")
    ax.axhline(hold_a["scores"]["h33_analogue_foldfair"]["dti"], color="#059669", linestyle="--", linewidth=1.0, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=8.2)
    ax.set_ylim(0, 0.165)
    ax.set_ylabel("Distance-Weighted Tversky Index (DTI)")
    ax.set_title("C. Gating HOLDOUT-DTI (A) & Report-Only Proxies\nH73-M M3: A = 0.1224 (+30.4%), C_pied = 0.1435 (+53.2%)", fontsize=9.5, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=7.5, framealpha=0.92)
    for rect in list(b1) + list(b2):
        h_v = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2.0, h_v + 0.002, f"{h_v:.3f}", ha="center", va="bottom", fontsize=6.5, rotation=90)

    plt.tight_layout()
    out_png = ROOT / "docs/assets/fig_h73m_vs_h33.png"
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    print("wrote", out_png.relative_to(ROOT), f"({out_png.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
