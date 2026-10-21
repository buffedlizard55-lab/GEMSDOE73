"""Multi-physics pure-signal feature bank for GEMSDOE73 (H73-2 MECS-AutoCtx).

Builds 48 strictly label-free, catalogue-free, coordinate-free physical features across
the 5,167,373 active footprint pixels of EPSG:32611 (3292 x 3730, 100 m), stored as a
compact in-memory / disk-cached `float16` matrix (`496 MB`, well inside 3.8 GiB cgroup limits;
lossless for histogram GBDTs with 255 quantile bins).
"""
from __future__ import annotations

import csv
import gc
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy.ndimage import gaussian_filter, maximum_filter, sobel, uniform_filter

FEATURE_NAMES: tuple[str, ...] = (
    # Modality A: Seamless 1m + 10m Geomorphology & Fluvial Chi (0..15)
    "m00_scarp_seamless_q",
    "m01_lidar_step_raw",
    "m02_lidar_dipole",
    "m03_lidar_lap_dipole",
    "m04_lidar_coh_cross",
    "m05_topo10_slope_p90",
    "m06_topo10_slope_max_hp",
    "m07_topo10_steep_frac",
    "m08_topo10_slope_std",
    "m09_topo10_curv_prof",
    "m10_topo10_aspect_coh",
    "m11_topo10_hs_lineament",
    "m12_elev_slope_hp15",
    "m13_det_elev_tpi7",
    "m14_morph_worm_1500m",
    "m15_chi_ksn_knick",
    # Modality B: Subsurface Potential Fields, Cross-Gradients & Strain (16..35)
    "s16_mag_anom_hp15",
    "s17_rtp_hp15",
    "s18_log_tmi_hg",
    "s19_tmi_vg",
    "s20_tc_tilt",
    "s21_analytic_sig",
    "s22_mag_up150_persist",
    "s23_worm_mag_1500m",
    "s24_grav_hp15",
    "s25_grav_slope",
    "s26_grav_vg",
    "s27_grav_hg_abs",
    "s28_worm_grav_1500m",
    "s29_basement_depth_log",
    "s30_basement_grad",
    "s31_xgrad_gm_align",
    "s32_xgrad_gm_ortho",
    "s33_strain_2ndinv",
    "s34_strain_shear",
    "s35_strain_dilate_eq",
    # Modality C: Hydrothermal Upflow, Alteration & Geothermometry (36..43)
    "h36_k_th_potassic",
    "h37_uk_ratio_anom",
    "h38_demag_conduit",
    "h39_cond_cap_grad",
    "h40_gdr_spring_temp",
    "h41_gdr_geothermom",
    "h42_ingenious_2m_probe",
    "h43_paleo_sinter_vent",
    # Modality D: Cross-Domain Structural Coupling & Confounder Guards (44..47)
    "c44_xgrad_topo_subsurf",
    "c45_anderson_strike_fav",
    "c46_playa_fan_confounder",
    "c47_multisensor_witness",
)

IDX_MORPH = list(range(0, 16))
IDX_SUBSURF = list(range(16, 36))
IDX_HYDRO = list(range(36, 44))
IDX_COUPLE = list(range(44, 48))
IDX_JOINT = list(range(0, 48))

BLOCKED_COLUMNS = frozenset({"dist_known_fault_px"})
_F16_MAX = 65000.0


