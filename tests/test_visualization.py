"""Тесты визуализации."""

import pandas as pd
import pytest

from crosscorr_lib.analysis.visualization import (
    plot_correlation_heatmap,
    plot_detectors_map,
    plot_distance_correlation,
)


@pytest.fixture
def sample_detectors():
    return pd.DataFrame({
        "detector_id": ["D_A", "D_B", "D_C"],
        "lat": [55.0, 56.0, 60.0],
        "lon": [37.0, 38.0, 30.0],
        "detector_type": ["wspr"] * 3,
    })


@pytest.fixture
def sample_pairs():
    return pd.DataFrame({
        "detector_1": ["D_A", "D_A", "D_B"],
        "detector_2": ["D_B", "D_C", "D_C"],
        "correlation": [0.8, 0.3, 0.2],
        "lag": [0, 0, 0],
        "p_value": [0.001, 0.1, 0.2],
        "q_value": [0.003, 0.2, 0.2],
        "significant": [True, False, False],
    })


@pytest.fixture
def sample_distance():
    return pd.DataFrame({
        "distance_km": [100, 200, 300, 400, 500],
        "correlation": [0.9, 0.7, 0.5, 0.3, 0.1],
    })


def test_plot_detectors_map(sample_detectors, sample_pairs, tmp_path):
    out = plot_detectors_map(sample_detectors, sample_pairs, tmp_path)
    assert out.exists()
    assert out.suffix == ".png"
    # SVG тоже должен быть
    assert (tmp_path / "detectors_map.svg").exists()


def test_plot_correlation_heatmap(sample_pairs, sample_detectors, tmp_path):
    out = plot_correlation_heatmap(sample_pairs, sample_detectors, tmp_path)
    assert out.exists()
    assert out.suffix == ".png"


def test_plot_distance_correlation(sample_distance, tmp_path):
    model = {"slope": -0.002, "intercept": 1.0, "r_squared": 0.99, "n": 5}
    out = plot_distance_correlation(sample_distance, model, tmp_path)
    assert out.exists()
    assert out.suffix == ".png"


def test_plot_distance_correlation_nan_model(sample_distance, tmp_path):
    """Не должно падать, если модель невалидна."""
    model = {"slope": float("nan"), "intercept": float("nan"),
             "r_squared": float("nan"), "n": 5}
    out = plot_distance_correlation(sample_distance, model, tmp_path)
    assert out.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
