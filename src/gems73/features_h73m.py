"""GEMSDOE73 multi-physics feature engineering & fold-safe transtensional mechanics (H73-M).

Strict invariants enforced across every function in this module:
  1. Zero historical submission or registry prediction rasters are read anywhere here.
  2. `sgmc_faults_100m.tif` is NEVER added to `X`; it is loaded separately in the
     experiment runner strictly to construct out-of-fold held-in structural targets
     and report-only proxy evaluations.
  3. Columns encoding catalogue distance (`dist_known_fault_px`, `known_fault`, `label`)
     in external point CSVs are explicitly blocked and asserted unused.
  4. All 82 physical features are streamed band-by-band into a disk-backed `np.memmap`
     on the 5,167,373 footprint pixels so peak RSS stays well below 3.8 GiB.
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

from .surface import chain_occupancy, norm as pnorm

FORBIDDEN_POINT_COLUMNS = frozenset({"dist_known_fault_px", "known_fault", "label"})

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
    "chi_step_max",
    "chi_step_min",
    "chi_ksn_max",
    "chi_log10_area",
    "chi_zmean_m",
]


def _grad_mag(arr: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    sm = gaussian_filter(arr.astype(np.float32), sigma=sigma)
    gy, gx = np.gradient(sm)
    return np.hypot(gy, gx).astype(np.float32)


def _utm_to_rc(
    xs: list[float] | np.ndarray,
    ys: list[float] | np.ndarray,
    transform: Any,
    shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_arr = np.asarray(xs, dtype=np.float64)
    y_arr = np.asarray(ys, dtype=np.float64)
    cols = np.floor((x_arr - transform.c) / transform.a).astype(np.int64)
    rows = np.floor((y_arr - transform.f) / transform.e).astype(np.int64)
    ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    return rows[ok], cols[ok], ok


def _parse_2m_probes_dbf(zip_path: Path, transform: Any, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Read INGENIOUS 2-meter temperature probes (T2m, F2mDAB) using pure stdlib struct."""
    imp_dab = np.zeros(shape, dtype=np.float32)
    imp_cnt = np.zeros(shape, dtype=np.float32)
    if not zip_path.is_file():
        return imp_dab, imp_cnt
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
            lat_s = rec[fmap["LatDegreeN"][0] : fmap["LatDegreeN"][0] + fmap["LatDegreeN"][1]].strip()
            lon_s = rec[fmap["LongDegree"][0] : fmap["LongDegree"][0] + fmap["LongDegree"][1]].strip()
            dab_s = rec[fmap["F2mDAB"][0] : fmap["F2mDAB"][0] + fmap["F2mDAB"][1]].strip()
            t2m_s = rec[fmap["T2m"][0] : fmap["T2m"][0] + fmap["T2m"][1]].strip()
            lat = float(lat_s)
            lon = float(lon_s)
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
        rows, cols, ok = _utm_to_rc(ux, uy, transform, shape)
        vals = np.asarray(dabs, dtype=np.float32)[ok]
        np.add.at(imp_cnt, (rows, cols), 1.0)
        np.maximum.at(imp_dab, (rows, cols), vals)
    return imp_dab, imp_cnt


