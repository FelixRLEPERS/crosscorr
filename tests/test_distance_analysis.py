"""
Тесты distance-based analysis.

Проверяем, что алгоритм восстанавливает искусственную зависимость
корреляции от расстояния: близкие детекторы → сильная корреляция.
Дополнительно (docs/roadmap.md, шаг 2): load_detectors, ветки ошибок,
ветка «пары без координат» и CLI main() с методами mantel/ols.
"""

import runpy
import sys
from pathlib import Path

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
    load_detectors,
)
from crosscorr_lib.analysis.distance_analysis import (
    main as distance_main,
)


def test_haversine_known_distance():
    """Москва (55.7558, 37.6173) — Питер (59.9311, 30.3609) ≈ 635 км."""
    d = haversine_km(55.7558, 37.6173, 59.9311, 30.3609)
    assert 600 < d < 700, f"Ожидали ~635 км, получили {d}"


def test_haversine_zero():
    d = haversine_km(55.0, 37.0, 55.0, 37.0)
    assert d < 1e-6


def test_add_distances_basic():
    cc = pd.DataFrame(
        {
            "detector_1": ["A", "A", "B"],
            "detector_2": ["B", "C", "C"],
            "correlation": [0.8, 0.5, 0.3],
            "lag": [0, 0, 0],
        }
    )
    detectors = pd.DataFrame(
        {
            "detector_id": ["A", "B", "C"],
            "lat": [55.0, 56.0, 60.0],
            "lon": [37.0, 38.0, 30.0],
        }
    ).set_index("detector_id")

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


def test_fit_distance_model_uses_true_correlation():
    """fit_distance_model использует rho_at_best_lag, не Fisher."""
    distances = np.array([100, 200, 300, 400, 500])
    rho = np.array([0.9, 0.7, 0.5, 0.3, 0.1])
    fisher = np.array([3.0, 2.5, 2.0, 1.5, 1.0])
    df = pd.DataFrame(
        {
            "distance_km": distances,
            "correlation": fisher,  # deprecated alias = Fisher (старый CSV)
            "max_stat_score": fisher,  # Fisher-score
            "rho_at_best_lag": rho,  # настоящий Spearman
        }
    )

    model = fit_distance_model(df)

    # Наклон должен соответствовать rho ~ distance (≈ -0.002),
    # а не Fisher-score ~ distance (≈ -0.005).
    expected = np.polyfit(distances, rho, 1)[0]
    assert abs(model["slope"] - expected) < 1e-9, (
        f"slope={model['slope']} рассчитан не по rho_at_best_lag"
    )
    assert model["r_squared"] > 0.95


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
        signals[detector_ids[i]] = alpha * base + (1 - alpha) * rng.normal(size=n_time)

    # Собираем wide-таблицу
    idx = pd.date_range("2025-01-01", periods=n_time, freq="1h", tz="UTC")
    wide = pd.DataFrame(dict(signals), index=idx)

    # CC-пары
    cc = cross_correlation_pairs(wide, max_lag=10, alpha=0.05)

    # Координаты
    detectors = pd.DataFrame(
        {
            "detector_id": detector_ids,
            "lat": lats,
            "lon": lons,
        }
    ).set_index("detector_id")

    df = add_distances(cc, detectors)
    model = fit_distance_model(df)

    print(f"\nSlope: {model['slope']:.6f}")
    print(f"R²: {model['r_squared']:.4f}")
    print(f"n: {model['n']}")

    assert model["slope"] < 0, f"Ожидали отрицательный slope, получили {model['slope']}"


# ------------------------------------------------------------------ #
#              load_detectors и ветки ошибок (roadmap шаг 2)          #
# ------------------------------------------------------------------ #


def test_load_detectors_sets_index(tmp_path):
    path = tmp_path / "detectors.csv"
    pd.DataFrame({"detector_id": ["A", "B"], "lat": [55.0, 59.0], "lon": [37.0, 30.0]}).to_csv(
        path, index=False
    )

    df = load_detectors(path)

    assert list(df.index) == ["A", "B"]
    assert {"lat", "lon"} <= set(df.columns)


