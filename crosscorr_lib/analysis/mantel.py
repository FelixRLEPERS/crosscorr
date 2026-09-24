"""
Mantel test для матриц расстояний и корреляций.

Заменяет OLS-регрессию correlation ~ distance_km, которая нарушает
i.i.d. остатков: ε_ij и ε_ik коррелируют (общий узел i).

Mantel test использует пермутацию строк и столбцов матрицы расстояний,
сохраняя топологию графа детекторов.

Reference:
    Mantel, N. (1967). The detection of disease clustering and a
    generalized regression approach. Cancer Research, 27(2), 209–220.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mantel_test(
    dist_matrix: np.ndarray,
    corr_matrix: np.ndarray,
    n_permutations: int = 9999,
    seed: int = 42,
    alternative: str = "less",
) -> dict:
    """
    Mantel test: проверка связи между матрицей расстояний и корреляций.

    Args:
        dist_matrix: (N, N) симметричная матрица расстояний.
        corr_matrix: (N, N) симметричная матрица корреляций.
        n_permutations: число пермутаций.
        seed: seed для воспроизводимости.
        alternative: 'less' (corr убывает с расстоянием),
                     'greater', 'two-sided'.

    Returns:
        dict: {'r_obs', 'p_value', 'n_permutations', 'method'}
    """
    dist = np.asarray(dist_matrix, dtype=float)
    corr = np.asarray(corr_matrix, dtype=float)

    n = dist.shape[0]
    if dist.shape != (n, n) or corr.shape != (n, n):
        raise ValueError("Матрицы должны быть (N, N)")

    triu = np.triu_indices(n, k=1)
    x = dist[triu]
    y = corr[triu]

    x_c = x - x.mean()
    y_c = y - y.mean()
    x_norm = np.linalg.norm(x_c)
    y_norm = np.linalg.norm(y_c)

    if x_norm == 0 or y_norm == 0:
        return {
            "r_obs": 0.0,
            "p_value": 1.0,
            "n_permutations": n_permutations,
            "method": "mantel",
        }

    r_obs = float(np.dot(x_c, y_c) / (x_norm * y_norm))

    rng = np.random.default_rng(seed)
    count_extreme = 0

    for _ in range(n_permutations):
        idx = rng.permutation(n)
        dist_perm = dist[idx, :][:, idx]
        x_perm = dist_perm[triu]

        x_p_c = x_perm - x_perm.mean()
        x_p_norm = np.linalg.norm(x_p_c)

        if x_p_norm == 0:
            r_perm = 0.0
        else:
            r_perm = float(np.dot(x_p_c, y_c) / (x_p_norm * y_norm))

        if alternative == "less" and r_perm <= r_obs:
            count_extreme += 1
        elif alternative == "greater" and r_perm >= r_obs:
            count_extreme += 1
        elif alternative == "two-sided" and abs(r_perm) >= abs(r_obs):
            count_extreme += 1

    p_value = (1.0 + count_extreme) / (1.0 + n_permutations)

    return {
        "r_obs": r_obs,
        "p_value": float(p_value),
        "n_permutations": n_permutations,
        "method": "mantel",
    }


def build_corr_matrix(
    corr_pairs: pd.DataFrame,
    detector_ids: list[str],
) -> np.ndarray:
    """
    Собрать (N, N) матрицу корреляций из tidy-таблицы пар.

    Args:
        corr_pairs: DataFrame с колонками detector_1, detector_2, correlation.
        detector_ids: список ID в нужном порядке (индекс матрицы).

    Returns:
        (N, N) симметричная матрица с единицами на диагонали.
    """
    import pandas as pd  # noqa: F401

    n = len(detector_ids)
    idx = {d: i for i, d in enumerate(detector_ids)}
    mat = np.full((n, n), np.nan)
    np.fill_diagonal(mat, 1.0)

    for _, row in corr_pairs.iterrows():
        i = idx.get(row["detector_1"])
        j = idx.get(row["detector_2"])
        if i is None or j is None:
            continue
        if np.isfinite(row["correlation"]):
            mat[i, j] = float(row["correlation"])
            mat[j, i] = float(row["correlation"])

    return mat


def build_dist_matrix(
    detectors: pd.DataFrame,
    detector_ids: list[str],
) -> np.ndarray:
    """
    Собрать (N, N) матрицу haversine-расстояний.

    Args:
        detectors: DataFrame с колонками detector_id, lat, lon.
        detector_ids: список ID в нужном порядке.

    Returns:
        (N, N) симметричная матрица с нулями на диагонали.
    """
    from crosscorr_lib.analysis.distance_analysis import haversine_km

    n = len(detector_ids)
    idx = {d: i for i, d in enumerate(detector_ids)}
    coords = {}
    for _, row in detectors.iterrows():
        if row["detector_id"] in idx:
            coords[row["detector_id"]] = (row["lat"], row["lon"])

    mat = np.zeros((n, n))
    for d1, i in idx.items():
        for d2, j in idx.items():
            if i >= j:
                continue
            if d1 not in coords or d2 not in coords:
                continue
            lat1, lon1 = coords[d1]
            lat2, lon2 = coords[d2]
            d = haversine_km(lat1, lon1, lat2, lon2)
            mat[i, j] = d
            mat[j, i] = d

    return mat
