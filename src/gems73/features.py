"""GEMSDOE73 — Cross-Drainage Alluvial Piedmont Scarp Physics & 90-Channel Feature Stack.

Strict scientific & parallel-run invariants enforced throughout:
  1. Zero historical submission or registry prediction rasters are read anywhere here.
  2. ``sgmc_faults_100m.tif`` is NEVER read anywhere in feature extraction or model training
     (100% pure zero-SGMC in BOTH X and y).
  3. Columns encoding catalogue distance in external point tables are explicitly blocked.
  4. All 90 static physical features stream band-by-band into a disk-backed float32 memmap
     so peak RSS stays well below 900 MB on a 3.8 GiB sandbox.

Novel GEMSDOE73 physical operators (not implemented in any prior GEMSDOE1..82 repository):
  - ``cross_drainage_orthogonality``: |sin(theta_scarp - theta_regional_bajada_slope)|
    weighted by multi-scale scarp coherence, separating contour-parallel tectonic piedmont
    fault scarps from radial down-fan gullies, washes, and E-W erosional incisions.
  - ``cross_fan_scarp_score``: road-deconfounded cross-drainage 1m/10m scarp intensity.
  - ``along_strike_elev_std_1600m``: 1.6 km along-strike true-elevation standard deviation
    sigma_z(s in [-800 m, +800 m]), distinguishing fan-climbing Quaternary fault scarps
    (sigma_z ~ 8-60 m) from horizontal Pleistocene Lake Lahontan / Lake Dixie wave-cut
    paleo-shorelines (sigma_z ~ 0-2 m).
  - ``lahontan_shoreline_mimic_index``: explicit physical indicator for equipotential benches
    inside the [1,190 m, 1,365 m] pluvial highstand envelope with flat along-strike elevation.
  - ``radon_line_900m``, ``radon_line_2100m``, ``radon_anisotropy_2100m``: 12-azimuth steerable
    Radon line-integral persistence and along-strike / cross-strike contrast ratio.
  - ``hessian_centerline_1d``: multi-scale 1D curvilinear ridge peak sharpness.
  - ``dem10_onesided``, ``dem10_onesided3``, ``dem10_hgm20_max``, ``dem10_hgm50_max``,
    ``dem1m_openness_dipole``, ``dem1m_lrm_grad``, ``tiger_road_logdist``.
"""
from __future__ import annotations

import gc
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import (
    convolve,
    distance_transform_edt,
    gaussian_filter,
    label as ndi_label,
    maximum_filter,
)

# Reuse shared template feature builder for the 76 baseline physical bands (Rule 2: Reuse, Don't Rebuild)
GEMS70_SRC = Path("/tmp/GEMSDOE70/src")
if GEMS70_SRC.exists() and str(GEMS70_SRC) not in sys.path:
    sys.path.insert(0, str(GEMS70_SRC))

GEMS73_EXTRA_NAMES = [
    "dem10_onesided",
    "dem10_onesided3",
    "dem10_hgm20_max",
    "dem10_hgm50_max",
    "tiger_road_logdist",
    "dem1m_openness_dipole",
    "dem1m_lrm_grad",
    "cross_drainage_orthogonality",
    "cross_fan_scarp_score",
    "along_strike_elev_std_1600m",
    "lahontan_shoreline_mimic_index",
    "radon_line_900m",
    "radon_line_2100m",
    "radon_anisotropy_2100m",
    "hessian_centerline_1d",
]


def _fill_2d(arr: np.ndarray, valid: np.ndarray, idx_nn: np.ndarray | None = None) -> np.ndarray:
    bad = ~valid
    if not bad.any():
        return arr.astype(np.float32, copy=False)
    if idx_nn is None:
        idx_nn = distance_transform_edt(bad, return_distances=False, return_indices=True)
    out = arr.astype(np.float32, copy=True)
    out[bad] = out[idx_nn[0][bad], idx_nn[1][bad]]
    return out


