"""GeoTIFF submission validator — strict format checks."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import numpy as np
import rasterio
from .grid import WIDTH, HEIGHT, CRS, TRANSFORM

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

@dataclass(frozen=True)
class ValidationReport:
    file_path: str
    sha256: str
    passed: bool
    checks: list[CheckResult]
    def to_dict(self):
        return {"file_path": str(self.file_path), "sha256": str(self.sha256),
                "passed": bool(self.passed), "checks": [asdict(c) for c in self.checks]}

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()

def validate_submission_geotiff(geotiff_path: Path, template_path: Path,
                                strict_whole_array_finite: bool = False) -> ValidationReport:
    checks = []
    sha = compute_sha256(geotiff_path)
    with rasterio.open(template_path) as tpl, rasterio.open(geotiff_path) as sub:
        checks.append(CheckResult("dimensions", bool((sub.height, sub.width) == (tpl.height, tpl.width)),
                                  f"shape {sub.shape} expected {tpl.shape}"))
        checks.append(CheckResult("band_count", bool(sub.count == 1), f"bands {sub.count} expected 1"))
        checks.append(CheckResult("crs", bool(sub.crs == tpl.crs), f"CRS {sub.crs} expected {tpl.crs}"))
        checks.append(CheckResult("transform", bool(sub.transform == tpl.transform), "transform match"))
        checks.append(CheckResult("dtype", bool(sub.dtypes[0] == "float32"), f"dtype {sub.dtypes[0]} expected float32"))
        tpl_data = tpl.read(1)
        valid = np.isfinite(tpl_data)
        sub_data = sub.read(1)
        inside = sub_data[valid]
        finite_inside = np.all(np.isfinite(inside))
        range_ok = False
        detail = "non-finite or empty"
        if finite_inside and len(inside) > 0:
            mn, mx = float(inside.min()), float(inside.max())
            range_ok = (mn >= 0.0 and mx <= 1.0)
            detail = f"in-footprint [{mn:.4f},{mx:.4f}] finite={finite_inside}"
        checks.append(CheckResult("in_footprint_range", bool(range_ok and finite_inside), detail))
        if strict_whole_array_finite:
            all_fin = bool(np.all(np.isfinite(sub_data)))
            all_range = bool(all_fin and float(sub_data.min()) >= 0.0 and float(sub_data.max()) <= 1.0)
            checks.append(CheckResult("portal_safe_whole_array", bool(all_range),
                                      f"whole [{sub_data.min():.4f},{sub_data.max():.4f}] finite={all_fin}"))
    return ValidationReport(str(geotiff_path), sha, all(c.passed for c in checks), checks)

def write_submission_geotiff(predictions_2d: np.ndarray, template_path: Path, output_path: Path,
                             outside_mode: str = "zeros", note: str | None = None) -> dict:
    preds = np.asarray(predictions_2d, dtype=np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as tpl:
        profile = tpl.profile.copy()
        profile.update(dtype=rasterio.float32, count=1, compress="deflate", tiled=True,
                       nodata=None if outside_mode == "zeros" else float("nan"))
        tpl_data = tpl.read(1)
        valid = np.isfinite(tpl_data)
        if outside_mode == "zeros":
            out_array = np.where(valid, preds, 0.0).astype(np.float32)
            out_array = np.clip(out_array, 0.0, 1.0)
        else:
            out_array = np.where(valid, preds, np.nan).astype(np.float32)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(out_array, 1)
    report = validate_submission_geotiff(output_path, template_path,
                                         strict_whole_array_finite=(outside_mode == "zeros"))
    if not report.passed:
        raise ValueError(f"Validation failed: {report.to_dict()}")
    emitted = int(np.count_nonzero(out_array[valid] > 0))
    return {"file_path": str(output_path), "sha256": report.sha256,
            "emitted_dots": emitted, "note": note or "", "validation": report.to_dict()}


def write_submission(arr: np.ndarray, out_path: Path | str) -> dict[str, Any]:
    """Portal-safe fail-closed writer using the official competition grid profile."""
    a = np.asarray(arr, dtype=np.float32)
    assert a.shape == (HEIGHT, WIDTH), f"shape {a.shape} != {(HEIGHT, WIDTH)}"
    assert np.isfinite(a).all(), "array contains NaN or Inf"
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0, "values must lie in [0, 1]"
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        p, "w", driver="GTiff", dtype="float32", count=1,
        width=WIDTH, height=HEIGHT, crs=CRS, transform=TRANSFORM,
        nodata=None, compress="deflate", tiled=True,
    ) as dst:
        dst.write(a, 1)
    with rasterio.open(p) as chk:
        rb = chk.read(1)
        all_fin = bool(np.isfinite(rb).all() and float(rb.min()) >= 0.0 and float(rb.max()) <= 1.0)
    return {
        "file_path": str(p),
        "sha256": compute_sha256(p),
        "all_finite": all_fin,
        "emitted": int((a > 0).sum()),
    }

