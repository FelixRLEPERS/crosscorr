"""Transfer entropy between time series (directed, KSG estimator).

Классическая направленная информационная мера — аналог directed quantum
information flow (см. docs/methodology.md). В отличие от симметричной
корреляции, T(X→Y) != T(Y→X).

Определение (Schreiber, 2000):

    T(X→Y) = I(Y_{t+1} : X_t | Y_t)

эквивалентно H(Y_t | Y_{t-1}) - H(Y_t | Y_{t-1}, X_{t-1}).

Оценка — через условную взаимную информацию (KSG), см.
:func:`crosscorr_lib.analysis.mutual_info.conditional_mutual_information`.

References
----------
Schreiber (2000), Phys. Rev. Lett. 85, 461.
Frenzel & Pompe (2007), Phys. Rev. Lett. 99, 204101.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.mutual_info import (
    _as_1d,
    conditional_mutual_information,
)


def _validate_inputs(
    x: np.ndarray,
    y: np.ndarray,
    k: int,
    lag: int,
    k_nn: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate TE parameters and return finite, equal-length float arrays."""
    for name, value in (("k", k), ("lag", lag), ("k_nn", k_nn)):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise ValueError(f"{name} must be a positive integer, got {value!r}")
        if value < 1:
            raise ValueError(f"{name} must be >= 1, got {value}")

    xa_raw = np.asarray(x).ravel()
    ya_raw = np.asarray(y).ravel()
    if xa_raw.size == 0 or ya_raw.size == 0:
        raise ValueError("x and y must be non-empty")
    if xa_raw.size != ya_raw.size:
        raise ValueError(
            f"x and y must have equal lengths, got {xa_raw.size} and {ya_raw.size}"
        )

    # Reuse the MI module's NaN interpolation policy, then reject all-NaN/inf.
    xa = _as_1d(xa_raw)
    ya = _as_1d(ya_raw)
    if not np.isfinite(xa).all() or not np.isfinite(ya).all():
        raise ValueError("x and y must contain at least one finite value each")
    return xa, ya


def _embed_history(x: np.ndarray, k: int, lag: int) -> np.ndarray:
    """Матрица истории (n_eff x k): столбцы x[t-lag], x[t-2*lag], ..."""
    x = np.asarray(x, dtype=np.float64).ravel()
    span = k * lag
    n_eff = x.size - span
    if n_eff <= 0:
        raise ValueError("ряд слишком короткий для заданных k и lag")
    cols = [x[span - (j + 1) * lag: span - (j + 1) * lag + n_eff]
            for j in range(k)]
    return np.column_stack(cols) if k > 1 else cols[0][:, None]


def transfer_entropy(
    x: np.ndarray,
    y: np.ndarray,
    k: int = 1,
    lag: int = 1,
    k_nn: int = 5,
) -> float:
    """Оценка transfer entropy T(X→Y) методом KSG.

    T(X→Y) = I(Y_{t+1} : X_t | Y_t), где истории берутся с шагом ``lag``
    и длиной ``k``.

    Parameters
    ----------
    x, y : array-like
        Одномерные ряды равной длины.
    k : int, default 1
        Длина истории. Сейчас реализовано только ``k=1``; для k>1
        совместный joint-history estimator пока не реализован.
    lag : int, default 1
        Шаг истории.
    k_nn : int, default 5
        Число соседей для KSG.

    Returns
    -------
    float
        T(X→Y) в натах. Как правило T(X→Y) != T(Y→X).

    References
    ----------
    Schreiber (2000), Phys. Rev. Lett. 85, 461.
    """
    xa, ya = _validate_inputs(x, y, k, lag, k_nn)
    if k > 1:
        raise NotImplementedError(
            "joint-history transfer entropy for k>1 is not implemented; "
            "use k=1"
        )
    n = xa.size

    span = k * lag
    if n - span < k_nn + 2:
        raise ValueError("ряд слишком короткий для TE-оценки")

    hist_x = _embed_history(xa, k, lag)     # x_t (история)
    hist_y = _embed_history(ya, k, lag)     # y_t (история)
    y_next = ya[span:]                      # y_{t+1}

    # Совместить по длине.
    m = min(hist_x.shape[0], hist_y.shape[0], y_next.size)
    hist_x = hist_x[:m]
    hist_y = hist_y[:m]
    y_next = y_next[:m]

    # For k=1 this is the Schreiber definition T(X->Y)=I(Y[t+lag]:X[t]|Y[t]).
    return conditional_mutual_information(
        y_next, hist_x[:, 0], hist_y[:, 0], k=k_nn
    )


def transfer_entropy_matrix(
    wide: pd.DataFrame,
    k: int = 1,
    lag: int = 1,
    k_nn: int = 5,
) -> pd.DataFrame:
    """Асимметричная матрица TE между всеми детекторами.

    Позиция [i, j] — T(detector_i -> detector_j).

    Returns
    -------
    pandas.DataFrame
        Матрица (N x N), асимметричная, диагональ = 0.
    """
    cols = list(wide.columns)
    ncol = len(cols)
    mat = np.zeros((ncol, ncol), dtype=np.float64)
    for i in range(ncol):
        for j in range(ncol):
            if i == j:
                continue
            mat[i, j] = transfer_entropy(
                wide[cols[i]].to_numpy(),
                wide[cols[j]].to_numpy(),
                k=k, lag=lag, k_nn=k_nn,
            )
    return pd.DataFrame(mat, index=cols, columns=cols)