def compute_steerable_radon_and_shoreline_physics(
    scarp_2d: np.ndarray,
    zmean_2d: np.ndarray,
    road_dist_2d: np.ndarray,
    fp: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute GEMSDOE73's closed-form Quaternary geomorphology & mimic-suppression fields."""
    H, W = fp.shape

    # 1. Regional coalescing-bajada / piedmont downslope vector at sigma = 15 px (1.5 km)
    z_reg = gaussian_filter(zmean_2d.astype(np.float32), sigma=15.0, mode="nearest")
    fgy, fgx = np.gradient(z_reg)
    fan_slope_mag = np.hypot(fgx, fgy) + 1e-6
    theta_fan = np.arctan2(fgy, fgx)  # regional downslope vector angle in radians
    del z_reg

    # 2. Local multi-scale scarp orientation & coherence via structure tensor on scarp_2d
    sm = gaussian_filter(scarp_2d.astype(np.float32), sigma=1.4, mode="nearest")
    sgy, sgx = np.gradient(sm)
    jxx = gaussian_filter((sgx * sgx).astype(np.float32), sigma=2.5, mode="nearest")
    jyy = gaussian_filter((sgy * sgy).astype(np.float32), sigma=2.5, mode="nearest")
    jxy = gaussian_filter((sgx * sgy).astype(np.float32), sigma=2.5, mode="nearest")
    coh = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0)) / (jxx + jyy + 1e-9)
    # Principal gradient normal of scarp feature:
    theta_norm = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy + 1e-12)
    # Scarp strike direction is perpendicular to scarp gradient normal:
    theta_strike = theta_norm + (0.5 * np.pi)
    del sgy, sgx, jxx, jyy, jxy

    # Cross-drainage orthogonality:
    # A down-fan stream bank has strike parallel to fan downslope -> |sin(theta_strike - theta_fan)| ~ 0
    # A contour-parallel piedmont fault scarp cuts perpendicular to fan downslope -> |sin(...)| ~ 1
    sin_cross = np.abs(np.sin(theta_strike - theta_fan)).astype(np.float32)
    fan_relief_gate = np.clip(fan_slope_mag / 0.8, 0.25, 1.0).astype(np.float32)
    orthogonality = (coh * sin_cross * fan_relief_gate).astype(np.float32)

    road_suppress = np.where(road_dist_2d < 150.0, 0.45, 1.0).astype(np.float32)
    cross_fan_scarp = (scarp_2d * (0.35 + 0.65 * sin_cross) * road_suppress).astype(np.float32)
    del fan_slope_mag, fan_relief_gate, road_suppress, theta_fan

    # 3. 12-azimuth steerable Radon line-integral persistence & along-strike true-elevation variance!
    # Simultaneously measures:
    #  - best 900 m (half=4) & 2,100 m (half=10) strike-line mean scarp response
    #  - cross-strike flanking mean (for true 1D linear sharpness vs broad slope blob)
    #  - along-strike elevation standard deviation sigma_z over +-800 m along best strike!
    az_deg = np.linspace(0.0, 165.0, 12, dtype=np.float32)  # every 15 degrees across [0, 180)
    best_r900 = np.full((H, W), -1e9, dtype=np.float32)
    best_r2100 = np.full((H, W), -1e9, dtype=np.float32)
    best_aniso = np.zeros((H, W), dtype=np.float32)
    best_zstd = np.zeros((H, W), dtype=np.float32)

    z_f32 = zmean_2d.astype(np.float32)
    s_f32 = scarp_2d.astype(np.float32)

    for deg in az_deg:
        rad = float(np.deg2rad(deg))
        # Strike unit vector in (dy, dx): deg clockwise from North -> dx = sin(deg), dy = -cos(deg)
        ux = float(np.sin(rad))
        uy = float(-np.cos(rad))
        # Andersonian weight gentle bias ONLY inside tie-breaking, pure physical response preserved:
        acc_9 = np.zeros((H, W), dtype=np.float32)
        acc_21 = np.zeros((H, W), dtype=np.float32)
        z_sum = np.zeros((H, W), dtype=np.float32)
        z_sq = np.zeros((H, W), dtype=np.float32)
        n_z = 0
        for k in range(-10, 11):
            sy = int(round(k * uy))
            sx = int(round(k * ux))
            shifted_s = np.roll(np.roll(s_f32, sy, axis=0), sx, axis=1)
            acc_21 += shifted_s
            if -4 <= k <= 4:
                acc_9 += shifted_s
            if k in (-8, -4, 0, 4, 8):
                sz = np.roll(np.roll(z_f32, sy, axis=0), sx, axis=1)
                z_sum += sz
                z_sq += sz * sz
                n_z += 1
        mean_9 = acc_9 / 9.0
        mean_21 = acc_21 / 21.0
        # Cross-strike flanking values at +-3 px normal (-uy, ux):
        ny1, nx1 = int(round(3.0 * (-ux))), int(round(3.0 * uy))
        flank = 0.5 * (
            np.roll(np.roll(mean_21, ny1, axis=0), nx1, axis=1)
            + np.roll(np.roll(mean_21, -ny1, axis=0), -nx1, axis=1)
        )
        aniso = mean_21 - 0.65 * flank
        z_mean_s = z_sum / float(n_z)
        z_std_s = np.sqrt(np.maximum(z_sq / float(n_z) - z_mean_s * z_mean_s, 0.0))

        np.maximum(best_r900, mean_9, out=best_r900)
        better = mean_21 > best_r2100
        best_r2100[better] = mean_21[better]
        best_aniso[better] = aniso[better]
        best_zstd[better] = z_std_s[better]
        del acc_9, acc_21, z_sum, z_sq, mean_9, mean_21, flank, aniso, z_mean_s, z_std_s, better

    # 4. Explicit Pleistocene Lake Lahontan (~1,190-1,355 m ASL) horizontal wave-cut shoreline mimic index:
    # Wave-cut paleo-shorelines occupy the pluvial basin rim AND have near-zero along-strike elevation SD!
    in_pluvial_band = np.exp(-0.5 * ((z_f32 - 1295.0) / 65.0) ** 2).astype(np.float32)
    is_equipotential = np.exp(-0.5 * (best_zstd / 4.0) ** 2).astype(np.float32)
    lahontan_mimic = (in_pluvial_band * is_equipotential * np.clip(coh, 0.0, 1.0)).astype(np.float32)

    # 5. Multi-scale 1D Hessian curvilinear ridge centerline response
    hess_max = np.zeros((H, W), dtype=np.float32)
    for sig in (1.1, 2.2):
        axx = gaussian_filter(s_f32, sig, order=(0, 2), mode="nearest")
        ayy = gaussian_filter(s_f32, sig, order=(2, 0), mode="nearest")
        axy = gaussian_filter(s_f32, sig, order=(1, 1), mode="nearest")
        rad_e = np.sqrt(np.maximum(((axx - ayy) * 0.5) ** 2 + axy * axy, 0.0))
        eig_min = np.minimum((axx + ayy) * 0.5 + rad_e, (axx + ayy) * 0.5 - rad_e)
        ridge = np.maximum(-eig_min * (sig ** 1.5), 0.0).astype(np.float32)
        np.maximum(hess_max, ridge, out=hess_max)
        del axx, ayy, axy, rad_e, eig_min, ridge

    gc.collect()
    return {
        "cross_drainage_orthogonality": orthogonality,
        "cross_fan_scarp_score": cross_fan_scarp,
        "along_strike_elev_std_1600m": best_zstd,
        "lahontan_shoreline_mimic_index": lahontan_mimic,
        "radon_line_900m": best_r900,
        "radon_line_2100m": best_r2100,
        "radon_anisotropy_2100m": best_aniso,
        "hessian_centerline_1d": hess_max,
    }


