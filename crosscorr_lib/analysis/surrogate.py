"""
Surrogate-тесты для оценки значимости наблюдаемых кросс-корреляций.

Используются фазовые суррогаты (phase randomization), которые сохраняют
амплитудный спектр, но разрушают нелинейные связи.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results"
DEFAULT_OUT.mkdir(parents=True, exist_ok=True)


def phase_surrogate(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Возвращает фазовый суррогат для одномерного ряда.

    Фиксирует фазу DC (индекс 0) и Nyquist (последний индекс для чётной
    длины), чтобы сохранить нулевое среднее и вещественность сигнала.
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size < 4:
        return x

    fft = np.fft.rfft(x)
    magnitudes = np.abs(fft)
    random_phases = rng.uniform(-np.pi, np.pi, size=magnitudes.shape)

    # Фиксация DC (сохраняет нулевое среднее)
    random_phases[0] = 0.0
    # Фиксация Nyquist для чётных длин (сохраняет вещественность)
    if x.size % 2 == 0:
        random_phases[-1] = 0.0

    fft_surrogate = magnitudes * np.exp(1j * random_phases)
    return np.fft.irfft(fft_surrogate, n=x.size)


def build_wide(df: pd.DataFrame, freq: str = "1h") -> pd.DataFrame:
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["bucket"] = df["timestamp_utc"].dt.floor(freq)
    wide = (
        df.groupby(["detector_id", "bucket"])["residual"]
        .mean()
        .unstack("detector_id")
        .sort_index()
    )
    return wide


def surrogate_test(wide: pd.DataFrame, n_surrogates: int = 1000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = wide.columns.tolist()
    real = wide.corr(method="spearman").values

    # накапливаем распределение корреляций по суррогатам
    surrogate_corrs = np.zeros((n_surrogates, len(cols), len(cols)))
    filled = wide.fillna(wide.mean())

    for i in range(n_surrogates):
        surro = np.column_stack([
            phase_surrogate(filled[c].values, rng) for c in cols
        ])
        surro_df = pd.DataFrame(surro, columns=cols)
        surrogate_corrs[i] = surro_df.corr(method="spearman").values

    # p-value: доля суррогатов, где |corr| >= |real|
    pvals = np.zeros_like(real)
    for r in range(len(cols)):
        for c in range(len(cols)):
            if r == c:
                pvals[r, c] = 0.0
                continue
            pvals[r, c] = np.mean(np.abs(surrogate_corrs[:, r, c]) >= abs(real[r, c]))

    result = pd.DataFrame(pvals, index=cols, columns=cols)
    return result


def fdr_bh(pvals: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg FDR.

    Работает в двух режимах:
    - 2D матрица (N×N): использует верхний треугольник (i<j),
      возвращает симметричную булеву маску той же формы.
    - 1D массив: применяет BH напрямую к списку p-values,
      возвращает 1D булеву маску.

    Args:
        pvals: 1D или 2D массив p-values.
        alpha: уровень значимости.

    Returns:
        Булева маска той же размерности, что вход.
    """
    pvals = np.asarray(pvals, dtype=float)

    if pvals.ndim == 1:
        n = pvals.size
        order = np.argsort(pvals)
        ranked = pvals[order]
        thresholds = alpha * (np.arange(1, n + 1) / n)
        passed = ranked <= thresholds

        mask_flat = np.zeros(n, dtype=bool)
        if passed.any():
            k = int(np.max(np.where(passed)[0]))
            mask_flat[order[: k + 1]] = True
        return mask_flat

    if pvals.ndim == 2:
        n_total = pvals.shape[0]
        iu = np.triu_indices(n_total, k=1)
        flat = pvals[iu]
        n = flat.size

        order = np.argsort(flat)
        ranked = flat[order]
        thresholds = alpha * (np.arange(1, n + 1) / n)
        passed = ranked <= thresholds

        mask_flat = np.zeros(n, dtype=bool)
        if passed.any():
            k = int(np.max(np.where(passed)[0]))
            mask_flat[order[: k + 1]] = True

        mask = np.zeros((n_total, n_total), dtype=bool)
        mask[iu] = mask_flat
        mask = mask | mask.T
        return mask

    raise ValueError(f"fdr_bh ожидает 1D или 2D массив, получил {pvals.ndim}D")

