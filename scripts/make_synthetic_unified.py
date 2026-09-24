"""
Генератор синтетических данных для тестирования distance-based analysis.

Создаёт:
    data/detectors.csv          — координаты детекторов
    data/processed/unified.parquet — временные ряды

Модель:
    Корреляция между детекторами убывает с расстоянием:
        K(i, j) = exp(-d(i, j) / L), где L = 500 км.
    Плюс AR(1) структура по времени для автокорреляции.

Запуск:
    python scripts/make_synthetic_unified.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# 10 детекторов в разных точках России и Европы
DETECTORS = [
    ("D_MOSCOW",  55.7558, 37.6173, "wspr"),
    ("D_SPB",     59.9311, 30.3609, "wspr"),
    ("D_KALININGRAD", 54.7104, 20.4522, "intermagnet"),
    ("D_EKATERINBURG", 56.8389, 60.6057, "intermagnet"),
    ("D_NOVOSIBIRSK", 55.0084, 82.9357, "ngl"),
    ("D_Krasnoyarsk", 56.0153, 92.8932, "ngl"),
    ("D_IRKUTSK", 52.2870, 104.3050, "wspr"),
    ("D_Vladivostok", 43.1332, 131.9113, "intermagnet"),
    ("D_MURMANSK", 68.9585, 33.0827, "ngl"),
    ("D_SOCHI", 43.5855, 39.7231, "wspr"),
]

LAG_CORRELATION_KM = 500.0   # характерная длина корреляции
N_TIME = 720                  # 30 дней по часам
AR_PHI = 0.7                  # AR(1) коэффициент
SEED = 42


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


def build_covariance_matrix(coords, L):
    """Экспоненциальное ядро: K(i,j) = exp(-d(i,j)/L)."""
    n = len(coords)
    K = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_km(*coords[i], *coords[j])
            K[i, j] = K[j, i] = np.exp(-d / L)
    return K


def main():
    rng = np.random.default_rng(SEED)

    # 1. Координаты
    detector_ids = [d[0] for d in DETECTORS]
    coords = [(d[1], d[2]) for d in DETECTORS]
    types = [d[3] for d in DETECTORS]

    # 2. Ковариационная матрица по пространству
    K = build_covariance_matrix(coords, LAG_CORRELATION_KM)

    # 3. Пространственно-коррелированный "базовый" сигнал
    #    Каждый временной шаг — сэмпл из MVN(0, K)
    L_chol = np.linalg.cholesky(K + 1e-6 * np.eye(len(K)))
    base = L_chol @ rng.normal(size=(len(K), N_TIME))  # (N, T)

    # 4. Наложить AR(1) по времени
    signal = np.zeros_like(base)
    for t in range(1, N_TIME):
        signal[:, t] = AR_PHI * signal[:, t - 1] + base[:, t]

    # 5. Собрать long-format
    timestamps = pd.date_range(
        "2025-01-01", periods=N_TIME, freq="1h", tz="UTC"
    )

    rows = []
    for k, det_id in enumerate(detector_ids):
        df_det = pd.DataFrame({
            "timestamp_utc": timestamps,
            "detector_id": det_id,
            "detector_type": types[k],
            "residual": signal[k],
        })
        rows.append(df_det)

    unified = pd.concat(rows, ignore_index=True)

    # 6. Сохранить
    parquet_path = PROCESSED_DIR / "unified.parquet"
    unified.to_parquet(parquet_path, index=False)
    print(f"[OK] unified.parquet: {unified.shape} -> {parquet_path}")

    # 7. Координаты детекторов
    detectors_df = pd.DataFrame({
        "detector_id": detector_ids,
        "lat": [c[0] for c in coords],
        "lon": [c[1] for c in coords],
        "detector_type": types,
    })
    detectors_path = DATA_DIR / "detectors.csv"
    detectors_df.to_csv(detectors_path, index=False)
    print(f"[OK] detectors.csv: {detectors_df.shape} -> {detectors_path}")


if __name__ == "__main__":
    main()
