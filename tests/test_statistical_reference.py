"""Численные эталоны для ключевых статистических функций CrossCorr.

Каждый эталон вычисляется аналитически или из формулы, заданной в тесте,
и фиксируется в assert. Цель — ловить регрессии в логике, а не в тексте
исходника.

Ссылки:
    Benjamini & Hochberg (1995), JRSS-B 57(1), 289-300.
    Benjamini & Yekutieli (2001), Ann. Statist. 29(4), 1165-1188.
"""

import numpy as np

from crosscorr_lib.analysis.cross_correlation import (
    lagged_cross_correlation,
)
from crosscorr_lib.analysis.surrogate import (
    benjamini_yekutieli,
    fdr_bh_q,
    fisher_weighted_max_stat,
    max_lag_surrogate_pvalue,
)


# ---------------------------------------------------------------------------
# ЭТАЛОН 1 — fdr_bh_q (Benjamini-Hochberg)
# ---------------------------------------------------------------------------
def test_fdr_bh_q_reference():
    """BH с эталонным входом.

    p = [0.01, 0.02, 0.03, 0.04, 0.05], m = 5.
    BH q_(i) = p_(i) * m / rank, с монотонизацией (минимум справа налево).
    p_(i) = 0.01*i, rank = i → q_(i) = 0.01*i*5/i = 0.05 для всех i.
    Эталон: [0.05, 0.05, 0.05, 0.05, 0.05].
    """
    p = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
    reject, q = fdr_bh_q(p, alpha=0.05, method="bh")
    expected = np.array([0.05, 0.05, 0.05, 0.05, 0.05])
    np.testing.assert_allclose(q, expected, atol=1e-12)
    assert reject.all()


def test_fdr_bh_q_monotone():
    """q-values не убывают по отсортированному p.

    Для любого входа после сортировки p возрастанию соответствует
    неубывание q (монотонизация np.minimum.accumulate в обратном порядке).
    """
    rng = np.random.default_rng(0)
    p = rng.uniform(0, 1, size=50)
    _, q = fdr_bh_q(p, alpha=0.05, method="bh")

    order = np.argsort(p)
    q_sorted = q[order]
    assert np.all(np.diff(q_sorted) >= -1e-12), "q-values не монотонны"


def test_fdr_bh_q_nan_propagates():
    """NaN в p → NaN в q; остальные компоненты совпадают с версией без NaN."""
    p = np.array([0.01, np.nan, 0.03, 0.04, 0.05])
    _, q = fdr_bh_q(p, alpha=0.05, method="bh")
    assert np.isnan(q[1])

    p_clean = np.array([0.01, 0.03, 0.04, 0.05])
    _, q_clean = fdr_bh_q(p_clean, alpha=0.05, method="bh")
    np.testing.assert_allclose(q[[0, 2, 3, 4]], q_clean, atol=1e-12)


# ---------------------------------------------------------------------------
# ЭТАЛОН 2 — benjamini_yekutieli (BY)
# ---------------------------------------------------------------------------
def test_benjamini_yekutieli_reference():
    """BY с эталоном.

    c(m) = sum(1/k, k=1..m). m=5: c = 1 + 1/2 + 1/3 + 1/4 + 1/5 = 137/60.
    p_(i) = 0.001*i, rank = i → q_(i) = 0.001*i * m * c / i = 0.005*c.
    Эталон: все q равны 0.005*c (монотонизация не меняет).
    """
    m = 5
    c_m = np.sum(1.0 / np.arange(1, m + 1))  # 137/60
    p = np.array([0.001, 0.002, 0.003, 0.004, 0.005])
    _, q = benjamini_yekutieli(p, alpha=0.05)
    expected = np.full(m, 0.005 * c_m)
    np.testing.assert_allclose(q, expected, atol=1e-12)


def test_by_more_conservative_than_bh():
    """BY даёт q >= BH на одном входе (c(m) >= 1 — гармоническая поправка)."""
    p = np.array([0.001, 0.01, 0.02, 0.04, 0.2])
    _, q_bh = fdr_bh_q(p, alpha=0.05, method="bh")
    _, q_by = fdr_bh_q(p, alpha=0.05, method="by")
    assert np.all(q_by >= q_bh - 1e-12), "BY должен быть не мягче BH"


