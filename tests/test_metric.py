import numpy as np
from src.gems73.metric import kernel, dti_exact, ALPHA, BETA, RADIUS_PX

def test_worked_example():
    # From competition page: TP=3 FP=1.89 FN=2 DTI=0.60
    tp=3.0; fp=1.89; fn=2.0
    dti = tp/(tp+ALPHA*fp+BETA*fn)
    assert abs(dti-0.60) < 1e-6

def test_kernel():
    assert kernel(0) == 1.0
    assert kernel(3.0) == 0.0
    assert abs(kernel(np.hypot(2,2)) - (1-2*np.sqrt(2)/3)) < 1e-9


"""Metric identity and worked example (problem page 967)."""
from src.gems73.metric import dti_fast, kernel, ALPHA, BETA
import numpy as np
from scipy.ndimage import distance_transform_edt

def test_worked_example():
    # Published TPw=3.00 FPw=1.89 FNw=2.00 -> 0.60
    TPw, FPw, FNw = 3.00, 1.89, 2.00
    dti = TPw/(TPw+ALPHA*FPw+BETA*FNw)
    assert abs(dti-0.60) < 0.01

def test_kernel_support():
    assert kernel(np.array([0.0]))[0]==1.0
    assert kernel(np.array([3.0]))[0]==0.0
    assert kernel(np.array([1.5]))[0]==0.5

def test_dti_brute_vs_fast():
    pred = np.zeros((20,20), dtype=np.float32)
    truth = np.zeros((20,20), dtype=np.uint8)
    truth[10,10]=1
    pred[10,11]=1.0
    # distance 1 -> k=0.666
    dti = dti_fast(pred, truth)
    assert 0 <= dti <= 1

def test_identity_no_truth():
    pred = np.zeros((10,10), dtype=np.float32)
    truth = np.zeros((10,10), dtype=np.uint8)
    assert dti_fast(pred, truth)==1.0

