"""H73-MCSC: Multi-Scale Steerable Curvilinear Centerline Propagation & Crest-Sharpened Submodular Decoding.

Core physical & statistical invariants enforced throughout this module:
  1. ZERO prior submission rasters or sibling predictions are ever read here.
  2. ZERO catalogue-distance features (e.g. d_cat, dist_known_fault_px) enter X at Stage 1 or Stage 2,
     preventing the hide-and-recover collar trap that collapses live scores on unmapped basins.
  3. ZERO raw coordinates or non-detrended elevations enter X.
  4. Stage-1 nested pairwise quadrant models M_{a,b} guarantee 100% out-of-quadrant Stage-1 posteriors
     on BOTH training quadrants and buffered outer holdout quadrants.
"""

from __future__ import annotations

import csv
import heapq
import io
import json
import struct
import zipfile
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import rasterio
from rasterio.warp import transform as rio_transform
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

FORBIDDEN_COLS = frozenset({"dist_known_fault_px", "known_fault", "label", "d_cat"})

SENSOR_FEATURE_NAMES: tuple[str, ...] = (
    # Group A: 1m USGS 3DEP LiDAR micro-scarp geometry & polarity (13)
    "lid_valid",
    "lid_ex_max",
    "lid_ex_mean",
    "lid_step_max",
    "lid_lapneg_max",
    "lid_lappos_max",
    "lid_downface_max",
    "lid_upface_max",
    "lid_cross_max",
    "lid_relief",
    "lid_coh100",
    "lid_step_polarity",
    "lid_crest_dipole",
    # Group B: 10m seamless USGS 3DEP DEM & fluvial knickpoint physics across 100% of footprint (13)
    "t10_slope_p90",
    "t10_slope_max",
    "t10_steep_frac",
    "t10_slope_std",
    "t10_relief_local",
    "t10_curv_prof_absmax",
    "t10_aspect_coherence",
    "t10_hs_lineament",
    "t10_scarp_sharpness",
    "t10_slope_anom7",
    "chi_chan_n",
    "chi_knick_n",
    "chi_raised_n",
    # Group C: 100m multi-scale detrended topography, piedmont depth & seamless scarp worm (8)
    "elev_slope",
    "elev_slope_anom15",
    "det_elev_loc7",
    "det_elev_loc21",
    "det_elev_lap",
    "depth_base_log",
    "depth_base_grad",
    "worm_scarp_1300m",
    # Group D: GeoDAWN subsurface geopotential steps, upward-continuation persistence & cross-gradient (12)
    "log_tmi_hg",
    "tmi_vg",
    "mag_tc",
    "rtp_loc15",
    "up150_grad",
    "mag_depth_persist",
    "grav_slope",
    "grav_vg",
    "grav_hg_abs",
    "worm_mag_1500m",
    "worm_grav_1500m",
    "xgrad_parallel_gm",
    # Group E: DOE GDR-1391 + USGS ScienceBase hydrothermal conduit inversion, alteration & GPS strain (6)
    "hydro_upflow_1km",
    "hydro_outflow_3km",
    "hydro_kth_local",
    "hydro_demag_clay",
    "strain_kostrov",
    "seismic_strain_log",
)

STAGE2_FEATURE_NAMES: tuple[str, ...] = (
    "p1_raw",
    "p1_smooth1",
    "p1_smooth3",
    "p1_smooth8",
    "p1_dog1_4",
    "s1_bridge_max",
    "s1_bilateral_min",
    "s1_crest_w2",
    "s2_bridge_max",
    "s2_bilateral_min",
    "s2_crest_w3",
    "s2_aniso_ratio",
    "s3_bridge_max",
    "s3_crest_w4",
    "multiscale_strand_product",
    "strike_cos2",
    "strike_sin2",
    "anchor_lid_valid",
    "anchor_lid_step",
    "anchor_t10_sharp",
    "anchor_elev_slope",
    "anchor_depth_base",
    "anchor_tmi_hg",
    "anchor_grav_slope",
    "anchor_hydro_upflow",
)

ANCHOR_COL_INDICES: tuple[int, ...] = tuple(
    SENSOR_FEATURE_NAMES.index(nm)
    for nm in (
        "lid_valid",
        "lid_step_max",
        "t10_scarp_sharpness",
        "elev_slope",
        "depth_base_log",
        "log_tmi_hg",
        "grav_slope",
        "hydro_upflow_1km",
    )
)


BLAKELY_CREST_NAMES: tuple[str, ...] = (
    "sb_crest_lidar_100m",
    "sb_crest_dem10_100m",
    "sb_crest_dem10_250m",
    "sb_crest_slope_150m",
    "sb_crest_slope_350m",
    "sb_crest_slope_700m",
    "sb_toe_concavity_200m",
    "sb_crest_grav_200m",
    "sb_crest_grav_450m",
    "sb_crest_mag_200m",
    "sb_crest_mag_450m",
    "sb_crest_up150_300m",
    "sb_crest_depthbase_300m",
    "sb_corroborated_nolidar",
    "sb_corroborated_all",
)


