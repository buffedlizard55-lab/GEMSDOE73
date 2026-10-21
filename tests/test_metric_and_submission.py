import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "src"))
from gems57 import metric
from gems73.emit import greedy_dots

def test_official_worked_example_components():
    # Official page 967: TPw=3.00 FPw=1.89 FNw=2.00 -> TI=0.60
    assert abs(metric.dti_from_components(3.00, 1.89, 2.00) - 0.60) < 0.005

def test_exact_matches_bruteforce():
    rng = np.random.default_rng(0)
    truth = np.zeros((12, 12), bool); truth[2:10, 5] = True
    pred = np.zeros((12, 12)); pred[3:9, 6] = 1.0; pred[4, 4] = 0.5
    assert abs(metric.dti_exact(pred, truth)["dti"] - metric.dti_bruteforce(pred, truth)["dti"]) < 1e-12

def test_emission_spacing_and_budget():
    surf = np.random.default_rng(1).random((60, 60), dtype=np.float32)
    dots = greedy_dots(surf, np.ones((60, 60), bool), budget=100)
    ys, xs = np.nonzero(dots)
    assert dots.sum() == 100
    for i in range(len(ys)):
        d = np.hypot(ys[i+1:]-ys[i], xs[i+1:]-xs[i])
        assert (d >= 2.5 - 1e-9).all()

def test_shipped_file_range_if_present():
    p = ROOT / "docs/downloads/gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif"
    if not p.exists():
        return
    import rasterio
    with rasterio.open(p) as s:
        a = s.read(1)
        assert s.count == 1 and s.dtypes[0] == "float32"
        assert (s.height, s.width) == (3730, 3292) and str(s.crs) == "EPSG:32611"
        assert s.nodata is None
    assert np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0
    assert int((a > 0).sum()) == 37654
