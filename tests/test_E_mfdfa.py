"""Группа E — покрытие mfdfa.py (E7).

MFDFA — опциональная зависимость; тест пропускается, если библиотека
не установлена.
"""

import numpy as np
import pytest

pytest.importorskip("MFDFA")

from crosscorr_lib.analysis.mfdfa import mfdfa_spectrum  # noqa: E402


def test_mfdfa_spectrum_shapes_and_finiteness(rng):
    """mfdfa_spectrum возвращает (lag, q, dq) согласованных форм."""
    x = rng.normal(size=512)
    lag, q, dq = mfdfa_spectrum(x)

    assert lag.ndim == 1
    assert q.ndim == 1
    assert dq.ndim == 2
    assert dq.shape[0] == len(lag)
    assert np.all(np.isfinite(dq))
    assert np.all(lag >= 1)


def test_mfdfa_spectrum_short_input_raises():
    """Ряд короче 100 отсчётов → ValueError с понятным сообщением."""
    with pytest.raises(ValueError):
        mfdfa_spectrum(np.arange(50, dtype=float))


def test_mfdfa_spectrum_custom_q(rng):
    """Явный массив q пробрасывается в результат без изменений."""
    x = rng.normal(size=512)
    q_in = np.array([-2.0, 2.0])
    _, q_out, dq = mfdfa_spectrum(x, q=q_in)
    np.testing.assert_array_equal(q_out, q_in)
    assert dq.shape[1] == len(q_in)
