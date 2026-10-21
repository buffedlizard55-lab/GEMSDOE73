"""H73-MVH feature engineering: multi-scale geophysics, 1m-LiDAR + 10m-DEM local-prominence
scarps, GeoDAWN radiometrics & shallow magnetic residual, INGENIOUS/GDR paleo-geothermal
vent Radon corridors, and strictly fold-isolated fault-network bridge & hanging-wall mechanics.

Strict protocol invariants enforced everywhere in this module:
  1. Zero historical/registry prediction rasters are read anywhere here.
  2. Zero SGMC fault rasters are read anywhere here.
  3. Columns encoding catalogue distance (``dist_known_fault_px``, ``known_fault``, ``label``)
     in external point CSVs are explicitly asserted forbidden at parse time.
  4. All static features stream band-by-band into a sequential float32 ``np.memmap`` over the
     5,167,373 in-footprint cells so peak RAM stays comfortably below 900 MB.
"""
from __future__ import annotations

import csv
import io
import json
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.warp import transform as rio_transform
from scipy.ndimage import (
    convolve,
    distance_transform_edt,
    gaussian_filter,
    label as ndi_label,
)
from scipy.spatial import cKDTree

FORBIDDEN_POINT_COLUMNS = frozenset({"dist_known_fault_px", "known_fault", "label"})
STRUCT3 = np.ones((3, 3), dtype=np.int8)

TF_BAND_NAMES = [
    "mag_anom",
    "rtp",
    "tmi_hg",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "tc",
    "geod_shearrate",
    "geod_dilaterate",
    "tmi_vg",
    "deq_n100a15",
    "iso_grav_anom_vg",
    "det_elev",
    "iso_grav_anom",
    "tmi",
    "depth_to_base_surf",
    "ieq_n100a15",
    "cond_surf",
    "iso_grav_anom_hg",
    "det_elev_slope",
]

LIDAR_BAND_NAMES = [
    "lidar_ex_max",
    "lidar_ex_mean",
    "lidar_step_max",
    "lidar_lapneg_max",
    "lidar_lappos_max",
    "lidar_downface_max",
    "lidar_upface_max",
    "lidar_cross_max",
    "lidar_relief",
    "lidar_coh100",
    "lidar_strike",
]

TOPO10_BAND_NAMES = [
    "topo10_slope_p90",
    "topo10_slope_max",
    "topo10_steep_frac",
    "topo10_slope_std",
    "topo10_relief_local",
    "topo10_curv_prof_absmax",
    "topo10_aspect_coherence",
    "topo10_hs_lineament",
    "topo10_dem_mean",
]

CHI_BAND_NAMES = [
    "chi_chan_n",
    "chi_knick_n",
    "chi_raised_n",
    "chi_valid_n",
]

HIGH_TEMP_DEPOSIT_TYPES = frozenset(
    {
        "Sinter",
        "Explosion craters",
        "Silicified fault breccia",
        "Silica vein",
        "Calcite-qtz veins",
        "Sulfur",
        "Argillic alteration",
        "Alteration",
    }
)


def _shift_add(acc: np.ndarray, src: np.ndarray, dy: int, dx: int) -> None:
    h, w = src.shape
    ys = slice(max(0, dy), min(h, h + dy))
    xs = slice(max(0, dx), min(w, w + dx))
    yt = slice(max(0, -dy), min(h, h - dy))
    xt = slice(max(0, -dx), min(w, w - dx))
    acc[ys, xs] += src[yt, xt]


def radon_line_occupancy(field: np.ndarray, half_len: int = 6, n_az: int = 16) -> np.ndarray:
    """Maximum undirected straight-line average along ``n_az`` azimuths over ``[-half_len, +half_len]``."""
    src = field.astype(np.float32, copy=False)
    best = np.zeros(src.shape, dtype=np.float32)
    for k in range(n_az):
        theta = k * np.pi / n_az
        dyu, dxu = np.sin(theta), np.cos(theta)
        offsets = sorted(
            {(int(round(t * dyu)), int(round(t * dxu))) for t in range(-half_len, half_len + 1) if t != 0}
            - {(0, 0)}
        )
        if not offsets:
            continue
        acc = np.zeros(src.shape, dtype=np.float32)
        for dy, dx in offsets:
            _shift_add(acc, src, dy, dx)
        acc *= np.float32(1.0 / len(offsets))
        np.maximum(best, acc, out=best)
    return best


