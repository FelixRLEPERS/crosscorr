"""
Effective sample size (ESS) для автокоррелированных временных рядов.

Проблема: обычный p-value для корреляции предполагает НЕЗАВИСИМЫЕ
наблюдения. Для AR(1) процессов с φ=0.7 эффективный размер выборки
падает в ~5 раз. Это значит, что p-value завышает значимость.

Решение: интегрированное время автокорреляции (IAT):

    τ_int = 1 + 2 * Σ_{k=1}^{K} ρ(k)
    N_eff = N / τ_int

Для AR(1): N_eff = N * (1 - φ) / (1 + φ)

Дополнительно: скорректированный t-статистика для корреляции:

    t = r * sqrt(N_eff - 2) / sqrt(1 - r²)
    p = 2 * SF_t(|t|, df=N_eff - 2)
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from scipy.signal import fftconvolve

# Число подряд идущих лагов ниже порога, после которого суммирование
# автокорреляции прекращается.
N_CONSECUTIVE = 5
# Квантиль нормального распределения для 95% доверия (двусторонний).
Z_95 = 1.96
# Минимальное число наблюдений для оценки автокорреляции/корреляции.
MIN_SAMPLES = 10


def integrated_autocorrelation_time(
    x: np.ndarray,
    max_lag: int | None = None,
) -> float:
    """
    Оценка интегрированного времени автокорреляции τ_int.

    τ_int = 1 + 2 * Σ_{k=1}^{K} ρ(k)

    где ρ(k) — выборочная автокорреляция на лаге k.

    Правило остановки: суммирование продолжается, пока подряд не
    наберётся N_CONSECUTIVE (5) лагов с |ρ(k)| ниже порога
    1.96 / sqrt(n); одиночное пересечение порога не прерывает сумму
    (это флуктуация, а не конец автокорреляции).

    Args:
        x: 1D временной ряд (без NaN).
        max_lag: максимальный лаг. По умолчанию min(N//4, 100).

    Returns:
        τ_int ≥ 1. Для белого шума ≈ 1.
    """
    x = np.asarray(x, dtype=float)
    if np.isnan(x).any():
        idx = np.arange(x.size)
        good = np.isfinite(x)
        if good.sum() < 2:
            return 1.0
        x = np.interp(idx, idx[good], x[good])
    n = x.size

    if n < MIN_SAMPLES:
        return 1.0

    if max_lag is None:
        max_lag = min(n // 4, 100)

    x_centered = x - x.mean()
    var = np.var(x_centered)
    if var == 0:
        return 1.0

    # FFT-based свёртка (O(n log n)) вместо прямой свёртки (O(n²)).
    # Корреляция = свёртка с развёрнутым рядом; lag 0 совпадает с var(x).
    acf = fftconvolve(x_centered, x_centered[::-1], mode="full")
    acf = acf[n - 1 :]  # положительные лаги
    acf = acf / acf[0]  # нормировка ρ(0) = 1

    # Окно обрезки: суммируем, пока |rho_k| не остаётся ниже порога
    # на протяжении N_CONSECUTIVE подряд лагов. Одиночное пересечение
    # порога — флуктуация, а не конец автокорреляции; прежний break
    # обрывал сумму на первом же таком лаге, занижая tau и завышая N_eff.
    threshold = Z_95 / np.sqrt(n)

    tau = 1.0
    below = 0
    for k in range(1, min(max_lag + 1, len(acf))):
        rho_k = acf[k]
        if abs(rho_k) < threshold:
            below += 1
            if below >= N_CONSECUTIVE:
                break
        else:
            below = 0
            tau += 2 * rho_k

    return max(tau, 1.0)


def effective_sample_size(x: np.ndarray, y: np.ndarray) -> float:
    """
    Эффективный размер выборки для пары (x, y).

    Использует консервативную оценку:
        N_eff = N / max(τ_x, τ_y)

    Args:
        x, y: одномерные ряды (могут содержать NaN).

    Returns:
        N_eff — эффективный размер выборки.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    n = int(mask.sum())

    if n < MIN_SAMPLES:
        return float(n)

    tau_x = integrated_autocorrelation_time(x[mask])
    tau_y = integrated_autocorrelation_time(y[mask])
    tau = max(tau_x, tau_y)

    return float(n / tau)


def correlation_pvalue_with_ess(
    x: np.ndarray,
    y: np.ndarray,
    method: str = "pearson",
) -> tuple[float, float, float]:
    """
    Корреляция с p-value, скорректированным на автокорреляцию.

    Args:
        x, y: одномерные ряды.
        method: 'pearson' или 'spearman'.

    Returns:
        (r, p_value, n_eff)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x_v, y_v = x[mask], y[mask]
    n = x_v.size

    if n < MIN_SAMPLES:
        return np.nan, 1.0, float(n)

    # Корреляция
    if method == "spearman":
        r, _ = stats.spearmanr(x_v, y_v)
    else:
        r, _ = stats.pearsonr(x_v, y_v)

    if np.isnan(r):
        return float(r), 1.0, float(n)

    if abs(r) >= 1.0:
        # Ровно 0.0 невозможен для корректного теста: логарифмы ломаются,
        # агрегированная статистика (Fisher) даёт -inf. Нижняя граница 1/n_eff.
        n_eff = effective_sample_size(x_v, y_v)
        if np.isfinite(n_eff) and n_eff > 0:
            p_floor = min(1.0, 1.0 / float(n_eff))
        else:
            p_floor = 1.0
        return float(r), float(p_floor), float(n_eff)

    # Эффективный размер выборки
    n_eff = effective_sample_size(x_v, y_v)

    if n_eff <= 2:
        return float(r), 1.0, float(n_eff)

    # t-статистика с n_eff - 2 степенями свободы.
    # sf (survival function) вместо 1 - cdf: при |t| >= 37 выражение
    # 1 - cdf округляется до 0.0 из-за float-точности, sf сохраняет хвост.
    t = r * np.sqrt(n_eff - 2) / np.sqrt(1 - r * r)
    p = 2 * stats.t.sf(abs(t), df=n_eff - 2)

    return float(r), float(p), float(n_eff)


def main() -> None:
    """CLI: демонстрация ESS на AR(1) разных φ."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--phi", type=float, nargs="+", default=[0.0, 0.5, 0.7, 0.9])
    args = parser.parse_args()

    rng = np.random.default_rng(42)

    print(f"\nN = {args.n}\n")
    print(f"{'phi':>6} | {'τ_int':>8} | {'N_eff':>8} | {'ratio':>8}")
    print("-" * 42)

    for phi in args.phi:
        x = np.zeros(args.n)
        for i in range(1, args.n):
            x[i] = phi * x[i - 1] + rng.normal(0, 1)

        tau = integrated_autocorrelation_time(x)
        n_eff = args.n / tau
        ratio = n_eff / args.n
        print(f"{phi:>6.2f} | {tau:>8.3f} | {n_eff:>8.1f} | {ratio:>8.3f}")

    print()


if __name__ == "__main__":
    main()
