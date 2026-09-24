"""
Тесты Mantel test.
"""

import numpy as np
import pytest

from crosscorr_lib.analysis.mantel import mantel_test


def test_mantel_perfect_negative_correlation():
    """Идеальная отрицательная связь: dist растёт → corr падает."""
    n = 5
    # Матрица расстояний: d_ij = |i - j|
    dist = np.array([[abs(i - j) for j in range(n)] for i in range(n)],
                    dtype=float)
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
