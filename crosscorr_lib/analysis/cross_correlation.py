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
import logging
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from crosscorr_lib.analysis.surrogate import fdr_bh_q as _fdr_correct

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results"

logger = logging.getLogger(__name__)


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
    fdr_method: str = "by",
    apply_preprocessing: bool = True,
) -> pd.DataFrame:
    """
    Все пары детекторов → лаговая корреляция → FDR-коррекция.
    Возвращает tidy-таблицу.
    """
    cols = wide.columns.tolist()
    rows = []
    if apply_preprocessing:
        from crosscorr_lib.analysis.preprocessing import preprocess
        wide = wide.copy()
        for col in wide.columns:
            wide[col] = preprocess(wide[col].values)

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
    sig_mask, q_vals = _fdr_correct(
        result["p_value"].values, alpha, method=fdr_method
    )
    result["q_value"] = q_vals
    result["significant"] = sig_mask

    return result

def cross_correlation_pairs_with_max_stat(
    wide: pd.DataFrame,
    max_lag: int = 72,
    alpha: float = 0.05,
    n_surrogates: int = 200,
    seed: int = 42,
    fdr_method: str = "by",
    apply_preprocessing: bool = True,
) -> pd.DataFrame:
    """
    Все пары детекторов → лаговая CC → max-statistic p-value → FDR.

    Отличается от cross_correlation_pairs тем, что p-value
    корректируется на множественное тестирование по всем лагам
    (max-statistic null), а не берётся с одного лучшего лага.

    Это научно корректный метод, но медленнее: n_surrogates × n_pairs
    × n_lags вычислений; время растёт с числом пар, суррогатов и лагов.

    Args:
        wide: wide-таблица (строки — время, колонки — detector_id).
        max_lag: максимальный лаг.
        alpha: уровень значимости для FDR.
        n_surrogates: число фазовых суррогатов (200 для теста,
                      1000+ для публикации).
        seed: базовый seed (для каждой пары используется свой).

    Returns:
        Tidy DataFrame с колонками:
        detector_1, detector_2, lag, correlation (deprecated alias of
        rho_at_best_lag), max_stat_score (Fisher-weighted score),
        rho_at_best_lag (Spearman r в [-1, 1] на лучшем лаге),
        p_value, q_value, n_obs, significant, n_surrogates.

        Колонка ``correlation`` сохранена для обратной совместимости и
        теперь равна ``rho_at_best_lag`` (Spearman r), а не Fisher-score.
        Fisher-weighted score доступен в ``max_stat_score``.
    """
    # Ленивый импорт: избегаем циклической зависимости
    from crosscorr_lib.analysis.surrogate import (
        max_lag_surrogate_pvalue,
    )

    # Per-pair RNG via spawn() for guaranteed independence
    parent_rng = np.random.default_rng(seed)
    child_rngs = parent_rng.spawn(len(wide.columns) * (len(wide.columns) - 1) // 2)

    cols = wide.columns.tolist()
    rows = []
    if apply_preprocessing:
        from crosscorr_lib.analysis.preprocessing import preprocess
        wide = wide.copy()
        for col in wide.columns:
            wide[col] = preprocess(wide[col].values)

    n_pairs = len(cols) * (len(cols) - 1) // 2
    logger.info(
        "[MAX-STAT] Пар: %s, суррогатов на пару: %s, max_lag: %s",
        n_pairs, n_surrogates, max_lag,
    )
    logger.info(
        "[MAX-STAT] Ожидаемое время: ~%.0f сек",
        n_pairs * n_surrogates * (2 * max_lag + 1) / 100000,
    )

    pair_idx = 0
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            d1, d2 = cols[i], cols[j]
            x = wide[d1].values
            y = wide[d2].values

            # Свой seed через spawn() — гарантированная независимость.
            # pair_idx увеличивается безусловно сразу после выбора child_rng,
            # чтобы пропуск пары через continue не приводил к повторному
            # использованию того же child_rng следующей парой.
            pair_seed = int(child_rngs[pair_idx].integers(0, 2**31))
            pair_idx += 1

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

            # rho_at_best_lag — Spearman r в [-1, 1] на лучшем лаге.
            # t_obs — Fisher-weighted score (|arctanh(r)|*sqrt(n-3)), его
            # нельзя интерпретировать как корреляцию.
            lags_obs, corrs_obs, _ = lagged_cross_correlation(x, y, max_lag)
            idx_obs = int(best_lag) + max_lag
            if 0 <= idx_obs < len(corrs_obs):
                rho_best = float(corrs_obs[idx_obs])
            else:
                rho_best = np.nan

            rows.append({
                "detector_1": d1,
                "detector_2": d2,
                "lag": int(best_lag),
                # deprecated alias: раньше здесь лежал Fisher-score,
                # теперь — Spearman r (== rho_at_best_lag).
                "correlation": rho_best,
                "max_stat_score": float(t_obs),
                "rho_at_best_lag": rho_best,
                "p_value": float(p),
                "n_obs": n_obs,
                "n_surrogates": int(n_surrogates),
            })

            if pair_idx % 5 == 0:
                logger.info(
                    "  [%s/%s] %s — %s: p=%.4f",
                    pair_idx, n_pairs, d1, d2, p,
                )

    if not rows:
        return pd.DataFrame(columns=[
            "detector_1", "detector_2", "lag", "correlation",
            "max_stat_score", "rho_at_best_lag", "p_value", "q_value",
            "n_obs", "significant", "n_surrogates",
        ])

    result = pd.DataFrame(rows)

    # FDR на всех парах
    sig_mask, q_vals = _fdr_correct(
        result["p_value"].values, alpha, method=fdr_method
    )
    result["q_value"] = q_vals
    result["significant"] = sig_mask

    result = result[[
        "detector_1", "detector_2", "lag", "correlation",
        "max_stat_score", "rho_at_best_lag", "p_value", "q_value",
        "n_obs", "significant", "n_surrogates",
    ]]

    return result

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    parser = argparse.ArgumentParser(
        description=(
            "Кросс-корреляционный анализ детекторов. "
            "По умолчанию используется max-statistic null "
            "(surrogate-based): он корректно учитывает поиск "
            "по всем лагам. Наивный single-lag путь доступен "
            "только через --use-naive и не рекомендован для "
            "публикаций."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--freq", default="1h")
    parser.add_argument("--max-lag", type=int, default=72)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--use-naive",
        action="store_true",
        help=(
            "Use naive single-lag p-value (deprecated, "
            "not recommended for publication). Default is "
            "max-statistic with surrogate null."
        ),
    )
    parser.add_argument(
        "--use-ess",
        action="store_true",
        help="Скорректировать p-values на автокорреляцию (ESS).",
    )
    parser.add_argument(
        "--remove-confounders",
        type=Path,
        default=None,
        help="CSV с Kp/Dst/F10.7. Удалить их вклад из всех рядов.",
    )
    parser.add_argument(
        "--n-surrogates",
        type=int,
        default=200,
        help="Число фазовых суррогатов для max-stat.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed для воспроизводимости.",
    )
    parser.add_argument(
        "--fdr-method",
        choices=["by", "bh"],
        default="by",
        help="FDR-метод: 'by' (Benjamini-Yekutieli, default) или 'bh'.",
    )
    args = parser.parse_args()

    if args.use_ess and not args.use_naive:
        parser.error(
            "--use-ess cannot be combined with the default "
            "max-statistic path. Use --use-naive if you really "
            "want ESS on single-lag correlations."
        )

    if args.use_naive:
        warnings.warn(
            "WARNING: --use-naive uses single-lag p-value without "
            "correction for multiple lag search. For "
            "publication-quality results, remove this flag.",
            DeprecationWarning,
            stacklevel=2,
        )
        if args.use_ess:
            warnings.warn(
                "WARNING: ESS correction applies to single-lag "
                "correlation, not to the max-statistic null. Result "
                "will not match publication-quality methodology.",
                UserWarning,
                stacklevel=2,
            )

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)

    df = load_unified(args.input)
    wide = build_wide_by_detector(df, freq=args.freq)

    # Удаление конфаундеров (если запрошено)
    if args.remove_confounders is not None:
        from crosscorr_lib.analysis.confounders import (
            load_confounders,
            remove_confounders,
        )
        conf = load_confounders(args.remove_confounders)
        wide = remove_confounders(wide, conf)
        print(f"[INFO] Конфаундеры удалены: {args.remove_confounders}")

    print(f"[INFO] Детекторов: {wide.shape[1]}, точек: {wide.shape[0]}")
    print(f"[INFO] Режим: "
          f"{'наивный (--use-naive)' if args.use_naive else 'max-stat (default)'} / "
          f"{'ESS' if args.use_ess else 'без ESS'}")

    if args.use_naive:
        result = cross_correlation_pairs(
            wide,
            max_lag=args.max_lag,
            alpha=args.alpha,
            fdr_method=args.fdr_method,
        )
    else:
        result = cross_correlation_pairs_with_max_stat(
            wide,
            max_lag=args.max_lag,
            alpha=args.alpha,
            n_surrogates=args.n_surrogates,
            seed=args.seed,
            fdr_method=args.fdr_method,
        )

    # ESS-коррекция p-values (если запрошено)
    if args.use_ess and len(result) > 0:
        from crosscorr_lib.analysis.effective_sample import (
            correlation_pvalue_with_ess,
        )
        from crosscorr_lib.analysis.surrogate import fdr_bh_q

        for idx, row in result.iterrows():
            d1 = row["detector_1"]
            d2 = row["detector_2"]
            _, p_ess, _ = correlation_pvalue_with_ess(
                wide[d1].values, wide[d2].values, method="spearman"
            )
            result.at[idx, "p_value"] = p_ess

        sig_mask, q_vals = fdr_bh_q(
            result["p_value"].values,
            args.alpha,
            method=args.fdr_method,
        )
        result["q_value"] = q_vals
        result["significant"] = sig_mask

    out_csv = DEFAULT_OUT / "cross_correlation_pairs.csv"
    result.to_csv(out_csv, index=False)
    print(f"\n[OK] {out_csv}")
    print(f"[OK] Пар: {len(result)}")
    if "significant" in result.columns:
        print(f"[OK] Значимых: {int(result['significant'].sum())}")

if __name__ == "__main__":
    main()
