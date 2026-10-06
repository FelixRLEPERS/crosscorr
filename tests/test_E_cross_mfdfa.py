"""Группа E — тесты cross_mfdfa.py (Podobnik-Stanley cross-MFDFA).

Численные эталоны (стандартные DFA-показатели):
- белый шум: h(q) ≈ 0.5;
- броуновский шум (cumsum белого): h(q) ≈ 1.5;
- 1/f шум: h(q) ≈ 1.0.
Примечание: в задании значения для белого шума (≈1) и 1/f (≈0.5) были
перепутаны; тесты используют корректные физические эталоны.
"""

import numpy as np
import pytest

from crosscorr_lib.analysis.cross_mfdfa import (
    cross_mfdfa,
    cross_mfdfa_spectrum,
)

_SCALES = (16, 32, 64, 128, 256)
_Q = (-3, -1, 0, 1, 3)


def _pink_noise(n: int, seed: int) -> np.ndarray:
    """1/f шум через спектральный синтез."""
    rng = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n)
    f[0] = f[1]
    amp = 1.0 / np.sqrt(f)
    phase = rng.uniform(0, 2 * np.pi, f.size)
    spec = amp * np.exp(1j * phase)
    return np.fft.irfft(spec, n)


def test_cross_mfdfa_white_noise_half(rng):
    """x = y = белый шум: h_xy(q) ≈ 0.5 для всех q."""
    x = rng.normal(size=4000)
    res = cross_mfdfa(x, x, q_values=_Q, scales=_SCALES)
    np.testing.assert_allclose(res["h_q"], 0.5, atol=0.08)


def test_cross_mfdfa_random_walk_1_5(rng):
    """x = y = броуновский шум: h_xy(q) ≈ 1.5."""
    x = np.cumsum(rng.normal(size=4000))
    res = cross_mfdfa(x, x, q_values=_Q, scales=_SCALES)
    np.testing.assert_allclose(res["h_q"], 1.5, atol=0.15)


def test_cross_mfdfa_pink_noise_one(rng):
    """1/f шум: h_xy(q=0) ≈ 1.0."""
    x = _pink_noise(4000, seed=3)
    res = cross_mfdfa(x, x, q_values=(0,), scales=_SCALES)
    np.testing.assert_allclose(res["h_q"][0], 1.0, atol=0.15)


def test_cross_mfdfa_scales_positive(rng):
    """F_q положительны и растут с масштабом (для белого шума)."""
    x = rng.normal(size=4000)
    res = cross_mfdfa(x, x, q_values=(2,), scales=_SCALES)
    f = res["F_q"][0]
    assert np.all(f > 0)
    assert np.all(np.diff(f) > 0)


def test_cross_mfdfa_spectrum_max_is_one(rng):
    """Мультифрактальный спектр: максимум f(alpha) ≈ 1."""
    x = rng.normal(size=4000)
    res = cross_mfdfa(x, x, q_values=(-5, -3, -1, 0, 1, 3, 5), scales=_SCALES)
    spec = cross_mfdfa_spectrum(res)
    assert spec["alpha"].size > 0
    np.testing.assert_allclose(float(np.max(spec["f"])), 1.0, atol=0.1)


def test_cross_mfdfa_short_input_raises():
    """Ряд короче 100 → ValueError."""
    with pytest.raises(ValueError):
        cross_mfdfa(np.arange(50.0), np.arange(50.0))


def test_cross_mfdfa_unequal_lengths_raises(rng):
    """Разные длины x и y → ValueError (без молчаливого truncation)."""
    x = rng.normal(size=4000)
    y = rng.normal(size=4001)
    with pytest.raises(ValueError):
        cross_mfdfa(x, y)


def test_cross_mfdfa_scales_bigger_than_n_raises(rng):
    """scales > n → ValueError."""
    x = rng.normal(size=400)
    y = rng.normal(size=400)
    with pytest.raises(ValueError):
        cross_mfdfa(x, y, q_values=_Q, scales=(16, 1024))


