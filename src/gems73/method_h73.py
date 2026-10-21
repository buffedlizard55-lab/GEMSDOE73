"""Lane H73: 4-Line Corroborated Piedmont/Fluvial-Knickzone/Hydrothermal/Dip-Projected
Out-of-Fold Multi-Physics Inversion & Exact 300 m Submodular Max-Cover.

Strict invariants enforced across every function in this module:
  1. Zero historical submission or registry prediction rasters are read anywhere here.
  2. `sgmc_faults_100m.tif` is NEVER added to the feature matrix `X46`; it is used
     strictly to construct out-of-fold structural targets in held-in training quadrants.
  3. Label-derived distance columns (e.g., `dist_known_fault_px`) in external CSVs
     are explicitly blocked and asserted unused.
  4. Fixes IR-73-04 (`dem10_chi_100m_i16.tif` int16 `-32768` nodata handling on non-channel cells)
     and IR-P5-2 (per-quadrant rank calibration of fold-visible mechanical transfer features).
"""
from __future__ import annotations

import csv
import gc
import heapq
import io
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from gems57 import holdout

FORBIDDEN_POINT_COLUMNS = frozenset({"dist_known_fault_px", "known_fault", "label"})

# Exact positive support of the competition's 300 m (3.0 px) triangular kernel on a 100 m grid:
# K(dy, dx) = max(0, 1 - hypot(dy, dx) / 3.0) for hypot(dy, dx) < 3.0 (21 pixels inside 5x5).
KERNEL_300M: tuple[tuple[int, int, float], ...] = tuple(
    (dy, dx, float(1.0 - np.hypot(dy, dx) / 3.0))
    for dy in range(-2, 3)
    for dx in range(-2, 3)
    if np.hypot(dy, dx) < 3.0
)

H73_STATIC_FEATURE_NAMES: tuple[str, ...] = (
    # --- Official 19-band localized & raw physical channels (25 features: 0..24) ---
    "b01_mag_anom_hp",
    "b02_rtp_hp",
    "b03_tmi_hg",
    "b04_geod_2ndinv",
    "b05_iso_grav_slope",
    "b06_tc",
    "b07_geod_shearrate",
    "b08_geod_dilaterate",
    "b09_tmi_vg",
    "b10_deq",
    "b11_iso_grav_vg",
    "b12_det_elev_hp8",
    "b13_iso_grav_hp8",
    "b15_depth_base",
    "b15_basement_grad",
    "b16_ieq",
    "b16_ieq_grad",
    "b17_cond_surf",
    "b17_cond_grad",
    "b18_iso_grav_hg",
    "b19_det_elev_slope",
    "ms_ridge_100m",
    "crossgrad_align",
    "crossgrad_ortho",
    "anderson_strike_fav",
    # --- USGS 3DEP 1 m LiDAR scarp stack (4 features: 25..28, NaN outside valid LiDAR) ---
    "lidar_scarp_dipole",
    "lidar_step_max",
    "lidar_lap_curv",
    "lidar_coh_cross",
    # --- USGS 3DEP 10 m seamless DEM derived stack across 100% of AOI (5 features: 29..33) ---
    "topo10_slope_std",
    "topo10_curv_prof",
    "topo10_hs_lineament",
    "topo10_slope_p90",
    "topo10_relief_hp",
    # --- GeoDAWN radiometrics, shallow demagnetization & GDR 1391 thermal conduits (4 features: 34..37) ---
    "rad_alteration_edge",
    "demag_shallow",
    "hydro_conduit_near",
    "hydro_conduit_far",
    # --- Novel H73 Relief-Normalized Scarp, Fluvial Chi/ksn, Decontamination & Dip-Projected Channels (8 features: 38..45) ---
    "h73_lidar_relief_norm_scarp_asymm",
    "h73_dem10_onesided3_piedmont",
    "h73_dem10_steep_ratio_max",
    "h73_fluvial_chi_knickzone_piedmont",
    "h73_hydro_hangingwall_ponding_grad",
    "h73_pluvial_shoreline_contour_mimic",
    "h73_tiger_road_embankment_deconf",
    "h73_anderson60_dip_projected_basement_step",
)

H73_FOLD_MECHANICAL_NAMES: tuple[str, ...] = (
    "vis_crack_tip_lobe",
    "vis_host_len_prox",
    "vis_relay_stepover_annulus",
)

H73_ALL_FEATURE_NAMES: tuple[str, ...] = H73_STATIC_FEATURE_NAMES + H73_FOLD_MECHANICAL_NAMES
N_STATIC_FEATURES = len(H73_STATIC_FEATURE_NAMES)  # 46
N_TOTAL_FEATURES = len(H73_ALL_FEATURE_NAMES)      # 49


