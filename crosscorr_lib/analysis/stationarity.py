"""
Проверка стационарности временных рядов.

Расширенный тест Дики-Фуллера (ADF) — стандартный тест на наличие
единичного корня. Если p-value < 0.05 — ряд стационарен.
Если p-value > 0.05 — ряд имеет единичный корень (нестационарен).

Нестационарные ряды нельзя использовать в phase randomization
без предварительного дифференцирования или детрендирования.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller


def adf_test(x: np.ndarray, alpha: float = 0.05) -> dict:
    """
    Расширенный тест Дики-Фуллера.

    Args:
        x: 1D временной ряд (без NaN или с NaN — они будут удалены).
        alpha: уровень значимости.

    Returns:
        dict с полями:
            statistic: ADF-статистика
            p_value:   p-value
            n_lags:    число использованных лагов
            n_obs:     число наблюдений
            is_stationary: bool (p_value < alpha)
            critical_values: dict критических значений
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]

    if x.size < 20:
        return {
            "statistic": np.nan,
            "p_value": 1.0,
            "n_lags": 0,
            "n_obs": int(x.size),
            "is_stationary": False,
            "critical_values": {},
        }

    try:
        result = adfuller(x, autolag="AIC")
        statistic, p_value, n_lags, n_obs, critical_values, _ = result
        return {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "n_lags": int(n_lags),
            "n_obs": int(n_obs),
            "is_stationary": bool(p_value < alpha),
            "critical_values": {k: float(v) for k, v in critical_values.items()},
        }
    except Exception as e:  # noqa: BLE001
        return {
            "statistic": np.nan,
            "p_value": 1.0,
            "n_lags": 0,
            "n_obs": int(x.size),
            "is_stationary": False,
            "critical_values": {},
            "error": str(e),
        }


def check_stationarity_wide(
    wide: pd.DataFrame,
    alpha: float = 0.05,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Проверить стационарность всех колонок wide-таблицы.

    Args:
        wide: DataFrame (строки — время, колонки — детекторы).
        alpha: уровень значимости.
        verbose: печатать результаты.

    Returns:
        DataFrame с колонками:
            detector, statistic, p_value, n_lags, n_obs, is_stationary
    """
    rows = []
    for col in wide.columns:
        res = adf_test(wide[col].values, alpha=alpha)
        rows.append({
            "detector": col,
            "statistic": res["statistic"],
            "p_value": res["p_value"],
            "n_lags": res["n_lags"],
            "n_obs": res["n_obs"],
            "is_stationary": res["is_stationary"],
        })

    result = pd.DataFrame(rows)

    if verbose:
        n_total = len(result)
        n_stationary = int(result["is_stationary"].sum())
        n_nonstat = n_total - n_stationary
        print(f"\n[ADF] Стационарных: {n_stationary}/{n_total}")
        if n_nonstat > 0:
            print(f"[ADF] НЕстационарных: {n_nonstat}")
            print(result[~result["is_stationary"]].to_string(index=False))
            print("\n[WARN] Нестационарные ряды могут давать ложные p-values "
                  "в phase randomization. Рекомендуется дифференцирование.")

    return result


def main() -> None:
    """CLI: проверить стационарность unified.parquet."""
    import argparse
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path,
        default=ROOT / "data" / "processed" / "unified.parquet",
    )
    parser.add_argument("--freq", default="1h")
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["bucket"] = df["timestamp_utc"].dt.floor(args.freq)

    # Группируем по detector_id (как в основном пайплайне)
    wide = (
        df.groupby(["detector_id", "bucket"])["residual"]
        .mean()
        .unstack("detector_id")
        .sort_index()
    )

    result = check_stationarity_wide(wide, alpha=args.alpha)
    print(f"\n[OK] Проверено {len(result)} рядов")


if __name__ == "__main__":
    main()
