"""Группа E — покрытие stationarity.py (E7)."""

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.stationarity import (
    adf_test,
    check_stationarity_wide,
)


def _ar1(n: int, phi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + rng.normal(0, 1)
    return x


def test_adf_test_white_noise_is_stationary(rng):
    """Белый шум → p-value мало, ряд признан стационарным."""
    result = adf_test(rng.normal(size=500))
    assert result["is_stationary"] is True
    assert result["p_value"] < 0.05
    assert result["n_obs"] > 0
    assert set(result["critical_values"]) >= {"1%", "5%", "10%"}


def test_adf_test_random_walk_not_stationary(rng):
    """Случайное блуждание (сумма шума) → нестационарно, p-value велико."""
    result = adf_test(np.cumsum(rng.normal(size=500)))
    assert result["is_stationary"] is False
    assert result["p_value"] > 0.05


def test_adf_test_short_input_is_degenerate():
    """Короткий ряд (< 20) → статистика NaN, p=1.0, без падения."""
    result = adf_test(np.arange(10, dtype=float))
    assert np.isnan(result["statistic"])
    assert result["p_value"] == 1.0
    assert result["is_stationary"] is False
    assert result["n_obs"] == 10


def test_check_stationarity_wide_columns_and_flags(rng):
    """check_stationarity_wide возвращает строку на колонку с флагом."""
    wide = pd.DataFrame({
        "white": rng.normal(size=400),
        "rw": np.cumsum(rng.normal(size=400)),
    })
    result = check_stationarity_wide(wide, verbose=False)

    assert len(result) == 2
    assert set(result["detector"]) == {"white", "rw"}
    assert set(result.columns) >= {
        "detector", "statistic", "p_value", "n_lags",
        "n_obs", "is_stationary",
    }
    flags = dict(zip(result["detector"], result["is_stationary"], strict=True))
    assert flags["white"] is True
    assert flags["rw"] is False
