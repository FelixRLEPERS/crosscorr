"""
Загрузка данных WSPR через публичный API wsprnet.org (или WSPR Live).
Сохраняет сырой CSV в data/raw/wspr/<date>.csv.

Примечание: WSPR-API нестабилен, лимиты и форматы меняются.
Скрипт — заготовка: подставьте актуальный эндпоинт.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import pandas as pd
import requests
import time

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "wspr"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ВНИМАНИЕ: WSPR API крайне нестабилен. Используем декоратор для повторных попыток.
WSPR_API = "https://db1.wsprnet.org/drupal/wsprnet/spotquery"

MAX_RETRIES = 3 # Максимальное количество попыток запроса
INITIAL_BACKOFF = 5 # Начальная задержка в секундах


def fetch_wspr(date: dt.date, band: str = "20m", limit: int = 5000) -> pd.DataFrame:
    """Скачивает споты WSPR за указанную дату с retry-логикой."""
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
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    date = dt.date.fromisoformat(args.date)
    df = fetch_wspr(date, band=args.band, limit=args.limit)
    df = normalize(df)

    out = RAW_DIR / f"wspr_{date.isoformat()}_{args.band}.csv"
    df.to_csv(out, index=False)
    print(f"[OK] {len(df)} строк -> {out}")


if __name__ == "__main__":
    main()