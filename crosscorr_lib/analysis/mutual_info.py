"""Mutual information between time series (KSG KNN estimator).

Классическая информационная мера, ловящая нелинейные связи, которые
коэффициент корреляции теряет. Это классический аналог квантовой
взаимной информации I(A:B) (см. docs/methodology.md).

Реализация: Kraskov-Stoegbauer-Grassberger (KSG), estimator type 1.

    I(X:Y) = psi(k) + psi(N) - <psi(n_x + 1) + psi(n_y + 1)>

где psi — дигамма-функция, n_x / n_y — число точек в x- и y-полосах
k-го соседа в совместном (максимальном) пространстве, N — размер
выборки.

References
----------
Kraskov, Stoegbauer, Grassberger (2004), Phys. Rev. E 69, 066138.
Frenzel & Pompe (2007), Phys. Rev. Lett. 99, 204101 (conditional MI).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.special import digamma


def _as_1d(x: np.ndarray) -> np.ndarray:
    """Привести вход к 1D float64 без NaN (NaN интерполируются)."""
    arr = np.asarray(x, dtype=np.float64).ravel()
    finite = np.isfinite(arr)
    if not finite.all():
        if not finite.any():
            return arr
        idx = np.arange(arr.size)
        arr = arr.copy()
        arr[~finite] = np.interp(idx[~finite], idx[finite], arr[finite])
    return arr


def _validate_k_base(k: int, base: float) -> None:
    """Validate KSG neighbour count and logarithm base."""
    if isinstance(k, bool) or not isinstance(k, (int, np.integer)) or k < 1:
        raise ValueError(f"k must be a positive integer, got {k!r}")
    if not np.isfinite(base) or base <= 0.0 or base == 1.0:
        raise ValueError("base must be finite, positive, and different from 1")


def _warn_on_joint_ties(*arrays: np.ndarray) -> None:
    """Warn when exact duplicate observations make continuous KSG ambiguous."""
    joint = np.column_stack(arrays)
    if np.unique(joint, axis=0).shape[0] < joint.shape[0]:
        warnings.warn(
            "KSG mutual information assumes continuous distributions; "
            "behavior on ties or quantized data is undefined",
            UserWarning,
            stacklevel=3,
        )


def _joint_eps(tree_z: cKDTree, k: int) -> np.ndarray:
    """Расстояние до k-го соседа (без себя) в совместном пространстве."""
    # query k+1: первый сосед — сама точка (расстояние 0).
    dist, _ = tree_z.query(np.asarray(tree_z.data), k=k + 1, p=np.inf)
    return dist[:, k]


def mutual_information(
    x: np.ndarray,
    y: np.ndarray,
    k: int = 5,
    base: float = np.e,
) -> float:
    """Оценка взаимной информации I(X:Y) методом KSG (KNN).

    Estimation assumes continuous distributions; behavior on ties / quantized
    data is undefined. Точные дубликаты совместных наблюдений вызывают
    ``UserWarning``.

    Parameters
    ----------
    x, y : array-like
        Одномерные ряды равной длины.
    k : int, default 5
        Число ближайших соседей.
    base : float, default np.e
        Основание логарифма (по умолчанию наты).

    Returns
    -------
    float
        Взаимная информация I(X:Y) в заданном основании.

    References
    ----------
    Kraskov, Stoegbauer, Grassberger (2004), Phys. Rev. E 69, 066138.
    """
    _validate_k_base(k, base)
    xa_raw = np.asarray(x).ravel()
    ya_raw = np.asarray(y).ravel()
    if xa_raw.size == 0 or ya_raw.size == 0:
        raise ValueError("x and y must be non-empty")
    if xa_raw.size != ya_raw.size:
        raise ValueError(
            f"x and y must have equal lengths, got {xa_raw.size} and {ya_raw.size}"
        )
    xa = _as_1d(xa_raw)
    ya = _as_1d(ya_raw)
    if not np.isfinite(xa).all() or not np.isfinite(ya).all():
        raise ValueError("x and y must contain at least one finite value each")
    n = xa.size
    if n < k + 2:
        raise ValueError("слишком короткие ряды для KSG-оценки")
    _warn_on_joint_ties(xa, ya)

    pts_z = np.column_stack([xa, ya])
    tree_z = cKDTree(pts_z)
    eps = _joint_eps(tree_z, k)

    tree_x = cKDTree(xa[:, None])
    tree_y = cKDTree(ya[:, None])

    # Строго меньше eps: чуть уменьшаем радиус, чтобы не считать границу.
    # ВАЖНО: все маргинальные подсчёты — в той же (Chebyshev) метрике, что и
    # совместный KDTree, иначе в размерности > 1 оценки расходятся.
    r = np.nextafter(eps, -np.inf)
    n_x = np.array([len(tree_x.query_ball_point(xa[i], r[i], p=np.inf)) - 1
                    for i in range(n)])
    n_y = np.array([len(tree_y.query_ball_point(ya[i], r[i], p=np.inf)) - 1
                    for i in range(n)])

    mi_nats = (digamma(k) + digamma(n)
               - np.mean(digamma(n_x + 1) + digamma(n_y + 1)))
    if base == np.e:
        return float(mi_nats)
    return float(mi_nats / np.log(base))


def conditional_mutual_information(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    k: int = 5,
    base: float = np.e,
) -> float:
    """Оценка условной взаимной информации I(X:Y|Z) методом KSG.

    Estimation assumes continuous distributions; behavior on ties / quantized
    data is undefined. Точные дубликаты совместных наблюдений вызывают
    ``UserWarning``.

    Формула (Vejmelka & Palus, 2008):

        I(X:Y|Z) = psi(k) + <psi(n_z + 1) - psi(n_xz + 1) - psi(n_yz + 1)>

    Returns
    -------
    float
        I(X:Y|Z) в заданном основании.
    """
    _validate_k_base(k, base)
    raw = [np.asarray(v).ravel() for v in (x, y, z)]
    if any(v.size == 0 for v in raw):
        raise ValueError("x, y, and z must be non-empty")
    if len({v.size for v in raw}) != 1:
        raise ValueError("x, y, and z must have equal lengths")
    xa, ya, za = (_as_1d(v) for v in raw)
    if not all(np.isfinite(v).all() for v in (xa, ya, za)):
        raise ValueError("x, y, and z must contain at least one finite value each")
    n = xa.size
    if n < k + 2:
        raise ValueError("слишком короткие ряды для KSG-оценки")
    _warn_on_joint_ties(xa, ya, za)

    tree_z = cKDTree(np.column_stack([xa, ya, za]))
    eps = _joint_eps(tree_z, k)
    r = np.nextafter(eps, -np.inf)

    tree_xz = cKDTree(np.column_stack([xa, za]))
    tree_yz = cKDTree(np.column_stack([ya, za]))
    tree_zm = cKDTree(za[:, None])

    xz = np.column_stack([xa, za])
    yz = np.column_stack([ya, za])
    n_xz = np.array([len(tree_xz.query_ball_point(xz[i], r[i], p=np.inf)) - 1
                     for i in range(n)])
    n_yz = np.array([len(tree_yz.query_ball_point(yz[i], r[i], p=np.inf)) - 1
                     for i in range(n)])
    n_z = np.array([len(tree_zm.query_ball_point(za[i], r[i], p=np.inf)) - 1
                    for i in range(n)])

    cmi_nats = (digamma(k)
                + np.mean(digamma(n_z + 1)
                          - digamma(n_xz + 1)
                          - digamma(n_yz + 1)))
    if base == np.e:
        return float(cmi_nats)
    return float(cmi_nats / np.log(base))


def mutual_information_matrix(
    wide: pd.DataFrame,
    k: int = 5,
) -> pd.DataFrame:
    """Матрица попарных MI для всех колонок wide-таблицы.

    Parameters
    ----------
    wide : pandas.DataFrame
        Таблица вида (время x детекторы).
    k : int, default 5
        Число соседей для KSG.

    Returns
    -------
    pandas.DataFrame
        Симметричная матрица (N_detectors x N_detectors), диагональ = 0.
    """
    cols = list(wide.columns)
    ncol = len(cols)
    mat = np.zeros((ncol, ncol), dtype=np.float64)
    for i in range(ncol):
        for j in range(i + 1, ncol):
            mi = mutual_information(
                wide[cols[i]].to_numpy(), wide[cols[j]].to_numpy(), k=k
            )
            mat[i, j] = mi
            mat[j, i] = mi
    return pd.DataFrame(mat, index=cols, columns=cols)
