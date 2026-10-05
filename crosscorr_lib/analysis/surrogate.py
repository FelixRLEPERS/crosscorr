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


def phase_surrogate(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Возвращает фазовый суррогат для одномерного ряда.

    Фиксирует фазу DC (индекс 0) и Nyquist (последний индекс для чётной
    длины), чтобы сохранить нулевое среднее и вещественность сигнала.

    NaN не удаляются, а интерполируются по индексу: длина результата всегда
    равна длине входа. Удаление NaN сдвигало бы все последующие отсчёты и
    разрушало лаговую структуру, из-за чего наблюдение и нулевое
    распределение считались бы на рядах разной длины.

    Returns:
        Массив той же длины, что и x. Если конечных значений меньше двух
        либо длина входа меньше 4 — массив NaN, а НЕ исходный ряд:
        совпадение с наблюдением исказило бы p-value.
    """
    x = np.asarray(x, dtype=float)

    if np.isnan(x).any():
        idx = np.arange(x.size)
        good = np.isfinite(x)
        if good.sum() < 2:
            return np.full_like(x, np.nan, dtype=float)
        x = np.interp(idx, idx[good], x[good])

    if x.size < 4:
        return np.full_like(x, np.nan, dtype=float)

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
    """Surrogate-тест значимости корреляций.

    Наблюдение (``real``) и каждое нулевое распределение считаются на
    ОДНОЙ И ТОЙ ЖЕ NaN-маске: ``wide.corr()`` использует попарное
    удаление NaN, поэтому суррогат строится из исходных значений, а NaN
    возвращаются на те же позиции, что и в наблюдении. Иначе real был бы
    посчитан на попарной подвыборке, а нуль — на полном ряду (после
    mean-импутации), и сравнение было бы некорректным.
    """
    rng = np.random.default_rng(seed)
    cols = wide.columns.tolist()
    real = wide.corr(method="spearman").values

    # накапливаем распределение корреляций по суррогатам
    surrogate_corrs = np.zeros((n_surrogates, len(cols), len(cols)))
    # Позиции исходных NaN: phase_surrogate интерполирует пропуски, но
    # для корректного pairwise-сравнения NaN нужно вернуть на место.
    nan_mask = wide.isna().values

    for i in range(n_surrogates):
        surro = np.column_stack([
            phase_surrogate(wide[c].values, rng) for c in cols
        ])
        surro[nan_mask] = np.nan
        surro_df = pd.DataFrame(surro, columns=cols)
        surrogate_corrs[i] = surro_df.corr(method="spearman").values

    # p-value: доля валидных суррогатов, где |corr| >= |real|.
    # Вырожденные суррогаты (NaN) исключаются из знаменателя, иначе
    # они искусственно раздувают B и занижают p-value.
    pvals = np.zeros_like(real)
    for r in range(len(cols)):
        for c in range(len(cols)):
            if r == c:
                pvals[r, c] = 0.0
                continue
            cell = surrogate_corrs[:, r, c]
            valid = np.isfinite(cell)
            n_used = int(valid.sum())
            if n_used == 0:
                pvals[r, c] = 1.0
                continue
            n_extreme = int(np.sum(
                np.abs(cell[valid]) >= abs(real[r, c])
            ))
            pvals[r, c] = (n_extreme + 1) / (n_used + 1)

    result = pd.DataFrame(pvals, index=cols, columns=cols)
    return result


def fdr_bh(
    pvals: np.ndarray,
    alpha: float = 0.05,
    method: str = "by",
) -> np.ndarray:
    """
    FDR-коррекция с поддержкой 1D и 2D.

    По умолчанию используется Benjamini-Yekutieli (для зависимых тестов,
    что необходимо в графе детекторов).

    Args:
        pvals: 1D массив или 2D симметричная матрица p-values.
        alpha: целевой уровень FDR.
        method: 'by' (default) или 'bh'.

    Returns:
        1D или 2D булева маска той же формы, что вход.
    """
    pvals = np.asarray(pvals, dtype=float)

    if pvals.ndim == 1:
        reject, _ = fdr_bh_q(pvals, alpha=alpha, method=method)
        return reject

    if pvals.ndim == 2:
        n_total = pvals.shape[0]
        iu = np.triu_indices(n_total, k=1)
        flat = pvals[iu]

        reject_flat, _ = fdr_bh_q(flat, alpha=alpha, method=method)

        mask = np.zeros((n_total, n_total), dtype=bool)
        mask[iu] = reject_flat
        mask = mask | mask.T
        return mask

    raise ValueError(f"fdr_bh ожидает 1D или 2D массив, получил {pvals.ndim}D")

def benjamini_yekutieli(
    pvals: np.ndarray,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Benjamini-Yekutieli FDR для произвольно зависимых тестов.

    Использует гармоническую поправку c(M) = sum(1/k, k=1..M).
    Даёт строгий контроль FDR при ЛЮБОЙ структуре зависимости,
    включая зависимые пары в графе детекторов (общий узел → PRDS не выполнен).

    Reference:
        Benjamini, Y., Yekutieli, D. (2001).
        The control of the false discovery rate in multiple testing
        under dependency. Annals of Statistics, 29(4), 1165–1188.

    Args:
        pvals: 1D массив p-values.
        alpha: целевой уровень FDR.

    Returns:
        (reject_mask, q_values)
    """
    p = np.asanyarray(pvals, dtype=float)
    m = len(p)
    if m == 0:
        return np.array([], dtype=bool), np.array([], dtype=float)

    # NaN-safe: работаем только с конечными p-values
    finite_mask = np.isfinite(p)
    n_finite = int(finite_mask.sum())

    if n_finite == 0:
        return np.zeros(m, dtype=bool), np.full(m, np.nan)

    # Гармоническая сумма по числу валидных тестов
    c_m = np.sum(1.0 / np.arange(1, n_finite + 1))

    # Индексы только валидных
    finite_idx = np.where(finite_mask)[0]
    p_finite = p[finite_idx]

    order_local = np.argsort(p_finite)
    p_sorted = p_finite[order_local]

    thresholds = (np.arange(1, n_finite + 1) / (n_finite * c_m)) * alpha
    passed = p_sorted <= thresholds

    reject_local = np.zeros(n_finite, dtype=bool)
    if passed.any():
        max_k = int(np.max(np.where(passed)[0]))
        reject_local[: max_k + 1] = True

    q_local = p_sorted * (n_finite * c_m) / np.arange(1, n_finite + 1)
    q_local = np.minimum.accumulate(q_local[::-1])[::-1]
    q_local = np.clip(q_local, 0.0, 1.0)

    # Разворачиваем обратно в полный массив
    reject = np.zeros(m, dtype=bool)
    q = np.full(m, np.nan)

    reject[finite_idx[order_local]] = reject_local
    q[finite_idx[order_local]] = q_local

    return reject, q


def fdr_bh_q(
    pvals: np.ndarray,
    alpha: float = 0.05,
    method: str = "by",
) -> tuple[np.ndarray, np.ndarray]:
    """
    FDR-коррекция. По умолчанию — Benjamini-Yekutieli (для зависимых тестов).

    Args:
        pvals: 1D массив p-values.
        alpha: целевой уровень FDR.
        method: 'by' (Benjamini-Yekutieli, по умолчанию) или
                'bh' (Benjamini-Hochberg, требует независимости или PRDS).

    Returns:
        (reject_mask, q_values)
    """
    if method == "by":
        return benjamini_yekutieli(pvals, alpha)

    if method == "bh":
        p = np.asanyarray(pvals, dtype=float)
        m = len(p)
        if m == 0:
            return np.array([], dtype=bool), np.array([], dtype=float)

        # NaN-safe: работаем только с конечными p-values
        finite_mask = np.isfinite(p)
        n_finite = int(finite_mask.sum())

        if n_finite == 0:
            return np.zeros(m, dtype=bool), np.full(m, np.nan)

        # Индексы только валидных
        finite_idx = np.where(finite_mask)[0]
        p_finite = p[finite_idx]

        order_local = np.argsort(p_finite)
        p_sorted = p_finite[order_local]

        thresholds = alpha * np.arange(1, n_finite + 1) / n_finite
        passed = p_sorted <= thresholds

        reject_local = np.zeros(n_finite, dtype=bool)
        if passed.any():
            max_k = int(np.max(np.where(passed)[0]))
            reject_local[: max_k + 1] = True

        q_local = p_sorted * n_finite / np.arange(1, n_finite + 1)
        q_local = np.minimum.accumulate(q_local[::-1])[::-1]
        q_local = np.clip(q_local, 0.0, 1.0)

        # Разворачиваем обратно в полный массив
        reject = np.zeros(m, dtype=bool)
        q = np.full(m, np.nan)

        reject[finite_idx[order_local]] = reject_local
        q[finite_idx[order_local]] = q_local

        return reject, q

    raise ValueError(f"Неизвестный метод FDR: {method}. Используйте 'by' или 'bh'.")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--freq", default="1h")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)

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
    surrogate_method: str = "phase",
    randomize_both: bool = True,
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
        surrogate_method : 'phase' | 'iaaft' | 'time_shift'.
                           'phase' — классическая фазовая рандомизация.
                           'iaaft' — сохраняет и спектр, и распределение
                           (Schreiber-Schmitz 1996), важно для heavy-tailed.
                           'time_shift' — циклический сдвиг (быстрый).
        randomize_both : bool (по умолчанию True)
            Если True — рандомизировать и x, и y. Это консервативный
            тест для автокоррелированных пар (правильная нулевая
            дисперсия). Если False — только y (быстрее, но занижает
            p-value для автокоррелированных данных).
    Returns:
        (t_obs, p_value, best_lag)
        t_obs    : Fisher-weighted (или обычный) max|corr| на реальных данных
        p_value  : доля суррогатов, где max_stat_surr >= t_obs
        best_lag : лаг, на котором достигнут t_obs
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    # Валидация max_lag: при max_lag >= n на дальних лагах нет
    # перекрывающихся отсчётов, и _count_valid_at_lag получил бы срезы
    # разной длины (numpy broadcasting ValueError без пояснения).
    n = x.size
    if max_lag < 0:
        raise ValueError(f"max_lag must be >= 0, got {max_lag}")
    if max_lag >= n:
        raise ValueError(
            f"max_lag={max_lag} must be < n={n}. "
            f"At larger lags there are no valid overlapping samples."
        )

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
    n_used = 0

    for _ in range(n_surrogates):
        if surrogate_method == "iaaft":
            y_surr = iaaft_surrogate(y, rng)
            x_surr = iaaft_surrogate(x, rng) if randomize_both else x
        elif surrogate_method == "time_shift":
            y_surr = _time_shift(y, rng)
            x_surr = _time_shift(x, rng) if randomize_both else x
        else:
            y_surr = _phase_surrogate_keep_length(y, rng)
            x_surr = _phase_surrogate_keep_length(x, rng) if randomize_both else x

        _, corrs_surr, _ = _lagged_cc(x_surr, y_surr, max_lag)

        if np.all(np.isnan(corrs_surr)):
            continue

        if fisher:
            # Веса Fisher должны считаться по n валидных пар СУРРОГАТА, а
            # не наблюдения: у time_shift на краях появляются NaN, поэтому
            # n_surr(tau) < n_obs(tau). Общие веса делали Var(score) > 1 и
            # нуль консервативным. Считаем n для тех же рядов, что пошли в
            # корреляцию, чтобы наблюдение и нуль были соизмеримы.
            n_lags_surr = np.array([
                _count_valid_at_lag(x_surr, y_surr, int(tau))
                for tau in lags
            ])
            t_surr, _, _ = fisher_weighted_max_stat(corrs_surr, n_lags_surr)
            if not np.isfinite(t_surr):
                continue
        else:
            t_surr = float(np.nanmax(np.abs(corrs_surr)))

        n_used += 1
        if t_surr >= t_obs:
            n_extreme += 1

    if n_used == 0:
        return np.nan, 1.0, 0

    p_value = (n_extreme + 1) / (n_used + 1)
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

    NaN не удаляются, а интерполируются по индексу. Длина результата всегда
    равна длине входа, поэтому наблюдение и нулевое распределение считаются
    на рядах одинаковой длины.

    Returns:
        Массив той же длины, что и x. Если конечных значений меньше четырёх
        либо длина входа меньше 4 — массив NaN, а НЕ исходный ряд:
        возврат наблюдения в нулевом распределении занижает p-value.
        Вызывающий код исключает такой суррогат из знаменателя через n_used.
    """
    x = np.asarray(x, dtype=float)
    if np.isnan(x).any():
        # Простая интерполяция для NaN
        mask = np.isfinite(x)
        if mask.sum() < 4:
            return np.full(x.size, np.nan, dtype=float)
        idx = np.arange(x.size)
        x = np.interp(idx, idx[mask], x[mask])

    n = x.size
    if n < 4:
        return np.full(n, np.nan, dtype=float)

    fft = np.fft.rfft(x)
    magnitudes = np.abs(fft)
    phases = rng.uniform(-np.pi, np.pi, size=magnitudes.shape)
    phases[0] = 0.0
    if n % 2 == 0:
        phases[-1] = 0.0
    fft_surr = magnitudes * np.exp(1j * phases)
    return np.fft.irfft(fft_surr, n=n)

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


def iaaft_surrogate(
    x: np.ndarray,
    rng: np.random.Generator,
    max_iter: int = 50,
    tol: float = 1e-6,
) -> np.ndarray:
    """
    IAAFT-суррогат (Iterative Amplitude Adjusted Fourier Transform).

    Сохраняет одновременно:
    - амплитудный спектр Фурье (как phase surrogates),
    - эмпирическое распределение амплитуд (rank-preserving).

    Это исправляет проблему классических phase surrogates:
    ЦПТ делает распределение гауссовским, что занижает дисперсию
    пиков для heavy-tailed данных (Kp, Dst).

    Reference:
        Schreiber, T., Schmitz, A. (1996).
        Improved surrogate data for nonlinearity tests.
        Physical Review Letters, 77(4), 635–638.

    Args:
        x: 1D временной ряд (без NaN).
        rng: генератор случайных чисел.
        max_iter: максимум итераций (обычно сходится за 20-30).
        tol: критерий сходимости по изменению значений.

    Returns:
        Суррогатный ряд той же длины, что x. Если длина входа меньше 4
        либо конечных значений меньше четырёх — массив NaN, а НЕ исходный
        ряд: возврат наблюдения в нулевом распределении занижает p-value.
        Вызывающий код исключает такой суррогат из знаменателя через n_used.
    """
    x = np.asarray(x, dtype=float)
    n = x.size

    if n < 4:
        return np.full(n, np.nan, dtype=float)

    if np.isnan(x).any():
        idx = np.arange(n)
        good = np.isfinite(x)
        if good.sum() < 4:
            return np.full(n, np.nan, dtype=float)
        x = np.interp(idx, idx[good], x[good])

    sorted_x = np.sort(x)
    fft_orig = np.fft.rfft(x)
    target_amplitudes = np.abs(fft_orig)

    s_curr = rng.permutation(x)
    prev_s = None

    for _ in range(max_iter):
        fft_s = np.fft.rfft(s_curr)
        phases = np.angle(fft_s)
        s_spectrum_matched = np.fft.irfft(
            target_amplitudes * np.exp(1j * phases), n=n
        )

        ranks = np.argsort(np.argsort(s_spectrum_matched))
        s_new = sorted_x[ranks]

        if prev_s is not None:
            delta = np.max(np.abs(s_new - prev_s))
            if delta < tol:
                return s_new

        prev_s = s_new
        s_curr = s_new

    return s_curr


def _time_shift(
    y: np.ndarray,
    rng: np.random.Generator,
    min_shift: int = 1,
) -> np.ndarray:
    """
    Циклический сдвиг ряда на случайное смещение.

    Быстрая альтернатива phase randomization. Сохраняет
    автокорреляционную структуру, но разрушает кросс-корреляцию
    с x. Для коротких рядов или exploratory анализа.

    Args:
        y: 1D временной ряд.
        rng: генератор случайных чисел.
        min_shift: минимальное смещение (>= 1).

    Returns:
        Сдвинутый ряд той же длины.
    """
    y = np.asarray(y, dtype=float)
    n = y.size
    if n < 4:
        return y.copy()

    # Сдвиг выбирается из [n/4, 3n/4]: он обязан заметно превышать время
    # корреляции, иначе разрушения кросс-корреляции не происходит.
    max_shift = max(min_shift, n // 4)
    upper = max(max_shift + 1, 3 * n // 4)
    shift = int(rng.integers(max_shift, upper))

    # Линейный сдвиг с NaN на краях: np.roll замыкал ряд циклически и
    # создавал разрыв на границе, добавляя ложную низкочастотную структуру.
    out = np.full_like(y, np.nan, dtype=float)
    if shift > 0:
        out[shift:] = y[:-shift]
    elif shift < 0:
        out[:shift] = y[-shift:]
    else:
        out[:] = y
    return out


if __name__ == "__main__":
    main()
