"""
Тесты Mantel test.
"""

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.mantel import (
    build_corr_matrix,
    build_dist_matrix,
    mantel_test,
)


def test_mantel_perfect_negative_correlation():
    """Идеальная отрицательная связь: dist растёт → corr падает."""
    n = 5
    # Матрица расстояний: d_ij = |i - j|
    dist = np.array([[abs(i - j) for j in range(n)] for i in range(n)], dtype=float)
    # Идеальная отрицательная связь
    corr = 1.0 - dist / dist.max()

    result = mantel_test(dist, corr, n_permutations=999, seed=42)

    assert result["r_obs"] < -0.9, f"r_obs={result['r_obs']}"
    assert result["p_value"] < 0.05, f"p={result['p_value']}"


def test_mantel_no_correlation():
    """Чистый шум: p-value должно быть большим."""
    rng = np.random.default_rng(42)
    n = 6
    dist = rng.uniform(0, 100, size=(n, n))
    dist = (dist + dist.T) / 2
    np.fill_diagonal(dist, 0)

    corr = rng.normal(size=(n, n))
    corr = (corr + corr.T) / 2
    np.fill_diagonal(corr, 1.0)

    result = mantel_test(dist, corr, n_permutations=999, seed=42)
    assert result["p_value"] > 0.1, f"Ложное срабатывание: p={result['p_value']}"


def test_mantel_deterministic_with_seed():
    """Один seed — один результат."""
    rng = np.random.default_rng(0)
    n = 5
    dist = rng.uniform(0, 100, size=(n, n))
    dist = (dist + dist.T) / 2
    np.fill_diagonal(dist, 0)

    corr = rng.normal(size=(n, n))
    corr = (corr + corr.T) / 2
    np.fill_diagonal(corr, 1.0)

    r1 = mantel_test(dist, corr, n_permutations=499, seed=42)
    r2 = mantel_test(dist, corr, n_permutations=499, seed=42)

    assert r1["r_obs"] == r2["r_obs"]
    assert r1["p_value"] == r2["p_value"]


def test_mantel_nan_corr_matrix():
    """NaN в матрице → p_value=1.0, не минимум."""
    rng = np.random.default_rng(0)
    n = 10
    corr = rng.normal(size=(n, n))
    corr = (corr + corr.T) / 2
    np.fill_diagonal(corr, 1.0)
    corr[0, 1] = np.nan
    corr[1, 0] = np.nan

    dist = rng.uniform(0, 100, size=(n, n))
    dist = (dist + dist.T) / 2
    np.fill_diagonal(dist, 0)

    result = mantel_test(corr, dist, n_permutations=99, seed=42)
    p = result["p_value"]
    assert p >= 0.5, f"NaN дала p={p}, ожидалось >= 0.5"


def test_mantel_unknown_alternative_raises():
    """Невалидный alternative → ValueError."""
    n = 5
    corr = np.eye(n)
    dist = np.ones((n, n)) - np.eye(n)

    with pytest.raises(ValueError, match="alternative"):
        mantel_test(corr, dist, n_permutations=50, alternative="bogus")


def test_mantel_rejects_shape_mismatch():
    """Матрица не (N, N) → ValueError."""
    dist = np.ones((3, 3))
    corr = np.ones((3, 4))

    with pytest.raises(ValueError, match="N, N"):
        mantel_test(dist, corr, n_permutations=10)


