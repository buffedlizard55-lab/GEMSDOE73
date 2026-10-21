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
