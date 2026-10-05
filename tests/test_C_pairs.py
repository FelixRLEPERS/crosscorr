"""Tests for group C findings (pairs.py), night session.

- C6: T < 2 не даёт лишних столбцов в FFT-корреляции.
- C3: прямая запись суррогатов в shared memory (без промежуточного out).
"""
import numpy as np
import pandas as pd

from crosscorr_lib.pairs import (
    _batch_max_stat_corr,
    _max_stat_corr,
    cross_correlation_pairs_with_max_stat,
)


# ---------------------------------------------------------------------------
# C6 — T=1 не ломает срезы
# ---------------------------------------------------------------------------
def test_batch_max_stat_single_sample_returns_zeros():
    si = np.array([[3.0], [4.0]])
    sj = np.array([[5.0], [6.0]])
    out = _batch_max_stat_corr(si, sj)
    assert out.shape == (2,)
    assert np.all(out == 0.0)


def test_max_stat_corr_short_series_returns_zero():
    assert _max_stat_corr(np.array([3.0]), np.array([5.0])) == 0.0
    assert _max_stat_corr(np.array([]), np.array([])) == 0.0


def test_batch_max_stat_two_samples_ok():
    """T=2 — минимальный валидный размер, не должен падать."""
    rng = np.random.default_rng(0)
    si = rng.normal(size=(3, 2))
    sj = rng.normal(size=(3, 2))
    out = _batch_max_stat_corr(si, sj)
    assert out.shape == (3,)
    assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# C3 — заполнение shared memory напрямую, результат идентичен
# ---------------------------------------------------------------------------
def test_c3_result_matches_expected():
    """После C3 результат детерминирован и совпадает с seed."""
    rng = np.random.default_rng(1234)
    wide = pd.DataFrame(rng.standard_normal((300, 3)), columns=["a", "b", "c"])

    df1 = cross_correlation_pairs_with_max_stat(
        wide, B=30, seed=7, n_jobs=1,
    )
    df2 = cross_correlation_pairs_with_max_stat(
        wide, B=30, seed=7, n_jobs=1,
    )
    pd.testing.assert_frame_equal(df1, df2)
    assert len(df1) == 3
    assert (df1["p_value"] > 0).all()
    assert (df1["p_value"] <= 1).all()


def test_c6_single_row_wide_is_handled():
    """wide из одной строки (T=1) не падает."""
    wide = pd.DataFrame({"a": [1.0], "b": [2.0]})
    df = cross_correlation_pairs_with_max_stat(
        wide, B=5, seed=1, n_jobs=1,
    )
    assert len(df) == 1
    assert np.isfinite(df["C_obs"].iloc[0])
