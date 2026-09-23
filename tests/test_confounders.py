"""
Тесты удаления физических конфаундеров.

Проверяем: два детектора, оба зависящие от Kp, после удаления
конфаундера должны потерять ложную корреляцию.
"""

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.confounders import (
    make_synthetic_confounders,
    remove_confounders,
)


def _make_two_detectors_driven_by_kp(
    n_time: int = 1500,
    coupling: float = 0.8,
    seed: int = 42,
):
    """
    Два детектора, оба зависят от Kp, но между собой не связаны.

    y1 = coupling * Kp + noise1
    y2 = coupling * Kp + noise2

    Без удаления Kp: corr(y1, y2) высокая (общий драйвер).
    С удалением Kp: corr(y1, y2) низкая (только шум).
    """
    rng = np.random.default_rng(seed)

    idx = pd.date_range("2025-01-01", periods=n_time, freq="1h", tz="UTC")
    conf = make_synthetic_confounders(idx, seed=seed)

    # Два детектора: общая компонента от Kp + независимый шум
    common = coupling * conf["kp"].values

    y1 = common + rng.normal(0, 0.3, n_time)
    y2 = common + rng.normal(0, 0.3, n_time)

    wide = pd.DataFrame({"D1": y1, "D2": y2}, index=idx)
    return wide, conf


def test_confounders_correlation_before_after():
    """Корреляция падает после удаления конфаундера."""
    wide, conf = _make_two_detectors_driven_by_kp(n_time=1500, coupling=0.8)

    # До удаления — высокая корреляция (общий Kp)
    corr_before = wide["D1"].corr(wide["D2"])
    assert corr_before > 0.7, (
        f"Ожидали высокую корреляцию, получили {corr_before:.3f}"
    )

    # Удаляем конфаундеры
    cleaned = remove_confounders(wide, conf)

    # После удаления — низкая корреляция
    corr_after = cleaned["D1"].corr(cleaned["D2"])
    assert corr_after < 0.2, (
        f"Ожидали низкую корреляцию, получили {corr_after:.3f}"
    )

    print(f"\n  corr до удаления:  {corr_before:.3f}")
    print(f"  corr после удаления: {corr_after:.3f}")


def test_confounders_preserves_shape():
    """Форма сохраняется."""
    wide, conf = _make_two_detectors_driven_by_kp(n_time=500)
    cleaned = remove_confounders(wide, conf)
    assert cleaned.shape == wide.shape
    assert list(cleaned.columns) == list(wide.columns)
    assert cleaned.index.equals(wide.index)


def test_confounders_no_confounders_in_data():
    """Если детекторы не зависят от конфаундеров, корреляция не меняется."""
    rng = np.random.default_rng(99)
    n = 500
    idx = pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC")
    conf = make_synthetic_confounders(idx, seed=99)

    # Оба ряда — независимый шум
    wide = pd.DataFrame(
        {"D1": rng.normal(size=n), "D2": rng.normal(size=n)},
        index=idx,
    )

    corr_before = wide["D1"].corr(wide["D2"])
    cleaned = remove_confounders(wide, conf)
    corr_after = cleaned["D1"].corr(cleaned["D2"])

    # Оба близки к нулю, разница маленькая
    assert abs(corr_before) < 0.1
    assert abs(corr_after) < 0.1
    print(f"\n  corr до: {corr_before:.4f}, после: {corr_after:.4f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])