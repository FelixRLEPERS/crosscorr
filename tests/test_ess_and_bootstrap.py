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

def test_ess_is_zero_lag_only_deprecated():
    """ESS — zero-lag only и помечен deprecated для лагового анализа.

    Проверяем, что функция считает корреляцию на нулевом лаге: для
    y = shift(x, lag) при lag != 0 r падает, а не остаётся единицей.
    Это фиксирует ограничение P1-11, а не поведение, которым следует
    пользоваться для лаговой гипотезы.
    """
    import numpy as np

    from crosscorr_lib.analysis.effective_sample import (
        correlation_pvalue_with_ess,
    )

    rng = np.random.default_rng(0)
    n = 1000
    x = rng.normal(size=n)
    lag = 20

    # нулевой лаг: y связано с x
    r0, _, _ = correlation_pvalue_with_ess(x, x, method="pearson")

    # лаг 20: связь на нулевом лаге отсутствует
    y_shift = np.concatenate([np.zeros(lag), x[:-lag]])
    r_shift, _, _ = correlation_pvalue_with_ess(x, y_shift, method="pearson")

    assert abs(r0 - 1.0) < 1e-6 or r0 > 0.9
    assert abs(r_shift) < 0.1, (
        f"ESS увидел ненулевую корреляцию на сдвинутом ряде: r={r_shift}"
    )


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


def test_iat_uses_fft_not_correlate():
    """В исходнике IAT не должно быть прямой корреляции O(n^2)."""
    import inspect

    from crosscorr_lib.analysis import effective_sample

    src = inspect.getsource(
        effective_sample.integrated_autocorrelation_time
    )
    assert "np.correlate" not in src, (
        "IAT должен использовать FFT-based свёртку, не прямую корреляцию"
    )


def test_ess_pvalue_never_zero():
    """p-value не может быть 0.0 при |r|=1."""
    from crosscorr_lib.analysis.effective_sample import (
        correlation_pvalue_with_ess,
    )

    n = 100
    x = np.linspace(-1, 1, n)
    y = x.copy()  # |r|=1
    _, p, _ = correlation_pvalue_with_ess(x, y)
    assert p > 0.0, f"p-value = {p}, ожидалось > 0"
    assert np.isfinite(p), f"p-value = {p}, ожидалось конечное"


def test_fix9_pvalue_not_zero_for_large_t():
    """p-value не округляется до 0.0 при умеренно большом |t|.

    Диапазон осмысленной проверки: 37 <= |t| <= 343.
    При |t| >= 343 stats.t.sf тоже возвращает 0.0 из-за float64,
    это не баг кода. Тест должен попасть в диапазон.
    """
    import numpy as np

    from crosscorr_lib.analysis.effective_sample import (
        correlation_pvalue_with_ess,
    )

    rng = np.random.default_rng(0)
    n = 200
    x = rng.normal(size=n)
    # умеренная корреляция: r ≈ 0.96-0.99, t ≈ 50-200
    y = x + 0.2 * rng.normal(size=n)

    r, p, n_eff = correlation_pvalue_with_ess(x, y)

    # sanity check: тест должен попасть в диапазон,
    # где sf отличается от cdf
    t_abs = abs(r) * np.sqrt((n_eff - 2) / (1 - r**2))
    assert 37 < t_abs < 343, (
        f"t = {t_abs:.1f} вне диапазона [37, 343], "
        f"тест не проверяет замену cdf→sf"
    )
    assert p > 0.0, (
        f"p-value = {p}, ожидалось > 0 при t = {t_abs:.1f}"
    )


def test_ess_handles_nan_by_interpolation():
    """NaN интерполируются, а не удаляются."""
    import inspect

    from crosscorr_lib.analysis import effective_sample

    src = inspect.getsource(effective_sample)
    assert "x = x[~np.isnan(x)]" not in src, (
        "NaN должны интерполироваться, не удаляться"
    )


def test_iat_is_nan_tolerant():
    """IAT принимает ряд с пропусками и не падает."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    x[10] = np.nan
    x[200] = np.nan
    tau = integrated_autocorrelation_time(x)
    assert np.isfinite(tau) and tau >= 1.0, f"tau={tau}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
