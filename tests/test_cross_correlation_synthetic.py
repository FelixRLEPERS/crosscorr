"""
Synthetic benchmark для лаговой кросс-корреляции.

Проверяем, что алгоритм восстанавливает известный лаг
между двумя AR(1) процессами.
"""

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.cross_correlation import (
    build_wide_by_detector,
    lagged_cross_correlation,
    cross_correlation_pairs,
)


def _make_synthetic_series(n=2000, seed=42, lag=6, strength=0.5):
    """y отстаёт от x на известный lag."""
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

    return x, y, lag, strength


def test_lagged_cc_finds_known_lag():
    x, y, true_lag, _ = _make_synthetic_series(n=2000, lag=6)
    lags, corrs, pvals = lagged_cross_correlation(x, y, max_lag=24)
    best_lag = lags[np.argmax(np.abs(corrs))]
    assert best_lag == true_lag, (
        f"Ожидали лаг {true_lag}, получили {best_lag}"
    )


def test_lagged_cc_zero_lag():
    rng = np.random.default_rng(99)
    x = rng.normal(size=1000)
    y = rng.normal(size=1000)
    lags, corrs, _ = lagged_cross_correlation(x, y, max_lag=24)
    assert np.max(np.abs(corrs)) < 0.15


def test_lagged_cc_sign():
    x, y, true_lag, _ = _make_synthetic_series(n=2000, lag=6, seed=7)
    lags, corrs, _ = lagged_cross_correlation(x, y, max_lag=24)
    idx = np.where(lags == true_lag)[0][0]
    assert corrs[idx] > 0.3


def test_lagged_cc_with_nan():
    x, y, true_lag, _ = _make_synthetic_series(n=2000, lag=6)
    rng = np.random.default_rng(123)
    nan_mask = rng.random(x.size) < 0.05
    x = x.copy()
    x[nan_mask] = np.nan
    lags, corrs, _ = lagged_cross_correlation(x, y, max_lag=24)
    assert len(lags) == len(corrs) == 49
    best_lag = lags[np.argmax(np.abs(corrs))]
    assert abs(best_lag - true_lag) <= 1


def test_cross_correlation_pairs_tidy_format():
    x, y, _, _ = _make_synthetic_series(n=1000, lag=6)
    idx = pd.date_range("2025-01-01", periods=1000, freq="1h", tz="UTC")
    wide = pd.DataFrame({"D1": x, "D2": y}, index=idx)
    result = cross_correlation_pairs(wide, max_lag=24, alpha=0.05)
    expected_cols = {
        "detector_1", "detector_2", "lag", "correlation",
        "p_value", "q_value", "n_obs", "significant",
    }
    assert expected_cols.issubset(set(result.columns))
    assert len(result) == 1
    row = result.iloc[0]
    assert {row["detector_1"], row["detector_2"]} == {"D1", "D2"}
    assert abs(row["lag"]) == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])