def _perfect_negative_pair(n: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """Идеально монотонная пара: corr = 1 - dist/max, r_obs = -1."""
    dist = np.array([[abs(i - j) for j in range(n)] for i in range(n)], dtype=float)
    corr = 1.0 - dist / dist.max()
    return dist, corr


def test_mantel_alternative_greater():
    """'greater': r_obs = -1 → почти все пермутации не меньше него, p ≈ 1."""
    dist, corr = _perfect_negative_pair()

    result = mantel_test(dist, corr, n_permutations=199, seed=1, alternative="greater")

    assert result["r_obs"] < -0.9
    assert 0.5 < result["p_value"] <= 1.0


def test_mantel_alternative_two_sided():
    """'two-sided': |r_perm| >= |r_obs| достигается почти никогда → p мала."""
    dist, corr = _perfect_negative_pair()

    result = mantel_test(dist, corr, n_permutations=199, seed=1, alternative="two-sided")

    assert result["r_obs"] < -0.9
    assert 0.0 < result["p_value"] < 0.1
    # two-sided строго строже 'greater' при r_obs = -1
    greater = mantel_test(dist, corr, n_permutations=199, seed=1, alternative="greater")
    assert result["p_value"] < greater["p_value"]


def test_mantel_two_sided_counts_when_r_obs_zero():
    """'two-sided' при r_obs = 0: |r_perm| >= 0 всегда → каждая пермутация засчитана."""
    dist = np.array(
        [
            [0.0, 1.0, 2.0],
            [1.0, 0.0, 3.0],
            [2.0, 3.0, 0.0],
        ]
    )
    # Подобрано так, что центрированные векторы ортогональны → r_obs = 0:
    # верхняя диагональ dist = (1, 2, 3), corr = (0.5, 0.9, 0.5).
    corr = np.array(
        [
            [1.0, 0.5, 0.9],
            [0.5, 1.0, 0.5],
            [0.9, 0.5, 1.0],
        ]
    )

    result = mantel_test(dist, corr, n_permutations=199, seed=3, alternative="two-sided")

    assert result["r_obs"] == pytest.approx(0.0, abs=1e-12)
    assert result["p_value"] == pytest.approx(1.0)


def test_mantel_zero_norm_permutation_branch():
    """Исполняется защитная ветка ``x_p_norm == 0 → r_perm = 0.0``.

    Для симметричной матрицы пермутация строк/столбцов сохраняет
    мультимножество внедиагональных элементов, поэтому x_p_norm всегда равен
    x_norm и ветка недостижима. Здесь намеренно передаётся несимметричная
    матрица: у неё найдётся пермутация, вся верхняя диагональ которой равна.
    """
    dist = np.array(
        [
            [0.0, 1.0, 5.0],
            [5.0, 0.0, 5.0],
            [5.0, 5.0, 0.0],
        ]
    )
    corr = np.array(
        [
            [1.0, 0.9, 0.1],
            [0.9, 1.0, 0.5],
            [0.1, 0.5, 1.0],
        ]
    )

    result = mantel_test(dist, corr, n_permutations=200, seed=42)

    assert np.isfinite(result["r_obs"])
    assert 0.0 <= result["p_value"] <= 1.0
    assert result["method"] == "mantel"
    assert result["n_permutations"] == 200


def test_build_corr_matrix_prefers_rho_at_best_lag():
    """Из двух колонок берётся rho_at_best_lag, а не deprecated correlation."""
    pairs = pd.DataFrame(
        {
            "detector_1": ["A", "B"],
            "detector_2": ["B", "C"],
            "rho_at_best_lag": [0.5, -0.25],
            "correlation": [0.99, 0.98],  # deprecated alias — игнорируется
        }
    )

    mat = build_corr_matrix(pairs, ["A", "B", "C"])

    assert mat[0, 1] == pytest.approx(0.5)
    assert mat[1, 0] == pytest.approx(0.5)  # симметрия
    assert mat[1, 2] == pytest.approx(-0.25)
    assert mat[2, 1] == pytest.approx(-0.25)
    np.testing.assert_array_equal(np.diag(mat), np.ones(3))
    # заполнены только известные пары, остальное — NaN
    assert np.isnan(mat[0, 2]) and np.isnan(mat[2, 0])


def test_build_corr_matrix_falls_back_to_correlation():
    """Без rho_at_best_lag используется deprecated колонка correlation."""
    pairs = pd.DataFrame(
        {
            "detector_1": ["A"],
            "detector_2": ["B"],
            "correlation": [0.4],
        }
    )

    mat = build_corr_matrix(pairs, ["A", "B", "C"])

    assert mat[0, 1] == pytest.approx(0.4)
    assert mat[1, 0] == pytest.approx(0.4)


def test_build_corr_matrix_skips_unknown_detector_and_nan():
    """Неизвестный детектор и NaN-строка не попадают в матрицу."""
    pairs = pd.DataFrame(
        {
            "detector_1": ["A", "X", "B"],
            "detector_2": ["B", "A", "C"],
            "rho_at_best_lag": [0.5, 0.9, np.nan],
        }
    )

    mat = build_corr_matrix(pairs, ["A", "B", "C"])

    assert mat[0, 1] == pytest.approx(0.5)
    assert mat[1, 0] == pytest.approx(0.5)
    assert not np.any(mat == 0.9)  # строка с неизвестным "X" пропущена
    assert np.isnan(mat[1, 2])  # NaN-значение пропущено
    assert mat[2, 2] == 1.0  # диагональ единицы


def test_build_corr_matrix_empty_pairs():
    """Пустая таблица пар → матрица только с единицами на диагонали."""
    pairs = pd.DataFrame(
        {
            "detector_1": pd.Series([], dtype=str),
            "detector_2": pd.Series([], dtype=str),
            "rho_at_best_lag": pd.Series([], dtype=float),
        }
    )

    mat = build_corr_matrix(pairs, ["A", "B"])

    assert mat.shape == (2, 2)
    assert mat[0, 0] == 1.0 and mat[1, 1] == 1.0
    assert np.isnan(mat[0, 1]) and np.isnan(mat[1, 0])


def test_build_dist_matrix_haversine_symmetry():
    """Расстояния считаются по haversine и симметричны."""
    detectors = pd.DataFrame(
        {
            "detector_id": ["A", "B", "C", "GHOST"],
            "lat": [55.7558, 59.9311, 60.0, 0.0],
            "lon": [37.6173, 30.3609, 30.0, 0.0],
        }
    )

    # GHOST есть в таблице, но его нет в списке id — строка пропускается.
    mat = build_dist_matrix(detectors, ["A", "B", "C"])

    assert mat.shape == (3, 3)
    assert 600 < mat[0, 1] < 700  # Москва — Петербург
    assert mat[0, 1] == pytest.approx(mat[1, 0])
    assert mat[0, 2] == pytest.approx(mat[2, 0])
    assert mat[0, 1] < mat[0, 2]  # A-B ближе, чем A-C
    # FIX (2026-10-27): диагональ теперь 0.0, как и обещает docstring
    np.testing.assert_array_equal(np.diag(mat), np.zeros(3))


def test_build_dist_matrix_missing_coords_stay_nan():
    """Детектор из списка id, отсутствующий в таблице координат → NaN."""
    detectors = pd.DataFrame(
        {
            "detector_id": ["A", "B"],
            "lat": [55.7558, 59.9311],
            "lon": [37.6173, 30.3609],
        }
    )

    mat = build_dist_matrix(detectors, ["A", "B", "C"])  # C нет в координатах

    assert not np.isnan(mat[0, 1])
    assert np.isnan(mat[0, 2]) and np.isnan(mat[1, 2])
    # диагональ заполнена нулями независимо от наличия координат
    np.testing.assert_array_equal(np.diag(mat), np.zeros(3))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
