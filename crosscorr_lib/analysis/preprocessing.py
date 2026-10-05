"""Предобработка временных рядов для кросс-корреляционного анализа.

Реализует Фикс 7 из аудита 24 сентября: единая функция ``preprocess``,
применяемая к каждой колонке wide-таблицы при ``apply_preprocessing=True``.

Слои обработки (P0-2)
---------------------
До P0-2 unified-таблица хранила в колонке ``residual`` сырое наблюдение,
и снятие тренда было единственным шагом очистки. Теперь ``residual``
содержит остаток после базовой физической модели
(:mod:`crosscorr_lib.analysis.residuals`):

1. ``fit_residual_model`` вычитает физическую модель детектора
   (MixedLM для ``ballistic``, OLS по Kp/Dst/F10.7 для остальных).
2. ``preprocess`` поверх этого снимает **приборный и сезонный дрейф**
   и приводит ряд к единой шкале перед вычислением корреляций.

Это разные операции: detrend в ``preprocess`` — это МНК-прямая по индексу
времени, а не вычитание физического вклада. Поэтому дефолты не менялись —
это ломало бы публичный API. Для остатков с тяжёлыми выбросами
рекомендуется ``robust=True``.
"""
from __future__ import annotations

import numpy as np


def preprocess(
    x: np.ndarray,
    detrend: bool = True,
    standardize: bool = True,
    robust: bool = False,
) -> np.ndarray:
    """Предобработка одномерного временного ряда.

    Parameters
    ----------
    x : array-like
        Входной ряд (приводится к 1D float64). Ожидается остаток после
        базовой модели (колонка ``residual`` unified-таблицы).
    detrend : bool, default True
        Удалять линейный тренд (МНК-прямая по индексу времени, без внешних
        зависимостей). Снимает приборный/сезонный дрейф, а не физический
        вклад: физическая модель уже вычтена в ``residual``.
    standardize : bool, default True
        Центрировать и масштабировать ряд.
    robust : bool, default False
        Если True — использовать медиану и MAD (устойчиво к выбросам)
        вместо среднего и СКО. Игнорируется при ``standardize=False``.

    Returns
    -------
    np.ndarray
        Обработанный ряд той же длины, dtype float64.
    """
    arr = np.asarray(x, dtype=np.float64).ravel()

    # --- NaN-интерполяция по индексу -------------------------------------
    finite_mask = np.isfinite(arr)
    if not finite_mask.all():
        if not finite_mask.any():
            return arr  # всё NaN — нечего интерполировать
        idx = np.arange(arr.size)
        arr = arr.copy()
        arr[~finite_mask] = np.interp(
            idx[~finite_mask], idx[finite_mask], arr[finite_mask]
        )

    # --- Детренд (МНК-прямая) --------------------------------------------
    if detrend and arr.size >= 2:
        t = np.arange(arr.size, dtype=np.float64)
        t_mean = t.mean()
        x_mean = arr.mean()
        denom = ((t - t_mean) ** 2).sum()
        if denom > 0.0:
            slope = ((t - t_mean) * (arr - x_mean)).sum() / denom
            arr = arr - (slope * (t - t_mean) + x_mean)

    # --- Стандартизация ---------------------------------------------------
    if standardize:
        if robust:
            center = float(np.median(arr))
            mad = float(np.median(np.abs(arr - center)))
            scale = 1.4826 * mad
        else:
            center = float(arr.mean())
            scale = float(arr.std())
        if scale > 0.0:
            arr = (arr - center) / scale
        else:
            arr = arr - center

    return arr