def fdr_bh_q(
    pvals: np.ndarray,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Benjamini-Hochberg FDR с возвратом q-values.

    Работает с 1D массивом p-values.

    Returns:
        (significant_mask, q_values)
        significant_mask: bool массив, True для значимых
        q_values:         adjusted p-values (q-values)
    """
    pvals = np.asarray(pvals, dtype=float)
    if pvals.ndim != 1:
        raise ValueError(
            f"fdr_bh_q ожидает 1D массив, получил {pvals.ndim}D"
        )

    n = pvals.size
    if n == 0:
        return np.array([], dtype=bool), np.array([])

    order = np.argsort(pvals)
    ranked = pvals[order]

    q = np.empty(n, dtype=float)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        val = ranked[i] * n / rank
        prev = min(prev, val)
        q[order[i]] = prev

    mask = q <= alpha
    return mask, q

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--freq", default="1h")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    wide = build_wide(df, freq=args.freq)

    pvals = surrogate_test(wide, n_surrogates=args.n, seed=args.seed)
    significant = fdr_bh(pvals.values, alpha=args.alpha)

    pvals.to_csv(DEFAULT_OUT / "surrogate_pvalues.csv")

    # Сохраняем плоский список значимых пар
    cols = pvals.columns.tolist()
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if significant[i, j]:
                pairs.append({
                    "Detector1": cols[i],
                    "Detector2": cols[j],
                    "p_value": float(pvals.iloc[i, j]),
                })

    pd.DataFrame(pairs).to_csv(
        DEFAULT_OUT / "surrogate_significant.csv", index=False
    )
    print(f"[OK] p-values -> {DEFAULT_OUT / 'surrogate_pvalues.csv'}")
    print(f"[OK] significant pairs: {len(pairs)}")

def max_lag_surrogate_pvalue(
    x: np.ndarray,
    y: np.ndarray,
    max_lag: int = 72,
    n_surrogates: int = 500,
    seed: int = 42,
    fisher: bool = True,
) -> tuple[float, float, int]:
    """
    Max-statistic p-value для лаговой кросс-корреляции.

    Тестирует гипотезу: "нет связи ни на одном лаге".
    Учитывает, что мы ищем максимум по всем 2*max_lag+1 лагам.

    Args:
        x, y          : ряды (1D)
        max_lag       : максимальный лаг
        n_surrogates  : число суррогатов
        seed          : seed для воспроизводимости
        fisher        : использовать Fisher-weighted max (по умолчанию True).
                        Если False — обычный max|rho|.

    Returns:
        (t_obs, p_value, best_lag)
        t_obs    : Fisher-weighted (или обычный) max|corr| на реальных данных
        p_value  : доля суррогатов, где max_stat_surr >= t_obs
        best_lag : лаг, на котором достигнут t_obs
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    # Реальное значение: считаем rho и n для всех лагов
    lags, corrs, _ = _lagged_cc(x, y, max_lag)

    # Считаем n (число валидных наблюдений) на каждом лаге
    n_lags = np.array([_count_valid_at_lag(x, y, int(tau)) for tau in lags])

    if np.all(np.isnan(corrs)):
        return np.nan, 1.0, 0

    if fisher:
        t_obs, best_idx, _ = fisher_weighted_max_stat(corrs, n_lags)
        if not np.isfinite(t_obs) or t_obs == 0.0:
            return np.nan, 1.0, 0
    else:
        best_idx = int(np.nanargmax(np.abs(corrs)))
        t_obs = float(np.abs(corrs[best_idx]))

    best_lag = int(lags[best_idx])

    # Суррогаты
    rng = np.random.default_rng(seed)
    n_extreme = 0

    for _ in range(n_surrogates):
        y_surr = _phase_surrogate_keep_length(y, rng)
        _, corrs_surr, _ = _lagged_cc(x, y_surr, max_lag)

        if np.all(np.isnan(corrs_surr)):
            continue

        if fisher:
            t_surr, _, _ = fisher_weighted_max_stat(corrs_surr, n_lags)
            if not np.isfinite(t_surr):
                continue
        else:
            t_surr = float(np.nanmax(np.abs(corrs_surr)))

        if t_surr >= t_obs:
            n_extreme += 1

    p_value = (n_extreme + 1) / (n_surrogates + 1)
    return t_obs, p_value, best_lag


def _count_valid_at_lag(x: np.ndarray, y: np.ndarray, tau: int) -> int:
    """Число валидных (не-NaN) пар на данном лаге."""
    n = len(x)
    if tau >= 0:
        a = x[: n - tau] if tau > 0 else x
        b = y[tau:]
    else:
        a = x[-tau:]
        b = y[: n + tau]
    mask = np.isfinite(a) & np.isfinite(b)
    return int(mask.sum())


def _lagged_cc(x, y, max_lag):
    """Внутренняя обёртка: избегаем циклического импорта."""
    from crosscorr_lib.analysis.cross_correlation import (
        lagged_cross_correlation,
    )
    return lagged_cross_correlation(x, y, max_lag)


def _phase_surrogate_keep_length(x, rng):
    """
    Фазовый суррогат, сохраняющий длину ряда.
    В отличие от phase_surrogate, здесь NaN не удаляются
    (используется интерполяция).
    """
    x = np.asarray(x, dtype=float)
    if np.isnan(x).any():
        # Простая интерполяция для NaN
        mask = ~np.isnan(x)
        if mask.sum() < 4:
            return x
        idx = np.arange(x.size)
        x = np.interp(idx, idx[mask], x[mask])

    n = x.size
    if n < 4:
        return x

    fft = np.fft.rfft(x)
    magnitudes = np.abs(fft)
    phases = rng.uniform(-np.pi, np.pi, size=magnitudes.shape)
    phases[0] = 0.0
    if n % 2 == 0:
        phases[-1] = 0.0
    fft_surr = magnitudes * np.exp(1j * phases)
    return np.fft.irfft(fft_surr, n=n)

if __name__ == "__main__":
    main()
def fisher_weighted_max_stat(
    rho: np.ndarray,
    n: np.ndarray,
    *,
    clip_eps: float = 1e-6,
) -> tuple[float, int, float]:
    """
    Fisher-weighted max of |rho| over lags.

    Если на разных лагах разное число наблюдений n(tau),
    обычный max|rho| смещён в сторону лагов с большим n.
    Fisher-weighting исправляет это:

        z(tau)     = arctanh(rho(tau))
        w(tau)     = sqrt(n(tau) - 3)
        score(tau) = |z(tau)| * w(tau)

    Args:
        rho: массив корреляций (NaN для невалидных лагов)
        n:   массив числа наблюдений на каждом лаге
        clip_eps: клип для arctanh, чтобы избежать inf

    Returns:
        (max_score, argmax_index, rho_at_argmax)
    """
    rho = np.asarray(rho, dtype=float)
    n = np.asarray(n, dtype=int)

    if rho.shape != n.shape:
        raise ValueError("rho and n must have the same shape")

    finite = np.isfinite(rho) & (n > 3)
    if not finite.any():
        return 0.0, 0, 0.0

    # Fisher z-transform с клипом
    rho_clipped = np.clip(rho, -1 + clip_eps, 1 - clip_eps)
    z = np.arctanh(rho_clipped)

    # Веса
    w = np.sqrt(np.maximum(n - 3, 1.0))

    # Score
    score = np.where(finite, np.abs(z) * w, -np.inf)

    idx = int(np.argmax(score))
    return float(score[idx]), idx, float(rho[idx])