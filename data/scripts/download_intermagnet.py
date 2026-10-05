"""
Загрузка магнитометрических данных INTERMAGNET (формат IAGA-2002).
Требуется аккаунт и API-ключ, либо ручное скачивание с https://intermagnet.org.

Формат строки данных
====================
Поддерживаются две записи одной и той же строки данных IAGA-2002.

1. Каноническая (пробельная) запись — реальные файлы INTERMAGNET ``*.min``,
   спецификация: https://intermagnet.github.io/format/

       YYYY MM DD HH MM SS.MS IAF X Y Z IAGA_of_year Version
       2020 01 01 00 00 00.000  1 12345.6 -2345.6 5678.9 1 2020 4.1

   Дата-время занимает первые 6 токенов (``parts[0..5]``). Далее идёт
   флаг IAF (``parts[6]``, значение 1 или 2) — он опционален. Компоненты
   магнитного поля начинаются с ``parts[7]``: X, Y, Z. Компоненты H/D/F
   в канонической записи отсутствуют и заполняются ``NaN``.

2. Фиксированно-ширинная запись — ISO-дата в начале строки, далее
   компоненты поля по 10 символов, начиная с позиции 24:

       позиции  0-22  — timestamp (``YYYY-MM-DD HH:MM:SS.fff``)
       позиции 24-32  — компонент 1 (X или H)
       позиции 34-42  — компонент 2 (Y или D)
       позиции 44-52  — компонент 3 (Z)
       позиции 54-62  — компонент 4 (F)

       2023-01-01 00:00:00.000  20230.0   -1045.7   43400.0   43430.0

Правила разбора
===============
* Значения компонент НЕ разбираются через ``split()``: в фиксированно-
  ширинной записи они вырезаются по позициям, в канонической — по токенам.
  Двойные пробелы и отрицательные значения поэтому не ломают разбор.
* Время разбирается ``pd.to_datetime`` с явным списком форматов; строка с
  нечитаемым временем пропускается (``None``), а не роняет разбор файла.
* Маркер пропуска IAGA-2002 (``99999.99`` / ``99999.999`` и их отрицательные
  варианты) преобразуется в ``NaN``. Используется порог по модулю, потому
  что реальные значения магнитного поля не превышают ~65000 нТ.
* Строки-комментарии (первый непробельный символ ``#``) и пустые строки
  пропускаются.
* Строка, у которой ни одна компонента поля не читается как число,
  отбрасывается: она не должна порождать строку из одних ``NaN``.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "intermagnet"

#: Колонки результата парсинга.
OUTPUT_COLUMNS = ["timestamp", "X", "Y", "Z", "F"]

#: Ширина поля времени в фиксированно-ширинной записи (символы 0..22).
_TIME_WIDTH = 23

#: Начало блока компонент поля в фиксированно-ширинной записи.
_COMPONENT_OFFSET = 24

#: Ширина одного поля компоненты в фиксированно-ширинной записи.
_COMPONENT_WIDTH = 10

#: Число компонент поля в фиксированно-ширинной записи: X, Y, Z, F.
_N_COMPONENTS_FIXED = 4

#: Число компонент поля в канонической записи: X, Y, Z.
_N_COMPONENTS_SPACED = 3

#: Число токенов в дате-времени канонической записи: Y M D H M S.MS.
_N_TIME_TOKENS = 6

#: Минимальное число токенов в канонической записи: 6 + 3 компоненты.
_MIN_SPACED_TOKENS = _N_TIME_TOKENS + _N_COMPONENTS_SPACED

#: Допустимые значения флага IAF (индикатор формата) в канонической записи.
#: Поле IAF — целое 1 или 2; компоненты поля — дробные значения в нТ.
_IAF_VALUES = frozenset({1, 2})

#: Модуль значения, начиная с которого оно считается маркером пропуска.
#: IAGA-2002: 99999.99 / 99999.999.
_MISSING_ABS_THRESHOLD = 99999.0

#: Явные форматы времени для обеих записей.
_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y %m %d %H %M %S.%f",
    "%Y %m %d %H %M %S",
)


def _parse_timestamp(text: str) -> pd.Timestamp | None:
    """Разобрать строку времени по явным форматам.

    Parameters
    ----------
    text : str
        Временная строка.

    Returns
    -------
    pd.Timestamp | None
        Время в UTC (``tz="UTC"``) либо ``None``, если ни один явный
        формат не подошёл.
    """
    text = text.strip()
    if not text:
        return None
    for fmt in _TIME_FORMATS:
        try:
            return pd.to_datetime(text, format=fmt, utc=True)
        except (TypeError, ValueError):
            continue
    return None


def _parse_component(text: str) -> float | None:
    """Разобрать одно поле компоненты магнитного поля.

    Parameters
    ----------
    text : str
        Подстрока компоненты.

    Returns
    -------
    float | None
        ``NaN`` — поле пустое либо содержит маркер пропуска IAGA-2002;
        ``None`` — поле нечитаемо (не число и не пустое).
    """
    text = text.strip()
    if not text:
        return float("nan")
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if math.isfinite(value) and abs(value) >= _MISSING_ABS_THRESHOLD:
        return float("nan")
    return value


def _is_IAF(token: str) -> bool:
    """Проверить, что токен — флаг IAF, а не компонента поля.

    Флаг IAF — целое 1 или 2; значения компонент — дробные в нТ.
    """
    try:
        value = float(token)
    except (TypeError, ValueError):
        return False
    return value in _IAF_VALUES


def _parse_fixed_width(line: str) -> dict | None:
    """Разобрать фиксированно-ширинную запись: ISO-дата + 4 компоненты.

    Parameters
    ----------
    line : str
        Строка данных без символа конца строки.

    Returns
    -------
    dict | None
        Словарь с ключами ``timestamp``, ``X``, ``Y``, ``Z``, ``F``
        либо ``None``, если строка не разобралась.
    """
    ts = _parse_timestamp(line[:_TIME_WIDTH])
    if ts is None:
        return None

    values: list[float] = []
    for i in range(_N_COMPONENTS_FIXED):
        start = _COMPONENT_OFFSET + i * _COMPONENT_WIDTH
        parsed = _parse_component(line[start : start + _COMPONENT_WIDTH])
        if parsed is None:
            return None
        values.append(parsed)

    if not any(math.isfinite(v) for v in values):
        return None
    return {
        "timestamp": ts,
        "X": values[0],
        "Y": values[1],
        "Z": values[2],
        "F": values[3],
    }


def _parse_space_separated(line: str) -> dict | None:
    """Разобрать каноническую пробельную запись IAGA-2002.

    Layout: ``YYYY MM DD HH MM SS.MS [IAF] X Y Z [...]``.

    Parameters
    ----------
    line : str
        Строка данных без символа конца строки.

    Returns
    -------
    dict | None
        Словарь с ключами ``timestamp``, ``X``, ``Y``, ``Z``, ``F``
        (``F`` = ``NaN``: в канонической записи только три компоненты)
        либо ``None``, если строка не разобралась.
    """
    parts = line.split()
    if len(parts) < _MIN_SPACED_TOKENS:
        return None

    ts = _parse_timestamp(" ".join(parts[:_N_TIME_TOKENS]))
    if ts is None:
        return None

    idx = _N_TIME_TOKENS
    if idx < len(parts) and _is_IAF(parts[idx]):
        idx += 1

    if idx + _N_COMPONENTS_SPACED > len(parts):
        return None

    values: list[float] = []
    for token in parts[idx : idx + _N_COMPONENTS_SPACED]:
        parsed = _parse_component(token)
        if parsed is None:
            return None
        values.append(parsed)

    if not any(math.isfinite(v) for v in values):
        return None
    return {
        "timestamp": ts,
        "X": values[0],
        "Y": values[1],
        "Z": values[2],
        "F": float("nan"),
    }


def parse_iaga_line(line: str) -> dict | None:
    """Разобрать одну строку данных IAGA-2002.

    Поддерживаются фиксированно-ширинная и каноническая пробельная
    записи (см. модульный docstring).

    Parameters
    ----------
    line : str
        Строка файла, возможно с символом конца строки.

    Returns
    -------
    dict | None
        ``{"timestamp": pd.Timestamp (UTC), "X": float, "Y": float,
        "Z": float, "F": float}`` — маркер пропуска IAGA-2002 (``99999.99``)
        даёт ``NaN``. ``None`` — строка является комментарием, пуста,
        содержит нечитаемое время или нечитаемую компоненту. Исключения
        не бросаются никогда.
    """
    if not isinstance(line, str):
        return None
    text = line.rstrip("\r\n")
    if not text.strip():
        return None
    if text.lstrip().startswith("#"):
        return None
    return _parse_fixed_width(text) or _parse_space_separated(text)


def parse_iaga2002(path: Path) -> pd.DataFrame:
    """Парсит файл IAGA-2002 в DataFrame.

    Parameters
    ----------
    path : Path
        Путь к файлу ``*.min``.

    Returns
    -------
    pd.DataFrame
        Колонки ``timestamp`` (tz-aware UTC), ``X``, ``Y``, ``Z``, ``F``.
        Комментарии, пустые и нечитаемые строки пропускаются. Если читаемых
        строк нет, возвращается пустой DataFrame с теми же колонками.
    """
    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_iaga_line(line)
            if parsed is not None:
                rows.append(parsed)
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def download_and_save_intermagnet(station: str, year: int, month: int) -> Path:
    """Зарезервировать путь под данные INTERMAGNET (заглушка загрузки).

    INTERMAGNET требует ручной загрузки через веб-интерфейс
    (https://intermagnet.org), автоматического API нет. Функция **не**
    создаёт файл: прежняя версия делала ``out_path.touch()`` и создавала
    пустой ``.min``, который затем молча парсился в пустой DataFrame
    (находки A20 / V2-26). Возвращается целевой путь; файл должен быть
    положен туда вручную.

    Parameters
    ----------
    station : str
        Код станции IAGA.
    year, month : int
        Год и месяц.

    Returns
    -------
    Path
        Абсолютный путь ``RAW_DIR / f"{station}_{year}_{month:02d}.min"``.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{station}_{year}_{month:02d}.min"
    print(
        f"[MANUAL] Скачайте данные INTERMAGNET для {station} "
        f"{year}-{month:02d} и положите в {out_path}"
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Путь к .min файлу IAGA-2002")
    parser.add_argument(
        "--station",
        required=True,
        help="Код станции IAGA (например 'ABBR'). Обязателен: UNKNOWN "
        "по умолчанию приводил к безымянным детекторам (находка A21).",
    )
    args = parser.parse_args()

    src = Path(args.file)
    if not src.exists():
        raise SystemExit(f"Файл не найден: {src}")

    df = parse_iaga2002(src)
    if df.empty:
        raise SystemExit(
            f"В {src} нет читаемых строк IAGA-2002. Проверьте формат файла."
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"{args.station}_{src.stem}.csv"
    df.to_csv(out, index=False)
    print(f"[OK] {len(df)} строк -> {out}")


if __name__ == "__main__":
    main()
