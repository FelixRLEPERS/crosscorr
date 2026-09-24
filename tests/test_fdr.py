import numpy as np

from crosscorr_lib.analysis.surrogate import fdr_bh


def test_fdr_uses_upper_triangle():
    # Тест с 4x4 симметричной матрицей, где только пара (0,1) должна быть значима при alpha=0.05
    p = np.array([
        [0.0,   0.001, 0.4,   0.5],
        [0.001, 0.0,   0.4,   0.5],
        [0.4,   0.4,   0.0,   0.5],
        [0.5,   0.5,   0.5,   0.0],
    ])
    sig = fdr_bh(p, alpha=0.05)
    assert sig[0, 1] and sig[1, 0], "пара (0,1) должна пройти"
    assert not sig[0, 0], "диагональ должна быть False"
    assert not sig[2, 3] and not sig[3, 2], "пара (2,3) не значима"
