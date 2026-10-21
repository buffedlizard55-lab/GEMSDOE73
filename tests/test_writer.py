"""Writer produces portal-safe bytes."""
import pathlib, tempfile, numpy as np, rasterio
from src.gems73.submission import write_submission, WIDTH, HEIGHT, CRS, TRANSFORM

def test_write_all_finite():
    arr = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    arr[100,100]=1.0; arr[200,200]=0.5
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)/"out.tif"
        info = write_submission(arr, p)
        assert info["all_finite"]
        assert info["emitted"]==2
        with rasterio.open(p) as src:
            assert src.nodata is None
            assert src.crs.to_epsg()==32611
            a=src.read(1)
            assert float(a.min())>=0 and float(a.max())<=1
            assert np.isfinite(a).all()

def test_rejects_out_of_range():
    arr = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    arr[0,0]=1.5
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        try:
            write_submission(arr, pathlib.Path(td)/"bad.tif")
            assert False, "should have asserted"
        except AssertionError: pass