def build_gems73_feature_stack(
    mmap_path: Path,
    fp: np.ndarray,
    transform: Any,
    data_dir: Path,
    ext_gems_dir: Path,
    ext_60_dir: Path,
    dem10_dir: Path,
) -> tuple[np.memmap, list[str], np.ndarray, dict[str, Any]]:
    """Build complete 91-feature zero-SGMC physical feature memmap on the 5,167,373 footprint pixels."""
    from gems70.phase5_features import build_feature_memmap as build_base76

    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    total_cols = 76 + len(GEMS73_EXTRA_NAMES)  # 91 features
    meta_path = mmap_path.with_suffix(".meta.json")

    if mmap_path.is_file() and meta_path.is_file():
        cm = json.loads(meta_path.read_text())
        if cm.get("n_features") == total_cols and cm.get("n_footprint_pixels") == n_fp:
            X = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(total_cols, n_fp))
            has_lidar_fp = np.asarray(X[cm["feature_names"].index("lidar_has_coverage"), :] > 0.5)
            return X, cm["feature_names"], has_lidar_fp, cm["meta"]

    base_mmap_path = mmap_path.parent / "base76_shared_fp.f32"
    X_base, base_names, has_lidar_fp, base_meta = build_base76(
        base_mmap_path, fp, transform, data_dir, ext_gems_dir, ext_60_dir
    )

    mmap_path.parent.mkdir(parents=True, exist_ok=True)
    X = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(total_cols, n_fp))
    for i in range(76):
        X[i, :] = X_base[i, :]
    del X_base
    gc.collect()

    names = list(base_names)
    col_ptr = 76

    def _push_fp(name: str, vec_fp: np.ndarray) -> None:
        nonlocal col_ptr
        X[col_ptr, :] = vec_fp.astype(np.float32, copy=False)
        names.append(name)
        col_ptr += 1

    # Add float32 dem10 breaklines (onesided, onesided3, hgm20_max, hgm50_max)
    for ch in ("dem10_onesided", "dem10_onesided3", "dem10_hgm20_max", "dem10_hgm50_max"):
        vec = np.load(dem10_dir / f"{ch}.f32.npy").astype(np.float32)
        _push_fp(ch, vec)

    # US Census TIGER road log-distance
    with rasterio.open(ext_gems_dir / "tiger_road_distance_m.tif") as src:
        road_2d = src.read(1).astype(np.float32)
    _push_fp("tiger_road_logdist", np.log1p(np.maximum(road_2d.ravel()[fp_idx], 0.0)))

    # 1m USGS 3DEP EarthMRI Openness dipole & LRM gradient (native NaN outside high-prior tiles)
    lrm_npz = np.load(ext_gems_dir / "dem1m_high_prior_openness_lrm.npz")
    cov_fp = lrm_npz["cov_fp_indices"]
    for key, out_nm in (
        ("openness_dipole_max", "dem1m_openness_dipole"),
        ("lrm_grad_max", "dem1m_lrm_grad"),
    ):
        arr_fp = np.full(n_fp, np.nan, dtype=np.float32)
        arr_fp[cov_fp] = lrm_npz[key].astype(np.float32)
        _push_fp(out_nm, arr_fp)
    del lrm_npz

    # Reconstruct 2D composite scarp field + true elevation zmean_2d for closed-form geomorphology
    idx_nn = distance_transform_edt(~fp, return_distances=False, return_indices=True)
    zmean_2d = np.zeros(fp.shape, dtype=np.float32)
    zmean_2d.ravel()[fp_idx] = np.asarray(X[names.index("chi_zmean_m"), :], dtype=np.float32)
    zmean_2d = _fill_2d(zmean_2d, fp, idx_nn)

    # Normalized multi-resolution scarp field combining 10m onesided3 + hgm20 + 1m LiDAR step where present
    os3 = np.asarray(X[names.index("dem10_onesided3"), :], dtype=np.float32)
    hgm20 = np.asarray(X[names.index("dem10_hgm20_max"), :], dtype=np.float32)
    lid_step = np.asarray(X[names.index("lidar_step_max"), :], dtype=np.float32)
    os3_z = np.clip((os3 - np.nanmedian(os3)) / (np.nanpercentile(os3, 90) - np.nanmedian(os3) + 1e-6), 0.0, 4.0)
    hgm_z = np.clip((hgm20 - np.nanmedian(hgm20)) / (np.nanpercentile(hgm20, 90) - np.nanmedian(hgm20) + 1e-6), 0.0, 4.0)
    lid_med = float(np.nanmedian(lid_step))
    lid_p90 = float(np.nanpercentile(lid_step, 90))
    lid_z = np.clip((lid_step - lid_med) / (lid_p90 - lid_med + 1e-6), 0.0, 4.0)
    comp_fp = np.where(has_lidar_fp, 0.45 * lid_z + 0.35 * os3_z + 0.20 * hgm_z, 0.60 * os3_z + 0.40 * hgm_z)

    scarp_2d = np.zeros(fp.shape, dtype=np.float32)
    scarp_2d.ravel()[fp_idx] = comp_fp
    scarp_2d = _fill_2d(scarp_2d, fp, idx_nn)
    del os3, hgm20, lid_step, os3_z, hgm_z, lid_z, comp_fp, idx_nn
    gc.collect()

    geo_fields = compute_steerable_radon_and_shoreline_physics(scarp_2d, zmean_2d, road_2d, fp)
    del scarp_2d, zmean_2d, road_2d
    gc.collect()

    for key in (
        "cross_drainage_orthogonality",
        "cross_fan_scarp_score",
        "along_strike_elev_std_1600m",
        "lahontan_shoreline_mimic_index",
        "radon_line_900m",
        "radon_line_2100m",
        "radon_anisotropy_2100m",
        "hessian_centerline_1d",
    ):
        _push_fp(key, geo_fields[key].ravel()[fp_idx])
    del geo_fields
    gc.collect()

    assert col_ptr == total_cols, f"Expected {total_cols} features, got {col_ptr}"
    X.flush()
    out_meta = {
        **base_meta,
        "gems73_extra_features": GEMS73_EXTRA_NAMES,
        "sgmc_in_feature_matrix": False,
        "sgmc_in_training_targets": False,
        "historical_predictions_in_feature_matrix": False,
    }
    meta_path.write_text(
        json.dumps(
            {
                "n_features": total_cols,
                "n_footprint_pixels": n_fp,
                "feature_names": names,
                "meta": out_meta,
            },
            indent=2,
        )
        + "\n"
    )
    return X, names, has_lidar_fp, out_meta


