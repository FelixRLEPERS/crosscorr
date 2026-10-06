"""Группа E — тесты transfer_entropy.py (направленная мера, KSG).

Численные эталоны:
- независимые ряды: T ≈ 0 в обе стороны;
- y[t] = a * x[t-1] + шум: T(X->Y) >> T(Y->X);
- матрица асимметрична.
"""

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.transfer_entropy import (
    transfer_entropy,
    transfer_entropy_matrix,
)


def _driven_series(n: int, a: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """x — драйвер; y[t] = a * x[t-1] + шум."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    y = np.empty(n)
    y[0] = 0.0
    for t in range(1, n):
        y[t] = a * x[t - 1] + 0.5 * rng.normal()
    return x, y


def test_te_independent_series_is_zero(rng):
    """Два независимых ряда → T мала по модулю в обе стороны."""
    x = rng.normal(size=3000)
    y = rng.normal(size=3000)
    assert abs(transfer_entropy(x, y)) < 0.05
    assert abs(transfer_entropy(y, x)) < 0.05


def test_te_directional():
    """y зависит от прошлого x → T(X->Y) заметно больше T(Y->X)."""
    x, y = _driven_series(n=3000, a=0.7, seed=1)
    t_xy = transfer_entropy(x, y)
    t_yx = transfer_entropy(y, x)
    assert t_xy > 0.1
    assert t_xy > 3.0 * t_yx


def test_te_matrix_asymmetric():
    """Матрица TE асимметрична для зависимой пары."""
    x, y = _driven_series(n=2500, a=0.7, seed=2)
    wide = pd.DataFrame({"driver": x, "target": y})
    mat = transfer_entropy_matrix(wide, k=1, lag=1)
    assert mat.shape == (2, 2)
    assert mat.loc["driver", "target"] > mat.loc["target", "driver"]
    np.testing.assert_allclose(np.diag(mat.to_numpy()), 0.0)


def test_te_self_does_not_crash(rng):
    """T(X->X) не должна падать и остаётся конечной."""
    x = rng.normal(size=2000)
    val = transfer_entropy(x, x)
    assert np.isfinite(val)