def build_feature_memmap(
    mmap_path: Path,
    fp: np.ndarray,
    transform: Any,
    data_dir: Path,
) -> tuple[np.memmap, list[str], np.ndarray, dict[str, Any]]:
    """Stream-extract all 82 label-free physical features into a disk-backed float32 memmap.

    Returns `(X_mmap, feature_names, has_lidar_fp, provenance_meta)`.
    """
    ext_dir = data_dir / "external"
    shape = fp.shape
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    names: list[str] = []

    total_cols = 82
    meta_path = mmap_path.with_suffix(".meta.json")
    if mmap_path.is_file() and meta_path.is_file():
        cached_meta = json.loads(meta_path.read_text())
        if cached_meta.get("n_features") == total_cols and cached_meta.get("n_footprint_pixels") == n_fp:
            X = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(total_cols, n_fp))
            has_lidar_fp = np.asarray(X[cached_meta["feature_names"].index("lidar_has_coverage"), :] > 0.5)
            return X, cached_meta["feature_names"], has_lidar_fp, cached_meta["meta"]

    mmap_path.parent.mkdir(parents=True, exist_ok=True)
    X = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(total_cols, n_fp))
    col_ptr = 0

    bad_fp = ~fp
    idx_fp = distance_transform_edt(bad_fp, return_distances=False, return_indices=True)
    idx_cache: list[tuple[np.ndarray, np.ndarray]] = [(bad_fp, idx_fp)]

    def _fast_fill(arr: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
        bad = ~valid_mask
        if not bad.any():
            return arr.astype(np.float32, copy=False)
        found_idx = None
        for prev_bad, prev_idx in idx_cache:
            if np.array_equal(bad, prev_bad):
                found_idx = prev_idx
                break
        if found_idx is None:
            found_idx = distance_transform_edt(bad, return_distances=False, return_indices=True)
            if len(idx_cache) < 5:
                idx_cache.append((bad.copy(), found_idx))
        out = arr.astype(np.float32, copy=True)
        out[bad] = out[found_idx[0][bad], found_idx[1][bad]]
        return out

    def _push(name: str, arr2d_or_1d: np.ndarray, is_fp_1d: bool = False) -> None:
        nonlocal col_ptr
        assert name not in FORBIDDEN_POINT_COLUMNS, f"Forbidden feature {name}"
        vec = arr2d_or_1d if is_fp_1d else arr2d_or_1d.ravel()[fp_idx]
        X[col_ptr, :] = vec.astype(np.float32, copy=False)
        names.append(name)
        col_ptr += 1

    # 1. Official 19-band training_features.tif + 8 geopotential & strain derivatives
    saved_bands: dict[str, np.ndarray] = {}
    with rasterio.open(data_dir / "training_features.tif") as ds:
        for b_idx, b_name in enumerate(TF_BAND_NAMES, start=1):
            raw = ds.read(b_idx).astype(np.float32)
            fin = fp & np.isfinite(raw) & (raw > -1e30)
            filled = _fast_fill(raw, fin)
            _push(b_name, filled)
            if b_name in (
                "iso_grav_anom_hg",
                "tmi_hg",
                "tmi_vg",
                "depth_to_base_surf",
                "cond_surf",
                "det_elev",
                "geod_shearrate",
                "geod_dilaterate",
            ):
                saved_bands[b_name] = filled

    _push("grav_hg_worm", saved_bands["iso_grav_anom_hg"] - gaussian_filter(saved_bands["iso_grav_anom_hg"], 8.0))
    _push("mag_hg_worm", saved_bands["tmi_hg"] - gaussian_filter(saved_bands["tmi_hg"], 8.0))
    _push("basement_grad", _grad_mag(saved_bands["depth_to_base_surf"], 1.5))
    _push("basement_curv", saved_bands["depth_to_base_surf"] - gaussian_filter(saved_bands["depth_to_base_surf"], 8.0))
    _push("cond_grad", _grad_mag(saved_bands["cond_surf"], 1.5))
    _push("det_elev_lrm", saved_bands["det_elev"] - gaussian_filter(saved_bands["det_elev"], 6.0))

    # GEMSDOE73 New Feature 1 & 2: Magnetic Tilt Derivative & Upward-Continued Width Ratio
    tmi_analytic = np.hypot(saved_bands["tmi_hg"], saved_bands["tmi_vg"]).astype(np.float32)
    mag_tilt = np.arctan2(saved_bands["tmi_vg"], np.abs(saved_bands["tmi_hg"]) + np.float32(1e-3)).astype(np.float32)
    mag_width = np.clip(
        gaussian_filter(tmi_analytic, 3.0) / (gaussian_filter(tmi_analytic, 1.0) + np.float32(1e-3)),
        0.0,
        3.0,
    ).astype(np.float32)
    _push("mag_tilt_derivative", mag_tilt)
    _push("mag_upward_width_ratio", mag_width)
    del tmi_analytic, mag_tilt, mag_width

    strain_transtens = np.hypot(saved_bands["geod_dilaterate"], saved_bands["geod_shearrate"]).astype(np.float32)
    cond_norm = pnorm(saved_bands["cond_surf"], fp)
    saved_bands.clear()

    # 2. 1m 3DEP LiDAR scarp features (native NaN outside 1m LiDAR coverage) + Polarity & 16-Azimuth Chain
    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as ds:
        has_lidar_2d = (ds.read(12) > 0) & fp
        has_lidar_fp = has_lidar_2d.ravel()[fp_idx]
        _push("lidar_has_coverage", has_lidar_fp.astype(np.float32), is_fp_1d=True)
        lidar_cache: dict[str, np.ndarray] = {}
        for b_idx, b_name in enumerate(LIDAR_BAND_NAMES, start=1):
            raw_b = ds.read(b_idx).astype(np.float32)
            v_fp = raw_b.ravel()[fp_idx].copy()
            v_fp[~has_lidar_fp] = np.nan
            _push(b_name, v_fp, is_fp_1d=True)
            if b_name in ("lidar_step_max", "lidar_lapneg_max", "lidar_lappos_max", "lidar_relief", "lidar_downface_max", "lidar_upface_max"):
                lidar_cache[b_name] = v_fp
            if b_name == "lidar_step_max":
                step_2d = raw_b

        dipole = np.sqrt(np.maximum(0.0, lidar_cache["lidar_lapneg_max"] * lidar_cache["lidar_lappos_max"]))
        sharpness = lidar_cache["lidar_step_max"] / (lidar_cache["lidar_relief"] + 5.0)
        # GEMSDOE73 New Feature 3: One-sided scarp polarity |D - U| / (D + U + 1)
        polarity = np.abs(lidar_cache["lidar_downface_max"] - lidar_cache["lidar_upface_max"]) / (
            np.abs(lidar_cache["lidar_downface_max"]) + np.abs(lidar_cache["lidar_upface_max"]) + 1.0
        )
        _push("lidar_crest_toe_dipole", dipole, is_fp_1d=True)
        _push("lidar_scarp_sharpness", sharpness, is_fp_1d=True)
        _push("lidar_scarp_polarity", polarity.astype(np.float32), is_fp_1d=True)
        lidar_cache.clear()

    # 3. Seamless 10m 3DEP topographic breaklines (100% footprint coverage) + 16-azimuth chain
    topo_cache: dict[str, np.ndarray] = {}
    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as ds:
        for b_idx, b_name in enumerate(TOPO10_BAND_NAMES, start=1):
            q = ds.read(b_idx)
            fin = fp & (q > 0)
            filled = _fast_fill(q.astype(np.float32), fin)
            _push(b_name, filled)
            if b_name in ("topo10_hs_lineament", "topo10_curv_prof_absmax"):
                topo_cache[b_name] = filled
    _push("topo10_hs_dog", topo_cache["topo10_hs_lineament"] - gaussian_filter(topo_cache["topo10_hs_lineament"], 6.0))
    _push(
        "topo10_curv_dog",
        topo_cache["topo10_curv_prof_absmax"] - gaussian_filter(topo_cache["topo10_curv_prof_absmax"], 6.0),
    )

    # GEMSDOE73 New Feature 4: 16-azimuth 1.3 km scarp skeleton chain occupancy
    scarp_hybrid = np.where(has_lidar_2d, pnorm(step_2d, has_lidar_2d), pnorm(topo_cache["topo10_curv_prof_absmax"], fp))
    thr90 = float(np.percentile(scarp_hybrid[fp], 90.0))
    skel = (scarp_hybrid >= thr90) & fp
    chain_16az = chain_occupancy(skel, half_len=6, n_az=16)
    _push("scarp_chain_occ_16az", chain_16az)
    del step_2d, scarp_hybrid, skel, chain_16az

    curv10 = topo_cache["topo10_curv_prof_absmax"].copy()
    topo_cache.clear()

    # 4. Fluvial tectonic geomorphology (chi, ksn, drainage area, zmean) + pluvial shoreline rejectors
    with rasterio.open(ext_dir / "dem10_chi_100m_i16.tif") as ds:
        ksn_arr = None
        z_arr = None
        for b_idx, b_name in enumerate(CHI_BAND_NAMES, start=1):
            arr = _fast_fill(ds.read(b_idx).astype(np.float32), fp)
            _push(b_name, arr)
            if b_name == "chi_ksn_max":
                ksn_arr = arr
            elif b_name == "chi_zmean_m":
                z_arr = arr
    assert ksn_arr is not None and z_arr is not None
    _push("chi_ksn_dog", ksn_arr - gaussian_filter(ksn_arr, 8.0))
    d_shore = np.minimum(
        np.abs(z_arr - 1332.0),
        np.minimum(np.abs(z_arr - 1463.0), np.abs(z_arr - 1552.0)),
    ).astype(np.float32)
    z_mean_g3 = gaussian_filter(z_arr, 3.0)
    z_std_300m = np.sqrt(np.maximum(0.0, gaussian_filter(z_arr * z_arr, 3.0) - z_mean_g3 * z_mean_g3)).astype(np.float32)
    z_lrm_400m = (z_arr - gaussian_filter(z_arr, 4.0)).astype(np.float32)
    _push("pluvial_shoreline_elev_dist_m", d_shore)
    _push("zmean_std_300m", z_std_300m)
    _push("zmean_lrm_400m", z_lrm_400m)

    # GEMSDOE73 New Feature 5: Cross-Contour Tectonic Scarp Index (rejects contour-parallel shorelines)
    cross_contour_scarp = (
        pnorm(curv10, fp) * np.clip(z_std_300m / (np.abs(z_lrm_400m) + 2.0), 0.0, 5.0) * np.clip(d_shore / 25.0, 0.2, 1.0)
    ).astype(np.float32)
    _push("cross_contour_scarp_index", cross_contour_scarp)
    del ksn_arr, z_arr, d_shore, z_mean_g3, z_std_300m, z_lrm_400m, curv10, cross_contour_scarp

    # 5. GeoDAWN airborne gamma-ray spectrometry & upward-continued TMI alteration
    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as ds:
        rad_k = None
        for b_idx, b_name in enumerate(["rad_K", "rad_Th", "rad_U", "rad_TC"], start=1):
            q = ds.read(b_idx)
            arr = _fast_fill(q.astype(np.float32), fp & (q > 0))
            _push(b_name, arr)
            if b_name == "rad_K":
                rad_k = arr
    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as ds:
        tmi_up = None
        thk_arr = None
        for b_idx, b_name in enumerate(["ext_ThK", "ext_UK", "ext_UTh", "ext_TMI_up150"], start=1):
            q = ds.read(b_idx)
            arr = _fast_fill(q.astype(np.float32), fp & (q > 0))
            _push(b_name, arr)
            if b_name == "ext_TMI_up150":
                tmi_up = arr
            elif b_name == "ext_ThK":
                thk_arr = arr
    idx_cache.clear()
    del idx_fp
    assert rad_k is not None and tmi_up is not None and thk_arr is not None
    k_halo = (rad_k - gaussian_filter(rad_k, 10.0)).astype(np.float32)
    demag = (gaussian_filter(tmi_up, 10.0) - tmi_up).astype(np.float32)
    _push("rad_K_alteration_halo", k_halo)
    _push("tmi_demagnetization_trough", demag)

    # GEMSDOE73 New Feature 6: Hydrothermal Alteration x Geodetic Transtensional Strain Conduit
    alt_norm = 0.40 * pnorm(thk_arr, fp) + 0.35 * pnorm(demag, fp) + 0.25 * cond_norm
    hydro_strain = (alt_norm * (0.4 + 0.6 * pnorm(strain_transtens, fp))).astype(np.float32)
    _push("hydrothermal_strain_conduit", hydro_strain)
    del rad_k, tmi_up, thk_arr, k_halo, demag, alt_norm, hydro_strain, strain_transtens, cond_norm

    # 6. Label-free hydrothermal conduits: GDR 1391 springs/geothermometers, 2m probes, sinter/tufa, volcanic vents
    imp_therm = np.zeros(shape, dtype=np.float32)
    ws_count = 0
    ws_path = ext_dir / "gdr_wellspring_in_footprint.csv"
    with ws_path.open(newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        used_ws_cols = ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c")
        assert set(used_ws_cols).isdisjoint(FORBIDDEN_POINT_COLUMNS)
        for r in reader:
            rr, cc = int(r["row"]), int(r["col"])
            if not (0 <= rr < shape[0] and 0 <= cc < shape[1]):
                continue
            vals_t = []
            for k_col, base_t in (
                ("temp_c", 20.0),
                ("geothermquartz_c", 70.0),
                ("geothermchalc_c", 60.0),
                ("geothermcat_c", 75.0),
            ):
                s_val = r.get(k_col, "")
                if s_val and s_val != "nan":
                    try:
                        vals_t.append(max(0.0, float(s_val) - base_t))
                    except ValueError:
                        pass
            if vals_t:
                score_t = float(np.log1p(max(vals_t)))
                if score_t > imp_therm[rr, cc]:
                    imp_therm[rr, cc] = score_t
                ws_count += 1
    _push("gdr_thermal_upflow_s5", gaussian_filter(imp_therm, 5.0))
    _push("gdr_thermal_upflow_s16", gaussian_filter(imp_therm, 16.0))
    del imp_therm

    imp_dab, imp_pcnt = _parse_2m_probes_dbf(
        ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip", transform, shape
    )
    _push("probe2m_dab_s5", gaussian_filter(np.log1p(imp_dab), 5.0))
    _push("probe2m_dab_s14", gaussian_filter(np.log1p(imp_dab), 14.0))
    probe_sites = int((imp_pcnt > 0).sum())
    del imp_dab, imp_pcnt

    imp_paleo = np.zeros(shape, dtype=np.float32)
    paleo_zip = ext_dir / "paleo_geothermal_regional.zip"
    paleo_count = 0
    if paleo_zip.is_file():
        with zipfile.ZipFile(paleo_zip) as zf:
            cname = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with io.TextIOWrapper(zf.open(cname), encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                lons, lats = [], []
                for r in reader:
                    try:
                        lons.append(float(r["Long_deg_NAD83"]))
                        lats.append(float(r["Lat_deg_NAD83"]))
                    except (KeyError, ValueError):
                        continue
        if lons:
            ux, uy = rio_transform("EPSG:4269", "EPSG:32611", lons, lats)
            rr, cc, _ = _utm_to_rc(ux, uy, transform, shape)
            imp_paleo[rr, cc] = 1.0
            paleo_count = int(rr.size)
    _push("paleo_sinter_tufa_s6", gaussian_filter(imp_paleo, 6.0))
    _push("paleo_sinter_tufa_s18", gaussian_filter(imp_paleo, 18.0))
    del imp_paleo

    imp_vent = np.zeros(shape, dtype=np.float32)
    vent_count = 0
    with (ext_dir / "gdr_volcanic_vents_in_footprint.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rr, cc = int(r["row"]), int(r["col"])
            if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
                imp_vent[rr, cc] = 1.0
                vent_count += 1
    _push("quaternary_volcanic_vent_s16", gaussian_filter(imp_vent, 16.0))
    del imp_vent

    assert col_ptr == total_cols, f"Expected {total_cols} columns, wrote {col_ptr}"
    X.flush()
    meta = {
        "n_footprint_pixels": n_fp,
        "n_features": total_cols,
        "forbidden_columns_blocked": sorted(FORBIDDEN_POINT_COLUMNS),
        "sgmc_in_feature_matrix": False,
        "historical_predictions_in_feature_matrix": False,
        "point_records_ingested": {
            "gdr_wellspring_records": ws_count,
            "probe_2m_cells": probe_sites,
            "paleo_sinter_travertine_tufa_records": paleo_count,
            "quaternary_volcanic_vents": vent_count,
        },
    }
    meta_path.write_text(
        json.dumps(
            {
                "n_features": total_cols,
                "n_footprint_pixels": n_fp,
                "feature_names": names,
                "meta": meta,
            },
            indent=2,
        )
        + "\n"
    )
    return X, names, has_lidar_fp, meta


def compute_fold_safe_transtensional_mechanics(
    visible_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute strictly fold-safe transtensional crack-tip, wing-crack, and relay-bridge fields.

    Uses ONLY `visible_mask` (`fold['visible']` on holdout folds, or `catalogue` for
    final off-catalogue inference). Zero information from any withheld truth enters.

    Returns:
      - `tip_lobe`: Direct strike continuation from visible fault terminations (3..18 px).
      - `wing_bridge`: Andersonian +-28 deg wing-crack splay lobes + long-range (6..26 px)
        collinear gap bridge weighted by fault segment length.
      - `relay_annulus`: Stepover annulus (4..16 px) between subparallel fault segments.
    """
    if not visible_mask.any():
        z = np.zeros(visible_mask.shape, dtype=np.float32)
        return z, z, z

    vis_b = visible_mask > 0
    comp, _ = ndi_label(vis_b, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(comp.ravel())
    major = vis_b & (sizes[comp] >= 8)

    nb = convolve(major.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant", cval=0)
    tips = major & ((nb == 2) | (nb == 3))

    sm = gaussian_filter(major.astype(np.float32), sigma=2.5)
    gy, gx = np.gradient(sm)
    norm = np.hypot(gx, gy) + 1e-6
    tx, ty = -gx / norm, gy / norm

    ty_idx, tx_idx = np.nonzero(tips)
    seg_len_w = np.clip(np.log1p(sizes[comp[ty_idx, tx_idx]].astype(np.float32)) / np.log1p(80.0), 0.35, 1.35)

    lobe = np.zeros(visible_mask.shape, dtype=np.float32)
    for step in (3.0, 6.0, 9.0, 12.0, 15.0, 18.0):
        w = float(np.exp(-0.5 * (step / 11.0) ** 2))
        for sgn in (-1.0, 1.0):
            ry = np.clip(np.round(ty_idx + sgn * step * ty[ty_idx, tx_idx]).astype(np.int64), 0, visible_mask.shape[0] - 1)
            rx = np.clip(np.round(tx_idx + sgn * step * tx[ty_idx, tx_idx]).astype(np.int64), 0, visible_mask.shape[1] - 1)
            np.maximum.at(lobe, (ry, rx), w)
    tip_field = gaussian_filter(lobe, sigma=2.5).astype(np.float32)

    # Wing-crack (+-28 deg) + extended collinear gap bridge (6..26 px)
    wing = np.zeros(visible_mask.shape, dtype=np.float32)
    cos28, sin28 = float(np.cos(np.deg2rad(28.0))), float(np.sin(np.deg2rad(28.0)))
    tx0, ty0 = tx[ty_idx, tx_idx], ty[ty_idx, tx_idx]
    for ang_c, ang_s, aw in ((1.0, 0.0, 1.0), (cos28, sin28, 0.75), (cos28, -sin28, 0.75)):
        d_x = tx0 * ang_c - ty0 * ang_s
        d_y = tx0 * ang_s + ty0 * ang_c
        for step in (5.0, 9.0, 13.0, 18.0, 23.0, 28.0):
            w_arr = (aw * float(np.exp(-0.5 * (step / 15.0) ** 2)) * seg_len_w).astype(np.float32)
            for sgn in (-1.0, 1.0):
                ry = np.clip(np.round(ty_idx + sgn * step * d_y).astype(np.int64), 0, visible_mask.shape[0] - 1)
                rx = np.clip(np.round(tx_idx + sgn * step * d_x).astype(np.int64), 0, visible_mask.shape[1] - 1)
                np.maximum.at(wing, (ry, rx), w_arr)
    wing_field = gaussian_filter(wing, sigma=3.0).astype(np.float32)

    d_vis = distance_transform_edt(~visible_mask).astype(np.float32)
    collar_taper = np.clip((d_vis - 2.2) / 2.0, 0.0, 1.0).astype(np.float32)
    relay_field = (
        np.maximum(0.0, gaussian_filter(major.astype(np.float32), 9.5) - 0.55 * gaussian_filter(major.astype(np.float32), 2.5))
        * collar_taper
    ).astype(np.float32)
    return (tip_field * collar_taper).astype(np.float32), (wing_field * collar_taper).astype(np.float32), relay_field