def test_load_detectors_missing_column_raises(tmp_path):
    path = tmp_path / "detectors.csv"
    pd.DataFrame({"detector_id": ["A"], "lat": [55.0]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="отсутствуют колонки"):
        load_detectors(path)


def test_add_distances_drops_unknown_detector(capsys):
    """Пара с неизвестным детектором отбрасывается с предупреждением."""
    cc = pd.DataFrame(
        {
            "detector_1": ["A", "X"],
            "detector_2": ["B", "A"],
            "correlation": [0.8, 0.1],
            "lag": [0, 0],
        }
    )
    detectors = pd.DataFrame(
        {
            "detector_id": ["A", "B"],
            "lat": [55.0, 56.0],
            "lon": [37.0, 38.0],
        }
    ).set_index("detector_id")

    df = add_distances(cc, detectors)

    assert len(df) == 1
    assert "[WARN] Отброшено 1 пар" in capsys.readouterr().out
    assert df["distance_km"].iloc[0] > 0


def test_fit_distance_model_too_few_rows_returns_nan():
    """n < 3 после отбрасывания NaN → NaN-коэффициенты, а не ±inf."""
    df = pd.DataFrame({"distance_km": [100.0, 200.0], "rho_at_best_lag": [0.8, 0.2]})

    model = fit_distance_model(df)

    assert model["n"] == 2
    assert np.isnan(model["slope"])
    assert np.isnan(model["intercept"])
    assert np.isnan(model["r_squared"])


def test_fit_distance_model_drops_nan_rows():
    """NaN-строки не участвуют в регрессии, n считается по оставшимся."""
    df = pd.DataFrame(
        {
            "distance_km": [100.0, 200.0, np.nan, 400.0, 500.0],
            "rho_at_best_lag": [0.9, 0.7, 0.5, 0.3, 0.1],
        }
    )

    model = fit_distance_model(df)

    assert model["n"] == 4
    assert model["slope"] < 0
    assert np.isfinite(model["r_squared"])


def test_fit_distance_model_constant_distance_returns_nan():
    """Все distance_km равны → вырожденный вход: NaN, а не slope = ±inf."""
    df = pd.DataFrame(
        {
            "distance_km": [500.0, 500.0, 500.0, 500.0],
            "rho_at_best_lag": [0.9, 0.7, 0.5, 0.1],
        }
    )

    model = fit_distance_model(df)

    assert model["n"] == 4
    assert np.isnan(model["slope"])
    assert np.isnan(model["intercept"])
    assert np.isnan(model["r_squared"])


# ------------------------------------------------------------------ #
#                              CLI main()                             #
# ------------------------------------------------------------------ #


def _write_main_inputs(tmp_path):
    """CSV для main(): 4 детектора -> C(4,2) = 6 пар (блок бинов требует >5)."""
    pairs = [(i, j) for i in range(4) for j in range(i + 1, 4)]
    lons = [0.0, 3.0, 8.0, 14.0]  # все 6 расстояний различны → qcut в 4 бина
    rho = [0.9, 0.7, 0.5, 0.85, 0.6, 0.8]  # убывает с расстоянием

    cc = pd.DataFrame(
        {
            "detector_1": [f"D{i}" for i, _ in pairs],
            "detector_2": [f"D{j}" for _, j in pairs],
            "correlation": rho,
            "rho_at_best_lag": rho,
            "lag": [0] * len(pairs),
        }
    )
    detectors = pd.DataFrame(
        {
            "detector_id": [f"D{i}" for i in range(4)],
            "lat": [0.0, 0.0, 0.0, 0.0],
            "lon": lons,
        }
    )

    cc_path = tmp_path / "cc.csv"
    det_path = tmp_path / "detectors.csv"
    cc.to_csv(cc_path, index=False)
    detectors.to_csv(det_path, index=False)
    return cc_path, det_path


def _run_main(tmp_path, monkeypatch, *extra):
    cc_path, det_path = _write_main_inputs(tmp_path)
    out_dir = tmp_path / "results"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "distance_analysis",
            "--cc",
            str(cc_path),
            "--detectors",
            str(det_path),
            "--out",
            str(out_dir),
            *extra,
        ],
    )
    distance_main()
    return out_dir


def test_main_missing_cc_raises_system_exit(tmp_path, monkeypatch):
    detectors = tmp_path / "detectors.csv"
    pd.DataFrame({"detector_id": ["A"], "lat": [55.0], "lon": [37.0]}).to_csv(
        detectors, index=False
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "distance_analysis",
            "--cc",
            str(tmp_path / "nope.csv"),
            "--detectors",
            str(detectors),
            "--out",
            str(tmp_path / "out"),
        ],
    )

    with pytest.raises(SystemExit):
        distance_main()


def test_main_missing_detectors_raises_system_exit(tmp_path, monkeypatch):
    cc_path, _ = _write_main_inputs(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "distance_analysis",
            "--cc",
            str(cc_path),
            "--detectors",
            str(tmp_path / "nope.csv"),
            "--out",
            str(tmp_path / "out"),
        ],
    )

    with pytest.raises(SystemExit):
        distance_main()


def test_main_mantel_pipeline(tmp_path, monkeypatch, capsys):
    """Полный прогон --method mantel: пары, матрицы, результат, бины."""
    out_dir = _run_main(
        tmp_path, monkeypatch, "--method", "mantel", "--n-permutations", "99", "--seed", "7"
    )

    pairs = pd.read_csv(out_dir / "distance_analysis.csv")
    assert "distance_km" in pairs.columns
    assert len(pairs) == 6

    result = pd.read_csv(out_dir / "mantel_result.csv")
    assert {"r_obs", "p_value", "n_permutations", "method"} <= set(result.columns)
    assert 0.0 <= float(result["p_value"].iloc[0]) <= 1.0

    summary = pd.read_csv(out_dir / "distance_summary.csv")
    assert {"n_pairs", "mean_distance_km", "mean_correlation"} <= set(summary.columns)

    out = capsys.readouterr().out
    assert "[MANTEL]" in out
    assert "По бинам расстояний" in out


def test_main_ols_pipeline(tmp_path, monkeypatch, capsys):
    """Ветка --method ols: регрессия вместо Mantel, mantel_result.csv нет."""
    out_dir = _run_main(tmp_path, monkeypatch, "--method", "ols")

    assert (out_dir / "distance_analysis.csv").exists()
    assert not (out_dir / "mantel_result.csv").exists()

    out = capsys.readouterr().out
    assert "OLS регрессия" in out
    assert "slope" in out


def test_script_entry_point_runs(tmp_path, monkeypatch, capsys):
    """Запуск модуля как скрипта (guard ``__main__``) доходит до main()."""
    module = (
        Path(__file__).resolve().parents[1] / "crosscorr_lib" / "analysis" / "distance_analysis.py"
    )
    cc_path, det_path = _write_main_inputs(tmp_path)
    out_dir = tmp_path / "results"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "distance_analysis.py",
            "--cc",
            str(cc_path),
            "--detectors",
            str(det_path),
            "--out",
            str(out_dir),
            "--method",
            "ols",
        ],
    )

    runpy.run_path(str(module), run_name="__main__")

    assert (out_dir / "distance_analysis.csv").exists()
    assert "OLS регрессия" in capsys.readouterr().out


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