def clean_band(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Replace non-finite / sentinel values with median over valid cells for safe filtering."""
    out = arr.astype(np.float32, copy=False)
    good = np.isfinite(out) & (out > -1e30) & valid
    med = float(np.median(out[good])) if good.any() else 0.0
    return np.where(good, out, med).astype(np.float32)


def rank01_domain(values: np.ndarray) -> np.ndarray:
    """Tie-averaged empirical quantile rank in (0, 1] on a 1D finite float vector."""
    v = np.asarray(values, dtype=np.float64)
    n = v.size
    if n == 0:
        return np.empty(0, dtype=np.float32)
    if np.ptp(v) == 0.0:
        return np.full(n, 0.5, dtype=np.float32)
    return (rankdata(v, method="average") / float(n)).astype(np.float32)


def rank_by_quad(vec: np.ndarray, quad_v: np.ndarray) -> np.ndarray:
    """Per-quadrant rank calibration in (0, 1] preventing inter-quadrant base-rate shift (IR-P5-2)."""
    out = np.empty_like(vec, dtype=np.float32)
    for q in range(4):
        m = quad_v == q
        out[m] = rank01_domain(vec[m])
    return out


def structure_tensor_ridge_and_strike(
    slope_field: np.ndarray, valid: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Multi-scale edge magnitude x axial coherence + Anderson (1905) strike favorability."""
    f = clean_band(slope_field, valid)
    ms = np.zeros_like(f, dtype=np.float32)
    for sig in (1.0, 2.0, 3.5):
        sm = ndi.gaussian_filter(f, sigma=sig)
        gy, gx = np.gradient(sm)
        ms += np.hypot(gy, gx).astype(np.float32)
    ms /= 3.0

    sm2 = ndi.gaussian_filter(f, sigma=2.0)
    gy, gx = np.gradient(sm2)
    jxx = ndi.gaussian_filter((gx * gx).astype(np.float32), sigma=3.0)
    jyy = ndi.gaussian_filter((gy * gy).astype(np.float32), sigma=3.0)
    jxy = ndi.gaussian_filter((gx * gy).astype(np.float32), sigma=3.0)
    denom = jxx + jyy + 1e-12
    coh = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0)) / denom

    theta = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    normal_az = (np.rad2deg(np.arctan2(np.cos(theta), -np.sin(theta))) + 360.0) % 180.0
    strike_az = (normal_az + 90.0) % 180.0

    diff_norm = np.minimum(np.abs(strike_az - 18.0), 180.0 - np.abs(strike_az - 18.0))
    diff_tran = np.minimum(np.abs(strike_az - 145.0), 180.0 - np.abs(strike_az - 145.0))
    fav = coh * np.maximum(
        np.cos(np.deg2rad(2.0 * diff_norm)),
        0.75 * np.cos(np.deg2rad(2.0 * diff_tran)),
    )
    return (ms * coh).astype(np.float32), fav.astype(np.float32)


