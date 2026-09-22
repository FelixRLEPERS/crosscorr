"""
Distance-based analysis: зависимость корреляции от расстояния.

Основной научный вопрос CrossCorr:
    Коррелируют ли близкие сенсоры сильнее, чем далёкие?

Пайплайн:
1. Загрузить cross_correlation_pairs.csv (результат P0-7).
2. Загрузить data/detectors.csv с координатами.
3. Для каждой пары (detector_1, detector_2) посчитать haversine-расстояние.
4. Регрессия: correlation ~ distance_km.
5. Сохранить results/distance_analysis.csv.

Запуск:
    python -m crosscorr_lib.analysis.distance_analysis
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CC = ROOT / "results" / "cross_correlation_pairs.csv"
DEFAULT_DETECTORS = ROOT / "data" / "detectors.csv"
DEFAULT_OUT = ROOT / "results"


def haversine_km(lat1, lon1, lat2, lon2):
    """Расстояние между двумя точками в километрах."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = (
        np.sin(dphi / 2) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    )
    return 2 * R * np.arcsin(np.sqrt(a))


def load_detectors(path: Path) -> pd.DataFrame:
    """Загрузить координаты детекторов. Ожидаемые колонки: detector_id, lat, lon."""
    df = pd.read_csv(path)
    required = {"detector_id", "lat", "lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"detectors.csv: отсутствуют колонки {missing}")
    return df.set_index("detector_id")


def add_distances(
    cc_df: pd.DataFrame,
    detectors: pd.DataFrame,
) -> pd.DataFrame:
    """
    Добавить колонку distance_km для каждой пары детекторов.
    Пары без координат — отбрасываются.
    """
    df = cc_df.copy()

    # Отбрасываем пары с неизвестными детекторами
    mask = (
        df["detector_1"].isin(detectors.index)
        & df["detector_2"].isin(detectors.index)
    )
    n_before = len(df)
    df = df[mask].copy()
    n_after = len(df)

    if n_after < n_before:
        print(f"[WARN] Отброшено {n_before - n_after} пар без координат")

    # Haversine
    distances = []
    for _, row in df.iterrows():
        d1 = detectors.loc[row["detector_1"]]
        d2 = detectors.loc[row["detector_2"]]
        d = haversine_km(
            d1["lat"], d1["lon"],
            d2["lat"], d2["lon"],
        )
        distances.append(d)

    df["distance_km"] = distances
    return df


def fit_distance_model(df: pd.DataFrame) -> dict:
    """
    Простая линейная регрессия: correlation ~ distance_km.
    Возвращает коэффициенты и R².
    """
    x = df["distance_km"].values
    y = df["correlation"].values

    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]

    if x.size < 3:
        return {"slope": np.nan, "intercept": np.nan, "r_squared": np.nan, "n": x.size}

    # OLS: y = a + b*x
    n = x.size
    x_mean = x.mean()
    y_mean = y.mean()
    b = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
    a = y_mean - b * x_mean

    y_pred = a + b * x
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    return {
        "slope": float(b),
        "intercept": float(a),
        "r_squared": float(r_squared),
        "n": int(n),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", type=Path, default=DEFAULT_CC)
    parser.add_argument("--detectors", type=Path, default=DEFAULT_DETECTORS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    # 1. Загрузка
    if not args.cc.exists():
        raise SystemExit(
            f"{args.cc} не найден. Сначала запустите cross_correlation.py"
        )
    if not args.detectors.exists():
        raise SystemExit(
            f"{args.detectors} не найден. Сначала запустите "
            f"scripts/make_synthetic_unified.py"
        )

    cc_df = pd.read_csv(args.cc)
    detectors = load_detectors(args.detectors)
    print(f"[OK] Загружено пар: {len(cc_df)}")
    print(f"[OK] Детекторов: {len(detectors)}")

    # 2. Расстояния
    df = add_distances(cc_df, detectors)

    # 3. Регрессия
    model = fit_distance_model(df)
    print(f"\n[STAT] Регрессия correlation ~ distance_km:")
    print(f"    slope     = {model['slope']:.6f}")
    print(f"    intercept = {model['intercept']:.4f}")
    print(f"    R²        = {model['r_squared']:.4f}")
    print(f"    n         = {model['n']}")

    # 4. Сохранение
    args.out.mkdir(parents=True, exist_ok=True)
    out_csv = args.out / "distance_analysis.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[OK] {out_csv}")

    # 5. Сводка по бинам расстояний
    if len(df) > 5:
        df["distance_bin"] = pd.qcut(df["distance_km"], q=4, duplicates="drop")
        summary = (
            df.groupby("distance_bin", observed=True)
            .agg(
                n_pairs=("correlation", "size"),
                mean_distance_km=("distance_km", "mean"),
                mean_correlation=("correlation", "mean"),
            )
            .round(4)
        )
        summary_path = args.out / "distance_summary.csv"
        summary.to_csv(summary_path)
        print(f"[OK] {summary_path}")
        print(f"\n[STAT] По бинам расстояний:\n{summary}")


if __name__ == "__main__":
    main()