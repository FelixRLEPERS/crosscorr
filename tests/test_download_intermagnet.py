"""Тесты парсера IAGA-2002 (аудит v2, P0-1 / находка V2-13).

Закрывает дефект: старый ``parse_iaga2002`` брал год и месяц как
дату-время (``parts[0], parts[1]``) и значения из ``parts[3..5]``,
из-за чего не мог обработать ни одной реальной строки ``*.min``.

Проверяются обе поддерживаемые записи строки данных:
фиксированно-ширинная (ISO-дата + компоненты по 10 символов) и
каноническая пробельная (``YYYY MM DD HH MM SS.MS [IAF] X Y Z``).
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from data.scripts.download_intermagnet import (
    OUTPUT_COLUMNS,
    parse_iaga2002,
    parse_iaga_line,
)

# Фиксированно-ширинная запись: позиции 0-22 время, далее 10 символов
# на компоненту начиная с позиции 24.
FIXED_VALID = (
    "2023-01-01 00:00:00.000  20230.0   -1045.7   43400.0   43430.0"
)
FIXED_NAN_99 = (
    "2023-01-01 00:00:00.000  99999.99   -1045.7   43400.0   43430.0"
)
FIXED_NAN_999 = (
    "2023-01-01 00:00:00.000  99999.999  -1045.7   43400.0   43430.0"
)
FIXED_NAN_NEG = (
    "2023-01-01 00:00:00.000  -99999.99  -1045.7   43400.0   43430.0"
)

# Каноническая пробельная запись реальных файлов INTERMAGNET.
SPACED_WITH_IAF = "2020 01 01 00 00 00.000  1 12345.6 -2345.6 5678.9 1 2020 4.1"
SPACED_NO_IAF = "2020 01 01 00 00 00.000 12345.6 -2345.6 5678.9"
SPACED_NAN = "2020 01 01 00 00 00.000  1 99999.99 -2345.6 5678.9"


# ---------------------------------------------------------------------------
# Фиксированно-ширинная запись
# ---------------------------------------------------------------------------
def test_parse_iaga_line_valid():
    """Валидная строка IAGA-2002 парсится в (timestamp, X, Y, Z, F)."""
    result = parse_iaga_line(FIXED_VALID)

    assert result is not None
    assert result["X"] == pytest.approx(20230.0)
    assert result["Y"] == pytest.approx(-1045.7)
    assert result["Z"] == pytest.approx(43400.0)
    assert result["F"] == pytest.approx(43430.0)
    assert str(result["timestamp"]) == "2023-01-01 00:00:00+00:00"
    assert result["timestamp"].tzinfo is not None


def test_parse_iaga_line_nan_marker():
    """99999.99 и 99999.999 → NaN (маркер пропуска IAGA-2002)."""
    for line in (FIXED_NAN_99, FIXED_NAN_999):
        result = parse_iaga_line(line)
        assert result is not None, line
        assert math.isnan(result["X"]), line
        # остальные компоненты читаются штатно
        assert result["Y"] == pytest.approx(-1045.7), line
        assert result["Z"] == pytest.approx(43400.0), line


def test_parse_iaga_line_nan_marker_negative():
    """Отрицательный маркер пропуска -99999.99 → NaN."""
    result = parse_iaga_line(FIXED_NAN_NEG)

    assert result is not None
    assert math.isnan(result["X"])


def test_parse_iaga_line_invalid_time():
    """Невалидное время → None, без исключения."""
    result = parse_iaga_line(
        "2023-13-45 99:99:99.999  20230.0   -1045.7   43400.0   43430.0"
    )

    assert result is None


def test_parse_iaga_line_comment():
    """Строка с '#' → None."""
    assert parse_iaga_line("#YEAR MONTH DAY HOUR MIN SEC.MS") is None
    assert parse_iaga_line("   # indented comment") is None


def test_parse_iaga_line_blank_and_non_string():
    """Пустые строки и не-строки → None, без исключения."""
    assert parse_iaga_line("") is None
    assert parse_iaga_line("   \n") is None
    assert parse_iaga_line("\n") is None
    assert parse_iaga_line(None) is None  # type: ignore[arg-type]


def test_parse_iaga_line_non_numeric_component():
    """Нечитаемая компонента → None, а не частичная строка."""
    result = parse_iaga_line(
        "2023-01-01 00:00:00.000  ABCDEFGHIJ   -1045.7   43400.0   43430.0"
    )

    assert result is None


def test_parse_iaga_line_all_missing_rejected():
    """Строка, где все компоненты — маркеры пропуска, отбрасывается."""
    result = parse_iaga_line(
        "2023-01-01 00:00:00.000  99999.99   99999.99   99999.99   99999.99"
    )

    assert result is None


def test_parse_iaga_line_truncated_components():
    """Обрезанная строка: прочитанные компоненты есть, остальные NaN."""
    result = parse_iaga_line("2023-01-01 00:00:00.000  20230.0")

    assert result is not None
    assert result["X"] == pytest.approx(20230.0)
    assert math.isnan(result["Y"])
    assert math.isnan(result["Z"])
    assert math.isnan(result["F"])


def test_parse_iaga_line_tolerates_newline_and_trailing_spaces():
    """Символ конца строки и хвостовые пробелы не ломают разбор."""
    stripped = parse_iaga_line(FIXED_VALID)
    with_eol = parse_iaga_line(FIXED_VALID + "\n")
    padded = parse_iaga_line(FIXED_VALID + "   \r\n")

    for result in (with_eol, padded):
        assert result is not None
        assert result["X"] == pytest.approx(stripped["X"])
        assert result["F"] == pytest.approx(stripped["F"])


# ---------------------------------------------------------------------------
# Каноническая пробельная запись
# ---------------------------------------------------------------------------
def test_parse_iaga_line_spaced_with_IAF():
    """Каноническая строка с флагом IAF: X/Y/Z с позиций 7/8/9."""
    result = parse_iaga_line(SPACED_WITH_IAF)

    assert result is not None
    assert result["X"] == pytest.approx(12345.6)
    assert result["Y"] == pytest.approx(-2345.6)
    assert result["Z"] == pytest.approx(5678.9)
    # H/D/F в канонической записи отсутствуют
    assert math.isnan(result["F"])
    assert str(result["timestamp"]) == "2020-01-01 00:00:00+00:00"


def test_parse_iaga_line_spaced_without_IAF():
    """Каноническая строка без флага IAF: X/Y/Z с позиций 6/7/8."""
    result = parse_iaga_line(SPACED_NO_IAF)

    assert result is not None
    assert result["X"] == pytest.approx(12345.6)
    assert result["Y"] == pytest.approx(-2345.6)
    assert result["Z"] == pytest.approx(5678.9)


def test_parse_iaga_line_spaced_nan_marker():
    """Маркер пропуска 99999.99 в канонической записи → NaN."""
    result = parse_iaga_line(SPACED_NAN)

    assert result is not None
    assert math.isnan(result["X"])
    assert result["Y"] == pytest.approx(-2345.6)
    assert result["Z"] == pytest.approx(5678.9)


def test_parse_iaga_line_spaced_invalid_time():
    """Невалидное время в канонической записи → None, без исключения."""
    result = parse_iaga_line("2020 13 45 00 00 00.000  1 1.0 2.0 3.0")

    assert result is None


def test_parse_iaga_line_spaced_too_short():
    """Каноническая строка с недостатком компонент → None."""
    assert parse_iaga_line("2020 01 01 00 00 00.000  1 1.0 2.0") is None


# ---------------------------------------------------------------------------
# Разбор файла целиком
# ---------------------------------------------------------------------------
def test_parse_iaga2002_file(tmp_path: Path):
    """Файл целиком: комментарии и битые строки пропускаются."""
    src = tmp_path / "ABBR_2020_01.min"
    src.write_text(
        "# INTERMAGNET 1 test data\n"
        "#YEAR MONTH DAY HOUR MIN SEC.MS IAF IAGA_of_year Version\n"
        f"{SPACED_WITH_IAF}\n"
        f"{FIXED_VALID}\n"
        f"{SPACED_NAN}\n"
        "\n"
        "broken line here\n",
        encoding="utf-8",
    )

    df = parse_iaga2002(src)

    assert list(df.columns) == OUTPUT_COLUMNS
    assert len(df) == 3
    assert df["X"].iloc[0] == pytest.approx(12345.6)
    assert df["X"].iloc[1] == pytest.approx(20230.0)
    assert math.isnan(df["X"].iloc[2])
    assert str(df["timestamp"].iloc[0]) == "2020-01-01 00:00:00+00:00"
    assert str(df["timestamp"].iloc[1]) == "2023-01-01 00:00:00+00:00"
    # таймзона обязательна: unify_schema делает pd.to_datetime(..., utc=True)
    assert df["timestamp"].dt.tz is not None


def test_parse_iaga2002_empty_file(tmp_path: Path):
    """Файл без читаемых строк → пустой DataFrame с ожидаемыми колонками."""
    src = tmp_path / "empty.min"
    src.write_text("# only a comment\n\n", encoding="utf-8")

    df = parse_iaga2002(src)

    assert df.empty
    assert list(df.columns) == OUTPUT_COLUMNS


def test_parse_iaga2002_handles_real_rows_only(tmp_path: Path):
    """Регрессия V2-13: ни одна реальная строка не должна теряться."""
    src = tmp_path / "ABBR_2020_01.min"
    src.write_text(
        "\n".join(
            f"2020 01 01 0{h} 00 00.000  1 12345.6 -2345.6 5678.9 1 2020 4.1"
            for h in range(3)
        )
        + "\n",
        encoding="utf-8",
    )

    df = parse_iaga2002(src)

    assert len(df) == 3
    assert df["timestamp"].is_monotonic_increasing
    assert df["Z"].notna().all()
