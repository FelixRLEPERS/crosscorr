"""Тесты для max-statistic null в лаговой кросс-корреляции."""

import numpy as np
import pandas as pd
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


def test_time_shift_null_statistic_comparable():
    """Для time_shift Fisher-веса согласованы между наблюдением и нулём.

    На чистом шуме p-value не должен быть вырожденно мал: если бы веса
    суррогата брались от наблюдения, нуль был бы консервативным и/или
    смещённым. Проверяем, что результат конечен и не минимален.
    """
    x, y = _make_noise(n=500, seed=7)
    t_obs, p, best_lag = max_lag_surrogate_pvalue(
        x, y, max_lag=24, n_surrogates=200, seed=42,
        surrogate_method="time_shift",
    )
    assert np.isfinite(t_obs)
    assert np.isfinite(p)
    # На чистом шуме p ~ Uniform(0, 1). Дегенератный случай (баг #7) —
    # когда p близко к минимуму 1/(B+1) ≈ 0.005. Проверяем, что
    # p-value не вырожденно мал, а не что он > 0.05.
    min_degenerate = 1.0 / (200 + 1)  # B=200 в вызове выше
    assert p > 3 * min_degenerate, (
        f"time_shift на шуме дал p={p}, ожидали > {3 * min_degenerate:.4f}"
    )


def test_max_lag_exceeds_n_raises():
    """max_lag >= n → ValueError с понятным сообщением."""
    x = np.random.default_rng(0).normal(size=50)
    y = np.random.default_rng(1).normal(size=50)
    with pytest.raises(ValueError, match="max_lag"):
        max_lag_surrogate_pvalue(
            x, y, max_lag=100, n_surrogates=10, seed=42,
        )


def test_max_lag_negative_raises():
    """max_lag < 0 → ValueError."""
    x = np.random.default_rng(0).normal(size=50)
    y = np.random.default_rng(1).normal(size=50)
    with pytest.raises(ValueError, match="max_lag"):
        max_lag_surrogate_pvalue(
            x, y, max_lag=-1, n_surrogates=10, seed=42,
        )


def test_surrogate_test_nan_consistent():
    """surrogate_test считает real и null на одной маске NaN.

    На двух независимых рядах с NaN p-value не должен быть минимальным:
    real и нуль сравнимы, ложной значимости нет.
    """
    from crosscorr_lib.analysis.surrogate import surrogate_test

    rng = np.random.default_rng(0)
    n = 300
    x = rng.normal(size=n)
    y = rng.normal(size=n)
    wide = pd.DataFrame({"x": x, "y": y})
    wide.loc[10:40, "x"] = np.nan
    wide.loc[100:130, "y"] = np.nan

    pvals = surrogate_test(wide, n_surrogates=100, seed=42)
    p = pvals.loc["x", "y"]
    # На независимых рядах p ~ Uniform(0, 1). Проверяем, что p-value
    # не вырожденно мал (минимум 1/(B+1)), а не что он > 0.05.
    min_degenerate = 1.0 / (100 + 1)  # B=100 в вызове выше
    assert p > 3 * min_degenerate, (
        f"Ложное срабатывание при согласованной NaN-маске: p={p}, "
        f"ожидали > {3 * min_degenerate:.4f}"
    )
    assert np.isfinite(p)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
