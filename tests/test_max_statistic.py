"""Тесты для max-statistic null в лаговой кросс-корреляции."""

import numpy as np
import pytest

from crosscorr_lib.analysis.surrogate import max_lag_surrogate_pvalue


def _make_signal(n=2000, lag=6, strength=0.5, seed=42):
    """y отстаёт от x на известный лаг."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.7 * x[i - 1] + rng.normal(0, 1)

    noise = np.zeros(n)
    for i in range(1, n):
        noise[i] = 0.7 * noise[i - 1] + rng.normal(0, 1)

    y = np.zeros(n)
    y[lag:] = strength * x[:-lag]
    y = y + noise
    return x, y


def _make_noise(n=2000, seed=99):
    """Два независимых шумовых ряда."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    y = rng.normal(size=n)
    return x, y


def test_max_stat_finds_real_signal():
    """Реальный сигнал → маленький p-value."""
    x, y = _make_signal(n=2000, lag=6, strength=0.5)
    t_obs, p, best_lag = max_lag_surrogate_pvalue(
        x, y, max_lag=24, n_surrogates=200, seed=42
    )
    assert abs(best_lag - 6) <= 1, f"Лаг: {best_lag} (ожидали ~6)"
    assert p < 0.05, f"p-value слишком большой: {p}"


def test_max_stat_rejects_pure_noise():
    """Чистый шум → большой p-value."""
    x, y = _make_noise(n=2000)
    t_obs, p, best_lag = max_lag_surrogate_pvalue(
        x, y, max_lag=24, n_surrogates=200, seed=42
    )
    assert p > 0.1, f"Ложное срабатывание: p={p}"


def test_max_stat_is_stricter_than_naive():
    """
    Max-statistic p-value должен быть больше (строже),
    чем обычный p-value на лучшем лаге.
    """

    from crosscorr_lib.analysis.cross_correlation import (
        lagged_cross_correlation,
    )

    x, y = _make_signal(n=2000, lag=6, strength=0.3, seed=7)

    # Обычный p-value на лучшем лаге
    lags, corrs, pvals = lagged_cross_correlation(x, y, max_lag=24)
    best_idx = int(np.nanargmax(np.abs(corrs)))
    naive_p = pvals[best_idx]

    # Max-statistic p-value
    _, max_p, _ = max_lag_surrogate_pvalue(
        x, y, max_lag=24, n_surrogates=200, seed=42
    )

    # Max-statistic должен быть строже (p больше)
    assert max_p >= naive_p - 0.01, (
        f"Max-stat p={max_p:.4f} должен быть >= naive p={naive_p:.4f}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