def compute_tip_protected_mechanics_and_gate(
    visible_mask: np.ndarray,
    flank_buffer_px: float = 2.0,
    tip_buffer_px: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute strictly fold-safe crack-tip propagation, relay annulus, and Staff 11516/4 gate.

    Per DrivenData Staff clarification (Forum Topic 11516, Post #4):
      1. Known catalogue faults are masked pixel-exactly (d_vis == 0).
      2. Lateral flanks (0 < d_vis <= 2.0 px) away from tips incur full FP penalty if unmapped.
      3. New/modified fault segments DO occur directly off fault terminations (1.0 < d_vis <= 2.0 px
         along tip strike tangent). We protect only that narrow along-strike tip wedge!
    """
    from gems70.phase5_features import compute_fold_safe_mechanics

    tip_lobe, relay_field = compute_fold_safe_mechanics(visible_mask)
    d_vis = distance_transform_edt(~visible_mask).astype(np.float32)

    # Identify narrow immediate along-strike tip corridor right off terminations of major traces:
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

    ty_i, tx_i = np.nonzero(tips)
    near_tip_wedge = np.zeros(visible_mask.shape, dtype=np.float32)
    for step in (1.5, 2.2):
        for sgn in (-1.0, 1.0):
            ry = np.clip(np.round(ty_i + sgn * step * ty[ty_i, tx_i]).astype(int), 0, visible_mask.shape[0] - 1)
            rx = np.clip(np.round(tx_i + sgn * step * tx[ty_i, tx_i]).astype(int), 0, visible_mask.shape[1] - 1)
            near_tip_wedge[ry, rx] = 1.0
    near_tip_wedge = maximum_filter(near_tip_wedge, size=2) > 0.5

    allowed = (~visible_mask) & ((d_vis > flank_buffer_px) | ((d_vis > tip_buffer_px) & near_tip_wedge))
    return tip_lobe, relay_field, allowed
