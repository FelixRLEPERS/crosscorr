"""
Загрузка данных WSPR через ClickHouse-зеркало wspr.live.

Два режима:
  --mode raw     сырые споты (пагинация, до 100k/день)
  --mode hourly  агрегация по часам (24 строки/день)

Источник: db1.wspr.live (ClickHouse SQL API, доступен из РФ).
Формат ответа: JSONCompact.
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
    """Записать sha256 файла в сайдкар ``<path>.sha256``."""
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

WSPR_API = "http://db1.wspr.live/"

RETRY_BACKOFF = [5, 15, 30]
MAX_RETRIES = len(RETRY_BACKOFF)
TIMEOUT = 60
USER_AGENT = "ionosphere-research/1.0"

CHUNK_SIZE = 2000
MAX_CHUNKS = 50

COLS = ["time", "band", "tx_sign", "rx_sign", "snr", "frequency", "distance"]


def _request_chunk(sql: str) -> list[list]:
    """Один запрос к ClickHouse с retry-логикой. Возвращает список строк."""
    headers = {"User-Agent": USER_AGENT}
    last_error = None

    for attempt, backoff in enumerate(RETRY_BACKOFF):
        try:
            resp = requests.get(
                WSPR_API,
                params={"query": sql},
                headers=headers,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

        except requests.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                print(f"[RETRY] Попытка {attempt + 1}/{MAX_RETRIES} "
                      f"не удалась: {e}. Ждём {backoff} сек...")
                time.sleep(backoff)

    raise RuntimeError(
        f"WSPR сервер недоступен после {MAX_RETRIES} попыток. "
        f"Последняя ошибка: {last_error}"
    )


def fetch_wspr(
    date: dt.date, band: str = "20m", chunk_size: int = CHUNK_SIZE
) -> pd.DataFrame:
    """Скачивает все споты WSPR за день пагинацией (raw mode).

    Использует ORDER BY time + OFFSET для детерминированного обхода.
    Максимум MAX_CHUNKS чанков (защита от бесконечного цикла).
    """
    if band not in BAND_MHZ:
        raise ValueError(f"Неизвестный диапазон: {band!r}. Доступны: {list(BAND_MHZ)}")
    band_index = BAND_MHZ[band]

    start_ts = date.isoformat() + " 00:00:00"
    end_ts = (date + dt.timedelta(days=1)).isoformat() + " 00:00:00"

    all_rows = []
    total = 0

    for chunk_num in range(1, MAX_CHUNKS + 1):
        offset = (chunk_num - 1) * chunk_size
        sql = (
            f"SELECT {', '.join(COLS)} "
            f"FROM wspr.rx "
            f"WHERE time >= '{start_ts}' AND time < '{end_ts}' "
            f"AND band = {band_index} "
            f"ORDER BY time "
            f"LIMIT {chunk_size} "
            f"OFFSET {offset} "
            f"FORMAT JSONCompact"
        )

        rows = _request_chunk(sql)

        if not rows:
            if chunk_num == 1:
                print("[WARN] WSPR: 0 строк. Дата может быть в будущем "
                      "или сервер не отвечает.")
            break

        all_rows.extend(rows)
        total += len(rows)
        print(f"[INFO] chunk {chunk_num}: {len(rows)} rows (total {total})")

        if len(rows) < chunk_size:
            break

    else:
        print(f"[WARN] Достигнут лимит {MAX_CHUNKS} чанков "
              f"({MAX_CHUNKS * chunk_size} строк). Возможно, данных больше.")

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=COLS)
    df = df.rename(columns={
        "time": "timestamp",
        "tx_sign": "tx_call",
        "rx_sign": "rx_call",
    })
    return df[["timestamp", "tx_call", "rx_call", "band", "snr", "frequency", "distance"]]


def fetch_wspr_hourly(date: dt.date, band: str = "20m") -> pd.DataFrame:
    """Скачивает агрегированные по часам споты WSPR за день.

    Один SQL-запрос (GROUP BY hour) — 24 строки за день.
    Колонки: timestamp_utc, spots_count, mean_snr, max_distance, mean_frequency.
    """
    if band not in BAND_MHZ:
        raise ValueError(f"Неизвестный диапазон: {band!r}. Доступны: {list(BAND_MHZ)}")
    band_index = BAND_MHZ[band]

    start_ts = date.isoformat() + " 00:00:00"
    end_ts = (date + dt.timedelta(days=1)).isoformat() + " 00:00:00"

    sql = (
        f"SELECT "
        f"toStartOfHour(time) AS hour, "
        f"count(*) AS spots_count, "
        f"avg(snr) AS mean_snr, "
        f"max(distance) AS max_distance, "
        f"avg(frequency) AS mean_frequency "
        f"FROM wspr.rx "
        f"WHERE time >= '{start_ts}' AND time < '{end_ts}' "
        f"AND band = {band_index} "
        f"GROUP BY hour "
        f"ORDER BY hour "
        f"FORMAT JSONCompact"
    )

    rows = _request_chunk(sql)

    if not rows:
        print("[WARN] WSPR hourly: 0 строк. Дата может быть в будущем "
              "или сервер не отвечает.")
        return pd.DataFrame()

    hourly_cols = ["hour", "spots_count", "mean_snr", "max_distance", "mean_frequency"]
    df = pd.DataFrame(rows, columns=hourly_cols)
    df["timestamp"] = pd.to_datetime(df["hour"], utc=True, errors="coerce")
    df = df.drop(columns=["hour"])
    df["band"] = band_index

    return df[["timestamp", "band", "spots_count", "mean_snr", "max_distance", "mean_frequency"]]


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит к минимально нужному набору колонок (raw mode)."""
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
        "--mode",
        choices=["raw", "hourly"],
        default="raw",
        help="raw = сырые споты (пагинация), hourly = агрегация по часам (24 строки).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=CHUNK_SIZE,
        help=f"Размер чанка для raw-пагинации (по умолчанию {CHUNK_SIZE}).",
    )
    args = parser.parse_args()

    date = dt.date.fromisoformat(args.date)

    if args.mode == "hourly":
        df = fetch_wspr_hourly(date, band=args.band)
        prefix = "wspr_hourly"
    else:
        df = fetch_wspr(date, band=args.band, chunk_size=args.chunk_size)
        if df.empty:
            print(f"[DONE] WSPR {date.isoformat()}: 0 строк. Пропускаем.")
            return
        df = normalize(df)
        prefix = "wspr"

    if df.empty:
        print(f"[DONE] WSPR {date.isoformat()}: 0 строк. Пропускаем.")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    out = RAW_DIR / f"{prefix}_{date.isoformat()}_{args.band}.csv"
    df.to_csv(out, index=False)
    print(f"[INFO] done: {len(df)} rows saved -> {out.name}")
    sidecar = _write_checksum(out)
    print(f"[OK] sha256 -> {sidecar.name}")


if __name__ == "__main__":
    main()