def _fill_invalid_nearest(arr: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """Nearest-neighbor fill outside finite mask so spatial kernels never bleed sentinel artifacts."""
    out = np.asarray(arr, dtype=np.float32).copy()
    bad = ~valid_mask | ~np.isfinite(out) | (out < -1e25)
    if bad.any():
        if (~bad).any():
            _, idx = ndi.distance_transform_edt(bad, return_distances=True, return_indices=True)
            out[bad] = out[idx[0][bad], idx[1][bad]]
        else:
            out.fill(0.0)
    return out


def steger_blakely_crest(
    field_2d: np.ndarray,
    valid_2d: np.ndarray,
    sigma: float,
    sigma_t: float = 0.80,
) -> np.ndarray:
    """Scale-normalized Steger (1998) / Blakely-Simpson (1986) sub-pixel 1D ridge crest detector.

    Computes exact Hessian minimum eigenvalue lambda_min < 0 across strike and weights by
    exp(-0.5 * (t* / sigma_t)^2) where t* = (grad E . v_min) / |lambda_min| is the sub-pixel
    distance from pixel center to the true physical fault contact crest.
    """
    f = _fill_invalid_nearest(field_2d, valid_2d).astype(np.float32)
    ex = ndi.gaussian_filter(f, sigma=sigma, order=(0, 1))
    ey = ndi.gaussian_filter(f, sigma=sigma, order=(1, 0))
    exx = ndi.gaussian_filter(f, sigma=sigma, order=(0, 2))
    eyy = ndi.gaussian_filter(f, sigma=sigma, order=(2, 0))
    exy = ndi.gaussian_filter(f, sigma=sigma, order=(1, 1))

    diff = exx - eyy
    disc = np.hypot(diff, 2.0 * exy)
    lmin = 0.5 * (exx + eyy - disc)
    theta_n = 0.5 * np.arctan2(2.0 * exy, diff) + (0.5 * np.pi)
    proj_g = ex * np.cos(theta_n) + ey * np.sin(theta_n)
    t_off = proj_g / (np.abs(lmin) + 1e-6)

    strength = np.maximum(-lmin, 0.0) * float(sigma * sigma)
    crest = strength * np.exp(-0.5 * (t_off / float(sigma_t)) ** 2)
    return np.where(valid_2d, crest, 0.0).astype(np.float32)


def build_or_load_blakely_stack(
    data_dir: Path,
    footprint: np.ndarray,
    cache_path: Path,
    log=print,
) -> np.memmap:
    """Build or load the 14 closed-form Steger-Blakely sub-pixel multi-modal crest channels."""
    n_fp = int(footprint.sum())
    n_ch = len(BLAKELY_CREST_NAMES)
    meta_path = cache_path.with_suffix(".json")
    if cache_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if meta.get("names") == list(BLAKELY_CREST_NAMES) and meta.get("n_fp") == n_fp:
            log(f"Loaded cached 14-channel Steger-Blakely crest stack: {cache_path}")
            return np.memmap(cache_path, dtype=np.float32, mode="r", shape=(n_fp, n_ch))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(cache_path, dtype=np.float32, mode="w+", shape=(n_fp, n_ch))
    fp_idx = np.flatnonzero(footprint.ravel())
    ext = data_dir / "external"

    def wcol(idx: int, name: str, arr: np.ndarray) -> np.ndarray:
        assert BLAKELY_CREST_NAMES[idx] == name
        v = np.nan_to_num(arr.ravel()[fp_idx].astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, idx] = v
        # Return robustly normalized [0, 1] array for multi-sensor crest corroboration
        p99 = float(np.percentile(v[v > 0], 98.5)) if (v > 0).any() else 1.0
        return np.clip(arr / max(p99, 1e-6), 0.0, 2.0).astype(np.float32)

    log("[Blakely 1/3] Sub-pixel scarp & break-in-slope crests (1m LiDAR + 10m DEM + 100m DEM)...")
    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as s:
        lid_ok = (s.read(12) > 0) & footprint
        lid_step = s.read(3).astype(np.float32)
    c_lid = steger_blakely_crest(lid_step, lid_ok, sigma=1.0, sigma_t=0.80)
    c_lid[~lid_ok] = 0.0
    n_lid = wcol(0, "sb_crest_lidar_100m", c_lid)
    del lid_step, c_lid

    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as s:
        t10_max = s.read(2).astype(np.float32)
    n_d10_1 = wcol(1, "sb_crest_dem10_100m", steger_blakely_crest(t10_max, footprint, sigma=1.0, sigma_t=0.80))
    n_d10_2 = wcol(2, "sb_crest_dem10_250m", steger_blakely_crest(t10_max, footprint, sigma=2.5, sigma_t=0.85))
    del t10_max

    with rasterio.open(data_dir / "training_features.tif") as src:
        tmi_hg = _fill_invalid_nearest(src.read(3), footprint)
        grav_slope = _fill_invalid_nearest(src.read(5), footprint)
        det_elev = _fill_invalid_nearest(src.read(12), footprint)
        depth_b = _fill_invalid_nearest(src.read(15), footprint)
        elev_slope = _fill_invalid_nearest(src.read(19), footprint)

    n_sl15 = wcol(3, "sb_crest_slope_150m", steger_blakely_crest(elev_slope, footprint, sigma=1.4, sigma_t=0.80))
    n_sl35 = wcol(4, "sb_crest_slope_350m", steger_blakely_crest(elev_slope, footprint, sigma=3.2, sigma_t=0.85))
    wcol(5, "sb_crest_slope_700m", steger_blakely_crest(elev_slope, footprint, sigma=6.5, sigma_t=0.90))
    # Piedmont toe break-in-slope: concave upward bend at mountain-fan junction (-det_elev ridge)
    n_toe = wcol(6, "sb_toe_concavity_200m", steger_blakely_crest(-det_elev, footprint, sigma=2.0, sigma_t=0.85))
    del det_elev, elev_slope

    log("[Blakely 2/3] Sub-pixel gravity, magnetic & basement-step contact crests...")
    n_gr2 = wcol(7, "sb_crest_grav_200m", steger_blakely_crest(grav_slope, footprint, sigma=2.0, sigma_t=0.80))
    n_gr4 = wcol(8, "sb_crest_grav_450m", steger_blakely_crest(grav_slope, footprint, sigma=4.5, sigma_t=0.85))
    del grav_slope

    log_hg = np.log1p(np.abs(tmi_hg)).astype(np.float32)
    n_mg2 = wcol(9, "sb_crest_mag_200m", steger_blakely_crest(log_hg, footprint, sigma=2.0, sigma_t=0.80))
    wcol(10, "sb_crest_mag_450m", steger_blakely_crest(log_hg, footprint, sigma=4.5, sigma_t=0.85))
    del tmi_hg, log_hg

    with rasterio.open(ext / "geodawn_extensions_u8.tif") as s:
        up150 = s.read(4).astype(np.float32)
    up150_g = np.hypot(*np.gradient(ndi.gaussian_filter(up150, sigma=1.2))).astype(np.float32)
    wcol(11, "sb_crest_up150_300m", steger_blakely_crest(up150_g, footprint, sigma=2.5, sigma_t=0.85))
    del up150, up150_g

    db_g = np.hypot(*np.gradient(ndi.gaussian_filter(depth_b, sigma=1.5))).astype(np.float32)
    n_db = wcol(12, "sb_crest_depthbase_300m", steger_blakely_crest(db_g, footprint, sigma=2.8, sigma_t=0.85))
    del depth_b, db_g

    log("[Blakely 3/3] Co-located multi-physics sub-pixel crest corroboration...")
    topo_nolid = np.maximum.reduce([n_d10_1, n_d10_2, n_sl15, n_sl35, 0.7 * n_toe])
    topo_all = np.maximum(np.where(lid_ok, n_lid, n_d10_1), topo_nolid)
    sub_c = np.maximum.reduce([n_gr2, n_gr4, n_mg2, n_db])
    sub_sm = ndi.gaussian_filter(sub_c, sigma=1.5)
    wcol(13, "sb_corroborated_nolidar", topo_nolid + 0.65 * sub_c + 0.90 * topo_nolid * sub_sm)
    wcol(14, "sb_corroborated_all", topo_all + 0.65 * sub_c + 0.90 * topo_all * sub_sm)
    del topo_nolid, topo_all, sub_c, sub_sm

    mm.flush()
    meta_path.write_text(json.dumps({"names": list(BLAKELY_CREST_NAMES), "n_fp": n_fp}, indent=2) + "\n")
    log(f"Cached {n_ch}-channel Steger-Blakely stack ({mm.nbytes / 1e9:.2f} GB) -> {cache_path}")
    return np.memmap(cache_path, dtype=np.float32, mode="r", shape=(n_fp, n_ch))


ALL67_FEATURE_NAMES: tuple[str, ...] = SENSOR_FEATURE_NAMES + BLAKELY_CREST_NAMES

NOLIDAR_COL_INDICES: tuple[int, ...] = tuple(
    i
    for i, nm in enumerate(ALL67_FEATURE_NAMES)
    if not nm.startswith("lid_") and nm not in ("worm_scarp_1300m", "sb_crest_lidar_100m", "sb_corroborated_all")
)


def fuse_seamfree_dual_regime(
    p_all_2d: np.ndarray,
    p_nolid_2d: np.ndarray,
    lid_ok_2d: np.ndarray,
    quad_2d: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Seam-free per-quadrant quantile transfer of LiDAR-free specialist into non-LiDAR survey gaps."""
    out = np.zeros(footprint.shape, dtype=np.float32)
    q_grid = np.concatenate([
        np.linspace(0.0, 0.95, 191, endpoint=False),
        np.linspace(0.95, 0.999, 246, endpoint=False),
        np.linspace(0.999, 1.0, 101),
    ])
    for q in range(4):
        in_q = (quad_2d == q) & footprint
        m_lid = in_q & lid_ok_2d
        m_gap = in_q & (~lid_ok_2d)
        if not m_lid.any():
            out[in_q] = p_nolid_2d[in_q]
            continue
        src_q = np.quantile(p_nolid_2d[m_lid], q_grid)
        dst_q = np.quantile(p_all_2d[m_lid], q_grid)
        # Blend inside LiDAR coverage for variance reduction on eroded scarps:
        mapped_lid = np.interp(p_nolid_2d[m_lid], src_q, dst_q).astype(np.float32)
        out[m_lid] = 0.78 * p_all_2d[m_lid] + 0.22 * mapped_lid
        # Exact quantile match across survey seam inside non-LiDAR gap:
        if m_gap.any():
            out[m_gap] = np.interp(p_nolid_2d[m_gap], src_q, dst_q).astype(np.float32)
    out[~footprint] = 0.0
    return out

    """Nearest-neighbor fill outside finite mask so spatial kernels never bleed sentinel artifacts."""
    out = np.asarray(arr, dtype=np.float32).copy()
    bad = ~valid_mask | ~np.isfinite(out) | (out < -1e25)
    if bad.any():
        if (~bad).any():
            _, idx = ndi.distance_transform_edt(bad, return_distances=True, return_indices=True)
            out[bad] = out[idx[0][bad], idx[1][bad]]
        else:
            out.fill(0.0)
    return out


def _shift_add(acc: np.ndarray, src: np.ndarray, dy: int, dx: int, weight: float = 1.0) -> None:
    """In-place zero-padded 2D array shift accumulation with zero wraparound."""
    h, w = src.shape
    ys = slice(max(0, dy), min(h, h + dy))
    xs = slice(max(0, dx), min(w, w + dx))
    yt = slice(max(0, -dy), min(h, h - dy))
    xt = slice(max(0, -dx), min(w, w - dx))
    if weight == 1.0:
        acc[ys, xs] += src[yt, xt]
    else:
        acc[ys, xs] += np.float32(weight) * src[yt, xt]


def _shifted(src: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Zero-padded shifted view copy."""
    out = np.zeros_like(src, dtype=np.float32)
    _shift_add(out, src, dy, dx, 1.0)
    return out


def _strike_worm_local(edge_2d: np.ndarray, valid_2d: np.ndarray, half_len: int = 6, flank: int = 3) -> np.ndarray:
    """8-azimuth flank-subtracted strike-coherent line integral over locally standardized edge."""
    x = np.where(valid_2d, np.nan_to_num(edge_2d, nan=0.0), 0.0).astype(np.float32)
    m = ndi.uniform_filter(x, size=31)
    v = np.maximum(ndi.uniform_filter(x * x, size=31) - m * m, 1e-6)
    z = np.clip((x - m) / (np.sqrt(v) + 0.20), -3.0, 6.0).astype(np.float32)
    del m, v

    best = np.full(x.shape, -1e9, dtype=np.float32)
    for k in range(8):
        theta = k * np.pi / 8.0
        dyu, dxu = np.sin(theta), np.cos(theta)
        offsets = sorted({
            (int(round(t * dyu)), int(round(t * dxu)))
            for t in range(-half_len, half_len + 1)
        })
        acc = np.zeros_like(z)
        for dy, dx in offsets:
            _shift_add(acc, z, dy, dx, 1.0)
        acc /= float(len(offsets))
        py, px = int(round(-flank * dxu)), int(round(flank * dyu))
        fl = 0.5 * (_shifted(acc, py, px) + _shifted(acc, -py, -px))
        np.maximum(best, acc - fl, out=best)
    return np.where(valid_2d, np.maximum(best, 0.0), 0.0).astype(np.float32)


def _utm_to_rc(xs: np.ndarray, ys: np.ndarray, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cols = np.floor((np.asarray(xs, dtype=np.float64) - 243350.0) / 100.0).astype(np.int64)
    rows = np.floor((4508550.0 - np.asarray(ys, dtype=np.float64)) / 100.0).astype(np.int64)
    ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    return rows[ok], cols[ok], ok


def _build_hydrothermal_impulse(ext_dir: Path, footprint: np.ndarray) -> np.ndarray:
    """Build purely physical geothermal anomaly impulse grid from verified DOE GDR-1391 + USGS sources.

    Explicitly blocks any catalogue-distance columns (e.g. dist_known_fault_px).
    """
    shape = footprint.shape
    imp = np.zeros(shape, dtype=np.float32)

    # 1. GDR 1391 wells & springs (temperature + silica/cation chemical geothermometers)
    ws_path = ext_dir / "gdr_wellspring_in_footprint.csv"
    with ws_path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Strictly read ONLY coordinates & physical temperature/geothermometry measurements
            try:
                rr = int(float(r["row"]))
                cc = int(float(r["col"]))
            except ValueError:
                continue
            if not (0 <= rr < shape[0] and 0 <= cc < shape[1]):
                continue
            tc = float(r["temp_c"]) if r.get("temp_c") else 0.0
            tq = float(r["geothermquartz_c"]) if r.get("geothermquartz_c") else 0.0
            tch = float(r["geothermchalc_c"]) if r.get("geothermchalc_c") else 0.0
            tcat = float(r["geothermcat_c"]) if r.get("geothermcat_c") else 0.0
            cls = (r.get("thermalclass") or "").lower()
            score = (
                max(0.0, tc - 22.0) / 40.0
                + 0.6 * max(0.0, tq - 75.0) / 80.0
                + 0.4 * max(0.0, tch - 65.0) / 80.0
                + 0.3 * max(0.0, tcat - 85.0) / 90.0
                + (0.5 if ("hot" in cls or "warm" in cls or "therm" in cls) else 0.0)
            )
            if score > 0.0:
                imp[rr, cc] = max(imp[rr, cc], min(float(score), 4.0))

    # 2. GDR 1391 INGENIOUS 2-meter shallow temperature probes (F2mDAB, T2m)
    pr_zip = ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    if pr_zip.is_file():
        with zipfile.ZipFile(pr_zip) as zf:
            dbf_name = next(n for n in zf.namelist() if n.lower().endswith(".dbf"))
            buf = zf.read(dbf_name)
        numrec, lenhdr, lenrec = struct.unpack("<4xIHH20x", buf[:32])
        fields: list[tuple[str, int, int]] = []
        pos, offset = 32, 1
        while buf[pos] != 0x0D:
            fname = buf[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            assert fname not in FORBIDDEN_COLS
            flen = buf[pos + 16]
            fields.append((fname, offset, flen))
            offset += flen
            pos += 32
        fmap = {n: (o, l) for n, o, l in fields}
        lats, lons, vals = [], [], []
        for i in range(numrec):
            rec = buf[lenhdr + i * lenrec : lenhdr + (i + 1) * lenrec]
            if not rec or rec[0:1] == b"*":
                continue
            try:
                lat = float(rec[fmap["LatDegreeN"][0] : fmap["LatDegreeN"][0] + fmap["LatDegreeN"][1]].strip())
                lon = float(rec[fmap["LongDegree"][0] : fmap["LongDegree"][0] + fmap["LongDegree"][1]].strip())
                dab_s = rec[fmap["F2mDAB"][0] : fmap["F2mDAB"][0] + fmap["F2mDAB"][1]].strip()
                t2m_s = rec[fmap["T2m"][0] : fmap["T2m"][0] + fmap["T2m"][1]].strip()
                dab = float(dab_s) if dab_s else 0.0
                t2m = float(t2m_s) if t2m_s else 0.0
            except ValueError:
                continue
            v = max(0.0, dab - 0.5) / 3.0 + 0.25 * max(0.0, t2m - 22.0) / 5.0
            if v > 0.0 and 25.0 <= lat <= 50.0 and -130.0 <= lon <= -100.0:
                lats.append(lat)
                lons.append(lon)
                vals.append(min(v, 3.5))
        if lons:
            ux, uy = rio_transform("EPSG:4269", "EPSG:32611", lons, lats)
            rr, cc, ok = _utm_to_rc(np.asarray(ux), np.asarray(uy), shape)
            vv = np.asarray(vals, dtype=np.float32)[ok]
            np.maximum.at(imp, (rr, cc), vv)

    # 3. GDR 1391 Paleo-geothermal deposits (sinter, travertine, tufa, explosion craters)
    pa_zip = ext_dir / "paleo_geothermal_regional.zip"
    if pa_zip.is_file():
        with zipfile.ZipFile(pa_zip) as zf:
            lines = zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace").splitlines()
        lats, lons, vals = [], [], []
        for r in csv.DictReader(lines):
            try:
                lon = float(r["Long_deg_NAD83"])
                lat = float(r["Lat_deg_NAD83"])
            except ValueError:
                continue
            dtype = (r.get("Deposit_type") or "").lower()
            w = 2.8 if "sinter" in dtype else (2.2 if "travertine" in dtype or "explosion" in dtype else 1.6)
            lats.append(lat)
            lons.append(lon)
            vals.append(w)
        if lons:
            ux, uy = rio_transform("EPSG:4269", "EPSG:32611", lons, lats)
            rr, cc, ok = _utm_to_rc(np.asarray(ux), np.asarray(uy), shape)
            np.maximum.at(imp, (rr, cc), np.asarray(vals, dtype=np.float32)[ok])

    # 4. GDR 1391 Quaternary volcanic vents (row/col only; dist_known_fault_px ignored)
    vv_path = ext_dir / "gdr_volcanic_vents_in_footprint.csv"
    if vv_path.is_file():
        with vv_path.open() as f:
            for r in csv.DictReader(f):
                try:
                    rr, cc = int(float(r["row"])), int(float(r["col"]))
                except ValueError:
                    continue
                if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
                    imp[rr, cc] = max(imp[rr, cc], 1.5)

    # 5. USGS ScienceBase Great Basin heat-flow wells (lossless EPSG:32611 coordinates)
    hf_json = ext_dir / "sb_heat_flow_in_footprint.json"
    if hf_json.is_file():
        obj = json.loads(hf_json.read_text())
        for r in obj.get("records", []):
            if r.get("kinds") == ["Point"] and r.get("parts"):
                hf_val = r.get("hf_est") if r.get("hf_est") is not None else r.get("hf_meas")
                try:
                    hf_f = float(hf_val)
                except (TypeError, ValueError):
                    continue
                if 85.0 < hf_f < 600.0:
                    x, y = r["parts"][0][0]
                    cc = int((x - 243350.0) // 100.0)
                    rr = int((4508550.0 - y) // 100.0)
                    if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
                        imp[rr, cc] = max(imp[rr, cc], min((hf_f - 85.0) / 60.0, 2.5))

    imp[~footprint] = 0.0
    return imp


def build_or_load_sensor_stack(
    data_dir: Path,
    footprint: np.ndarray,
    cache_path: Path,
    log=print,
) -> np.memmap:
    """Build or load the 52-channel de-regionalized pure-sensor matrix on footprint pixels."""
    n_fp = int(footprint.sum())
    n_ch = len(SENSOR_FEATURE_NAMES)
    meta_path = cache_path.with_suffix(".json")
    if cache_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if meta.get("names") == list(SENSOR_FEATURE_NAMES) and meta.get("n_fp") == n_fp:
            log(f"Loaded cached 52-channel sensor stack: {cache_path}")
            return np.memmap(cache_path, dtype=np.float32, mode="r", shape=(n_fp, n_ch))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(cache_path, dtype=np.float32, mode="w+", shape=(n_fp, n_ch))
    fp_idx = np.flatnonzero(footprint.ravel())
    ext = data_dir / "external"

    def write_col(idx: int, name: str, arr2d: np.ndarray) -> None:
        assert SENSOR_FEATURE_NAMES[idx] == name, f"{SENSOR_FEATURE_NAMES[idx]} != {name}"
        vals = arr2d.ravel()[fp_idx].astype(np.float32, copy=False)
        vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, idx] = vals

    # --- Group A: 1m USGS 3DEP LiDAR ---
    log("[Sensor 1/5] Extracting 1m USGS 3DEP LiDAR scarp & polarity channels...")
    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as s:
        lid_valid_b = s.read(12) > 0
        write_col(0, "lid_valid", lid_valid_b.astype(np.float32))
        ex_max = s.read(1).astype(np.float32)
        ex_mean = s.read(2).astype(np.float32)
        step_max = s.read(3).astype(np.float32)
        lapneg = s.read(4).astype(np.float32)
        lappos = s.read(5).astype(np.float32)
        downf = s.read(6).astype(np.float32)
        upf = s.read(7).astype(np.float32)
        crossf = s.read(8).astype(np.float32)
        lid_rel = s.read(9).astype(np.float32)
        lid_coh = s.read(10).astype(np.float32)

    write_col(1, "lid_ex_max", ex_max)
    write_col(2, "lid_ex_mean", ex_mean)
    write_col(3, "lid_step_max", step_max)
    write_col(4, "lid_lapneg_max", lapneg)
    write_col(5, "lid_lappos_max", lappos)
    write_col(6, "lid_downface_max", downf)
    write_col(7, "lid_upface_max", upf)
    write_col(8, "lid_cross_max", crossf)
    write_col(9, "lid_relief", lid_rel)
    write_col(10, "lid_coh100", lid_coh)
    pol = (np.abs(downf - upf) / (downf + upf + 1.0)) * step_max
    write_col(11, "lid_step_polarity", pol)
    write_col(12, "lid_crest_dipole", np.sqrt(np.maximum(lapneg * lappos, 0.0)))
    lid_step_norm = np.where(lid_valid_b, step_max / 255.0, 0.0).astype(np.float32)
    del ex_max, ex_mean, step_max, lapneg, lappos, downf, upf, crossf, lid_rel, lid_coh, pol

    # --- Group B: 10m seamless USGS 3DEP DEM + Fluvial Chi ---
    log("[Sensor 2/5] Extracting seamless 10m 3DEP DEM & fluvial chi/knickpoint channels...")
    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as s:
        t10_p90 = s.read(1).astype(np.float32)
        t10_max = s.read(2).astype(np.float32)
        t10_steep = s.read(3).astype(np.float32)
        t10_std = s.read(4).astype(np.float32)
        t10_rel = s.read(5).astype(np.float32)
        t10_curv = s.read(6).astype(np.float32)
        t10_coh = s.read(7).astype(np.float32)
        t10_hs = s.read(8).astype(np.float32)

    write_col(13, "t10_slope_p90", t10_p90)
    write_col(14, "t10_slope_max", t10_max)
    write_col(15, "t10_steep_frac", t10_steep)
    write_col(16, "t10_slope_std", t10_std)
    write_col(17, "t10_relief_local", t10_rel)
    write_col(18, "t10_curv_prof_absmax", t10_curv)
    write_col(19, "t10_aspect_coherence", t10_coh)
    write_col(20, "t10_hs_lineament", t10_hs)
    t10_sharp = np.maximum(t10_max - 0.75 * t10_p90, 0.0) * (t10_coh / 255.0)
    write_col(21, "t10_scarp_sharpness", t10_sharp)
    t10_anom7 = t10_p90 - ndi.uniform_filter(t10_p90, size=7)
    write_col(22, "t10_slope_anom7", t10_anom7)

    seamless_scarp = np.where(lid_valid_b & footprint, lid_step_norm, t10_sharp / 255.0).astype(np.float32)
    del t10_p90, t10_max, t10_steep, t10_std, t10_rel, t10_curv, t10_coh, t10_hs, t10_sharp, t10_anom7, lid_step_norm, lid_valid_b

    with rasterio.open(ext / "dem10_chi_100m_u8.tif") as s:
        write_col(23, "chi_chan_n", s.read(1).astype(np.float32))
        write_col(24, "chi_knick_n", s.read(2).astype(np.float32))
        write_col(25, "chi_raised_n", s.read(3).astype(np.float32))

    # --- Group C & D: Official 19-band GeoDAWN topography, potential fields & strain ---
    log("[Sensor 3/5] Extracting de-regionalized 19-band GeoDAWN topography & potential-field operators...")
    with rasterio.open(data_dir / "training_features.tif") as src:
        rtp = _fill_invalid_nearest(src.read(2), footprint)
        tmi_hg = _fill_invalid_nearest(src.read(3), footprint)
        geod_2nd = _fill_invalid_nearest(src.read(4), footprint)
        grav_slope = _fill_invalid_nearest(src.read(5), footprint)
        tc = _fill_invalid_nearest(src.read(6), footprint)
        geod_shear = _fill_invalid_nearest(src.read(7), footprint)
        geod_dil = _fill_invalid_nearest(src.read(8), footprint)
        tmi_vg = _fill_invalid_nearest(src.read(9), footprint)
        grav_vg = _fill_invalid_nearest(src.read(11), footprint)
        det_elev = _fill_invalid_nearest(src.read(12), footprint)
        grav_iso = _fill_invalid_nearest(src.read(13), footprint)
        depth_base = _fill_invalid_nearest(src.read(15), footprint)
        ieq = _fill_invalid_nearest(src.read(16), footprint)
        cond_surf = _fill_invalid_nearest(src.read(17), footprint)
        grav_hg = _fill_invalid_nearest(src.read(18), footprint)
        elev_slope = _fill_invalid_nearest(src.read(19), footprint)

    write_col(26, "elev_slope", elev_slope)
    write_col(27, "elev_slope_anom15", elev_slope - ndi.uniform_filter(elev_slope, size=15))
    write_col(28, "det_elev_loc7", det_elev - ndi.uniform_filter(det_elev, size=7))
    write_col(29, "det_elev_loc21", det_elev - ndi.uniform_filter(det_elev, size=21))
    write_col(30, "det_elev_lap", np.abs(ndi.gaussian_laplace(det_elev, sigma=1.2)))
    write_col(31, "depth_base_log", np.log1p(np.maximum(depth_base, 0.0)))
    db_sm = ndi.gaussian_filter(depth_base, sigma=1.5)
    write_col(32, "depth_base_grad", np.hypot(*np.gradient(db_sm)))
    del db_sm
    write_col(33, "worm_scarp_1300m", _strike_worm_local(seamless_scarp, footprint, half_len=6, flank=3))
    del seamless_scarp, det_elev, depth_base

    log_hg = np.log1p(np.abs(tmi_hg)).astype(np.float32)
    write_col(34, "log_tmi_hg", log_hg)
    write_col(35, "tmi_vg", tmi_vg)
    write_col(36, "mag_tc", tc)
    rtp_loc = rtp - ndi.uniform_filter(rtp, size=15)
    write_col(37, "rtp_loc15", rtp_loc)

    with rasterio.open(ext / "geodawn_extensions_u8.tif") as s:
        up150 = s.read(4).astype(np.float32)
    up150_g = np.hypot(*np.gradient(ndi.gaussian_filter(up150, sigma=1.0))).astype(np.float32)
    write_col(38, "up150_grad", up150_g)
    write_col(39, "mag_depth_persist", up150_g / (log_hg + 0.25))
    del up150, up150_g

    write_col(40, "grav_slope", grav_slope)
    write_col(41, "grav_vg", grav_vg)
    write_col(42, "grav_hg_abs", np.abs(grav_hg))
    write_col(43, "worm_mag_1500m", _strike_worm_local(log_hg, footprint, half_len=7, flank=3))
    write_col(44, "worm_grav_1500m", _strike_worm_local(grav_slope, footprint, half_len=7, flank=3))

    # Gallardo-Meju parallel gradient coupling across gravity x RTP magnetics
    gy_g, gx_g = np.gradient(ndi.gaussian_filter(grav_iso, sigma=1.5))
    gy_m, gx_m = np.gradient(ndi.gaussian_filter(rtp, sigma=1.5))
    mg = np.hypot(gy_g, gx_g) + 1e-6
    mm_g = np.hypot(gy_m, gx_m) + 1e-6
    cos_align = np.abs(gy_g * gy_m + gx_g * gx_m) / (mg * mm_g)
    write_col(45, "xgrad_parallel_gm", (cos_align * np.sqrt(mg * mm_g)).astype(np.float32))
    del gy_g, gx_g, gy_m, gx_m, mg, mm_g, cos_align, grav_iso, rtp, tmi_hg, tmi_vg, tc, grav_vg, grav_hg

    # --- Group E: Hydrothermal conduit inversion, alteration & crustal strain ---
    log("[Sensor 4/5] Computing DOE GDR-1391 + USGS ScienceBase hydrothermal & strain channels...")
    imp = _build_hydrothermal_impulse(ext, footprint)
    write_col(46, "hydro_upflow_1km", ndi.gaussian_filter(imp, sigma=10.0) * 100.0)
    write_col(47, "hydro_outflow_3km", ndi.gaussian_filter(imp, sigma=28.0) * 400.0)
    del imp

    with rasterio.open(ext / "geodawn_rad_u8.tif") as s:
        k_u8 = s.read(1).astype(np.float32)
        th_u8 = s.read(2).astype(np.float32)
    non_playa = (elev_slope > 1.2).astype(np.float32)
    kth = (k_u8 + 1.0) / (th_u8 + 10.0)
    write_col(48, "hydro_kth_local", (kth - ndi.uniform_filter(kth, size=21)) * non_playa)
    del k_u8, th_u8, kth

    demag = np.maximum(-rtp_loc, 0.0) * log_hg
    clay = np.maximum(cond_surf - ndi.uniform_filter(cond_surf, size=21), 0.0) * (elev_slope + 8.0 * grav_slope)
    write_col(49, "hydro_demag_clay", (0.5 * demag + 0.5 * clay) * non_playa)
    del rtp_loc, log_hg, cond_surf, elev_slope, grav_slope, non_playa, demag, clay

    kostrov = np.maximum(geod_dil, 0.0) * np.maximum(geod_shear, 0.0) + 0.25 * np.maximum(geod_2nd, 0.0)
    write_col(50, "strain_kostrov", kostrov)
    write_col(51, "seismic_strain_log", np.log1p(np.maximum(ieq, 0.0)))
    del geod_dil, geod_shear, geod_2nd, ieq, kostrov

    mm.flush()
    meta_path.write_text(json.dumps({"names": list(SENSOR_FEATURE_NAMES), "n_fp": n_fp}, indent=2) + "\n")
    log(f"[Sensor 5/5] Cached {n_ch}-channel pure-sensor stack ({mm.nbytes / 1e9:.2f} GB) -> {cache_path}")
    return np.memmap(cache_path, dtype=np.float32, mode="r", shape=(n_fp, n_ch))


def extract_stage2_curvilinear_features(
    p1_2d: np.ndarray,
    footprint: np.ndarray,
    X_sensor_fp: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute 25-channel Stage-2 steerable curvilinear centerline features + emergent strike theta*(y,x).

    Operates strictly on Stage-1 probability surface p1_2d (zero catalogue inputs).
    Returns:
      X2_fp: (N_fp, 25) float32 array matching STAGE2_FEATURE_NAMES
      strike_rad_2d: (H, W) float32 array in [0, pi) giving dominant fault strike azimuth at every cell
    """
    fp_idx = np.flatnonzero(footprint.ravel())
    n_fp = fp_idx.size
    X2 = np.empty((n_fp, len(STAGE2_FEATURE_NAMES)), dtype=np.float32)

    p = np.where(footprint & np.isfinite(p1_2d), np.clip(p1_2d, 0.0, 1.0), 0.0).astype(np.float32)
    g1 = ndi.gaussian_filter(p, sigma=1.0).astype(np.float32)
    g3 = ndi.gaussian_filter(p, sigma=3.0).astype(np.float32)
    g8 = ndi.gaussian_filter(p, sigma=8.0).astype(np.float32)
    g4 = ndi.gaussian_filter(p, sigma=4.0).astype(np.float32)

    X2[:, 0] = p.ravel()[fp_idx]
    X2[:, 1] = g1.ravel()[fp_idx]
    X2[:, 2] = g3.ravel()[fp_idx]
    X2[:, 3] = g8.ravel()[fp_idx]
    X2[:, 4] = (g1 - g4).ravel()[fp_idx]
    del g3, g8, g4

    n_az = 12  # every 15 degrees in [0, 180)
    s1_bridge = np.zeros_like(p)
    s1_bilat = np.zeros_like(p)
    s1_crest = np.full(p.shape, -1e9, dtype=np.float32)

    s2_bridge = np.zeros_like(p)
    s2_sum_az = np.zeros_like(p)
    s2_bilat = np.zeros_like(p)
    s2_crest = np.full(p.shape, -1e9, dtype=np.float32)
    best_az_idx = np.zeros(p.shape, dtype=np.uint8)

    s3_bridge = np.zeros_like(p)
    s3_crest = np.full(p.shape, -1e9, dtype=np.float32)

    for k in range(n_az):
        theta = k * np.pi / float(n_az)
        dyu, dxu = float(np.sin(theta)), float(np.cos(theta))

        # --- Scale 1: 900 m (t = 1..4 along + / - rays, center excluded!) ---
        pos1 = sorted({(int(round(t * dyu)), int(round(t * dxu))) for t in (1, 2, 3, 4)} - {(0, 0)})
        f_plus1 = np.zeros_like(p)
        f_minus1 = np.zeros_like(p)
        for dy, dx in pos1:
            _shift_add(f_plus1, p, dy, dx)
            _shift_add(f_minus1, p, -dy, -dx)
        f_plus1 /= float(len(pos1))
        f_minus1 /= float(len(pos1))
        along1 = 0.5 * (f_plus1 + f_minus1)
        np.maximum(s1_bridge, along1, out=s1_bridge)
        np.maximum(s1_bilat, np.minimum(f_plus1, f_minus1), out=s1_bilat)
        py2, px2 = int(round(-2.0 * dxu)), int(round(2.0 * dyu))
        c1 = along1 - 0.5 * (_shifted(along1, py2, px2) + _shifted(along1, -py2, -px2))
        np.maximum(s1_crest, c1, out=s1_crest)
        del f_plus1, f_minus1, along1, c1

        # --- Scale 2: 2.3 km (t = 2, 4, 6, 8, 10, 11 on mildly smoothed g1) ---
        pos2 = sorted({(int(round(t * dyu)), int(round(t * dxu))) for t in (2, 4, 6, 8, 10, 11)} - {(0, 0)})
        f_plus2 = np.zeros_like(p)
        f_minus2 = np.zeros_like(p)
        for dy, dx in pos2:
            _shift_add(f_plus2, g1, dy, dx)
            _shift_add(f_minus2, g1, -dy, -dx)
        f_plus2 /= float(len(pos2))
        f_minus2 /= float(len(pos2))
        along2 = 0.5 * (f_plus2 + f_minus2)
        s2_sum_az += along2
        np.maximum(s2_bridge, along2, out=s2_bridge)
        np.maximum(s2_bilat, np.minimum(f_plus2, f_minus2), out=s2_bilat)
        py3, px3 = int(round(-3.0 * dxu)), int(round(3.0 * dyu))
        c2 = along2 - 0.5 * (_shifted(along2, py3, px3) + _shifted(along2, -py3, -px3))
        better = c2 > s2_crest
        best_az_idx[better] = k
        s2_crest[better] = c2[better]
        del f_plus2, f_minus2, along2, c2, better

        # --- Scale 3: 4.5 km trunk continuity (t = 4, 8, 12, 16, 20, 22 on g1) ---
        pos3 = sorted({(int(round(t * dyu)), int(round(t * dxu))) for t in (4, 8, 12, 16, 20, 22)} - {(0, 0)})
        along3 = np.zeros_like(p)
        for dy, dx in pos3:
            _shift_add(along3, g1, dy, dx)
            _shift_add(along3, g1, -dy, -dx)
        along3 /= float(2 * len(pos3))
        np.maximum(s3_bridge, along3, out=s3_bridge)
        py4, px4 = int(round(-4.0 * dxu)), int(round(4.0 * dyu))
        c3 = along3 - 0.5 * (_shifted(along3, py4, px4) + _shifted(along3, -py4, -px4))
        np.maximum(s3_crest, c3, out=s3_crest)
        del along3, c3

    del g1
    s2_mean = s2_sum_az / float(n_az)
    aniso = s2_bridge / (s2_mean + 0.005)
    strand_prod = np.sqrt(np.maximum(s1_crest, 0.0) * np.maximum(s2_bridge, 0.0))
    strike_rad = (best_az_idx.astype(np.float32) * (np.pi / float(n_az))).astype(np.float32)

    X2[:, 5] = s1_bridge.ravel()[fp_idx]
    X2[:, 6] = s1_bilat.ravel()[fp_idx]
    X2[:, 7] = s1_crest.ravel()[fp_idx]
    X2[:, 8] = s2_bridge.ravel()[fp_idx]
    X2[:, 9] = s2_bilat.ravel()[fp_idx]
    X2[:, 10] = s2_crest.ravel()[fp_idx]
    X2[:, 11] = aniso.ravel()[fp_idx]
    X2[:, 12] = s3_bridge.ravel()[fp_idx]
    X2[:, 13] = s3_crest.ravel()[fp_idx]
    X2[:, 14] = strand_prod.ravel()[fp_idx]
    X2[:, 15] = np.cos(2.0 * strike_rad).ravel()[fp_idx]
    X2[:, 16] = np.sin(2.0 * strike_rad).ravel()[fp_idx]

    for j, col_i in enumerate(ANCHOR_COL_INDICES):
        X2[:, 17 + j] = X_sensor_fp[:, col_i]

    return X2, strike_rad


def fit_lgb_fault_model(
    X_fp: np.ndarray,
    pos_mask_fp: np.ndarray,
    neg_pool_mask_fp: np.ndarray,
    seed: int,
    n_estimators: int = 320,
    num_leaves: int = 63,
    neg_ratio: int = 6,
) -> tuple[lgb.LGBMClassifier, float]:
    """Fit a fast, regularized LightGBM classifier with prior-calibrated odds correction."""
    rng = np.random.default_rng(seed)
    pos_idx = np.flatnonzero(pos_mask_fp)
    neg_pool = np.flatnonzero(neg_pool_mask_fp)
    n_pos = int(pos_idx.size)
    n_neg_total = int(neg_pool.size)
    n_neg_sample = min(n_neg_total, n_pos * neg_ratio)
    neg_idx = rng.choice(neg_pool, size=n_neg_sample, replace=False)

    idx = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(n_pos, dtype=np.int32), np.zeros(n_neg_sample, dtype=np.int32)])
    X_tr = np.asarray(X_fp[idx], dtype=np.float32)

    clf = lgb.LGBMClassifier(
        n_estimators=n_estimators,
        learning_rate=0.055,
        num_leaves=num_leaves,
        min_child_samples=80,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_alpha=1.5,
        reg_lambda=4.0,
        random_state=seed,
        n_jobs=-1,
        verbose=-1,
    )
    clf.fit(X_tr, y)
    subsample_rate = float(n_neg_sample) / float(max(n_neg_total, 1))
    return clf, subsample_rate


def predict_calibrated_2d(
    clf: lgb.LGBMClassifier,
    subsample_rate: float,
    X_fp: np.ndarray,
    footprint: np.ndarray,
    mask_fp: np.ndarray | None = None,
    batch_size: int = 600_000,
) -> np.ndarray:
    """Predict true prior-calibrated fault probability p(y=1|x) on requested footprint subset."""
    r = float(subsample_rate)
    if mask_fp is None:
        n_fp = X_fp.shape[0]
        p_fp = np.empty(n_fp, dtype=np.float32)
        for start in range(0, n_fp, batch_size):
            end = min(start + batch_size, n_fp)
            raw = clf.predict_proba(np.asarray(X_fp[start:end], dtype=np.float32))[:, 1]
            p_fp[start:end] = (raw * r) / np.maximum(raw * r + (1.0 - raw), 1e-12)
        out = np.zeros(footprint.shape, dtype=np.float32)
        out[footprint] = p_fp
        return out

    idx = np.flatnonzero(mask_fp)
    p_sub = np.empty(idx.size, dtype=np.float32)
    for start in range(0, idx.size, batch_size):
        end = min(start + batch_size, idx.size)
        raw = clf.predict_proba(np.asarray(X_fp[idx[start:end]], dtype=np.float32))[:, 1]
        p_sub[start:end] = (raw * r) / np.maximum(raw * r + (1.0 - raw), 1e-12)
    p_fp = np.zeros(X_fp.shape[0], dtype=np.float32)
    p_fp[idx] = p_sub
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = p_fp
    return out


def align_quadrant_surfaces(
    p2_2d: np.ndarray,
    p1_sf_2d: np.ndarray,
    quad_2d: np.ndarray,
    footprint: np.ndarray,
    w_stage2: float = 0.72,
) -> np.ndarray:
    """Unsupervised inter-fold calibration alignment across separately-fitted LOQO models.

    Maps each quadrant's Stage-2 curvilinear posterior onto the common pooled sensor scale
    and blends with Stage-1 seam-free Steger-Blakely localization (0 label access).
    """
    q_grid = np.concatenate([
        np.linspace(0.0, 0.95, 191, endpoint=False),
        np.linspace(0.95, 0.999, 246, endpoint=False),
        np.linspace(0.999, 1.0, 101),
    ])
    ref_q = np.quantile(p2_2d[footprint], q_grid)
    ref_p1_q = np.quantile(p1_sf_2d[footprint], q_grid)
    out = np.zeros(footprint.shape, dtype=np.float32)
    for q in range(4):
        m = (quad_2d == q) & footprint
        if not m.any():
            continue
        s2_q = np.quantile(p2_2d[m], q_grid)
        s1_q = np.quantile(p1_sf_2d[m], q_grid)
        aligned_s2 = np.interp(p2_2d[m], s2_q, ref_q)
        aligned_s1 = np.interp(p1_sf_2d[m], s1_q, ref_p1_q)
        # Scale-matched combination preserving Stage-2 strand continuity + Stage-1 sub-pixel crest peak:
        out[m] = (w_stage2 * aligned_s2 + (1.0 - w_stage2) * aligned_s1).astype(np.float32)
    out[~footprint] = 0.0
    return out


def directional_crest_sharpen(
    prob_2d: np.ndarray,
    strike_rad_2d: np.ndarray,
    footprint: np.ndarray,
    flank_sub: float = 0.50,
    eta: float = 0.75,
) -> np.ndarray:
    """Suppress across-strike 2D apron bloat perpendicular to local strand strike theta*(y,x).

    1. Subtracts 400 m across-strike sheet background p_flank4 so broad lithologic/hillside
       blobs cannot exploit the 4.58x 2D disk-area advantage over 1-px fault traces.
    2. Applies directional crest ratio (p / p_perp_1_2)^eta so submodular dots snap dead-center
       onto the 1-pixel fault trace crest (k(0)=1.0 vs k(1)=0.67).
    """
    p = np.where(footprint & np.isfinite(prob_2d), np.clip(prob_2d, 0.0, 1.0), 0.0).astype(np.float32)
    sector = (np.rint(strike_rad_2d / (np.pi / 8.0)).astype(np.int32)) % 8
    perp_max = np.zeros_like(p)
    perp_flank4 = np.zeros_like(p)
    for s in range(8):
        th = s * (np.pi / 8.0)
        ny1, nx1 = int(round(-np.cos(th))), int(round(np.sin(th)))
        ny2, nx2 = int(round(-2.0 * np.cos(th))), int(round(2.0 * np.sin(th)))
        ny4, nx4 = int(round(-4.0 * np.cos(th))), int(round(4.0 * np.sin(th)))
        pm = np.maximum(
            np.maximum(_shifted(p, ny1, nx1), _shifted(p, -ny1, -nx1)),
            0.90 * np.maximum(_shifted(p, ny2, nx2), _shifted(p, -ny2, -nx2)),
        )
        pf4 = 0.5 * (_shifted(p, ny4, nx4) + _shifted(p, -ny4, -nx4))
        m = sector == s
        perp_max[m] = pm[m]
        perp_flank4[m] = pf4[m]

    line_excess = np.maximum(p - flank_sub * perp_flank4, 0.15 * p)
    ratio = np.clip((p + 1e-4) / (perp_max + 1e-4), 0.0, 1.35)
    sharpened = (line_excess * np.power(ratio, eta)).astype(np.float32)
    mx = float(sharpened[footprint].max()) if footprint.any() else 1.0
    if mx > 1.0:
        sharpened /= mx
    sharpened[~footprint] = 0.0
    return np.clip(sharpened, 0.0, 1.0).astype(np.float32)


def build_blind_basin_conduit_branch(
    X52_fp: np.ndarray,
    X15_fp: np.ndarray,
    depth_base_2d: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Subsurface Blakely-Simpson contact crests (gravity + magnetics + basement step)
    modulated by GDR-1391/ScienceBase hydrothermal upflow under deep alluvial fill (>= 150 m).

    Recovers completely blind geothermal conduits in sediment-filled valleys where
    surface 1m LiDAR / 10m DEM scarps are buried by Holocene fan progradation or playa fill.
    """
    fp_idx = np.flatnonzero(footprint.ravel())

    def _q99(v: np.ndarray) -> np.ndarray:
        pos = v[v > 0]
        p99 = float(np.percentile(pos, 99.0)) if pos.size else 1.0
        return np.clip(v / max(p99, 1e-6), 0.0, 1.5)

    c_grav = X15_fp[:, 7] + 0.8 * X15_fp[:, 8]
    c_mag = X15_fp[:, 9] + 0.8 * X15_fp[:, 11]
    c_db = X15_fp[:, 12]
    hydro = X52_fp[:, 46] + 0.5 * X52_fp[:, 47]

    sub_fp = (0.45 * _q99(c_grav) + 0.35 * _q99(c_mag) + 0.20 * _q99(c_db)) * (1.0 + 0.65 * _q99(hydro))
    out = np.zeros(footprint.shape, dtype=np.float32)
    out.ravel()[fp_idx] = sub_fp.astype(np.float32)
    burial_gate = np.tanh(np.maximum(depth_base_2d - 150.0, 0.0) / 250.0).astype(np.float32)
    return (out * burial_gate).astype(np.float32)


def compose_mcsc_final_surface(
    p2_2d: np.ndarray,
    p1_sf_2d: np.ndarray,
    strike_2d: np.ndarray,
    depth_base_2d: np.ndarray,
    blind_branch_2d: np.ndarray,
    quad_2d: np.ndarray,
    footprint: np.ndarray,
    lam_blind: float = 0.062,
) -> np.ndarray:
    """Combine inter-fold quantile-aligned Stage-2/Stage-1 posteriors, directional across-strike
    crest sharpening, piedmont burial compensation, and the blind-basin geophysical conduit branch.
    """
    aligned = align_quadrant_surfaces(p2_2d, p1_sf_2d, quad_2d, footprint, w_stage2=0.72)
    crest = directional_crest_sharpen(aligned, strike_2d, footprint, flank_sub=0.45, eta=0.75)
    w_pied = (1.0 + 0.60 * np.tanh(np.maximum(depth_base_2d, 0.0) / 250.0)).astype(np.float32)
    combined = (crest * w_pied + float(lam_blind) * blind_branch_2d).astype(np.float32)
    mx = float(combined[footprint].max()) if footprint.any() else 1.0
    if mx > 0.0:
        combined /= mx
    combined[~footprint] = 0.0
    return np.clip(combined, 0.0, 1.0).astype(np.float32)


def submodular_dti_emit(
    prob: np.ndarray,
    allowed_mask: np.ndarray,
    n_dots: int = 37654,
    fp_penalty_weight: float = 0.055,
    candidate_pool: int = 400_000,
) -> np.ndarray:
    """Exact lazy-greedy Minoux submodular maximizer of expected 300m triangular-kernel DTI utility."""
    from gems57 import metric

    H, W = prob.shape
    pad = 3
    q_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    q_pad[pad : pad + H, pad : pad + W] = np.clip(np.where(np.isfinite(prob), prob, 0.0), 0.0, 1.0)
    cov_pad = np.zeros_like(q_pad)

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    init_tp = np.zeros((H, W), dtype=np.float64)
    q_self = np.zeros((H, W), dtype=np.float64)
    for oy, ox, k_val in zip(dy, dx, kw):
        sub = q_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W]
        init_tp += k_val * sub
        np.maximum(q_self, k_val * sub, out=q_self)

    pen_arr = fp_penalty_weight * (1.0 - q_self)
    u0 = init_tp - pen_arr

    valid_idx = np.flatnonzero(allowed_mask & (init_tp > 0))
    if valid_idx.size > candidate_pool:
        u_sub = u0.ravel()[valid_idx]
        keep = np.argpartition(u_sub, -candidate_pool)[-candidate_pool:]
        valid_idx = valid_idx[keep]

    ys = (valid_idx // W + pad).tolist()
    xs = (valid_idx % W + pad).tolist()
    pens = pen_arr.ravel()[valid_idx].tolist()
    u_vals = u0.ravel()[valid_idx].tolist()

    heap: list[tuple[float, int]] = [(-u_vals[i], i) for i in range(len(u_vals))]
    heapq.heapify(heap)

    out = np.zeros((H, W), dtype=np.float32)
    selected = 0

    while selected < n_dots and heap:
        _, i = heapq.heappop(heap)
        cy, cx = ys[i], xs[i]
        gain = 0.0
        for m in range(n_off):
            ny, nx = cy + dy[m], cx + dx[m]
            k_m = kw[m]
            cur_c = cov_pad[ny, nx]
            if k_m > cur_c:
                gain += q_pad[ny, nx] * (k_m - cur_c)
        exact_u = gain - pens[i]

        if not heap or (-exact_u <= heap[0][0] + 1e-15):
            out[cy - pad, cx - pad] = 1.0
            for m in range(n_off):
                ny, nx = cy + dy[m], cx + dx[m]
                k_m = kw[m]
                if k_m > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = k_m
            selected += 1
        else:
            heapq.heappush(heap, (-exact_u, i))

    if selected != int(n_dots):
        raise RuntimeError(f"Submodular emitter selected {selected} != requested {n_dots}")
    return out


def compute_symmetric_canaries(
    X_fp: np.ndarray,
    names: tuple[str, ...],
    footprint: np.ndarray,
    cat_mask: np.ndarray,
    hidden_mask: np.ndarray,
    seed: int = 7301,
) -> dict[str, Any]:
    """Single-feature leakage canary check (symmetric AUC <= 0.90 on both withheld and catalogue)."""
    rng = np.random.default_rng(seed)
    fp_idx = np.flatnonzero(footprint.ravel())
    dcat = ndi.distance_transform_edt(~cat_mask)
    cat_fp = cat_mask.ravel()[fp_idx]
    hid_fp = hidden_mask.ravel()[fp_idx]
    neg_fp = (dcat.ravel()[fp_idx] > 5.0) & (~cat_fp)

    pos_hid_i = np.flatnonzero(hid_fp)
    pos_cat_i = rng.choice(np.flatnonzero(cat_fp), size=min(30_000, int(cat_fp.sum())), replace=False)
    neg_i = rng.choice(np.flatnonzero(neg_fp), size=min(150_000, int(neg_fp.sum())), replace=False)

    out_ch = {}
    for j, nm in enumerate(names):
        col = X_fp[:, j]
        vh = col[pos_hid_i]
        vc = col[pos_cat_i]
        vn = col[neg_i]
        yh = np.concatenate([np.ones(vh.size), np.zeros(vn.size)])
        yc = np.concatenate([np.ones(vc.size), np.zeros(vn.size)])
        auc_h = float(roc_auc_score(yh, np.concatenate([vh, vn])))
        auc_c = float(roc_auc_score(yc, np.concatenate([vc, vn])))
        sym = float(max(auc_h, 1.0 - auc_h, auc_c, 1.0 - auc_c))
        out_ch[nm] = {
            "auc_withheld": round(auc_h, 5),
            "auc_catalogue": round(auc_c, 5),
            "symmetric_auc": round(sym, 5),
            "pass": bool(sym <= 0.90),
        }
    return {
        "n_features": len(names),
        "max_symmetric_auc": round(max(v["symmetric_auc"] for v in out_ch.values()), 5),
        "all_pass": all(v["pass"] for v in out_ch.values()),
        "channels": out_ch,
    }
