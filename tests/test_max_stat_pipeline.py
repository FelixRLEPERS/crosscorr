"""
Тесты интеграции max-statistic в основной пайплайн.

Проверяем, что cross_correlation_pairs_with_max_stat:
- находит реальный сигнал (лаг=6) с p < 0.05
- не находит ложный сигнал на шуме с p > 0.05
"""

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.cross_correlation import (
    cross_correlation_pairs_with_max_stat,
)


def _make_signal_wide(n_time=1500, lag=6, strength=0.5, seed=42):
    """Один детектор с сильным сигналом, второй — шум."""
    rng = np.random.default_rng(seed)

    x = np.zeros(n_time)
    for i in range(1, n_time):
        x[i] = 0.7 * x[i - 1] + rng.normal(0, 1)

    noise = np.zeros(n_time)
    for i in range(1, n_time):
        noise[i] = 0.7 * noise[i - 1] + rng.normal(0, 1)

    y = np.zeros(n_time)
    y[lag:] = strength * x[:-lag]
    y = y + noise

    idx = pd.date_range("2025-01-01", periods=n_time, freq="1h", tz="UTC")
    return pd.DataFrame({"D1": x, "D2": y}, index=idx), lag


def _make_noise_wide(n_time=1500, seed=42):
    """Два независимых AR(1) шума."""
    rng = np.random.default_rng(seed)

    def ar1():
        s = np.zeros(n_time)
        for i in range(1, n_time):
            s[i] = 0.7 * s[i - 1] + rng.normal(0, 1)
        return s

    idx = pd.date_range("2025-01-01", periods=n_time, freq="1h", tz="UTC")
    return pd.DataFrame({"D1": ar1(), "D2": ar1()}, index=idx)


def test_max_stat_pipeline_finds_signal():
    """Реальный сигнал → p < 0.05, лаг найден."""
    wide, true_lag = _make_signal_wide(n_time=1500, lag=6)

    result = cross_correlation_pairs_with_max_stat(
        wide, max_lag=24, alpha=0.05, n_surrogates=200, seed=42
    )

    assert len(result) == 1
    row = result.iloc[0]
    assert abs(row["lag"]) == true_lag, (
        f"Ожидали |lag|={true_lag}, получили {row['lag']}"
    )
    assert row["p_value"] < 0.05, (
        f"p-value={row['p_value']} слишком большой для реального сигнала"
    )
    assert row["significant"], "Сигнал должен быть значимым"


def test_max_stat_pipeline_rejects_noise():
    """Чистый шум → p > 0.05, не значимо."""
    wide = _make_noise_wide(n_time=1500)

    result = cross_correlation_pairs_with_max_stat(
        wide, max_lag=24, alpha=0.05, n_surrogates=200, seed=42
    )

    assert len(result) == 1
    row = result.iloc[0]
    assert row["p_value"] > 0.05, (
        f"Ложное срабатывание: p={row['p_value']}"
    )
    assert not row["significant"], "Шум не должен быть значимым"


def test_max_stat_pipeline_tidy_format():
    """Проверка формата выходной таблицы."""
    wide, _ = _make_signal_wide(n_time=1000, lag=6)

    result = cross_correlation_pairs_with_max_stat(
        wide, max_lag=24, alpha=0.05, n_surrogates=100, seed=42
    )

    expected_cols = {
        "detector_1", "detector_2", "lag", "correlation",
        "p_value", "q_value", "n_obs", "significant", "n_surrogates",
    }
    assert expected_cols.issubset(set(result.columns)), (
        f"Отсутствуют колонки: {expected_cols - set(result.columns)}"
    )
    assert result["n_surrogates"].iloc[0] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])