# ---------------------------------------------------------------------------
# ЭТАЛОН 3 — max_lag_surrogate_pvalue и fisher_weighted_max_stat
# ---------------------------------------------------------------------------
def _signal_with_lag(n=2000, lag=6, strength=0.5, seed=42):
    """AR(1)-сигнал с известным лагом (как в test_max_statistic.py).

    x, noise — AR(1) с phi=0.7. y[lag:] = strength * x[:-lag] + noise.
    Параметры заимствованы из существующего детерминированного теста
    test_max_stat_finds_real_signal, чтобы эталон не был флейким.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    noise = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.7 * x[i - 1] + rng.normal(0, 1)
        noise[i] = 0.7 * noise[i - 1] + rng.normal(0, 1)
    y = np.zeros(n)
    y[lag:] = strength * x[:-lag]
    y = y + noise
    return x, y


def test_max_stat_recovers_known_lag():
    """Синтетика lag=6, strength=0.5 → best_lag ≈ 6, p < 0.05."""
    x, y = _signal_with_lag(n=2000, lag=6, strength=0.5, seed=42)
    t_obs, p, best_lag = max_lag_surrogate_pvalue(
        x, y, max_lag=24, n_surrogates=200, seed=42
    )
    assert abs(best_lag - 6) <= 1, f"best_lag={best_lag}, ожидали ~6"
    assert p < 0.05, f"p={p} слишком большой для реального сигнала"
    assert np.isfinite(t_obs)


def test_max_stat_rejects_pure_noise():
    """На чистом шуме p-value не вырожденно мал.

    p-value под H0 ~ Uniform(0,1); минимум при B=200 равен 1/201.
    Параметры и seed заимствованы из детерминированного
    test_max_stat_rejects_pure_noise (p > 0.1). Здесь проверяем более
    слабое условие: p не у самого дна распределения.
    """
    rng = np.random.default_rng(99)
    x = rng.normal(size=2000)
    y = rng.normal(size=2000)
    _, p, _ = max_lag_surrogate_pvalue(
        x, y, max_lag=24, n_surrogates=200, seed=42
    )
    min_p = 1.0 / (200 + 1)
    assert p > 3 * min_p, f"шум дал вырожденно малый p={p}"


def test_fisher_weighted_max_stat_reference():
    """Прямой вызов fisher_weighted_max_stat с аналитическим эталоном.

    rho = [0.5, -0.3], n = 20 на обоих лагах.
    z = arctanh(rho); w = sqrt(n - 3) = sqrt(17).
    score = |z| * w. T = max(score).
    Эталон: max(|arctanh(0.5)|, |arctanh(-0.3)|) * sqrt(17).
    """
    rho = np.array([0.5, -0.3])
    n = np.array([20, 20])
    t, idx, rho_at = fisher_weighted_max_stat(rho, n)

    expected = max(abs(np.arctanh(0.5)), abs(np.arctanh(-0.3))) * np.sqrt(17)
    np.testing.assert_allclose(t, expected, rtol=1e-12)
    assert idx == 0, "argmax должен указывать на лаг с rho=0.5"
    np.testing.assert_allclose(rho_at, 0.5, atol=1e-12)


def test_fisher_weighted_max_stat_ignores_small_n():
    """Лаг с n <= 3 исключается из максимума (finite = n > 3)."""
    rho = np.array([0.9, 0.1])
    n = np.array([3, 50])
    t, idx, _ = fisher_weighted_max_stat(rho, n)
    expected = abs(np.arctanh(0.1)) * np.sqrt(50 - 3)
    np.testing.assert_allclose(t, expected, rtol=1e-12)
    assert idx == 1


# ---------------------------------------------------------------------------
# ЭТАЛОН 4 — lagged_cross_correlation
# ---------------------------------------------------------------------------
def test_lagged_cc_recovers_known_lag():
    """y = x(t-5) без шума → best_lag = 5, rho ≈ 1.

    Знак лага: lag > 0 означает y отстаёт (y(t) связан с x(t-lag)).
    Сдвинутый на +5 ряд y[5:] = x[:-5] даёт максимум на lag = 5.
    """
    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    lag = 5
    y = np.concatenate([np.zeros(lag), x[:-lag]])

    lags, corrs, _ = lagged_cross_correlation(x, y, max_lag=15)
    best = int(lags[int(np.nanargmax(np.abs(corrs)))])
    assert best == lag, f"best_lag={best}, ожидали {lag}"
    rho_best = corrs[np.where(lags == lag)[0][0]]
    assert abs(rho_best) > 0.99, f"rho на известном лаге = {rho_best}"


def test_lagged_cc_zero_lag():
    """y = x → best_lag = 0, rho ≈ 1."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    lags, corrs, _ = lagged_cross_correlation(x, x, max_lag=10)
    best = int(lags[int(np.nanargmax(np.abs(corrs)))])
    assert best == 0
    np.testing.assert_allclose(corrs[np.where(lags == 0)[0][0]], 1.0, atol=1e-9)


def test_lagged_cc_sign():
    """y = -x → rho ≈ -1 на lag 0 (знак сохраняется)."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    lags, corrs, _ = lagged_cross_correlation(x, -x, max_lag=10)
    rho0 = corrs[np.where(lags == 0)[0][0]]
    np.testing.assert_allclose(rho0, -1.0, atol=1e-9)
