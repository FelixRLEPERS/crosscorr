"""
Тесты distance-based analysis.

Проверяем, что алгоритм восстанавливает искусственную зависимость
корреляции от расстояния: близкие детекторы → сильная корреляция.
"""

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.cross_correlation import (
    cross_correlation_pairs,
)
from crosscorr_lib.analysis.distance_analysis import (
    add_distances,
    fit_distance_model,
    haversine_km,
)


def test_haversine_known_distance():
    """Москва (55.7558, 37.6173) — Питер (59.9311, 30.3609) ≈ 635 км."""
    d = haversine_km(55.7558, 37.6173, 59.9311, 30.3609)
    assert 600 < d < 700, f"Ожидали ~635 км, получили {d}"


def test_haversine_zero():
    d = haversine_km(55.0, 37.0, 55.0, 37.0)
    assert d < 1e-6


def test_add_distances_basic():
    cc = pd.DataFrame({
        "detector_1": ["A", "A", "B"],
        "detector_2": ["B", "C", "C"],
        "correlation": [0.8, 0.5, 0.3],
        "lag": [0, 0, 0],
    })
    detectors = pd.DataFrame({
        "detector_id": ["A", "B", "C"],
        "lat": [55.0, 56.0, 60.0],
        "lon": [37.0, 38.0, 30.0],
    }).set_index("detector_id")

    df = add_distances(cc, detectors)
    assert "distance_km" in df.columns
    assert len(df) == 3
    # A-B ближе, чем A-C
    d_ab = df[df["detector_2"] == "B"]["distance_km"].iloc[0]
    d_ac = df[df["detector_2"] == "C"]["distance_km"].iloc[0]
    assert d_ab < d_ac


def test_fit_distance_model_negative_slope():
    """Искусственные данные: близкие → сильная корреляция."""
    distances = np.array([100, 200, 300, 400, 500])
    correlations = np.array([0.9, 0.7, 0.5, 0.3, 0.1])
    df = pd.DataFrame({"distance_km": distances, "correlation": correlations})
    model = fit_distance_model(df)
    assert model["slope"] < 0, "Slope должен быть отрицательным"
    assert model["r_squared"] > 0.95, "R² должен быть близким к 1"


def test_end_to_end_synthetic():
    """
    Полный пайплайн на синтетике с известной зависимостью:
    восстановить отрицательный slope.
    """
    rng = np.random.default_rng(42)

    # 5 детекторов на прямой линии вдоль экватора
    lats = np.zeros(5)
    lons = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
    detector_ids = [f"D{i}" for i in range(5)]

    # Генерируем корреляции как функцию расстояния
    # Между D0-D1 (близко): высокая; D0-D4 (далеко): низкая
    n_time = 500
    signals = {}
    base = rng.normal(size=n_time)
    for i in range(5):
        # Каждый следующий детектор — слабее связан с базовым сигналом
        alpha = np.exp(-i * 0.5)
        signals[detector_ids[i]] = (
            alpha * base + (1 - alpha) * rng.normal(size=n_time)
        )

    # Собираем wide-таблицу
    idx = pd.date_range("2025-01-01", periods=n_time, freq="1h", tz="UTC")
    wide = pd.DataFrame(dict(signals), index=idx)

    # CC-пары
    cc = cross_correlation_pairs(wide, max_lag=10, alpha=0.05)

    # Координаты
    detectors = pd.DataFrame({
        "detector_id": detector_ids,
        "lat": lats,
        "lon": lons,
    }).set_index("detector_id")

    df = add_distances(cc, detectors)
    model = fit_distance_model(df)

    print(f"\nSlope: {model['slope']:.6f}")
    print(f"R²: {model['r_squared']:.4f}")
    print(f"n: {model['n']}")

    assert model["slope"] < 0, (
        f"Ожидали отрицательный slope, получили {model['slope']}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
