"""
Benchmark utilities для power_curve.py.

Заменяет core.benchmark() из CrossCorr 2.0 на наш API.

Генерирует синтетику (AR(1) + coupling на лаге), прогоняет
max_lag_surrogate_pvalue, возвращает dict с hit/detected_lag/rho_max/p_value.
"""

from __future__ import annotations

import numpy as np

from crosscorr_lib.analysis.surrogate import max_lag_surrogate_pvalue


def synthetic_ar1_pair(
    n: int,
    true_lag: int,
    coupling: float,
    ar: float = 0.85,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Генерирует пару AR(1) рядов с известной связью.

    x(t) = ar * x(t-1) + noise
    y(t) = coupling * x(t - true_lag) + ar * y(t-1) + noise
    """
    rng = np.random.default_rng(seed)

    x = np.zeros(n)
    for i in range(1, n):
        x[i] = ar * x[i - 1] + rng.normal(0, 1)

    y = np.zeros(n)
    for i in range(1, n):
        link = coupling * x[i - true_lag] if i >= true_lag else 0.0
        y[i] = ar * y[i - 1] + link + rng.normal(0, 1)

    return x, y


def benchmark(
    true_lag: int = 6,
    coupling: float = 0.15,
    n: int = 4000,
    max_lag: int = 24,
    n_surrogates: int = 200,
    null_model_name: str = "phase",
    seed: int = 0,
    ar: float = 0.85,
) -> dict:
    """
    Один прогон бенчмарка.

    Returns:
        dict: hit, detected_lag, rho_max, p_value.
    """
    x, y = synthetic_ar1_pair(n=n, true_lag=true_lag, coupling=coupling,
                              ar=ar, seed=seed)

    t_obs, p_value, detected_lag = max_lag_surrogate_pvalue(
        x, y,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        seed=seed + 10000,
    )

    hit = abs(detected_lag - true_lag) <= 1

    return {
        "hit": bool(hit),
        "detected_lag": int(detected_lag),
        "rho_max": float(t_obs),
        "p_value": float(p_value),
    }