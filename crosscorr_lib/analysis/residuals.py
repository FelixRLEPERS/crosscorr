"""Остатки базовой физической модели для каждого типа детектора.

Зачем этот модуль
-----------------
До P0-2 унифицированная таблица (``data/scripts/unify_schema.py``) писала
сырое наблюдение в колонку ``residual``, смешивая физически несопоставимые
величины: SNR в дБ (WSPR), X-компонента магнитного поля в нТ (INTERMAGNET)
и гелиоцентрическое расстояние в а.е. (JPL Horizons). Аналитические модули
группируют строки по ``detector_id``, поэтому смешение не попадало в одну
колонку wide-таблицы, но имя колонки противоречило объявленной методологии
(``README.md``: «остаток после базовой модели MixedLM») и схеме
``data/schema/unified_schema.json``.

Модуль разделяет два понятия:

``value``
    Сырое наблюдение как измерено. Единица зависит от ``detector_type``.
``residual``
    Наблюдение минус предсказание базовой модели, подобранной для данного
    типа детектора. Именно ``residual`` потребляют ``cross_correlation``,
    ``mfdfa``, ``stationarity`` и ``surrogate``.

Базовые модели
--------------
* ``ballistic`` — MixedLM (statsmodels) по формуле
  ``value ~ charge_temp + mass + (1|range_id)``. Это та же формула, что
  обещана в ``README.md``: ``v0 ~ T_заряда + масса + (1|полигон)``.
* любой другой тип детектора — OLS ``value ~ kp + dst + f107``, если
  вызывающая сторона передала DataFrame с конфаундерами (столбец
  ``timestamp_utc``).
* конфаундеры не переданы — модель **не оценивается**: ``residual_method``
  становится ``"none"``, а ``residual`` равно ``value``. Помечать остаток
  как очищенный от физической модели, не оценив эту модель, было бы
  вводящим в заблуждение, поэтому факт фиксируется явно.

Имена колонок формулы MixedLM
-----------------------------
``README.md`` записывает баллистическую формулу в русской нотации
(``v0 ~ T_заряда + масса + (1|полигон)``). Ни одна колонка с такими именами
не существует в репозитории, поэтому латинские имена зафиксированы ниже как
константы модуля. Это задокументированный контракт входных данных баллистической
ветви; имена нужно переименовать вместе с появлением реального загрузчика
Ammolytics.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

#: Зависимая переменная и предикторы баллистической MixedLM.
BALLISTIC_VALUE_COL = "value"
BALLISTIC_TEMP_COL = "charge_temp"
BALLISTIC_MASS_COL = "mass"
BALLISTIC_GROUP_COL = "range_id"

#: Формула баллистической базовой модели.
BALLISTIC_FORMULA = (
    f"{BALLISTIC_VALUE_COL} ~ {BALLISTIC_TEMP_COL} + "
    f"{BALLISTIC_MASS_COL} + (1|{BALLISTIC_GROUP_COL})"
)

#: Колонки, необходимые баллистической ветви.
BALLISTIC_COLUMNS: tuple[str, ...] = (
    BALLISTIC_VALUE_COL,
    BALLISTIC_TEMP_COL,
    BALLISTIC_MASS_COL,
    BALLISTIC_GROUP_COL,
)

#: Колонки-конфаундеры OLS-ветви.
CONFOUNDER_COLUMNS: tuple[str, ...] = ("kp", "dst", "f107")

#: Колонка времени во входном DataFrame и в конфаундерах.
TIMESTAMP_COLUMN = "timestamp_utc"

#: Колонка сырого наблюдения.
VALUE_COLUMN = "value"

#: Колонка остатка.
RESIDUAL_COLUMN = "residual"

#: Колонка с названием применённой базовой модели.
METHOD_COLUMN = "residual_method"

#: Значения ``residual_method``.
METHOD_MIXEDLM = "mixedlm_ballistic"
METHOD_OLS = "ols_geomagnetic"
METHOD_NONE = "none"

#: Допустимые значения ``residual_method`` (соответствуют enum схемы).
RESIDUAL_METHODS: tuple[str, ...] = (METHOD_MIXEDLM, METHOD_OLS, METHOD_NONE)

#: Единица измерения ``value`` по типу детектора.
DETECTOR_UNITS: dict[str, str] = {
    "wspr": "dB",
    "magnetometer": "nT",
    "ephemeris": "AU",
    "ballistic": "s",
    "gnss": "mm",
    "ionosonde": "m",
    "metrology": "s",
    "genome": "count",
}

#: Единица для типа детектора, отсутствующего в :data:`DETECTOR_UNITS`.
DEFAULT_UNIT = "unknown"

#: Значения ``quality_flag``.
QUALITY_OK = 0
QUALITY_MISSING = 1

#: Минимальное число наблюдений для OLS-ветви: число параметров + 2.
_MIN_OLS_OBS = len(CONFOUNDER_COLUMNS) + 2

#: Минимальное число групп для MixedLM.
_MIN_MIXEDLM_GROUPS = 2

#: Минимальное число наблюдений на группу для MixedLM.
_MIN_MIXEDLM_PER_GROUP = 5


def detector_unit(detector_type: str) -> str:
    """Единица измерения сырого наблюдения для типа детектора.

    Parameters
    ----------
    detector_type : str
        Тип детектора из enum ``unified_schema.json``.

    Returns
    -------
    str
        Единица измерения (например ``"nT"``) либо :data:`DEFAULT_UNIT`.
    """
    return DETECTOR_UNITS.get(str(detector_type), DEFAULT_UNIT)


def quality_flags(values: pd.Series) -> pd.Series:
    """Вычислить ``quality_flag`` по наличию наблюдения.

    Parameters
    ----------
    values : pd.Series
        Сырые наблюдения.

    Returns
    -------
    pd.Series
        :data:`QUALITY_MISSING` там, где значение отсутствует (NaN),
        иначе :data:`QUALITY_OK`. dtype — ``int64``.
    """
    as_float = pd.to_numeric(values, errors="coerce")
    flags = np.where(as_float.isna().to_numpy(), QUALITY_MISSING, QUALITY_OK)
    return pd.Series(flags, index=values.index, dtype="int64")


def _failed(df: pd.DataFrame, method: str, reason: str) -> pd.DataFrame:
    """Вернуть копию ``df`` с пометкой неудачной модели.

    ``residual`` целиком ``NaN``, ``residual_method`` — имя метода,
    ``quality_flag`` — :data:`QUALITY_MISSING`. Причина логируется
    предупреждением.
    """
    warnings.warn(
        f"[residuals] Модель '{method}' не применена: {reason}. "
        "residual = NaN, quality_flag = 1.",
        UserWarning,
        stacklevel=3,
    )
    out = df.copy()
    out[RESIDUAL_COLUMN] = np.nan
    out[METHOD_COLUMN] = method
    out["quality_flag"] = QUALITY_MISSING
    return out


def _identity(df: pd.DataFrame) -> pd.DataFrame:
    """Оставить ``residual == value`` без оценки модели (метод ``none``)."""
    out = df.copy()
    out[VALUE_COLUMN] = pd.to_numeric(out[VALUE_COLUMN], errors="coerce")
    out[RESIDUAL_COLUMN] = out[VALUE_COLUMN]
    out[METHOD_COLUMN] = METHOD_NONE
    out["quality_flag"] = quality_flags(out[VALUE_COLUMN])
    return out


def _align_confounders(
    df: pd.DataFrame,
    confounders: pd.DataFrame,
) -> pd.DataFrame:
    """Привести конфаундеры к временной сетке ``df``.

    Полная копия ``confounders.remove_confounders._align_confounders``:
    прямое пересечение индексов заменено ресемплингом ``ffill`` по метке
    времени строки, затем линейная интерполяция по краям.

    Parameters
    ----------
    df : pd.DataFrame
        Таблица с колонкой ``timestamp_utc``.
    confounders : pd.DataFrame
        Таблица с колонками ``timestamp_utc`` и подмножеством ``kp``/``dst``/``f107``.

    Returns
    -------
    pd.DataFrame
        Конфаундеры с DatetimeIndex, совпадающим с порядком строк ``df``.
    """
    conf = confounders.copy()
    times = pd.to_datetime(conf[TIMESTAMP_COLUMN], utc=True, errors="coerce")
    conf = conf.assign(**{TIMESTAMP_COLUMN: times})
    conf = conf.dropna(subset=[TIMESTAMP_COLUMN])
    conf = conf.set_index(TIMESTAMP_COLUMN).sort_index()

    row_times = pd.to_datetime(df[TIMESTAMP_COLUMN], utc=True, errors="coerce")
    aligned = conf.reindex(pd.DatetimeIndex(row_times), method="ffill")
    return aligned.interpolate(method="linear", limit_direction="both")


def _fit_ols(df: pd.DataFrame, confounders: pd.DataFrame | None) -> pd.DataFrame:
    """ОLS-оценка ``value ~ kp + dst + f107``.

    Модель та же, что в ``confounders.remove_confounders``: МНК через
    псевдообратную матрицу, устойчивую к мультиколлинеарности Kp и Dst.

    Parameters
    ----------
    df : pd.DataFrame
        Таблица с колонками ``value`` и ``timestamp_utc``.
    confounders : pd.DataFrame | None
        Конфаундеры. ``None`` означает, что модель не оценивается.

    Returns
    -------
    pd.DataFrame
        Копия ``df`` с колонками ``residual``, ``residual_method``, ``quality_flag``.

    Raises
    ------
    ValueError
        Если в ``confounders`` нет ни одного из ``kp``/``dst``/``f107``
        или отсутствует колонка ``timestamp_utc``.
    """
    if confounders is None:
        return _identity(df)

    if TIMESTAMP_COLUMN not in confounders.columns:
        raise ValueError(
            f"В конфаундерах нет колонки {TIMESTAMP_COLUMN!r}; "
            "ожидаются timestamp_utc, kp, dst, f107"
        )

    columns = [c for c in CONFOUNDER_COLUMNS if c in confounders.columns]
    if not columns:
        raise ValueError(
            "Нет доступных конфаундеров для удаления: ожидались хотя бы "
            f"одна из {list(CONFOUNDER_COLUMNS)}"
        )

    conf = _align_confounders(df, confounders)

    value = pd.to_numeric(df[VALUE_COLUMN], errors="coerce").to_numpy(dtype=float)
    conf_values = conf[columns].to_numpy(dtype=float)

    # Строка годна к оценке, если все используемые конфаундеры и сам
    # ряд конечны в этой точке.
    usable = np.isfinite(value)
    for k in range(len(columns)):
        usable &= np.isfinite(conf_values[:, k])

    if int(usable.sum()) < _MIN_OLS_OBS:
        return _identity(df)

    design = conf_values[usable]
    design = np.column_stack([np.ones(len(design)), design])
    target = value[usable]

    try:
        beta, *_ = np.linalg.lstsq(design, target, rcond=None)
    except np.linalg.LinAlgError as exc:
        return _failed(df, METHOD_OLS, f"МНК не сошёлся: {exc!r}")

    residuals = np.full(len(df), np.nan, dtype=float)
    residuals[usable] = target - design @ beta

    out = df.copy()
    out[VALUE_COLUMN] = value
    out[RESIDUAL_COLUMN] = residuals
    out[METHOD_COLUMN] = METHOD_OLS
    out["quality_flag"] = quality_flags(pd.Series(value, index=df.index))
    # Строки, не попавшие в оценку, не несут остатка.
    out.loc[~usable, "quality_flag"] = QUALITY_MISSING
    return out


def _fit_mixedlm(df: pd.DataFrame) -> pd.DataFrame:
    """MixedLM-оценка ``value ~ charge_temp + mass + (1|range_id)``.

    Ленивый импорт ``statsmodels`` внутри функции: модуль должен
    импортироваться smoke-тестом без тяжёлых зависимостей.

    Parameters
    ----------
    df : pd.DataFrame
        Таблица с колонками :data:`BALLISTIC_COLUMNS`.

    Returns
    -------
    pd.DataFrame
        Копия ``df`` с колонками ``residual``, ``residual_method``, ``quality_flag``.
        При любой ошибке оценки — ``residual = NaN``,
        ``residual_method = "mixedlm_ballistic"``, ``quality_flag = 1``.
    """
    try:
        from statsmodels.regression.mixed_linear_model import MixedLM
    except ImportError as exc:  # pragma: no cover - зависимость объявлена в pyproject
        return _failed(df, METHOD_MIXEDLM, f"statsmodels недоступен: {exc!r}")

    work = df.copy()
    for column in BALLISTIC_COLUMNS:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    complete = work[list(BALLISTIC_COLUMNS)].notna().all(axis=1)
    if int(complete.sum()) < _MIN_MIXEDLM_GROUPS * _MIN_MIXEDLM_PER_GROUP:
        return _failed(
            df, METHOD_MIXEDLM,
            f"недостаточно полных строк ({int(complete.sum())})",
        )

    usable = work.loc[complete]
    n_groups = usable[BALLISTIC_GROUP_COL].nunique()
    if n_groups < _MIN_MIXEDLM_GROUPS:
        return _failed(df, METHOD_MIXEDLM, f"групп полигонов меньше {_MIN_MIXEDLM_GROUPS}")

    try:
        model = MixedLM.from_formula(
            BALLISTIC_FORMULA,
            data=usable,
            groups=usable[BALLISTIC_GROUP_COL],
        )
        fitted = model.fit()
    except Exception as exc:  # noqa: BLE001 - statsmodels бросает разнородные исключения
        return _failed(df, METHOD_MIXEDLM, f"подгонка не удалась: {exc!r}")

    out = df.copy()
    for column in BALLISTIC_COLUMNS:
        out[column] = work[column]
    out[RESIDUAL_COLUMN] = np.nan
    out[METHOD_COLUMN] = METHOD_MIXEDLM

    flags = quality_flags(work[BALLISTIC_VALUE_COL])

    try:
        predicted = fitted.predict(usable)
        out.loc[complete, RESIDUAL_COLUMN] = (
            usable[BALLISTIC_VALUE_COL].to_numpy(dtype=float)
            - np.asarray(predicted, dtype=float)
        )
    except Exception as exc:  # noqa: BLE001 - предсказание тоже может упасть
        return _failed(df, METHOD_MIXEDLM, f"предсказание не удалось: {exc!r}")

    out["quality_flag"] = flags.astype("int64")
    out.loc[~complete, "quality_flag"] = QUALITY_MISSING
    return out


def fit_residual_model(
    df: pd.DataFrame,
    detector_type: str,
    confounders: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Посчитать остаток базовой модели для типа детектора.

    Возвращается **новая** таблица; входная ``df`` не изменяется. Набор
    колонок, добавленных в результат: ``value`` (float64), ``residual``
    (float64), ``residual_method`` (:data:`RESIDUAL_METHODS`) и
    ``quality_flag`` (:data:`QUALITY_OK` / :data:`QUALITY_MISSING`).
    Колонка ``unit`` в результат не добавляется — она ставится загрузчиком
    через :func:`detector_unit`.

    Parameters
    ----------
    df : pd.DataFrame
        Таблица с колонками ``value`` и ``timestamp_utc``. Для
        ``detector_type == "ballistic"`` дополнительно нужны колонки
        :data:`BALLISTIC_COLUMNS`.
    detector_type : str
        Тип детектора из enum ``unified_schema.json``.
    confounders : pd.DataFrame | None, default None
        Конфаундеры с колонками ``timestamp_utc``, ``kp``, ``dst``,
        ``f107``. Используются только в OLS-ветви. ``None`` означает:
        базовая модель не оценивается, ``residual_method == "none"`` и
        ``residual == value``.

    Returns
    -------
    pd.DataFrame
        Копия ``df`` с добавленными ``residual``, ``residual_method``,
        ``quality_flag``.

    Raises
    ------
    ValueError
        Если нет колонки ``value`` или ``timestamp_utc``, а для баллистики
        — ещё и колонок :data:`BALLISTIC_COLUMNS`.

    Warns
    -----
    UserWarning
        Если базовая модель не удалась: ``residual`` становится ``NaN``,
        ``quality_flag`` — :data:`QUALITY_MISSING`.
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"Ожидался pd.DataFrame, получен {type(df).__name__}")

    missing = [c for c in (VALUE_COLUMN, TIMESTAMP_COLUMN) if c not in df.columns]
    if missing:
        raise ValueError(
            f"В таблице нет обязательных колонок {missing}; "
            f"ожидаются {VALUE_COLUMN} и {TIMESTAMP_COLUMN}"
        )

    if str(detector_type) == "ballistic":
        missing_b = [c for c in BALLISTIC_COLUMNS if c not in df.columns]
        if missing_b:
            raise ValueError(
                f"Для ballistic нет колонок {missing_b}; формула "
                f"{BALLISTIC_FORMULA!r} требует {list(BALLISTIC_COLUMNS)}"
            )
        return _fit_mixedlm(df)

    return _fit_ols(df, confounders)


def describe_schema() -> dict[str, Any]:
    """Сводка по новой схеме unified-таблицы (для документации и CLI).

    Returns
    -------
    dict
        Ключи ``value_column``, ``residual_column``, ``methods``,
        ``units``, ``quality_flags``.
    """
    return {
        "value_column": VALUE_COLUMN,
        "residual_column": RESIDUAL_COLUMN,
        "methods": list(RESIDUAL_METHODS),
        "units": dict(DETECTOR_UNITS),
        "quality_flags": {str(QUALITY_OK): "ok", str(QUALITY_MISSING): "missing"},
    }