def fast_pct_rank_1d(vals: np.ndarray, knots: int = 4096) -> np.ndarray:
    """Fast O(N) empirical quantile rank in `(0, 1)` using `knots` exact order-statistic knots."""
    v = np.asarray(vals, dtype=np.float32)
    step = max(1, v.size // 262_144)
    sample = np.sort(v[::step])
    q_grid = np.linspace(0.0, 1.0, min(knots, sample.size), dtype=np.float32)
    x_knots = np.quantile(sample, q_grid).astype(np.float32)
    # Collapse duplicate knot values cleanly so mid-ranks handle ties properly
    ux, inv_first = np.unique(x_knots, return_index=True)
    _, inv_last = np.unique(x_knots[::-1], return_index=True)
    inv_last = (x_knots.size - 1) - inv_last
    q_mid = 0.5 * (q_grid[inv_first] + q_grid[inv_last])
    return np.clip(np.interp(v, ux, q_mid), 1e-5, 1.0 - 1e-5).astype(np.float32)


def _pct_rank_2d(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros(arr.shape, dtype=np.float32)
    out[mask] = fast_pct_rank_1d(arr[mask])
    return out


def _clean_band(arr: np.ndarray, nodata: float | None = None) -> np.ndarray:
    a = arr.astype(np.float32, copy=False)
    bad = ~np.isfinite(a) | (np.abs(a) > 1e30)
    if nodata is not None and np.isfinite(nodata):
        bad |= a == np.float32(nodata)
    out = a.copy()
    if bad.any():
        med = float(np.median(out[~bad])) if (~bad).any() else 0.0
        out[bad] = med
    return out


def _grad_mag(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gx = sobel(arr, axis=1).astype(np.float32) * 0.125
    gy = sobel(arr, axis=0).astype(np.float32) * 0.125
    mag = np.hypot(gx, gy).astype(np.float32)
    return gx, gy, mag


def _steerable_worm_1500m(field: np.ndarray, angles_deg: tuple[int, ...] = (0, 30, 60, 90, 120, 150)) -> np.ndarray:
    """Memory-minimal flank-suppressed 1.5 km directional ridge persistence across 6 strikes."""
    base = gaussian_filter(field.astype(np.float32), sigma=1.0)
    h, w = base.shape
    best = np.full((h, w), -1e9, dtype=np.float32)
    along = np.empty((h, w), dtype=np.float32)
    flank = np.empty((h, w), dtype=np.float32)
    radii = (-6, -3, 0, 3, 6)
    for deg in angles_deg:
        th = np.deg2rad(deg)
        ux, uy = float(np.cos(th)), float(np.sin(th))
        px, py = -uy, ux
        along.fill(0.0)
        for s in radii:
            dx, dy = int(round(s * ux)), int(round(s * uy))
            along += np.roll(np.roll(base, -dy, axis=0), -dx, axis=1)
        along *= 0.2
        dx, dy = int(round(4.0 * px)), int(round(4.0 * py))
        flank[:] = np.roll(np.roll(base, -dy, axis=0), -dx, axis=1)
        flank += np.roll(np.roll(base, dy, axis=0), dx, axis=1)
        flank *= 0.5
        along -= flank
        np.maximum(best, along, out=best)
    best[:8, :] = 0.0
    best[-8:, :] = 0.0
    best[:, :8] = 0.0
    best[:, -8:] = 0.0
    del base, along, flank
    return best


def _splat_points(shape: tuple[int, int], rows: list[int], cols: list[int], weights: list[float], sigmas: tuple[float, ...]) -> np.ndarray:
    grid = np.zeros(shape, dtype=np.float32)
    h, w = shape
    for r, c, wt in zip(rows, cols, weights):
        if 0 <= r < h and 0 <= c < w and wt > grid[r, c]:
            grid[r, c] = float(wt)
    acc = np.zeros(shape, dtype=np.float32)
    for sig in sigmas:
        acc += gaussian_filter(grid, sigma=sig) * float(2.0 * np.pi * sig * sig)
    del grid
    return (acc / float(len(sigmas))).astype(np.float32)


def _load_2m_probes(zip_path: Path, transform, shape: tuple[int, int]) -> np.ndarray:
    rows, cols, wts = [], [], []
    with zipfile.ZipFile(zip_path) as zf:
        dbf = zf.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    numrec, lenhdr, lenrec = struct.unpack("<IHH", dbf[4:12])
    fields, pos = [], 32
    while dbf[pos] != 0x0D:
        fields.append((dbf[pos : pos + 11].split(b"\x00")[0].decode("ascii", "replace"), dbf[pos + 16]))
        pos += 32
    lons, lats, vals = [], [], []
    for i in range(numrec):
        rec = dbf[lenhdr + i * lenrec : lenhdr + (i + 1) * lenrec]
        if not rec or rec[0:1] == b"*":
            continue
        off = 1
        d = {}
        for nm, fl in fields:
            if nm in ("LatDegreeN", "LongDegree", "T2m", "F2mDAB"):
                d[nm] = rec[off : off + fl].decode("latin1", "replace").strip()
            off += fl
        try:
            lat = float(d["LatDegreeN"])
            lon = float(d["LongDegree"])
            f2m = float(d["F2mDAB"]) if d.get("F2mDAB") else 0.0
            t2m = float(d["T2m"]) if d.get("T2m") else 0.0
        except ValueError:
            continue
        if not (-125.0 < lon < -110.0 and 35.0 < lat < 45.0):
            continue
        anom = max(f2m, 0.0) + 0.35 * max(t2m - 20.0, 0.0)
        if anom > 0.25:
            lons.append(lon)
            lats.append(lat)
            vals.append(min(anom, 25.0) / 25.0)
    del dbf
    if lons:
        xs, ys = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
        inv = ~transform
        for x, y, v in zip(xs, ys, vals):
            cc, rr = inv * (x, y)
            rows.append(int(round(rr)))
            cols.append(int(round(cc)))
            wts.append(float(v))
    return _splat_points(shape, rows, cols, wts, sigmas=(6.0, 18.0))


def _load_paleo_vents(data_dir: Path, transform, shape: tuple[int, int]) -> np.ndarray:
    rows, cols, wts = [], [], []
    inv = ~transform
    zpath = data_dir / "external" / "paleo_geothermal_regional.zip"
    if zpath.exists():
        lons, lats, p_wt = [], [], []
        with zipfile.ZipFile(zpath) as zf, zf.open("Paleo_geothermal_final.csv") as fh:
            for r in csv.DictReader((line.decode("utf-8", "replace") for line in fh)):
                try:
                    lon = float(r["Long_deg_NAD83"])
                    lat = float(r["Lat_deg_NAD83"])
                except (KeyError, ValueError):
                    continue
                dtype = (r.get("Deposit_type") or "").lower()
                w = 1.0 if "sinter" in dtype else (0.8 if "travertine" in dtype else 0.6)
                lons.append(lon)
                lats.append(lat)
                p_wt.append(w)
        if lons:
            xs, ys = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
            for x, y, w in zip(xs, ys, p_wt):
                cc, rr = inv * (x, y)
                rows.append(int(round(rr)))
                cols.append(int(round(cc)))
                wts.append(float(w))
    vpath = data_dir / "external" / "gdr_vents_in_footprint.csv"
    if vpath.exists():
        with vpath.open() as fh:
            for r in csv.DictReader(fh):
                try:
                    rows.append(int(float(r["row"])))
                    cols.append(int(float(r["col"])))
                    wts.append(0.55)
                except (KeyError, ValueError):
                    continue
    return _splat_points(shape, rows, cols, wts, sigmas=(8.0, 24.0))


def _load_wellspring_plumes(data_dir: Path, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    rows_t, cols_t, w_t = [], [], []
    rows_g, cols_g, w_g = [], [], []
    wpath = data_dir / "external" / "gdr_wellspring_in_footprint.csv"
    with wpath.open() as fh:
        reader = csv.DictReader(fh)
        allowed_cols = set(reader.fieldnames or []) - BLOCKED_COLUMNS
        assert "dist_known_fault_px" not in allowed_cols, "blocked fault-distance column leaked"
        for r in reader:
            row_clean = {k: r[k] for k in allowed_cols}
            try:
                rr = int(float(row_clean["row"]))
                cc = int(float(row_clean["col"]))
            except (KeyError, ValueError):
                continue
            tc = row_clean.get("temp_c", "")
            if tc:
                try:
                    tv = float(tc)
                    if tv > 22.0:
                        rows_t.append(rr)
                        cols_t.append(cc)
                        w_t.append(min(max(tv - 20.0, 0.0) / 80.0, 1.5))
                except ValueError:
                    pass
            gvals = []
            for gk in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                if row_clean.get(gk):
                    try:
                        gv = float(row_clean[gk])
                        if 40.0 < gv < 380.0:
                            gvals.append(gv)
                    except ValueError:
                        pass
            if gvals:
                rows_g.append(rr)
                cols_g.append(cc)
                w_g.append(min(max(max(gvals) - 60.0, 0.0) / 160.0, 1.5))
    return (
        _splat_points(shape, rows_t, cols_t, w_t, sigmas=(10.0, 28.0)),
        _splat_points(shape, rows_g, cols_g, w_g, sigmas=(12.0, 32.0)),
    )


def build_or_load_feature_bank(data_dir: Path, cache_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return `(X_fp [5_167_373, 48] float16 (~496 MB RAM), fp_flat_indices [5_167_373] int64)`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    f16_path = cache_dir / "X_fp_48_f16.npy"
    idx_path = cache_dir / "fp_idx_i64.npy"

    with rasterio.open(data_dir / "sample_submission.tif") as s_tpl:
        foot = np.isfinite(s_tpl.read(1))
        transform = s_tpl.transform
        shape = foot.shape
    fp_idx = np.flatnonzero(foot).astype(np.int64)
    n_fp = int(fp_idx.size)
    n_feat = len(FEATURE_NAMES)

    if f16_path.exists() and idx_path.exists():
        X_cached = np.load(f16_path)
        if X_cached.shape == (n_fp, n_feat) and X_cached.dtype == np.float16:
            return X_cached, fp_idx

    X = np.empty((n_fp, n_feat), dtype=np.float16)

    def put_raw(col: int, arr2d: np.ndarray, allow_nan: bool = False) -> None:
        v = arr2d.ravel()[fp_idx].astype(np.float32, copy=False)
        if allow_nan:
            X[:, col] = np.where(np.isnan(v), np.nan, np.clip(v, -_F16_MAX, _F16_MAX)).astype(np.float16)
        else:
            # Robust z-score compression if range exceeds float16 comfort zone
            vmax = float(np.max(np.abs(v)))
            if vmax > 5000.0:
                med = float(np.median(v))
                iqr = float(np.percentile(v, 90) - np.percentile(v, 10)) + 1e-5
                v = (v - med) / iqr
            X[:, col] = np.clip(v, -_F16_MAX, _F16_MAX).astype(np.float16)

    # ---- Stage A: Geomorphology & Chi (Cols 0..15) ----
    with rasterio.open(data_dir / "external" / "lidar_scarp_features_u8.tif") as sl:
        lid_valid = (sl.read(12) > 0) & foot
        lid_step = sl.read(3).astype(np.float32)
        q_lid = _pct_rank_2d(lid_step, lid_valid)
        put_raw(1, np.where(lid_valid, lid_step, np.nan), allow_nan=True)
        lid_down = sl.read(6).astype(np.float32)
        lid_up = sl.read(7).astype(np.float32)
        put_raw(2, np.where(lid_valid, lid_step * np.abs(lid_down - lid_up) / (lid_down + lid_up + 2.0), np.nan), allow_nan=True)
        del lid_step, lid_down, lid_up
        lid_lapn = sl.read(4).astype(np.float32)
        lid_lapp = sl.read(5).astype(np.float32)
        put_raw(3, np.where(lid_valid, np.sqrt(np.maximum(lid_lapn * lid_lapp, 0.0)), np.nan), allow_nan=True)
        del lid_lapn, lid_lapp
        lid_cross = sl.read(8).astype(np.float32)
        lid_coh = sl.read(10).astype(np.float32)
        put_raw(4, np.where(lid_valid, lid_coh * lid_cross / 255.0, np.nan), allow_nan=True)
        del lid_cross, lid_coh

    with rasterio.open(data_dir / "external" / "topo_10m_derived_100m_u8.tif") as st10:
        t10_p90 = st10.read(1).astype(np.float32)
        t10_smax = st10.read(2).astype(np.float32)
        t10_sstd = st10.read(4).astype(np.float32)
        t10_curv = st10.read(6).astype(np.float32)
        proxy10 = 0.45 * t10_smax + 0.35 * t10_curv + 0.20 * t10_sstd
        q_t10 = _pct_rank_2d(proxy10, foot)
        del proxy10
        seamless_scarp = np.where(lid_valid, 0.72 * q_lid + 0.28 * q_t10, q_t10).astype(np.float32)
        del q_lid, q_t10, lid_valid
        put_raw(0, seamless_scarp)
        put_raw(5, t10_p90)
        put_raw(6, t10_smax - uniform_filter(t10_smax, size=15))
        del t10_smax
        put_raw(7, st10.read(3).astype(np.float32))
        put_raw(8, t10_sstd)
        del t10_sstd
        put_raw(9, t10_curv)
        del t10_curv
        put_raw(10, st10.read(7).astype(np.float32))
        put_raw(11, st10.read(8).astype(np.float32))

    put_raw(14, _steerable_worm_1500m(seamless_scarp))

    with rasterio.open(data_dir / "external" / "dem10_chi_100m_i16.tif") as sc16, rasterio.open(
        data_dir / "external" / "dem10_chi_100m_u8.tif"
    ) as sc8:
        chi_step = np.abs(sc16.read(1).astype(np.float32)) * 0.001
        log_ksn = np.log1p(np.maximum(sc16.read(3).astype(np.float32), 0.0))
        knick = sc8.read(2).astype(np.float32) + sc8.read(3).astype(np.float32)
    put_raw(15, gaussian_filter(log_ksn - uniform_filter(log_ksn, size=21) + 0.5 * np.log1p(chi_step + knick), sigma=1.5))
    del chi_step, log_ksn, knick
    gc.collect()

    # ---- Stage B: Subsurface Potential Fields, Elevation Residuals, Strain (Cols 12..13, 16..35) ----
    with rasterio.open(data_dir / "training_features.tif") as tf:
        nd = tf.nodata
        mag_anom = _clean_band(tf.read(1), nd)
        put_raw(16, mag_anom - uniform_filter(mag_anom, size=15))
        del mag_anom

        rtp = _clean_band(tf.read(2), nd)
        rtp_hp15 = rtp - uniform_filter(rtp, size=15)
        put_raw(17, rtp_hp15)

        tmi_hg = _clean_band(tf.read(3), nd)
        log_hg = np.log1p(np.maximum(tmi_hg, 0.0))
        put_raw(18, log_hg)
        tmi_vg = _clean_band(tf.read(4), nd)
        put_raw(19, tmi_vg)
        put_raw(20, _clean_band(tf.read(5), nd))
        put_raw(21, np.log1p(np.hypot(np.maximum(tmi_hg, 0.0), tmi_vg)))
        del tmi_hg, tmi_vg

        with rasterio.open(data_dir / "external" / "geodawn_extensions_u8.tif") as gext:
            uk_u8 = gext.read(2).astype(np.float32)
            _, _, up150_gmag = _grad_mag(gext.read(4).astype(np.float32))
        put_raw(22, up150_gmag / (gaussian_filter(log_hg, sigma=2.0) + 0.25))
        del up150_gmag

        worm_mag = _steerable_worm_1500m(log_hg)
        put_raw(23, worm_mag)

        grav = _clean_band(tf.read(6), nd)
        put_raw(24, grav - uniform_filter(grav, size=15))
        put_raw(25, _clean_band(tf.read(7), nd))
        put_raw(26, _clean_band(tf.read(8), nd))
        grav_edge = np.abs(_clean_band(tf.read(9), nd))
        put_raw(27, grav_edge)
        worm_grav = _steerable_worm_1500m(grav_edge)
        put_raw(28, worm_grav)

        depth_base = _clean_band(tf.read(10), nd)
        put_raw(29, np.log1p(np.maximum(depth_base, 0.0)))
        _, _, base_gmag = _grad_mag(depth_base)
        put_raw(30, np.log1p(base_gmag))
        del depth_base, base_gmag

        det_elev = _clean_band(tf.read(11), nd)
        det_slope = _clean_band(tf.read(12), nd)
        put_raw(12, det_slope - uniform_filter(det_slope, size=15))
        put_raw(13, det_elev - uniform_filter(det_elev, size=7))

        put_raw(33, _clean_band(tf.read(13), nd))
        put_raw(34, _clean_band(tf.read(14), nd))
        gdil = _clean_band(tf.read(15), nd)
        deq = _clean_band(tf.read(16), nd)
        ieq = _clean_band(tf.read(18), nd)
        put_raw(35, gdil + 0.25 * np.log1p(np.maximum(ieq, 0.0)) + 0.15 * np.log1p(np.maximum(deq, 0.0)))
        del gdil, deq, ieq
        cond = _clean_band(tf.read(19), nd)

    # Gallardo & Meju (2004) cross-gradients
    ggx, ggy, ggm = _grad_mag(gaussian_filter(grav, sigma=1.5))
    mgx, mgy, mgm = _grad_mag(gaussian_filter(rtp, sigma=1.5))
    del grav, rtp
    dot_gm = ggx * mgx + ggy * mgy
    cross_gm = ggx * mgy - ggy * mgx
    denom_gm = ggm * mgm + 1e-6
    put_raw(31, np.log1p(ggm * mgm) * (dot_gm * dot_gm / (denom_gm * denom_gm)))
    put_raw(32, np.log1p(np.abs(cross_gm)))
    del dot_gm, cross_gm, denom_gm
    gc.collect()

    # ---- Stage C: Hydrothermal Upflow, Alteration & Geothermometry (Cols 36..43) ----
    with rasterio.open(data_dir / "external" / "geodawn_rad_u8.tif") as grad_r:
        rad_k = grad_r.read(1).astype(np.float32)
        rad_th = grad_r.read(2).astype(np.float32)
    k_th = rad_k / (rad_th + 10.0)
    del rad_k, rad_th
    k_th_hp = k_th - uniform_filter(k_th, size=21)
    del k_th
    put_raw(36, k_th_hp)
    put_raw(37, uk_u8 - uniform_filter(uk_u8, size=21))
    del uk_u8
    put_raw(38, np.log1p(np.maximum(-rtp_hp15, 0.0) * log_hg))
    del rtp_hp15
    _, _, cond_gm = _grad_mag(gaussian_filter(cond, sigma=1.5))
    put_raw(39, np.log1p(cond_gm) + 0.5 * (cond - uniform_filter(cond, size=21)))
    del cond, cond_gm

    ws_temp, ws_geo = _load_wellspring_plumes(data_dir, shape)
    probe_2m = _load_2m_probes(data_dir / "external" / "2m_temperature_probe_INGENIOUS_regional_data.zip", transform, shape)
    paleo_vent = _load_paleo_vents(data_dir, transform, shape)
    put_raw(40, ws_temp)
    put_raw(41, ws_geo)
    put_raw(42, probe_2m)
    put_raw(43, paleo_vent)
    del ws_geo, paleo_vent
    gc.collect()

    # ---- Stage D: Coupling & Confounder Guards (Cols 44..47) ----
    egx, egy, egm = _grad_mag(gaussian_filter(det_elev, sigma=1.5))
    del det_elev
    sub_gx = ggx / (ggm + 1e-5) + mgx / (mgm + 1e-5)
    sub_gy = ggy / (ggm + 1e-5) + mgy / (mgm + 1e-5)
    del ggx, ggy, ggm, mgx, mgy, mgm
    sub_gm = np.hypot(sub_gx, sub_gy) + 1e-5
    cos2_ts = ((egx * sub_gx + egy * sub_gy) / ((egm + 1e-5) * sub_gm)) ** 2
    del sub_gx, sub_gy, sub_gm
    put_raw(44, seamless_scarp * cos2_ts * _pct_rank_2d(worm_mag + worm_grav, foot))
    del cos2_ts

    jxx = gaussian_filter(egx * egx, sigma=3.0)
    jxy = gaussian_filter(egx * egy, sigma=3.0)
    jyy = gaussian_filter(egy * egy, sigma=3.0)
    del egx, egy, egm
    coh_st = np.hypot(jxx - jyy, 2.0 * jxy) / (jxx + jyy + 1e-5)
    strike_rad = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy) + 0.5 * np.pi
    del jxx, jxy, jyy
    fav = np.maximum(np.cos(strike_rad - np.deg2rad(72.0)) ** 2, np.cos(strike_rad - np.deg2rad(125.0)) ** 2)
    del strike_rad
    put_raw(45, coh_st * fav)
    del coh_st, fav

    sub_weak = 1.0 - _pct_rank_2d(log_hg + grav_edge, foot)
    del log_hg, grav_edge
    playa_flat = 1.0 / (1.0 + det_slope + 0.2 * t10_p90)
    del det_slope, t10_p90
    put_raw(46, seamless_scarp * sub_weak * (0.5 + 0.5 * maximum_filter(playa_flat, size=9)))
    del sub_weak, playa_flat

    # 2nd-highest quantile across (morph, mag, grav, hydro) in 1D footprint space (zero 3D stack allocation!)
    qm_1d = seamless_scarp.ravel()[fp_idx]
    qmag_1d = fast_pct_rank_1d(worm_mag.ravel()[fp_idx])
    qgrv_1d = fast_pct_rank_1d(worm_grav.ravel()[fp_idx])
    qhyd_1d = fast_pct_rank_1d((np.abs(k_th_hp) + ws_temp + probe_2m).ravel()[fp_idx])
    del seamless_scarp, worm_mag, worm_grav, k_th_hp, ws_temp, probe_2m
    stack1d = np.column_stack([qm_1d, qmag_1d, qgrv_1d, qhyd_1d])
    X[:, 47] = np.partition(stack1d, 2, axis=1)[:, 2].astype(np.float16)
    del stack1d, qm_1d, qmag_1d, qgrv_1d, qhyd_1d
    gc.collect()

    np.save(f16_path, X)
    np.save(idx_path, fp_idx)
    return X, fp_idx
