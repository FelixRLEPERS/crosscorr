"""Группа E — тесты mse.py (sample entropy + multiscale entropy).

Численные эталоны:
- SampEn белого шума при m=2, r=0.2*std ≈ 2.2 (Richman & Moorman);
- MSE белого шума почти не меняется с масштабом;
- MSE периодического сигнала растёт около масштаба, равного периоду.
"""

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.mse import (
    multiscale_entropy,
    multiscale_entropy_matrix,
    sample_entropy,
)


def test_sampen_white_noise_reference(rng):
    """SampEn белого шума m=2, r=0.2σ ≈ 2.2 (численный эталон)."""
    x = rng.normal(size=3000)
    se = sample_entropy(x, m=2, r=0.2 * float(np.std(x)))
    np.testing.assert_allclose(se, 2.2, atol=0.2)


def test_sampen_periodic_is_low():
    """Регулярный сигнал имеет малую SampEn (высокая предсказуемость)."""
    t = np.arange(2000)
    x = np.sin(2 * np.pi * t / 50.0)
    se = sample_entropy(x, m=2, r=0.2 * float(np.std(x)))
    assert se < 0.5


def test_mse_white_noise_flat(rng):
    """MSE белого шума слабо зависит от масштаба."""
    x = rng.normal(size=4000)
    mse = multiscale_entropy(x, scales=tuple(range(1, 11)), m=2)
    assert np.all(np.isfinite(mse))
    assert float(np.max(mse) - np.min(mse)) < 0.6


def test_mse_periodic_rises_at_period():
    """sin с периодом 50: MSE на масштабе 50 больше, чем на масштабе 10."""
    t = np.arange(4000)
    x = np.sin(2 * np.pi * t / 50.0)
    scales = (1, 10, 25, 50, 100)
    mse = multiscale_entropy(x, scales=scales, m=2)
    d = dict(zip(scales, mse, strict=True))
    assert d[50] > d[10]
    assert d[100] > d[10]


def test_mse_matrix_shape(rng):
    """multiscale_entropy_matrix возвращает (N_detectors, len(scales))."""
    scales = (1, 2, 4, 8)
    wide = pd.DataFrame(
        {f"d{i}": rng.normal(size=2000) for i in range(3)}
    )
    mat = multiscale_entropy_matrix(wide, scales=scales, m=2)
    assert mat.shape == (3, 4)
    assert list(mat.columns) == list(scales)
    assert list(mat.index) == ["d0", "d1", "d2"]
