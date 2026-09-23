"""
Physical confounders: Kp, Dst, F10.7 — общие драйверы геофизических рядов.

Если два детектора коррелируют, это может быть не связь между ними,
а общая зависимость от солнечной активности. Модуль удаляет эту
компоненту перед кросс-корреляционным анализом.

Реальные данные:
    Kp:     GFZ Potsdam — https://www.gfz-potsdam.de/kp-index
    Dst:    WDC Kyoto  — https://wdc.kugi.kyoto-u.ac.jp/dstae/
    F10.7:  NOAA SWPC  — https://services.swpc.noaa.gov/json/solar-cycle/
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFOUNDERS = ROOT / "data" / "confounders.csv"


def load_confounders(path: Path) -> pd.DataFrame:
    """
    Загрузить конфаундеры. Ожидаемые колонки:
        timestamp_utc, kp, dst, f107

    Возвращает DataFrame с DatetimeIndex, отсортированный по времени.
    """
    df = pd.read_csv(path)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.set_index("timestamp_utc").sort_index()
    return df


def make_synthetic_confounders(
    timestamps: pd.DatetimeIndex,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Генерирует синтетические Kp, Dst, F10.7.

    Kp:   AR(1), 0..9
    Dst:  AR(1), -200..+20 (нТл)
    F107: медленный тренд + шум, 70..300 (sfu)
    """
    rng = np.random.default_rng(seed)
    n = len(timestamps)

    def ar1(phi, sigma):
        s = np.zeros(n)
        for i in range(1, n):
            s[i] = phi * s[i - 1] + rng.normal(0, sigma)
        return s

    kp = np.clip(3.0 + ar1(0.95, 0.5), 0, 9)
    dst = np.clip(-30 + ar1(0.98, 10), -200, 20)
    f107 = np.clip(150 + ar1(0.995, 5) + np.linspace(-30, 30, n), 70, 300)

    return pd.DataFrame(
        {"kp": kp, "dst": dst, "f107": f107},
        index=timestamps,
    ).rename_axis("timestamp_utc")


def _align_confounders(
    wide: pd.DataFrame,
    confounders: pd.DataFrame,
) -> pd.DataFrame:
    """Привести конфаундеры к индексу wide: ресемплинг + интерполяция."""
    conf = confounders.reindex(wide.index, method="ffill")
    conf = conf.interpolate(method="linear", limit_direction="both")
    return conf


def remove_confounders(
    wide: pd.DataFrame,
    confounders: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Удалить вклад конфаундеров из каждого ряда wide через OLS.

    Для каждого детектора:
        y(t) = α + β1*Kp(t) + β2*Dst(t) + β3*F107(t) + residual(t)
    Возвращает DataFrame с residual'ами той же формы, что wide.
    """
    if columns is None:
        columns = [c for c in ["kp", "dst", "f107"] if c in confounders.columns]

    if not columns:
        raise ValueError("Нет доступных конфаундеров для удаления")

    conf = _align_confounders(wide, confounders)

    mask = conf[columns].notna().all(axis=1)

    X = conf.loc[mask, columns].values
    X = np.column_stack([np.ones(len(X)), X])

    result = pd.DataFrame(index=wide.index, columns=wide.columns, dtype=float)

    for col in wide.columns:
        y = wide[col].values
        valid = mask.values & ~np.isnan(y)

        if valid.sum() < len(columns) + 2:
            result[col] = y
            continue

        X_v = X[valid]
        y_v = y[valid]

        try:
            beta, *_ = np.linalg.lstsq(X_v, y_v, rcond=None)
        except np.linalg.LinAlgError:
            result[col] = y
            continue

        y_pred = X_v @ beta
        residuals = np.full_like(y, np.nan, dtype=float)
        residuals[valid] = y_v - y_pred
        result[col] = residuals

    return result


def main() -> None:
    """CLI: показать сводку конфаундеров."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_CONFOUNDERS)
    args = parser.parse_args()

    if not args.path.exists():
        print(f"[WARN] {args.path} не найден.")
        print("Создайте файл или используйте make_synthetic_confounders().")
        return

    conf = load_confounders(args.path)
    print(f"[OK] Загружено {len(conf)} строк")
    print(f"[OK] Колонки: {list(conf.columns)}")
    print(f"[OK] Диапазон: {conf.index.min()} — {conf.index.max()}")
    print()
    print(conf.describe().round(3))


if __name__ == "__main__":
    main()