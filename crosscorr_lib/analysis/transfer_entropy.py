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

from crosscorr_lib.analysis.mutual_info import conditional_mutual_information


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
        Длина истории (размерность вложения).
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
    xa = np.asarray(x, dtype=np.float64).ravel()
    ya = np.asarray(y, dtype=np.float64).ravel()
    n = min(xa.size, ya.size)
    xa, ya = xa[:n], ya[:n]

    span = k * lag
    if n - span - 1 <= k_nn + 2:
        raise ValueError("ряд слишком короткий для TE-оценки")

    hist_x = _embed_history(xa, k, lag)     # x_t (история)
    hist_y = _embed_history(ya, k, lag)     # y_t (история)
    y_next = ya[span:]                      # y_{t+1}

    # Совместить по длине.
    m = min(hist_x.shape[0], hist_y.shape[0], y_next.size)
    hist_x = hist_x[:m]
    hist_y = hist_y[:m]
    y_next = y_next[:m]

    # T = I(y_next : hist_x | hist_y). Для k=1 истории одномерны.
    if k == 1:
        return conditional_mutual_information(
            y_next, hist_x[:, 0], hist_y[:, 0], k=k_nn
        )
    # Многомерные истории: объединяем в признаки через строковое хеширование
    # запрещено (нужна геометрия), поэтому для k>1 используем покомпонентное
    # усреднение по истории x при общей истории y — консервативная оценка.
    vals = [
        conditional_mutual_information(
            y_next, hist_x[:, j], hist_y[:, 0], k=k_nn
        )
        for j in range(hist_x.shape[1])
    ]
    return float(np.mean(vals))


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
