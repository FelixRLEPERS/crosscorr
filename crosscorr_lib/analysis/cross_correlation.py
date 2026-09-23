"""
Кросс-корреляционный анализ унифицированной таблицы.

Ключевая идея:
1. Загрузить data/processed/unified.parquet.
2. Сгруппировать по detector_id (а не detector_type!),
   привести к общему временному индексу.
3. Для каждой пары детекторов — посчитать корреляцию
   на всех лагах от -max_lag до +max_lag.
4. Найти лаг с максимальной |correlation|.
5. Скорректировать p-value через Benjamini-Hochberg (FDR).
6. Сохранить tidy-таблицу: 
   detector_1, detector_2, lag, correlation, p_value, 
   q_value, n_obs, significant.
"""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results"


from crosscorr_lib.analysis.surrogate import fdr_bh_q as _benjamini_hochberg

def load_unified(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df


def build_wide_by_detector(df: pd.DataFrame, freq: str = "1h") -> pd.DataFrame:
    """
    Усредняем residual по (detector_id, time) и разворачиваем в wide-формат.
    Используем detector_id (а не detector_type) — каждая станция уникальна.
    """
    df = df.copy()
    df["bucket"] = df["timestamp_utc"].dt.floor(freq)
    wide = (
        df.groupby(["detector_id", "bucket"])["residual"]
        .mean()
        .unstack("detector_id")
        .sort_index()
    )
    return wide


def lagged_cross_correlation(x: np.ndarray, y: np.ndarray, max_lag: int = 72):
    """
    Кросс-корреляция двух рядов для всех лагов от -max_lag до +max_lag.

    Знак лага:
        lag > 0 — y отстаёт от x (y(t) связан с x(t - lag))
        lag < 0 — x отстаёт от y

    Возвращает:
        lags  : np.ndarray (2*max_lag + 1,)
        corrs : np.ndarray (2*max_lag + 1,)
        pvals : np.ndarray (2*max_lag + 1,)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    lags = np.arange(-max_lag, max_lag + 1)
    corrs = np.full(len(lags), np.nan)
    pvals = np.ones(len(lags))

    for i, lag in enumerate(lags):
        if lag < 0:
            xs, ys = x[-lag:], y[:lag]
        elif lag > 0:
            xs, ys = x[:-lag], y[lag:]
        else:
            xs, ys = x, y

        # Маска валидных пар
        mask = ~(np.isnan(xs) | np.isnan(ys))
        n = mask.sum()

        if n < 10:
            continue

        r, p = stats.spearmanr(xs[mask], ys[mask])
        corrs[i] = r
        pvals[i] = p

    return lags, corrs, pvals



def cross_correlation_pairs(
    wide: pd.DataFrame,
    max_lag: int = 72,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """
    Все пары детекторов → лаговая корреляция → FDR-коррекция.
    Возвращает tidy-таблицу.
    """
    cols = wide.columns.tolist()
    rows = []

    for d1, d2 in combinations(cols, 2):
        x = wide[d1].values
        y = wide[d2].values

        lags, corrs, pvals = lagged_cross_correlation(x, y, max_lag)

        # Пропускаем пары без валидных лагов
        if np.all(np.isnan(corrs)):
            continue

        # Лаг с максимальной |corr|
        best_idx = int(np.nanargmax(np.abs(corrs)))
        rows.append({
            "detector_1": d1,
            "detector_2": d2,
            "lag": int(lags[best_idx]),
            "correlation": float(corrs[best_idx]),
            "p_value": float(pvals[best_idx]),
            "n_obs": int(np.sum(~np.isnan(x) & ~np.isnan(y))),
        })

    if not rows:
        return pd.DataFrame(columns=[
            "detector_1", "detector_2", "lag", "correlation",
            "p_value", "q_value", "n_obs", "significant",
        ])

    result = pd.DataFrame(rows)

    # FDR на всех парах
    sig_mask, q_vals = _benjamini_hochberg(result["p_value"].values, alpha)
    result["q_value"] = q_vals
    result["significant"] = sig_mask

    return result

def cross_correlation_pairs_with_max_stat(
    wide: pd.DataFrame,
    max_lag: int = 72,
    alpha: float = 0.05,
    n_surrogates: int = 200,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Все пары детекторов → лаговая CC → max-statistic p-value → FDR.

    Отличается от cross_correlation_pairs тем, что p-value
    корректируется на множественное тестирование по всем лагам
    (max-statistic null), а не берётся с одного лучшего лага.

    Это научно корректный метод, но медленнее: n_surrogates × n_pairs
    × n_lags вычислений. Для 45 пар × 200 суррогатов × 145 лагов
    ~ 5-10 минут.

    Args:
        wide: wide-таблица (строки — время, колонки — detector_id).
        max_lag: максимальный лаг.
        alpha: уровень значимости для FDR.
        n_surrogates: число фазовых суррогатов (200 для теста,
                      1000+ для публикации).
        seed: базовый seed (для каждой пары используется свой).

    Returns:
        Tidy DataFrame с колонками:
        detector_1, detector_2, lag, correlation, p_value,
        q_value, n_obs, significant, n_surrogates.
    """
    # Ленивый импорт: избегаем циклической зависимости
    from crosscorr_lib.analysis.surrogate import (
        fdr_bh_q,
        max_lag_surrogate_pvalue,
    )

    cols = wide.columns.tolist()
    rows = []

    n_pairs = len(cols) * (len(cols) - 1) // 2
    print(f"[MAX-STAT] Пар: {n_pairs}, "
          f"суррогатов на пару: {n_surrogates}, "
          f"max_lag: {max_lag}")
    print(f"[MAX-STAT] Ожидаемое время: "
          f"~{n_pairs * n_surrogates * (2 * max_lag + 1) / 100000:.0f} сек")

    pair_idx = 0
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            d1, d2 = cols[i], cols[j]
            x = wide[d1].values
            y = wide[d2].values

            # Свой seed для каждой пары — суррогаты независимы
            pair_seed = seed + i * 1000 + j

            t_obs, p, best_lag = max_lag_surrogate_pvalue(
                x, y,
                max_lag=max_lag,
                n_surrogates=n_surrogates,
                seed=pair_seed,
            )

            if np.isnan(t_obs):
                continue

            # n_obs — число валидных пар значений
            mask = ~(np.isnan(x) | np.isnan(y))
            n_obs = int(mask.sum())

            rows.append({
                "detector_1": d1,
                "detector_2": d2,
                "lag": int(best_lag),
                "correlation": float(t_obs),
                "p_value": float(p),
                "n_obs": n_obs,
                "n_surrogates": int(n_surrogates),
            })

            pair_idx += 1
            if pair_idx % 5 == 0:
                print(f"  [{pair_idx}/{n_pairs}] "
                      f"{d1} — {d2}: p={p:.4f}")

    if not rows:
        return pd.DataFrame(columns=[
            "detector_1", "detector_2", "lag", "correlation",
            "p_value", "q_value", "n_obs", "significant", "n_surrogates",
        ])

    result = pd.DataFrame(rows)

    # FDR на всех парах
    sig_mask, q_vals = fdr_bh_q(result["p_value"].values, alpha)
    result["q_value"] = q_vals
    result["significant"] = sig_mask

    return result

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Кросс-корреляционный анализ детекторов."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--freq", default="1h")
    parser.add_argument("--max-lag", type=int, default=72)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--use-max-stat",
        action="store_true",
        help="Использовать max-statistic null (медленно, научно). "
             "По умолчанию — быстрый наивный p-value.",
    )
    parser.add_argument(
        "--n-surrogates",
        type=int,
        default=200,
        help="Число фазовых суррогатов для max-stat (по умолчанию 200).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed для воспроизводимости (по умолчанию 42).",
    )
    args = parser.parse_args()

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)

    df = load_unified(args.input)
    wide = build_wide_by_detector(df, freq=args.freq)

    print(f"[INFO] Детекторов: {wide.shape[1]}, точек: {wide.shape[0]}")
    print(f"[INFO] Пар: {wide.shape[1] * (wide.shape[1] - 1) // 2}")
    print(f"[INFO] Режим: "
          f"{'max-statistic (научный)' if args.use_max_stat else 'наивный (быстрый)'}")

    if args.use_max_stat:
        result = cross_correlation_pairs_with_max_stat(
            wide,
            max_lag=args.max_lag,
            alpha=args.alpha,
            n_surrogates=args.n_surrogates,
            seed=args.seed,
        )
    else:
        result = cross_correlation_pairs(
            wide,
            max_lag=args.max_lag,
            alpha=args.alpha,
        )

    out_csv = DEFAULT_OUT / "cross_correlation_pairs.csv"
    result.to_csv(out_csv, index=False)
    print(f"\n[OK] {out_csv}")
    print(f"[OK] Пар: {len(result)}")
    if "significant" in result.columns:
        print(f"[OK] Значимых: {int(result['significant'].sum())}")


if __name__ == "__main__":
    main()