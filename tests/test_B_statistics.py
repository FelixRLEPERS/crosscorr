"""Тесты группы B (ядро анализа), ночная сессия.

- B24: n_obs считается по исходным данным, не после интерполяции NaN.
- B38: argsort в FDR стабилен при ties.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.cross_correlation import (
    cross_correlation_pairs,
    cross_correlation_pairs_with_max_stat,
)
from crosscorr_lib.analysis.surrogate import fdr_bh_q


# ---------------------------------------------------------------------------
# B24 — n_obs не включает интерполированные точки
# ---------------------------------------------------------------------------
def test_n_obs_excludes_interpolated_points_max_stat():
    rng = np.random.default_rng(0)
    n = 200
    a = rng.normal(size=n)
    b = 0.5 * a + rng.normal(size=n)
    a[10:60] = np.nan
    wide = pd.DataFrame({"a": a, "b": b})

    raw_valid = int((~np.isnan(a) & ~np.isnan(b)).sum())
    df = cross_correlation_pairs_with_max_stat(
        wide, max_lag=10, n_surrogates=30, seed=1,
    )
    assert int(df["n_obs"].iloc[0]) == raw_valid


def test_n_obs_excludes_interpolated_points_naive():
    rng = np.random.default_rng(0)
    n = 200
    a = rng.normal(size=n)
    b = 0.5 * a + rng.normal(size=n)
    a[10:60] = np.nan
    wide = pd.DataFrame({"a": a, "b": b})

    raw_valid = int((~np.isnan(a) & ~np.isnan(b)).sum())
    df = cross_correlation_pairs(wide, max_lag=10)
    assert int(df["n_obs"].iloc[0]) == raw_valid


def test_n_obs_unchanged_without_nan():
    """Без NaN правка не меняет n_obs (регрессия)."""
    rng = np.random.default_rng(2)
    n = 150
    wide = pd.DataFrame(rng.normal(size=(n, 3)), columns=["a", "b", "c"])
    df = cross_correlation_pairs(wide, max_lag=10)
    assert (df["n_obs"] == n).all()


# ---------------------------------------------------------------------------
# B38 — стабильный порядок при ties
# ---------------------------------------------------------------------------
def test_fdr_ties_are_stable_across_calls():
    p = np.array([0.01, 0.01, 0.01, 0.02, 0.03])
    r1, q1 = fdr_bh_q(p, alpha=0.05, method="bh")
    r2, q2 = fdr_bh_q(p, alpha=0.05, method="bh")
    np.testing.assert_array_equal(r1, r2)
    np.testing.assert_allclose(q1, q2)
    # равные p получают равные q
    assert q1[0] == q1[1] == q1[2]
