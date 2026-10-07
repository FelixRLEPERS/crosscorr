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

BAND_MHZ = {
    "160m": 1, "80m": 3, "60m": 5, "40m": 7, "30m": 10,
    "20m": 14, "17m": 18, "15m": 21, "12m": 24, "10m": 28,
    "6m": 50, "2m": 144,
}

# ВНИМАНИЕ: WSPR API крайне нестабилен. Используем декоратор для повторных попыток.
WSPR_API = "http://db1.wspr.live/"

MAX_RETRIES = 3
INITIAL_BACKOFF = 5
USER_AGENT = "ionosphere-research/1.0"


def fetch_wspr(date: dt.date, band: str = "20m", limit: int = 5000) -> pd.DataFrame:
    """Скачивает споты WSPR за указанную дату с retry-логикой.

    Использует ClickHouse-зеркало db1.wspr.live (SQL-интерфейс).
    Запрос: SELECT ... FROM wspr.rx WHERE time >= ... AND time < ...
    Колонки маппятся в имена, ожидаемые normalize() и unify_schema.py.
    """
    if band not in BAND_MHZ:
        raise ValueError(f"Неизвестный диапазон: {band!r}. Доступны: {list(BAND_MHZ)}")
    band_mhz = BAND_MHZ[band]

    start_ts = date.isoformat() + " 00:00:00"
    end_ts = (date + dt.timedelta(days=1)).isoformat() + " 00:00:00"
    sql = (
        "SELECT time AS timestamp, tx_sign AS tx_call, rx_sign AS rx_call, "
        "band, snr, frequency, distance "
        f"FROM wspr.rx "
        f"WHERE time>='{start_ts}' AND time<'{end_ts}' "
        f"AND band = {band_mhz} "
        f"LIMIT {limit} "
        f"FORMAT CSVWithNames"
    )
    headers = {"User-Agent": USER_AGENT}

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(WSPR_API, params={"query": sql},
                                headers=headers, timeout=30)
            resp.raise_for_status()
            from io import StringIO
            df = pd.read_csv(StringIO(resp.text))
            if df.empty:
                print("[WARN] WSPR: 0 строк, сервер не отвечает. "
                      "Дата может быть в будущем.")
                return pd.DataFrame()
            return df
        except requests.RequestException as e:
            last_error = e
            backoff = INITIAL_BACKOFF * (2 ** attempt)
            if attempt < MAX_RETRIES - 1:
                print(f"[RETRY] Попытка {attempt + 1}/{MAX_RETRIES} "
                      f"не удалась: {e}. Ждём {backoff} сек...")
                time.sleep(backoff)

    print("[WARN] WSPR: сервер недоступен после "
          f"{MAX_RETRIES} попыток. Дата может быть в будущем. "
          f"Последняя ошибка: {last_error}")
    return pd.DataFrame()


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
