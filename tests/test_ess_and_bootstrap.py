"""
Тесты effective sample size и block bootstrap.
"""

import numpy as np
import pytest

from crosscorr_lib.analysis.block_bootstrap import (
    block_bootstrap_pvalue,
    block_bootstrap_surrogate,
)
from crosscorr_lib.analysis.effective_sample import (
    correlation_pvalue_with_ess,
    effective_sample_size,
    integrated_autocorrelation_time,
)

# ============ ESS ============

def test_iat_white_noise():
    """Для белого шума τ_int ≈ 1."""
    rng = np.random.default_rng(42)
    x = rng.normal(size=2000)
    tau = integrated_autocorrelation_time(x)
    assert 0.9 <= tau <= 1.5, f"τ_int={tau:.3f} (ожидали ≈1)"


def test_iat_ar1_decreases_with_phi():
    """С ростом φ растёт τ_int."""
    rng = np.random.default_rng(42)
    n = 2000

    taus = []
    for phi in [0.0, 0.5, 0.7, 0.9]:
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = phi * x[i - 1] + rng.normal(0, 1)
        taus.append(integrated_autocorrelation_time(x))

    # τ_int монотонно растёт
    for i in range(len(taus) - 1):
        assert taus[i] < taus[i + 1], (
            f"τ_int не растёт: {taus[i]:.3f} >= {taus[i+1]:.3f}"
        )

    print(f"\n  τ_int: {[f'{t:.2f}' for t in taus]}")


def test_ess_reduces_with_autocorrelation():
    """N_eff << N при высокой автокорреляции."""
    rng = np.random.default_rng(42)
    n = 2000

    # Сильно автокоррелированный
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0, 1)

    y = x + 0.5 * rng.normal(size=n)

    n_eff = effective_sample_size(x, y)
    assert n_eff < n / 2, (
        f"N_eff={n_eff:.0f} не меньше N/2={n/2:.0f}"
    )
    print(f"\n  N={n}, N_eff={n_eff:.0f}, ratio={n_eff/n:.3f}")


def test_correlation_pvalue_with_ess_is_stricter():
    """ESS-скорректированный p-value строже наивного."""
    from scipy import stats

    rng = np.random.default_rng(42)
    n = 1000

    # Слабая автокорреляция + слабая связь
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.5 * x[i - 1] + rng.normal(0, 1)

    # Слабая связь — чтобы p-value не уходил в underflow
    y = 0.15 * x + 1.0 * rng.normal(size=n)

    # Наивный p-value
    r_naive, p_naive = stats.pearsonr(x, y)

    # ESS-скорректированный
    r_ess, p_ess, n_eff = correlation_pvalue_with_ess(x, y, method="pearson")

    # r должен совпадать (используем одну и ту же корреляцию)
    assert abs(r_naive - r_ess) < 1e-6, (
        f"r_naive={r_naive:.6f}, r_ess={r_ess:.6f}"
    )

    # ESS-версия должна давать строже (больше) p-value
    # (с допуском на численные эффекты)
    assert p_ess >= p_naive * 0.9, (
        f"p_ess={p_ess:.6e} должен быть ≥ p_naive={p_naive:.6e}"
    )

    print(f"\n  p_naive={p_naive:.4e}")
    print(f"  p_ess  ={p_ess:.4e}")
    print(f"  N_eff  ={n_eff:.0f}")

# ============ Block Bootstrap ============

def test_block_bootstrap_preserves_length():
    """Суррогат той же длины, что исходный ряд."""
    rng = np.random.default_rng(42)
    x = rng.normal(size=500)
    surr = block_bootstrap_surrogate(x, block_size=24, rng=rng)
    assert surr.shape == x.shape


def test_block_bootstrap_destroys_correlation():
    """Block bootstrap находит связь на zero-lag."""
    rng = np.random.default_rng(42)
    n = 1000

    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.7 * x[i - 1] + rng.normal(0, 1)

    # Zero-lag связь (не сдвиг!) — block_bootstrap_pvalue считает zero-lag Pearson
    y = 0.5 * x + 0.3 * rng.normal(size=n)

    r, p = block_bootstrap_pvalue(
        x, y, block_size=24, n_surrogates=200, seed=42
    )
    assert r > 0.3, f"Наблюдаемая корреляция r={r:.3f} слишком мала"
    assert p < 0.05, f"p={p:.4f} слишком большой для реального сигнала"
    print(f"\n  r={r:.4f}, p={p:.4f} (реальный сигнал, zero-lag)")

def test_block_bootstrap_rejects_noise():
    """Block bootstrap отклоняет чистый шум."""
    rng = np.random.default_rng(42)
    n = 1000

    x = rng.normal(size=n)
    y = rng.normal(size=n)

    r, p = block_bootstrap_pvalue(
        x, y, block_size=24, n_surrogates=200, seed=42
    )
    assert p > 0.05, f"Ложное срабатывание: p={p:.4f}"
    print(f"\n  r={r:.4f}, p={p:.4f} (чистый шум)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
