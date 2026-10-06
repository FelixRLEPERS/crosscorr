"""Multiscale entropy (MSE) of time series.

Классический scale axis `s` — дискретный аналог MERA (см.
docs/methodology.md). MSE(s) = SampEn(coarse-grained series, m, r).

Coarse-graining (Costa et al.):

    x_s[i] = mean(x[i*s : (i+1)*s])

References
----------
Richman & Moorman (2000), Am. J. Physiol. 278, H2039 (SampEn).
Costa, Goldberger, Peng (2002), Phys. Rev. Lett. 89, 068102 (MSE).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


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


def sample_entropy(
    x: np.ndarray,
    m: int = 2,
    r: float | None = None,
) -> float:
    """Sample entropy SampEn(m, r, N).

    SampEn = -log(A / B), где B — число пар шаблонов длины m с
    расстоянием (Chebyshev) < r, A — то же для длины m+1. Самосравнения
    исключаются. Константный ряд имеет SampEn=0 по конвенции A=B. Если
    совпадений длины m+1 нет при B>0, возвращается ``inf``.

    Parameters
    ----------
    x : array-like
        Одномерный ряд.
    m : int, default 2
        Размерность вложения.
    r : float, optional
        Порог; по умолчанию 0.2 * std(x).

    Returns
    -------
    float
        SampEn. ``0.0`` для константного ряда; ``inf``, если B>0 и A=0.

    References
    ----------
    Richman & Moorman (2000), Am. J. Physiol. 278, H2039.
    """
    xa = _as_1d(x)
    n = xa.size
    if n == 0:
        raise ValueError("x must be non-empty")
    if not np.isfinite(xa).all():
        raise ValueError("x must contain at least one finite value")
    if isinstance(m, bool) or not isinstance(m, (int, np.integer)) or m < 1:
        raise ValueError(f"m must be a positive integer, got {m!r}")
    if n < m + 2:
        raise ValueError("ряд слишком короткий для SampEn")
    if r is None:
        r = 0.2 * float(np.std(xa))
    elif not np.isfinite(r):
        raise ValueError("r must be finite when provided")
    if float(np.std(xa)) == 0.0:
        return 0.0
    if r <= 0.0:
        return float("inf")

    def _templates(dim: int) -> np.ndarray:
        return np.lib.stride_tricks.sliding_window_view(xa, dim)

    tmpl_m = _templates(m)
    tmpl_m1 = _templates(m + 1)

    def _count(tmpl: np.ndarray) -> int:
        tree = cKDTree(tmpl)
        pairs = tree.query_pairs(r, p=np.inf, output_type="ndarray")
        return pairs.shape[0]

    b = _count(tmpl_m)
    a = _count(tmpl_m1)
    if b == 0:
        return float("inf")
    if a == 0:
        return float("inf")
    return float(-np.log(a / b))


def _coarse_grain(x: np.ndarray, s: int) -> np.ndarray:
    """Coarse-graining масштаба s: среднее внутри последовательных окон."""
    n = (x.size // s) * s
    if n == 0:
        return np.array([])
    return x[:n].reshape(-1, s).mean(axis=1)


def multiscale_entropy(
    x: np.ndarray,
    scales: Sequence[int] = tuple(range(1, 21)),
    m: int = 2,
    r: float | None = None,
) -> np.ndarray:
    """Multiscale entropy MSE(s) = SampEn(x_coarse(s), m, r).

    Parameters
    ----------
    x : array-like
        Одномерный ряд.
    scales : sequence of int, default range(1, 21)
        Масштабы s.
    m : int, default 2
        Размерность вложения.
    r : float, optional
        Порог; по умолчанию 0.2 * std каждого coarse-grained ряда.

    Returns
    -------
    np.ndarray
        Массив формы (len(scales),); NaN на масштабах, где ряд короток.

    References
    ----------
    Costa, Goldberger, Peng (2002), Phys. Rev. Lett. 89, 068102.
    """
    xa = _as_1d(x)
    out = np.full(len(scales), np.nan, dtype=np.float64)
    for i, s in enumerate(scales):
        if s < 1:
            continue
        coarse = _coarse_grain(xa, s)
        if coarse.size < m + 2:
            continue
        out[i] = sample_entropy(coarse, m=m, r=r)
    return out


def multiscale_entropy_matrix(
    wide: pd.DataFrame,
    scales: Sequence[int] = tuple(range(1, 21)),
    m: int = 2,
    r: float | None = None,
) -> pd.DataFrame:
    """MSE для каждого детектора.

    Returns
    -------
    pandas.DataFrame
        Форма (N_detectors, len(scales)); индекс — детекторы, колонки — s.
    """
    cols = list(wide.columns)
    mat = np.vstack([
        multiscale_entropy(wide[c].to_numpy(), scales=scales, m=m, r=r)
        for c in cols
    ])
    return pd.DataFrame(mat, index=cols, columns=list(scales))