def _grad_mag(arr: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    sm = gaussian_filter(arr.astype(np.float32), sigma=sigma)
    gy, gx = np.gradient(sm)
    return np.hypot(gy, gx).astype(np.float32)


def _parse_2m_probes_dbf(zip_path: Path, transform: Any, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Read INGENIOUS 2-meter temperature probes (T2m, F2mDAB) with zero forbidden columns."""
    imp_dab = np.zeros(shape, dtype=np.float32)
    imp_hit = np.zeros(shape, dtype=bool)
    if not zip_path.is_file():
        return imp_dab, imp_hit
    with zipfile.ZipFile(zip_path) as zf:
        dbf_name = next(n for n in zf.namelist() if n.lower().endswith(".dbf"))
        buf = zf.read(dbf_name)
    numrec, lenhdr, lenrec = struct.unpack("<4xIHH20x", buf[:32])
    fields: list[tuple[str, int, int]] = []
    pos = 32
    offset = 1
    while buf[pos] != 0x0D:
        fname = buf[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        assert fname not in FORBIDDEN_POINT_COLUMNS, f"Forbidden column: {fname}"
        flen = buf[pos + 16]
        fields.append((fname, offset, flen))
        offset += flen
        pos += 32
    fmap = {name: (off, flen) for name, (off, flen) in ((f[0], (f[1], f[2])) for f in fields)}
    lats, lons, dabs = [], [], []
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
        if not (25.0 <= lat <= 50.0 and -130.0 <= lon <= -100.0):
            continue
        excess = max(0.0, dab) + 0.25 * max(0.0, t2m - 22.0)
        lats.append(lat)
        lons.append(lon)
        dabs.append(excess)
    if lons:
        ux, uy = rio_transform("EPSG:4269", "EPSG:32611", lons, lats)
        cols = np.floor((np.asarray(ux) - transform.c) / transform.a).astype(np.int64)
        rows = np.floor((np.asarray(uy) - transform.f) / transform.e).astype(np.int64)
        ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
        vals = np.asarray(dabs, dtype=np.float32)[ok]
        np.maximum.at(imp_dab, (rows[ok], cols[ok]), vals)
        imp_hit[rows[ok][vals > 0.5], cols[ok][vals > 0.5]] = True
    return imp_dab, imp_hit


def build_sense_raster(csv_path: Path, transform: Any, shape: tuple[int, int]) -> np.ndarray:
    """Build raw int8 slip-sense raster (2=RL dextral, 3=LL sinistral, 1=N/other) from segment endpoints.
    Never used directly as a feature; always masked strictly by ``visible_mask`` inside each fold!"""
    out = np.zeros(shape, dtype=np.int8)
    if not csv_path.is_file():
        return out
    with csv_path.open() as fh:
        reader = csv.DictReader(fh)
        assert not (FORBIDDEN_POINT_COLUMNS & set(reader.fieldnames or [])), "Forbidden column in sense CSV"
        for row in reader:
            s_txt = (row.get("sense") or "").strip().upper()
            code = 2 if s_txt == "RL" else (3 if s_txt == "LL" else (1 if s_txt else 0))
            if code == 0:
                continue
            try:
                x0, y0 = float(row["x0"]), float(row["y0"])
                x1, y1 = float(row["x1"]), float(row["y1"])
            except ValueError:
                continue
            c0 = int((x0 - transform.c) / transform.a)
            r0 = int((y0 - transform.f) / transform.e)
            c1 = int((x1 - transform.c) / transform.a)
            r1 = int((y1 - transform.f) / transform.e)
            n = max(abs(r1 - r0), abs(c1 - c0), 1)
            rs = np.linspace(r0, r1, n + 1).astype(np.int64)
            cs = np.linspace(c0, c1, n + 1).astype(np.int64)
            ok = (rs >= 0) & (rs < shape[0]) & (cs >= 0) & (cs < shape[1])
            out[rs[ok], cs[ok]] = code
    return out


def build_static_feature_memmap(
    mmap_path: Path,
    fp: np.ndarray,
    transform: Any,
    data_dir: Path,
    log=print,
) -> tuple[np.memmap, list[str], dict[str, np.ndarray]]:
    """Build or load the 82-feature label-free static memmap + auxiliary 2D planes needed for mechanics."""
    ext_dir = data_dir / "external"
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    meta_path = mmap_path.with_suffix(".meta.json")
    aux_path = mmap_path.with_suffix(".aux.npz")

    if mmap_path.is_file() and meta_path.is_file() and aux_path.is_file():
        meta = json.loads(meta_path.read_text())
        n_feat = int(meta["n_features"])
        if meta["n_footprint_pixels"] == n_fp:
            X = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n_feat, n_fp))
            z = np.load(aux_path)
            aux = {k: z[k] for k in z.files}
            log(f"Loaded cached static feature memmap: {n_feat} features x {n_fp:,} fp cells")
            return X, meta["feature_names"], aux

    mmap_path.parent.mkdir(parents=True, exist_ok=True)
    total_cols = 82
    X = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(total_cols, n_fp))
    names: list[str] = []
    col_ptr = 0

    bad_fp = ~fp
    idx_fp = distance_transform_edt(bad_fp, return_distances=False, return_indices=True)

    def _fill_fp(arr: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
        bad = ~valid_mask
        out = arr.astype(np.float32, copy=True)
        if np.array_equal(bad, bad_fp):
            out[bad] = out[idx_fp[0][bad], idx_fp[1][bad]]
        elif bad.any():
            idx = distance_transform_edt(bad, return_distances=False, return_indices=True)
            out[bad] = out[idx[0][bad], idx[1][bad]]
        return out

    def _push(name: str, arr: np.ndarray, is_fp_1d: bool = False) -> None:
        nonlocal col_ptr
        assert name not in FORBIDDEN_POINT_COLUMNS, f"Forbidden feature {name}"
        vec = arr if is_fp_1d else arr.ravel()[fp_idx]
        X[col_ptr, :] = vec.astype(np.float32, copy=False)
        names.append(name)
        col_ptr += 1

    # ---- Block A: Official 19 GeoDAWN bands + 10 geophysical/openness/local-relief transforms (29 cols)
    saved: dict[str, np.ndarray] = {}
    with rasterio.open(data_dir / "training_features.tif") as ds:
        for b_idx, b_name in enumerate(TF_BAND_NAMES, start=1):
            raw = ds.read(b_idx).astype(np.float32)
            fin = fp & np.isfinite(raw) & (raw > -1e30)
            filled = _fill_fp(raw, fin)
            _push(b_name, filled)
            if b_name in (
                "iso_grav_anom_hg",
                "tmi_hg",
                "tmi_vg",
                "tmi",
                "depth_to_base_surf",
                "cond_surf",
                "det_elev",
                "det_elev_slope",
            ):
                saved[b_name] = filled

    tilt = np.arctan2(saved["tmi_vg"], np.maximum(saved["tmi_hg"], 1e-6)).astype(np.float32)
    _push("mag_tilt_angle", tilt)
    _push("mag_tilt_zero_prox", np.cos(tilt).astype(np.float32))
    del tilt
    _push("grav_hg_worm", saved["iso_grav_anom_hg"] - gaussian_filter(saved["iso_grav_anom_hg"], 8.0))
    _push("mag_hg_worm", saved["tmi_hg"] - gaussian_filter(saved["tmi_hg"], 8.0))
    _push("basement_grad", _grad_mag(saved["depth_to_base_surf"], 1.5))
    _push("basement_curv", saved["depth_to_base_surf"] - gaussian_filter(saved["depth_to_base_surf"], 8.0))
    _push("cond_grad", _grad_mag(saved["cond_surf"], 1.5))
    _push("det_elev_lrm_s2", saved["det_elev"] - gaussian_filter(saved["det_elev"], 2.0))
    _push("det_elev_lrm_s6", saved["det_elev"] - gaussian_filter(saved["det_elev"], 6.0))
    slope_bg = gaussian_filter(np.maximum(saved["det_elev_slope"], 0.0), 12.0) + 1.0
    _push("det_slope_local_prominence", (saved["det_elev_slope"] / slope_bg).astype(np.float32))
    del slope_bg

    depth_2d = saved["depth_to_base_surf"].copy()
    elev_2d = saved["det_elev"].copy()
    slope_fp = saved["det_elev_slope"].ravel()[fp_idx].astype(np.float32)
    tmi_2d = saved["tmi"].copy()
    cond_2d = saved["cond_surf"].copy()
    saved.clear()
    log(f"Block A complete: {col_ptr} cols")

    # ---- Block B: 1m 3DEP LiDAR scarp features + polarity + prominence + Radon chain (16 cols)
    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as ds:
        has_lidar_2d = (ds.read(12) > 0) & fp
        has_lidar_fp = has_lidar_2d.ravel()[fp_idx]
        _push("lidar_has_coverage", has_lidar_fp.astype(np.float32), is_fp_1d=True)
        lid_map: dict[str, np.ndarray] = {}
        for b_idx, b_name in enumerate(LIDAR_BAND_NAMES, start=1):
            raw_fp = ds.read(b_idx).ravel()[fp_idx].astype(np.float32)
            raw_fp[~has_lidar_fp] = np.nan
            _push(b_name, raw_fp, is_fp_1d=True)
            if b_name in ("lidar_step_max", "lidar_downface_max", "lidar_upface_max", "lidar_relief", "lidar_strike"):
                lid_map[b_name] = raw_fp
        step2d_raw = ds.read(3).astype(np.float32)
        strike2d_lid = ds.read(11).astype(np.float32) * (180.0 / 255.0)

    pol_fp = np.abs(lid_map["lidar_downface_max"] - lid_map["lidar_upface_max"]) / (
        lid_map["lidar_downface_max"] + lid_map["lidar_upface_max"] + 1.0
    )
    _push("lidar_step_polarity", pol_fp.astype(np.float32), is_fp_1d=True)
    _push(
        "lidar_step_rel_relief",
        (lid_map["lidar_step_max"] / (lid_map["lidar_relief"] + 4.0)).astype(np.float32),
        is_fp_1d=True,
    )
    strike_rad_fp = np.deg2rad(lid_map["lidar_strike"] * (180.0 / 255.0))
    _push("lidar_walker_lane_cos", np.abs(np.cos(strike_rad_fp - np.deg2rad(18.0))).astype(np.float32), is_fp_1d=True)
    thr_lid = float(np.percentile(step2d_raw[has_lidar_2d], 90.0))
    sk_lid = (step2d_raw >= thr_lid) & has_lidar_2d
    rad_lid_fp = radon_line_occupancy(sk_lid, half_len=6, n_az=16).ravel()[fp_idx]
    rad_lid_fp[~has_lidar_fp] = np.nan
    _push("lidar_scarp_radon16", rad_lid_fp, is_fp_1d=True)
    del lid_map, pol_fp, strike_rad_fp, step2d_raw, sk_lid, rad_lid_fp
    log(f"Block B complete: {col_ptr} cols")

    # ---- Block C: 10m 3DEP seamless DEM + tectonic fluvial chi/ksn across 100% of footprint (16 cols)
    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as ds:
        for b_idx, b_name in enumerate(TOPO10_BAND_NAMES, start=1):
            a = ds.read(b_idx).astype(np.float32)
            _push(b_name, a)
            if b_name == "topo10_slope_p90":
                t10_p90 = a
            elif b_name == "topo10_hs_lineament":
                t10_lin = a
    _push("topo10_rel_scarp", (t10_p90 / (gaussian_filter(t10_p90, 12.0) + 2.0)).astype(np.float32))
    thr_t10 = float(np.percentile(t10_lin[fp], 90.0))
    _push("topo10_lineament_radon16", radon_line_occupancy((t10_lin >= thr_t10) & fp, half_len=6, n_az=16))
    # Smooth local topographic strike from 10m slope ridges where 1m LiDAR is absent
    gy10, gx10 = np.gradient(gaussian_filter(t10_p90, 1.5))
    t10_strike2d = (np.rad2deg(np.arctan2(gx10, -gy10)) % 180.0).astype(np.float32)
    local_scarp_strike2d = np.where(has_lidar_2d, strike2d_lid, t10_strike2d).astype(np.float32)
    del t10_p90, t10_lin, gy10, gx10, t10_strike2d, strike2d_lid

    with rasterio.open(ext_dir / "dem10_chi_100m_u8.tif") as ds:
        chi_ch = None
        chi_kn = None
        for b_idx, b_name in enumerate(CHI_BAND_NAMES, start=1):
            ca = ds.read(b_idx).astype(np.float32)
            _push(b_name, ca)
            if b_idx == 1:
                chi_ch = ca
            elif b_idx == 2:
                chi_kn = ca
        _push("chi_knick_excess", (chi_kn / (chi_ch + 4.0)).astype(np.float32))
        del chi_ch, chi_kn
    log(f"Block C complete: {col_ptr} cols")

    # ---- Block D: GeoDAWN airborne radiometrics (K/Th/U/TC + ratios) & upward-continued magnetics (11 cols)
    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as ds:
        for b_idx, b_name in enumerate(("rad_K", "rad_Th", "rad_U", "rad_TC"), start=1):
            a = ds.read(b_idx).astype(np.float32)
            _push(b_name, a)
            if b_name == "rad_K":
                rad_k = a
    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as ds:
        for b_idx, b_name in enumerate(("ext_ThK", "ext_UK", "ext_UTh", "ext_tmi_up150"), start=1):
            a = ds.read(b_idx).astype(np.float32)
            _push(b_name, a)
            if b_name == "ext_ThK":
                ext_thk = a
            elif b_name == "ext_tmi_up150":
                ext_up = a
    tmi_z = (tmi_2d - float(np.median(tmi_2d[fp]))) / (float(np.std(tmi_2d[fp])) + 1e-6)
    up_z = (ext_up - float(np.median(ext_up[fp]))) / (float(np.std(ext_up[fp])) + 1e-6)
    _push("tmi_shallow_residual", (tmi_z - up_z).astype(np.float32))
    _push("rad_K_lrm", (rad_k - gaussian_filter(rad_k, 10.0)).astype(np.float32))
    _push("ext_ThK_lrm", (ext_thk - gaussian_filter(ext_thk, 10.0)).astype(np.float32))
    del tmi_z, up_z, ext_up, tmi_2d
    log(f"Block D complete: {col_ptr} cols")

    # ---- Block E: INGENIOUS / GDR 1391 Paleo-Geothermal Vents, Geothermometers & 2m Probes (10 cols)
    paleo_all = np.zeros(fp.shape, dtype=bool)
    paleo_hi = np.zeros(fp.shape, dtype=bool)
    with zipfile.ZipFile(ext_dir / "paleo_geothermal_regional.zip") as zf:
        txt = zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(txt))
        assert not (FORBIDDEN_POINT_COLUMNS & set(reader.fieldnames or [])), "Forbidden column in paleo CSV"
        p_lons, p_lats, p_hi = [], [], []
        for row in reader:
            try:
                lo, la = float(row["Long_deg_NAD83"]), float(row["Lat_deg_NAD83"])
            except ValueError:
                continue
            p_lons.append(lo)
            p_lats.append(la)
            p_hi.append(row.get("Deposit_type", "").strip() in HIGH_TEMP_DEPOSIT_TYPES)
    if p_lons:
        ux, uy = rio_transform("EPSG:4269", "EPSG:32611", p_lons, p_lats)
        cc = np.floor((np.asarray(ux) - transform.c) / transform.a).astype(np.int64)
        rr = np.floor((np.asarray(uy) - transform.f) / transform.e).astype(np.int64)
        ok = (rr >= 0) & (rr < fp.shape[0]) & (cc >= 0) & (cc < fp.shape[1])
        paleo_all[rr[ok], cc[ok]] = True
        hi_arr = np.asarray(p_hi, dtype=bool)[ok]
        paleo_hi[rr[ok][hi_arr], cc[ok][hi_arr]] = True
    paleo_all &= fp
    paleo_hi &= fp

    spring_hot = np.zeros(fp.shape, dtype=bool)
    geotherm_hi = np.zeros(fp.shape, dtype=bool)
    geotherm_grid = np.zeros(fp.shape, dtype=np.float32)
    with (ext_dir / "gdr_wellspring_in_footprint.csv").open() as fh:
        reader = csv.DictReader(fh)
        # Verify we NEVER touch dist_known_fault_px even though present in CSV file header:
        allowed_ws_cols = {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}
        assert allowed_ws_cols.issubset(set(reader.fieldnames or []))
        for row in reader:
            r_i = int(float(row["row"]))
            c_i = int(float(row["col"]))
            if not (0 <= r_i < fp.shape[0] and 0 <= c_i < fp.shape[1] and fp[r_i, c_i]):
                continue
            vals = []
            tc_s = row["temp_c"]
            tc_v = float(tc_s) if tc_s not in ("", "nan", "NaN") else np.nan
            if np.isfinite(tc_v) and tc_v >= 37.0:
                spring_hot[r_i, c_i] = True
                vals.append(tc_v)
            for gk in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                gs = row[gk]
                gv = float(gs) if gs not in ("", "nan", "NaN") else np.nan
                if np.isfinite(gv) and 20.0 <= gv <= 360.0:
                    vals.append(gv)
                    if gv >= 110.0:
                        geotherm_hi[r_i, c_i] = True
            if vals:
                mx_v = float(max(vals))
                if mx_v > geotherm_grid[r_i, c_i]:
                    geotherm_grid[r_i, c_i] = mx_v

    volc_mask = np.zeros(fp.shape, dtype=bool)
    with (ext_dir / "gdr_volcanic_vents_in_footprint.csv").open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            r_i, c_i = int(float(row["row"])), int(float(row["col"]))
            if 0 <= r_i < fp.shape[0] and 0 <= c_i < fp.shape[1] and fp[r_i, c_i]:
                volc_mask[r_i, c_i] = True

    imp_dab, imp_hit = _parse_2m_probes_dbf(
        ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip", transform, fp.shape
    )

    _push("paleo_vent_logdist", np.log1p(distance_transform_edt(~paleo_all)).astype(np.float32))
    _push("paleo_sinter_hightemp_logdist", np.log1p(distance_transform_edt(~paleo_hi)).astype(np.float32))
    paleo_halo = gaussian_filter(paleo_all.astype(np.float32), 2.0)
    _push("paleo_vent_radon16", radon_line_occupancy(paleo_halo, half_len=14, n_az=16))
    _push("geotherm_high_logdist", np.log1p(distance_transform_edt(~geotherm_hi)).astype(np.float32))
    _push("geotherm_temp_plume", gaussian_filter(geotherm_grid, 5.0).astype(np.float32))
    all_vents = (paleo_all | spring_hot | geotherm_hi | imp_hit) & fp
    _push(
        "all_vent_radon16",
        radon_line_occupancy(gaussian_filter(all_vents.astype(np.float32), 1.8), half_len=12, n_az=16),
    )
    _push("probe2m_dab_plume", gaussian_filter(imp_dab, 4.0).astype(np.float32))
    _push("probe2m_hit_logdist", np.log1p(distance_transform_edt(~(imp_hit & fp))).astype(np.float32))
    _push("volcanic_vent_logdist", np.log1p(distance_transform_edt(~volc_mask)).astype(np.float32))

    vent_prox = np.exp(-distance_transform_edt(~all_vents) / 25.0).astype(np.float32)
    cond_z = np.clip((cond_2d - float(np.median(cond_2d[fp]))) / (float(np.std(cond_2d[fp])) + 1e-6), 0.0, 5.0)
    k_z = np.clip((rad_k - float(np.median(rad_k[fp]))) / (float(np.std(rad_k[fp])) + 1e-6), 0.0, 5.0)
    _push("hydrothermal_upflow_witness", (vent_prox * (0.4 + 0.3 * cond_z + 0.3 * k_z)).astype(np.float32))

    assert col_ptr == total_cols, f"Expected {total_cols} cols, wrote {col_ptr}"
    X.flush()

    sense_raw = build_sense_raster(ext_dir / "trace_segments_utm11.csv", transform, fp.shape)
    aux = {
        "depth_2d": depth_2d,
        "elev_2d": elev_2d,
        "local_scarp_strike2d": local_scarp_strike2d,
        "slope_fp": slope_fp,
        "has_lidar_fp": has_lidar_fp,
        "sense_raw": sense_raw,
    }
    np.savez_compressed(aux_path, **aux)
    meta_path.write_text(
        json.dumps(
            {
                "n_features": total_cols,
                "n_footprint_pixels": n_fp,
                "feature_names": names,
            },
            indent=2,
        )
        + "\n"
    )
    log(f"Built & cached static memmap: {total_cols} features x {n_fp:,} fp cells")
    return np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(total_cols, n_fp)), names, aux


MECH_FEATURE_NAMES = [
    "bridge_ellipse_tight",
    "bridge_ellipse_wide",
    "tip_proj_short",
    "tip_proj_long",
    "d_vis_collar",
    "d_perp_vis",
    "d_par_vis",
    "comp_loglen_vis",
    "hw_depth_delta",
    "hw_elev_delta",
    "scarp_strike_align",
    "vis_annulus_density",
]


def compute_visible_network_mechanics(
    visible_mask: np.ndarray,
    fp: np.ndarray,
    aux: dict[str, np.ndarray],
) -> np.ndarray:
    """Compute all 12 fold-isolated fault-network bridge, tip, and hanging-wall features
    strictly from ``visible_mask`` ONLY (never touching withheld truth or its 3 px buffer).

    Returns shape ``(12, n_fp)`` float32 aligned with ``np.flatnonzero(fp)``.
    """
    vis = np.asarray(visible_mask, dtype=bool) & fp
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    if not vis.any():
        return np.zeros((12, n_fp), dtype=np.float32)

    H, W = vis.shape
    comp, n_comp = ndi_label(vis, structure=STRUCT3)
    comp_sizes = np.bincount(comp.ravel(), minlength=n_comp + 1).astype(np.float32)
    major = comp_sizes[comp] >= 6

    # Local strike unit tangent (tx, ty) of visible strands via smoothed gradient
    sm = gaussian_filter(vis.astype(np.float32), sigma=2.5)
    gy, gx = np.gradient(sm)
    gnorm = np.hypot(gx, gy) + 1e-6
    tx = (-gx / gnorm).astype(np.float32)  # col component of tangent
    ty = (gy / gnorm).astype(np.float32)   # row component of tangent

    # Visible fault terminations (1 or 2 8-connected neighbors among major visible traces)
    nb = convolve(major.astype(np.int16), np.ones((3, 3), dtype=np.int16), mode="constant", cval=0)
    tips_mask = major & ((nb == 2) | (nb == 3))
    ty_i, tx_i = np.nonzero(tips_mask)
    tip_loglen = np.log1p(comp_sizes[comp[ty_i, tx_i]])

    # 1 & 2. Two-tip elliptical relay-bridge fields across unmapped alluvial gaps (3.5..56 px)
    bridge_tight = np.zeros((H, W), dtype=np.float32)
    bridge_wide = np.zeros((H, W), dtype=np.float32)
    if ty_i.size >= 2:
        pts = np.column_stack([ty_i.astype(np.float64), tx_i.astype(np.float64)])
        tree = cKDTree(pts)
        pairs = tree.query_pairs(r=56.0, output_type="ndarray")
        if pairs.shape[0] > 0:
            i0, i1 = pairs[:, 0], pairs[:, 1]
            same_comp = comp[ty_i[i0], tx_i[i0]] == comp[ty_i[i1], tx_i[i1]]
            dy_p = pts[i1, 0] - pts[i0, 0]
            dx_p = pts[i1, 1] - pts[i0, 1]
            dist_p = np.hypot(dy_p, dx_p)
            uy = dy_p / np.maximum(dist_p, 1e-6)
            ux = dx_p / np.maximum(dist_p, 1e-6)
            align0 = np.abs(ty[ty_i[i0], tx_i[i0]] * uy + tx[ty_i[i0], tx_i[i0]] * ux)
            align1 = np.abs(ty[ty_i[i1], tx_i[i1]] * uy + tx[ty_i[i1], tx_i[i1]] * ux)
            keep = (~same_comp) & (dist_p >= 3.5) & ((align0 > 0.55) | (align1 > 0.55)) & (
                (align0 + align1) > 1.05
            )
            for a, b, L, al in zip(i0[keep], i1[keep], dist_p[keep], (0.5 * (align0 + align1))[keep]):
                r0, c0 = int(ty_i[a]), int(tx_i[a])
                r1, c1 = int(ty_i[b]), int(tx_i[b])
                w_pair = float(al * 0.5 * (tip_loglen[a] + tip_loglen[b]) / np.log1p(50.0))
                pad_b = 6
                ya = max(0, min(r0, r1) - pad_b)
                yb = min(H, max(r0, r1) + pad_b + 1)
                xa = max(0, min(c0, c1) - pad_b)
                xb = min(W, max(c0, c1) + pad_b + 1)
                yy, xx = np.ogrid[ya:yb, xa:xb]
                slack = np.hypot(yy - r0, xx - c0) + np.hypot(yy - r1, xx - c1) - L
                if L <= 38.0:
                    bt = (w_pair * np.exp(-np.maximum(slack, 0.0) / 1.8)).astype(np.float32)
                    np.maximum(bridge_tight[ya:yb, xa:xb], bt, out=bridge_tight[ya:yb, xa:xb])
                bw = (w_pair * np.exp(-np.maximum(slack, 0.0) / 4.5)).astype(np.float32)
                np.maximum(bridge_wide[ya:yb, xa:xb], bw, out=bridge_wide[ya:yb, xa:xb])

    d_vis, (ay, ax) = distance_transform_edt(~vis, return_indices=True)
    d_vis = d_vis.astype(np.float32)
    taper = np.clip((d_vis - 2.3) / 1.8, 0.0, 1.0).astype(np.float32)
    bridge_tight = gaussian_filter(bridge_tight, 1.2) * taper
    bridge_wide = gaussian_filter(bridge_wide, 2.0) * taper

    # 3 & 4. Log-length-weighted directional strike projections from visible tips
    lobe_s = np.zeros((H, W), dtype=np.float32)
    lobe_l = np.zeros((H, W), dtype=np.float32)
    if ty_i.size > 0:
        w_tip = (tip_loglen / np.log1p(50.0)).astype(np.float32)
        for step in range(3, 29, 2):
            ws = w_tip * np.float32(np.exp(-0.5 * (step / 7.5) ** 2))
            wl = w_tip * np.float32(np.exp(-0.5 * (step / 17.0) ** 2))
            for sgn in (-1.0, 1.0):
                ry = np.clip(np.round(ty_i + sgn * step * ty[ty_i, tx_i]).astype(np.int64), 0, H - 1)
                rx = np.clip(np.round(tx_i + sgn * step * tx[ty_i, tx_i]).astype(np.int64), 0, W - 1)
                if step <= 15:
                    np.maximum.at(lobe_s, (ry, rx), ws)
                np.maximum.at(lobe_l, (ry, rx), wl)
    tip_short = gaussian_filter(lobe_s, 1.8).astype(np.float32) * taper
    tip_long = gaussian_filter(lobe_l, 2.8).astype(np.float32) * taper

    # 5..12. Anchor frame, cross-strike/along-strike offsets, hanging-wall step & strike concordance
    ry_fp = fp_idx // W
    rx_fp = fp_idx % W
    anc_y = ay.ravel()[fp_idx]
    anc_x = ax.ravel()[fp_idx]
    d_fp = d_vis.ravel()[fp_idx]

    dy_fp = (ry_fp - anc_y).astype(np.float32)
    dx_fp = (rx_fp - anc_x).astype(np.float32)
    ty_a = ty[anc_y, anc_x]
    tx_a = tx[anc_y, anc_x]

    d_par = np.abs(dy_fp * ty_a + dx_fp * tx_a)
    signed_perp = dy_fp * tx_a - dx_fp * ty_a
    d_perp = np.abs(signed_perp)

    # Collar-censor distance inside d < 3.2 px so nested-hide training & full-catalogue inference match seamlessly
    d_collar = np.clip(np.maximum(d_fp, 3.2), 3.2, 65.0).astype(np.float32)
    d_perp_safe = np.where(d_fp < 3.2, np.maximum(d_perp, 2.4), np.minimum(d_perp, 65.0)).astype(np.float32)
    d_par_safe = np.minimum(d_par, 65.0).astype(np.float32)

    comp_loglen = np.log1p(comp_sizes[comp[anc_y, anc_x]]).astype(np.float32)
    depth_2d = aux["depth_2d"]
    elev_2d = aux["elev_2d"]
    hw_depth_delta = (depth_2d.ravel()[fp_idx] - depth_2d[anc_y, anc_x]).astype(np.float32)
    hw_elev_delta = (elev_2d.ravel()[fp_idx] - elev_2d[anc_y, anc_x]).astype(np.float32)

    anc_az_rad = np.arctan2(tx_a, -ty_a)
    scarp_az_rad = np.deg2rad(aux["local_scarp_strike2d"].ravel()[fp_idx])
    scarp_align = np.abs(np.cos(scarp_az_rad - anc_az_rad)).astype(np.float32)

    annulus = (
        np.maximum(0.0, gaussian_filter(vis.astype(np.float32), 10.0) - 0.65 * gaussian_filter(vis.astype(np.float32), 2.5))
        * taper
    ).ravel()[fp_idx]
    # Add visible-only slip-sense modulation without leaking any withheld trace
    vis_sense = np.where(vis, aux["sense_raw"], 0)
    s_code = vis_sense[anc_y, anc_x]
    sgn_sense = np.where(s_code == 2, 1.0, np.where(s_code == 3, -1.0, 0.0)).astype(np.float32)
    annulus_mod = (annulus * (1.0 + 0.15 * sgn_sense * np.sign(signed_perp))).astype(np.float32)

    out = np.empty((12, n_fp), dtype=np.float32)
    out[0] = bridge_tight.ravel()[fp_idx]
    out[1] = bridge_wide.ravel()[fp_idx]
    out[2] = tip_short.ravel()[fp_idx]
    out[3] = tip_long.ravel()[fp_idx]
    out[4] = d_collar
    out[5] = d_perp_safe
    out[6] = d_par_safe
    out[7] = comp_loglen
    out[8] = hw_depth_delta
    out[9] = hw_elev_delta
    out[10] = scarp_align
    out[11] = annulus_mod
    return out