def test_cross_mfdfa_empty_q_values_raises(rng):
    """Пустой q_values → ValueError."""
    x = rng.normal(size=4000)
    y = rng.normal(size=4000)
    with pytest.raises(ValueError):
        cross_mfdfa(x, y, q_values=[])


def test_cross_mfdfa_nan_input_raises(rng):
    """NaN во входе → ValueError."""
    x = rng.normal(size=4000)
    y = rng.normal(size=4000)
    x[5] = np.nan
    with pytest.raises(ValueError):
        cross_mfdfa(x, y)


def test_cross_mfdfa_result_has_diagnostics(rng):
    """Результат содержит r_squared и n_scales."""
    x = rng.normal(size=4000)
    res = cross_mfdfa(x, x, q_values=_Q, scales=_SCALES)
    assert "r_squared" in res
    assert "n_scales" in res
    assert res["r_squared"].shape == res["q"].shape
    assert res["n_scales"] > 0


def test_cross_mfdfa_q2_matches_dcca():
    """x = y, q=2: abs и split дают одинаковый h (все F²_v ≥ 0)."""
    rng = np.random.default_rng(42)
    x = np.cumsum(rng.standard_normal(1000))
    y = x.copy()

    result_abs = cross_mfdfa(
        x, y, q_values=[2], scales=[16, 32, 64], signed="abs"
    )
    result_split = cross_mfdfa(
        x, y, q_values=[2], scales=[16, 32, 64], signed="split"
    )

    np.testing.assert_allclose(
        result_abs["h_q"], result_split["h_plus_q"], atol=1e-10
    )
    assert result_split["n_minus"] == 0


def test_cross_mfdfa_anticorrelated_segments():
    """Половина сегментов +cov, половина −cov: abs даёт спектр, split — два."""
    rng = np.random.default_rng(42)
    n = 2000
    x = rng.standard_normal(n)

    y = np.empty(n)
    y[: n // 2] = x[: n // 2] + 0.1 * rng.standard_normal(n // 2)
    y[n // 2 :] = -x[n // 2 :] + 0.1 * rng.standard_normal(n - n // 2)

    q_values = [2, 3]
    scales = [16, 32, 64]
    result = cross_mfdfa(x, y, q_values=q_values, scales=scales, signed="split")

    assert result["n_plus"] > 0, "No positive segments found"
    assert result["n_minus"] > 0, "No negative segments found"
    assert result["n_plus"] + result["n_minus"] > 0

    assert result["h_minus_q"].shape == (len(q_values),)
    assert not np.allclose(
        result["h_plus_q"], result["h_minus_q"], atol=0.01
    ), "h_plus and h_minus are too close — test data may not be split"

    result_abs = cross_mfdfa(
        x, y, q_values=q_values, scales=scales, signed="abs"
    )
    assert np.all(np.isfinite(result_abs["h_q"]))


def test_cross_mfdfa_all_positive_matches_standard():
    """y = a*x + b (a > 0): все F²_v ≥ 0, split вырождается в abs.

    НЕ ПУТАТЬ с двумя независимыми AR(1): там на малых масштабах
    появляются отрицательные ковариации, и abs ≠ plus.
    """
    rng = np.random.default_rng(42)
    n = 2000
    x = np.cumsum(rng.standard_normal(n))
    y = 2.0 * x + 0.5

    q_values = [2, 3]
    scales = [16, 32, 64]
    result_abs = cross_mfdfa(
        x, y, q_values=q_values, scales=scales, signed="abs"
    )
    result_split = cross_mfdfa(
        x, y, q_values=q_values, scales=scales, signed="split"
    )

    assert result_split["n_minus"] == 0
    assert result_split["n_plus"] > 0
    np.testing.assert_allclose(
        result_abs["h_q"], result_split["h_plus_q"], atol=1e-10
    )
    assert np.all(np.isnan(result_split["h_minus_q"]))
