"""
Загрузка данных WSPR через публичный API wsprnet.org (или WSPR Live).
Сохраняет сырой CSV в data/raw/wspr/wspr_<date>_<band>.csv.

Примечание: WSPR-API нестабилен, лимиты и форматы меняются.
Скрипт — заготовка: подставьте актуальный эндпоинт.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import time
from pathlib import Path

import pandas as pd
import requests


def _write_checksum(path: Path) -> Path:
    """Записать sha256 файла в сайдкар ``<path>.sha256``.

    Позволяет позже проверить, что сырой файл не изменился между прогонами
    (находка A8 / V2-35).
    """
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return sidecar

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "wspr"

# ВНИМАНИЕ: WSPR API крайне нестабилен. Используем декоратор для повторных попыток.
WSPR_API = "https://db1.wsprnet.org/drupal/wsprnet/spotquery"

MAX_RETRIES = 3 # Максимальное количество попыток запроса
INITIAL_BACKOFF = 5 # Начальная задержка в секундах


def fetch_wspr(date: dt.date, band: str = "20m", limit: int = 5000) -> pd.DataFrame:
    """Скачивает споты WSPR за указанную дату с retry-логикой.

    ВНИМАНИЕ: ``limit`` ограничивает число строк ответа. WSPRnet отдаёт
    споты в порядке времени, поэтому ``limit=5000`` детерминированно
    отрезает конец суток, а не случайную выборку (находка A26 / V2-32).
    Для полных суток увеличивайте ``limit`` или разбивайте запрос по часам.
    """
    params = {
        "start": date.isoformat(),
        "end": date.isoformat(),
        "band": band,
        "limit": limit,
        "format": "csv",
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(WSPR_API, params=params, timeout=60)
            resp.raise_for_status()
            from io import StringIO
            df = pd.read_csv(StringIO(resp.text))
            return df
        except requests.RequestException as e:
            last_error = e
            backoff = INITIAL_BACKOFF * (2 ** attempt)
            if attempt < MAX_RETRIES - 1:
                print(f"[RETRY] Попытка {attempt + 1}/{MAX_RETRIES} "
                      f"не удалась: {e}. Ждём {backoff} сек...")
                time.sleep(backoff)

    raise RuntimeError(
        f"WSPR API не ответил за {MAX_RETRIES} попыток. "
        f"Последняя ошибка: {last_error}"
    )


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит к минимально нужному набору колонок."""
    expected = ["timestamp", "tx_call", "rx_call", "band", "snr", "frequency"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"В ответе WSPR нет колонок: {missing}")
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--band", default="20m")
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Максимум строк; отдаётся начало суток (см. fetch_wspr).",
    )
    args = parser.parse_args()

    date = dt.date.fromisoformat(args.date)
    df = fetch_wspr(date, band=args.band, limit=args.limit)
    df = normalize(df)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    out = RAW_DIR / f"wspr_{date.isoformat()}_{args.band}.csv"
    df.to_csv(out, index=False)
    sidecar = _write_checksum(out)
    print(f"[OK] {len(df)} строк -> {out} (sha256 -> {sidecar.name})")


if __name__ == "__main__":
    main()