def cross_gradient_coupling(
    grav: np.ndarray, rtp: np.ndarray, valid: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Gallardo & Meju (2004) parallel alignment and orthogonal confounder operators."""
    g = ndi.gaussian_filter(clean_band(grav, valid), sigma=2.0)
    m = ndi.gaussian_filter(clean_band(rtp, valid), sigma=2.0)
    ggy, ggx = np.gradient(g)
    mgy, mgx = np.gradient(m)
    ng = np.hypot(ggy, ggx) + 1e-9
    nm = np.hypot(mgy, mgx) + 1e-9
    cos_a = np.abs(ggx * mgx + ggy * mgy) / (ng * nm)
    sin_a = np.abs(ggx * mgy - ggy * mgx) / (ng * nm)
    amp = np.sqrt(ng / (np.median(ng[valid]) + 1e-9) * nm / (np.median(nm[valid]) + 1e-9))
    amp = np.log1p(amp).astype(np.float32)
    return (amp * cos_a).astype(np.float32), (amp * sin_a).astype(np.float32)


def _read_dbf_probes(zip_path: Path, shape: tuple[int, int]) -> np.ndarray:
    """Extract Coolbaugh/INGENIOUS 2 m temperature probe anomalies (F2mDAB >= 1.5 C) to grid."""
    h, w = shape
    grid_pts = np.zeros((h, w), dtype=np.float32)
    if not zip_path.is_file():
        return grid_pts
    with zipfile.ZipFile(zip_path) as z:
        dbf = z.read(
            "2m_temperature_probe_INGENIOUS_regional_data/"
            "2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf"
        )
    nrec, hdrlen, reclen = struct.unpack("<IHH", dbf[4:12])
    fields = []
    off = 32
    while dbf[off] != 0x0D:
        fname = dbf[off : off + 11].split(b"\x00")[0].decode("latin1")
        assert fname not in FORBIDDEN_POINT_COLUMNS, f"Forbidden column {fname}"
        flen = dbf[off + 16]
        fields.append((fname, flen))
        off += 32
    lons, lats, anoms = [], [], []
    pos = hdrlen
    for _ in range(nrec):
        if dbf[pos] == 0x2A:
            pos += reclen
            continue
        p = pos + 1
        row_d = {}
        for fn, fl in fields:
            if fn in ("LatDegreeN", "LongDegree", "F2mDAB"):
                row_d[fn] = dbf[p : p + fl].decode("latin1").strip()
            p += fl
        pos += reclen
        try:
            lat = float(row_d["LatDegreeN"])
            lon = float(row_d["LongDegree"])
            anom = float(row_d["F2mDAB"])
        except (KeyError, ValueError):
            continue
        if np.isfinite(lat) and np.isfinite(lon) and np.isfinite(anom) and anom >= 1.5:
            lons.append(lon)
            lats.append(lat)
            anoms.append(min(anom, 15.0))
    if lons:
        xs, ys = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
        rs = ((4508550.0 - np.asarray(ys)) // 100.0).astype(np.int32)
        cs = ((np.asarray(xs) - 243350.0) // 100.0).astype(np.int32)
        ok = (rs >= 0) & (rs < h) & (cs >= 0) & (cs < w)
        np.add.at(grid_pts, (rs[ok], cs[ok]), np.asarray(anoms, dtype=np.float32)[ok])
    return grid_pts


def _read_paleo_sinter(zip_path: Path, shape: tuple[int, int]) -> np.ndarray:
    """Extract Ayling/INGENIOUS paleo-geothermal sinter/travertine/tufa deposits to grid."""
    h, w = shape
    grid_pts = np.zeros((h, w), dtype=np.float32)
    if not zip_path.is_file():
        return grid_pts
    with zipfile.ZipFile(zip_path) as z:
        txt = z.read("Paleo_geothermal_final.csv").decode("cp1252")
    lons, lats = [], []
    for row in csv.DictReader(io.StringIO(txt)):
        try:
            lon = float(row["Long_deg_NAD83"])
            lat = float(row["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        if np.isfinite(lon) and np.isfinite(lat):
            lons.append(lon)
            lats.append(lat)
    if lons:
        xs, ys = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
        rs = ((4508550.0 - np.asarray(ys)) // 100.0).astype(np.int32)
        cs = ((np.asarray(xs) - 243350.0) // 100.0).astype(np.int32)
        ok = (rs >= 0) & (rs < h) & (cs >= 0) & (cs < w)
        np.add.at(grid_pts, (rs[ok], cs[ok]), 2.0)
    return grid_pts


def _read_thermal_springs(csv_path: Path, shape: tuple[int, int]) -> np.ndarray:
    """Extract DOE GDR 1391 thermal springs/wells & chemical geothermometers (strictly coordinates only;
    NEVER reads dist_known_fault_px to guarantee zero catalogue-distance leakage)."""
    h, w = shape
    grid_pts = np.zeros((h, w), dtype=np.float32)
    if not csv_path.is_file():
        return grid_pts
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        used_cols = ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c", "thermalclass")
        assert set(used_cols).isdisjoint(FORBIDDEN_POINT_COLUMNS)
        for row in reader:
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if not (0 <= r < h and 0 <= c < w):
                continue
            strength = 0.0
            for k, thr in (
                ("temp_c", 25.0),
                ("geothermquartz_c", 80.0),
                ("geothermchalc_c", 70.0),
                ("geothermcat_c", 90.0),
            ):
                val_s = row.get(k, "")
                if val_s:
                    try:
                        val = float(val_s)
                        if np.isfinite(val) and val >= thr:
                            strength = max(strength, 1.0 + min((val - thr) / 50.0, 2.0))
                    except ValueError:
                        pass
            tcls = (row.get("thermalclass") or "").lower()
            if any(tok in tcls for tok in ("hot", "warm", "therm")):
                strength = max(strength, 1.0)
            if strength > 0.0:
                grid_pts[r, c] += strength
    return grid_pts


def tip_kernels(
    fault_mask: np.ndarray, shape: tuple[int, int], mask: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Compute signed along-strike tip continuation distance u and cross-strike distance v."""
    from scipy.spatial import cKDTree

    b = fault_mask > 0
    comp, ncomp = ndi.label(b, structure=np.ones((3, 3), int))
    tips = []
    for cid in range(1, ncomp + 1):
        ys, xs = np.nonzero(comp == cid)
        if ys.size < 8:
            continue
        pts = np.column_stack([ys.astype(np.float64), xs.astype(np.float64)])
        c = pts.mean(0)
        u_svd, s_svd, vt_svd = np.linalg.svd(pts - c, full_matrices=False)
        if s_svd[0] < 3.0:
            continue
        t = vt_svd[0]
        proj = (pts - c) @ t
        i0, i1 = int(np.argmin(proj)), int(np.argmax(proj))
        tips.append((pts[i0, 0], pts[i0, 1], -t[0], -t[1]))
        tips.append((pts[i1, 0], pts[i1, 1], t[0], t[1]))
    if not tips:
        return np.full(shape, 999.0, np.float32), np.full(shape, 999.0, np.float32)
    arr = np.asarray(tips, np.float64)
    tree = cKDTree(arr[:, :2])
    if mask is not None:
        my, mx = np.nonzero(mask)
        q = np.column_stack([my.astype(np.float64), mx.astype(np.float64)])
        _, idx = tree.query(q, k=1)
        ty, tx, dy, dx = arr[idx, 0], arr[idx, 1], arr[idx, 2], arr[idx, 3]
        vy, vx = q[:, 0] - ty, q[:, 1] - tx
        u_out = np.full(shape, 999.0, dtype=np.float32)
        v_out = np.full(shape, 999.0, dtype=np.float32)
        u_out[mask] = (vy * dy + vx * dx).astype(np.float32)
        v_out[mask] = (-vy * dx + vx * dy).astype(np.float32)
        return u_out, v_out
    gy, gx = np.mgrid[0 : shape[0], 0 : shape[1]]
    q = np.column_stack([gy.ravel(), gx.ravel()])
    _, idx = tree.query(q, k=1)
    ty, tx, dy, dx = arr[idx, 0], arr[idx, 1], arr[idx, 2], arr[idx, 3]
    vy, vx = q[:, 0] - ty, q[:, 1] - tx
    u = (vy * dy + vx * dx).reshape(shape).astype(np.float32)
    v = (-vy * dx + vx * dy).reshape(shape).astype(np.float32)
    return u, v


def place_dots_nms(
    score: np.ndarray, allowed: np.ndarray, n: int = 37654, radius_px: float = 2.8
) -> tuple[np.ndarray, int]:
    """Greedy Poisson-disk / distance-prioritized dot placement with exclusion radius `radius_px`."""
    s = np.where(allowed & np.isfinite(score), score, -np.inf)
    flat = s.ravel()
    cand = np.flatnonzero(flat > -np.inf)
    if cand.size > n * 35:
        cand = cand[np.argpartition(flat[cand], -n * 35)[-n * 35 :]]
    order = cand[np.argsort(flat[cand])[::-1]]
    h, w = score.shape
    r = int(np.ceil(radius_px))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    disk = (yy * yy + xx * xx) <= radius_px * radius_px
    dy, dx = yy[disk], xx[disk]
    blocked = np.zeros((h, w), bool)
    out = np.zeros((h, w), np.float32)
    cnt = 0
    for idx in order:
        y, x = int(idx // w), int(idx % w)
        if blocked[y, x]:
            continue
        out[y, x] = 1.0
        cnt += 1
        if cnt >= n:
            break
        ys = np.clip(y + dy, 0, h - 1)
        xs = np.clip(x + dx, 0, w - 1)
        blocked[ys, xs] = True
    return out, cnt


def submodular_pack_300m(
    surface_2d: np.ndarray,
    allowed_2d: np.ndarray,
    target_n: int = 37654,
    support_quantile: float = 0.88,
    gamma: float = 2.0,
    max_candidates: int = 450000,
) -> tuple[np.ndarray, int]:
    """Unblurred exact 300 m kernel lazy-greedy submodular dot packing (Minoux 1978)."""
    h, w = surface_2d.shape
    allow = np.asarray(allowed_2d, dtype=bool)
    vals = surface_2d[allow]
    if vals.size < target_n:
        raise ValueError(f"Allowed support ({vals.size}) smaller than target_n ({target_n})")

    ranks = rank01_domain(vals)
    pos = np.clip((ranks - support_quantile) / max(1.0 - support_quantile, 1e-6), 0.0, 1.0)
    weights_allow = (pos ** gamma).astype(np.float32)
    weights_allow = weights_allow + (1e-5 * ranks).astype(np.float32)

    pad = 2
    hp, wp = h + 2 * pad, w + 2 * pad
    w_pad = np.zeros((hp, wp), dtype=np.float32)
    ay, ax = np.nonzero(allow)
    w_pad[ay + pad, ax + pad] = weights_allow

    g0 = np.zeros((h, w), dtype=np.float32)
    for dy, dx, k in KERNEL_300M:
        g0 += k * w_pad[pad + dy : pad + dy + h, pad + dx : pad + dx + w]

    cand_scores = g0[allow]
    if cand_scores.size > max_candidates:
        part = np.argpartition(cand_scores, -max_candidates)[-max_candidates:]
        part = part[np.argsort(cand_scores[part], kind="mergesort")[::-1]]
    else:
        part = np.argsort(cand_scores, kind="mergesort")[::-1]

    cy = (ay[part] + pad).astype(np.int32)
    cx = (ax[part] + pad).astype(np.int32)
    flat_idx = cy * wp + cx
    init_gains = cand_scores[part]

    heap = [(-float(init_gains[i]), int(flat_idx[i])) for i in range(flat_idx.size)]
    heapq.heapify(heap)
    del g0, cand_scores, part, cy, cx, flat_idx, init_gains

    w_flat = np.ascontiguousarray(w_pad.ravel(), dtype=np.float32)
    cov_flat = np.zeros(hp * wp, dtype=np.float32)
    w_list = memoryview(w_flat)
    cov_list = memoryview(cov_flat)
    off_k = tuple((dy * wp + dx, float(k)) for dy, dx, k in KERNEL_300M)

    dots = np.zeros((h, w), dtype=bool)
    picked = 0
    pop = heapq.heappop
    push = heapq.heappush

    while picked < target_n and heap:
        neg_ub, idx = pop(heap)
        gain = 0.0
        for off, k in off_k:
            j = idx + off
            wj = w_list[j]
            if wj > 0.0:
                rem = k - cov_list[j]
                if rem > 0.0:
                    gain += wj * rem
        if not heap or gain >= -heap[0][0] - 1e-12:
            y = idx // wp - pad
            x = idx % wp - pad
            if not dots[y, x]:
                dots[y, x] = True
                for off, k in off_k:
                    j = idx + off
                    if k > cov_list[j]:
                        cov_list[j] = k
                picked += 1
        elif gain > 0.0:
            push(heap, (-gain, idx))

    del heap, w_list, cov_list, w_flat, cov_flat, w_pad
    gc.collect()
    return dots, picked


def build_or_load_h73_feature_mmap(
    valid: np.ndarray,
    fp: np.ndarray,
    data_dir: Path,
    ext_dir: Path,
    dem10_dir: Path,
    cache_dir: Path,
) -> tuple[np.memmap, np.ndarray]:
    """Build or load the 46-column static physical feature memmap `h73_static46.mmap` and `h73_unsup.npy`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    n_val = int(valid.sum())
    mmap_path = cache_dir / "h73_static46.mmap"
    unsup_path = cache_dir / "h73_unsup.npy"

    if mmap_path.is_file() and unsup_path.is_file() and mmap_path.stat().st_size == n_val * N_STATIC_FEATURES * 4:
        X46 = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n_val, N_STATIC_FEATURES))
        unsup_vec = np.load(unsup_path)
        return X46, unsup_vec

    X = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(n_val, N_STATIC_FEATURES))

    with rasterio.open(data_dir / "training_features.tif") as src:
        b1 = clean_band(src.read(1), valid)
        X[:, 0] = (b1 - ndi.gaussian_filter(b1, sigma=8.0))[valid]
        del b1

        rtp = clean_band(src.read(2), valid)
        X[:, 1] = (rtp - ndi.gaussian_filter(rtp, sigma=8.0))[valid]

        X[:, 2] = clean_band(src.read(3), valid)[valid]
        b4 = clean_band(src.read(4), valid)
        X[:, 3] = (b4 - ndi.gaussian_filter(b4, sigma=12.0))[valid]
        del b4
        X[:, 4] = clean_band(src.read(5), valid)[valid]
        X[:, 5] = clean_band(src.read(6), valid)[valid]
        b7 = clean_band(src.read(7), valid)
        X[:, 6] = (b7 - ndi.gaussian_filter(b7, sigma=12.0))[valid]
        del b7
        b8 = clean_band(src.read(8), valid)
        X[:, 7] = (b8 - ndi.gaussian_filter(b8, sigma=12.0))[valid]
        del b8
        X[:, 8] = clean_band(src.read(9), valid)[valid]
        X[:, 9] = clean_band(src.read(10), valid)[valid]
        X[:, 10] = clean_band(src.read(11), valid)[valid]

        det_el = clean_band(src.read(12), valid)
        X[:, 11] = (det_el - ndi.gaussian_filter(det_el, sigma=8.0))[valid]
        del det_el

        grav = clean_band(src.read(13), valid)
        X[:, 12] = (grav - ndi.gaussian_filter(grav, sigma=8.0))[valid]

        dbase = clean_band(src.read(15), valid)
        X[:, 13] = (dbase - ndi.gaussian_filter(dbase, sigma=12.0))[valid]
        gy, gx = np.gradient(ndi.gaussian_filter(dbase, sigma=2.0))
        X[:, 14] = np.hypot(gy, gx).astype(np.float32)[valid]
        del gy, gx

        ieq = clean_band(src.read(16), valid)
        X[:, 15] = (ieq - ndi.gaussian_filter(ieq, sigma=12.0))[valid]
        gy, gx = np.gradient(ndi.gaussian_filter(ieq, sigma=2.0))
        X[:, 16] = np.hypot(gy, gx).astype(np.float32)[valid]
        del ieq, gy, gx

        cond = clean_band(src.read(17), valid)
        X[:, 17] = (cond - ndi.gaussian_filter(cond, sigma=12.0))[valid]
        gy, gx = np.gradient(ndi.gaussian_filter(cond, sigma=2.0))
        X[:, 18] = np.hypot(gy, gx).astype(np.float32)[valid]
        del cond, gy, gx

        X[:, 19] = clean_band(src.read(18), valid)[valid]
        det_sl = clean_band(src.read(19), valid)
        X[:, 20] = det_sl[valid]

    ms_ridge, strike_fav = structure_tensor_ridge_and_strike(det_sl, valid)
    X[:, 21] = ms_ridge[valid]
    X[:, 24] = strike_fav[valid]
    del det_sl, strike_fav

    cg_align, cg_ortho = cross_gradient_coupling(grav, rtp, valid)
    X[:, 22] = cg_align[valid]
    X[:, 23] = cg_ortho[valid]
    del grav, cg_align

    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as lsrc:
        l_valid = lsrc.read(12) > 0
        upf = lsrc.read(7).astype(np.float32)
        dnf = lsrc.read(6).astype(np.float32)
        exm = lsrc.read(1).astype(np.float32)
        stp = lsrc.read(3).astype(np.float32)
        ln = lsrc.read(4).astype(np.float32)
        lp = lsrc.read(5).astype(np.float32)
        crs = lsrc.read(8).astype(np.float32)
        l_rel = lsrc.read(9).astype(np.float32)
        coh = lsrc.read(10).astype(np.float32)

    dipole = np.maximum(np.maximum(upf, dnf), exm)
    lap_c = 0.5 * (ln + lp)
    coh_x = crs * (coh / 255.0)
    for col_i, arr2d in ((25, dipole), (26, stp), (27, lap_c), (28, coh_x)):
        masked = np.where(l_valid, arr2d, np.nan).astype(np.float32)
        X[:, col_i] = masked[valid]
    lidar_norm = np.where(l_valid, dipole / 255.0, np.nan).astype(np.float32)
    lid_rel_step = np.where(
        l_valid,
        (stp / np.sqrt(l_rel + 9.0)) * (0.4 + 0.6 * (coh / 255.0)) / (crs / 255.0 + 0.15),
        np.nan,
    ).astype(np.float32)
    X[:, 38] = lid_rel_step[valid]
    del l_valid, upf, dnf, exm, stp, ln, lp, crs, l_rel, coh, dipole, lap_c, coh_x, lid_rel_step

    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as tsrc:
        sl_p90 = tsrc.read(1).astype(np.float32)
        sl_std = tsrc.read(4).astype(np.float32)
        rel_loc = tsrc.read(5).astype(np.float32)
        curv_p = tsrc.read(6).astype(np.float32)
        hs_lin = tsrc.read(8).astype(np.float32)

    X[:, 29] = sl_std[valid]
    X[:, 30] = curv_p[valid]
    X[:, 31] = hs_lin[valid]
    X[:, 32] = sl_p90[valid]
    X[:, 33] = (rel_loc - ndi.gaussian_filter(rel_loc, sigma=8.0))[valid]
    rel_m = np.maximum(rel_loc - 1.0, 0.0) / 254.0 * 80.54

    r_ms100 = rank01_domain(ms_ridge[valid])
    r_t10 = rank01_domain((0.40 * sl_std + 0.35 * curv_p + 0.25 * hs_lin)[valid])
    r_ortho = rank01_domain(cg_ortho[valid])
    lid_v = lidar_norm[valid]
    lid_ok = np.isfinite(lid_v)
    r_lid = np.empty_like(r_ms100)
    r_lid[lid_ok] = rank01_domain(lid_v[lid_ok])
    r_lid[~lid_ok] = r_t10[~lid_ok]
    unsup_vec = ((0.40 * r_ms100 + 0.35 * r_t10 + 0.25 * r_lid) * (1.0 - 0.20 * r_ortho)).astype(np.float32)
    np.save(unsup_path, unsup_vec)
    del ms_ridge, cg_ortho, lidar_norm, sl_p90, sl_std, rel_loc, curv_p, hs_lin

    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as esrc:
        thk = esrc.read(1).astype(np.float32)
        uk = esrc.read(2).astype(np.float32)
        tmi150 = esrc.read(4).astype(np.float32)
    rad_valid = thk > 0
    thk_s = ndi.gaussian_filter(np.where(rad_valid, thk, float(np.median(thk[rad_valid]))), sigma=1.5)
    uk_s = ndi.gaussian_filter(np.where(rad_valid, uk, float(np.median(uk[rad_valid]))), sigma=1.5)
    gy1, gx1 = np.gradient(thk_s)
    gy2, gx2 = np.gradient(uk_s)
    alt_edge = np.hypot(gy1, gx1) + np.hypot(gy2, gx2)
    X[:, 34] = np.where(rad_valid, alt_edge, np.nan).astype(np.float32)[valid]

    t150_ok = tmi150 > 0
    rtp_z = (rtp - float(np.mean(rtp[valid]))) / (float(np.std(rtp[valid])) + 1e-6)
    t150_m = np.where(t150_ok, tmi150, float(np.mean(tmi150[t150_ok])))
    t150_z = (t150_m - float(np.mean(t150_m[valid]))) / (float(np.std(t150_m[valid])) + 1e-6)
    X[:, 35] = np.where(t150_ok, t150_z - rtp_z, np.nan).astype(np.float32)[valid]
    del thk, uk, tmi150, rtp, rtp_z, t150_m, t150_z, alt_edge, gy1, gx1, gy2, gx2

    pts = (
        _read_thermal_springs(ext_dir / "gdr_wellspring_in_footprint.csv", valid.shape)
        + _read_dbf_probes(ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip", valid.shape)
        + _read_paleo_sinter(ext_dir / "paleo_geothermal_regional.zip", valid.shape)
    )
    X[:, 36] = np.log1p(ndi.gaussian_filter(pts, sigma=4.0) * 10.0).astype(np.float32)[valid]
    X[:, 37] = np.log1p(ndi.gaussian_filter(pts, sigma=12.0) * 25.0).astype(np.float32)[valid]
    del pts

    onesided3_2d = np.zeros(fp.shape, dtype=np.float32)
    onesided3_2d[fp] = np.nan_to_num(np.load(dem10_dir / "dem10_onesided3.f32.npy"), nan=0.0)
    X[:, 39] = (onesided3_2d / np.sqrt(rel_m + 9.0)).astype(np.float32)[valid]
    del onesided3_2d

    steep_ratio_2d = np.zeros(fp.shape, dtype=np.float32)
    steep_ratio_2d[fp] = np.nan_to_num(np.load(dem10_dir / "dem10_steep_ratio_max.f32.npy"), nan=0.0)
    X[:, 40] = steep_ratio_2d[valid]
    del steep_ratio_2d

    # Fluvial chi/ksn knickzone halo (IR-73-04 nodata -32768 fixed), raised ponding, pluvial shoreline mimic
    with rasterio.open(ext_dir / "dem10_chi_100m_i16.tif") as csrc:
        c_step = csrc.read(1)
        c_ksn = csrc.read(3)
        c_z = csrc.read(5).astype(np.float32)
    with rasterio.open(ext_dir / "dem10_chi_100m_u8.tif") as cusrc:
        c_knick_n = cusrc.read(2).astype(np.float32)
        c_raised_n = cusrc.read(3).astype(np.float32)

    step_clean = np.where(c_step > -30000, np.maximum(c_step.astype(np.float32), 0.0) / 1000.0, 0.0)
    ksn_clean = np.where(c_ksn > -30000, np.maximum(c_ksn.astype(np.float32), 0.0), 0.0)
    knick_pied = ndi.gaussian_filter(
        (step_clean * np.log1p(ksn_clean) + 0.35 * c_knick_n) / np.sqrt(rel_m + 9.0),
        sigma=3.5,
    ).astype(np.float32)
    X[:, 41] = knick_pied[valid]
    del c_step, c_ksn, c_knick_n, step_clean, ksn_clean, knick_pied

    raised_pond = (ndi.gaussian_filter(c_raised_n, sigma=3.0) - ndi.gaussian_filter(c_raised_n, sigma=10.0)).astype(np.float32)
    X[:, 42] = raised_pond[valid]
    del c_raised_n, raised_pond

    z_clean = clean_band(c_z, valid)
    d_shore = np.minimum(
        np.abs(z_clean - 1330.0),
        np.minimum(np.abs(z_clean - 1235.0), np.minimum(np.abs(z_clean - 1463.0), np.abs(z_clean - 1552.0))),
    )
    z_g3 = ndi.gaussian_filter(z_clean, sigma=3.0)
    z_std3 = np.sqrt(np.maximum(0.0, ndi.gaussian_filter(z_clean * z_clean, sigma=3.0) - z_g3 * z_g3))
    pluvial_mimic = (np.exp(-((d_shore / 22.0) ** 2)) * np.exp(-((z_std3 / 3.0) ** 2))).astype(np.float32)
    X[:, 43] = pluvial_mimic[valid]
    del c_z, z_clean, d_shore, z_g3, z_std3, pluvial_mimic, rel_m

    with rasterio.open(ext_dir / "tiger_road_distance_m.tif") as rsrc:
        d_road = rsrc.read(1).astype(np.float32)
    d_road = np.where(np.isfinite(d_road) & (d_road >= 0), d_road, 5000.0).astype(np.float32)
    X[:, 44] = np.clip(d_road / 250.0, 0.0, 1.0).astype(np.float32)[valid]
    del d_road

    db_sm = ndi.gaussian_filter(dbase, sigma=2.0)
    gy_b, gx_b = np.gradient(db_sm)
    del db_sm
    grad_b = np.hypot(gy_b, gx_b).astype(np.float32)
    norm_b = grad_b + 1e-6
    uy_b, ux_b = (-gy_b / norm_b).astype(np.float32), (-gx_b / norm_b).astype(np.float32)
    del gy_b, gx_b, norm_b
    yy, xx = np.indices(fp.shape, dtype=np.float32)
    shift_px = np.clip(dbase * 0.57735 / 100.0, 0.0, 12.0)
    del dbase
    src_y = np.clip(np.round(yy - shift_px * uy_b).astype(np.int32), 0, fp.shape[0] - 1)
    src_x = np.clip(np.round(xx - shift_px * ux_b).astype(np.int32), 0, fp.shape[1] - 1)
    del yy, xx, shift_px, uy_b, ux_b
    dip_proj_base = ndi.gaussian_filter(grad_b[src_y, src_x], sigma=2.0).astype(np.float32)
    del grad_b, src_y, src_x
    X[:, 45] = dip_proj_base[valid]
    del dip_proj_base

    X.flush()
    del X
    gc.collect()
    X46 = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n_val, N_STATIC_FEATURES))
    return X46, unsup_vec


def compute_fold_mechanical_channels(
    vis_mask: np.ndarray, valid: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute 3 fold-proper visible-catalogue mechanical vectors on `valid` + 2D distance `d_vis`."""
    vis = np.asarray(vis_mask, dtype=bool)
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    u_v, v_v = tip_kernels(vis, vis.shape, mask=valid)
    tip_v = np.where(
        np.isfinite(u_v[valid]),
        np.exp(-np.clip(u_v[valid], 0.0, None) / 22.0) * np.exp(-np.abs(v_v[valid]) / 7.5),
        0.0,
    ).astype(np.float32)
    del u_v, v_v

    comp, _ = ndi.label(vis, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(comp.ravel())
    sizes[0] = 0
    len_on_vis = sizes[comp].astype(np.float32)
    _, inds = ndi.distance_transform_edt(~vis, return_indices=True)
    nearest_len = len_on_vis[inds[0], inds[1]]
    host_v = (np.log1p(nearest_len) * np.exp(-d_vis / 16.0)).astype(np.float32)[valid]
    del comp, sizes, len_on_vis, inds, nearest_len

    collar_t = np.clip((d_vis - 2.1) / 2.0, 0.0, 1.0).astype(np.float32)
    relay_v = (
        np.maximum(
            0.0,
            ndi.gaussian_filter(vis.astype(np.float32), 8.5)
            - 0.55 * ndi.gaussian_filter(vis.astype(np.float32), 2.5),
        )
        * collar_t
    ).astype(np.float32)[valid]
    return tip_v, host_v, relay_v, d_vis


def run_all_49_leakage_canaries(
    X46: np.memmap,
    valid: np.ndarray,
    folds_spec: list[dict[str, Any]],
    cat: np.ndarray,
    proxy_prime: np.ndarray,
    max_neg: int = 200000,
) -> dict[str, Any]:
    """Protocol Rule 4: audit all 46 static features + 3 fold-visible mechanical features individually."""
    tip_a0, host_a0, rel_a0, _ = compute_fold_mechanical_channels(folds_spec[0]["visible"], valid)
    tip_cat, host_cat, rel_cat, _ = compute_fold_mechanical_channels(cat, valid)

    def eval_on_truth(
        truth_on_valid: np.ndarray,
        domain_on_valid: np.ndarray,
        mech_tuple: tuple[np.ndarray, np.ndarray, np.ndarray],
        seed: int,
    ) -> dict[str, dict[str, Any]]:
        pos_idx = np.flatnonzero(truth_on_valid & domain_on_valid)
        neg_pool = np.flatnonzero((~truth_on_valid) & domain_on_valid)
        rng = np.random.default_rng(seed)
        neg_idx = np.sort(rng.choice(neg_pool, min(max_neg, neg_pool.size), replace=False))
        sample = np.concatenate([pos_idx, neg_idx])
        y = np.concatenate([np.ones(pos_idx.size, np.int8), np.zeros(neg_idx.size, np.int8)])
        X_sub = np.asarray(X46[sample, :], dtype=np.float32)

        out: dict[str, dict[str, Any]] = {}
        for j, name in enumerate(H73_STATIC_FEATURE_NAMES):
            col = X_sub[:, j]
            fin = np.isfinite(col)
            if fin.sum() < 100 or y[fin].min() == y[fin].max() or np.ptp(col[fin]) == 0.0:
                auc = 0.5
            else:
                auc = float(roc_auc_score(y[fin], col[fin]))
            sym = float(max(auc, 1.0 - auc))
            out[name] = {
                "auc": round(auc, 6),
                "symmetric_auc": round(sym, 6),
                "finite_fraction": round(float(fin.mean()), 6),
                "n_positive": int(y[fin].sum()),
                "suspected_leakage": bool(sym > 0.90),
            }
        for m_name, m_vec in zip(H73_FOLD_MECHANICAL_NAMES, mech_tuple):
            col = m_vec[sample]
            fin = np.isfinite(col)
            auc = float(roc_auc_score(y[fin], col[fin])) if fin.sum() >= 100 and np.ptp(col[fin]) > 0 else 0.5
            sym = float(max(auc, 1.0 - auc))
            out[m_name] = {
                "auc": round(auc, 6),
                "symmetric_auc": round(sym, 6),
                "finite_fraction": round(float(fin.mean()), 6),
                "n_positive": int(y[fin].sum()),
                "suspected_leakage": bool(sym > 0.90),
            }
        return out

    dom_a0 = (folds_spec[0]["region"] & valid & (~folds_spec[0]["visible"]))[valid]
    dom_bp = (~cat)[valid]
    canary_a0 = eval_on_truth((folds_spec[0]["truth"] & valid)[valid], dom_a0, (tip_a0, host_a0, rel_a0), seed=7305)
    canary_bp = eval_on_truth((proxy_prime & valid)[valid], dom_bp, (tip_cat, host_cat, rel_cat), seed=7306)
    leaks_a = [k for k, v in canary_a0.items() if v["suspected_leakage"]]
    leaks_bp = [k for k, v in canary_bp.items() if v["suspected_leakage"]]
    return {
        "n_features_audited": N_TOTAL_FEATURES,
        "threshold_symmetric_auc": 0.90,
        "max_symmetric_auc_instrument_a_fold0": max(v["symmetric_auc"] for v in canary_a0.values()),
        "max_symmetric_auc_instrument_b_prime": max(v["symmetric_auc"] for v in canary_bp.items() if False)
        if False
        else max(v["symmetric_auc"] for v in canary_bp.values()),
        "leaks_a": leaks_a,
        "leaks_b_prime": leaks_bp,
        "all_clean": len(leaks_a) == 0 and len(leaks_bp) == 0,
        "per_feature_a_fold0": canary_a0,
        "per_feature_b_prime": canary_bp,
    }
