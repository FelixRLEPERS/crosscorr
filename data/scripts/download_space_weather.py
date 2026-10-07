"""
Загрузка индексов космической погоды: Kp, Dst, F10.7.

Три независимых источника — каждый скачивается отдельно.
Если один падает, остальные продолжают.

Источники:
- Kp:  GFZ Potsdam JSON API  (3-часовой)
- Dst: WDC Kyoto text        (часовой)
- F107: NOAA SWPC JSON       (месячный)

Сохраняет CSV-файлы в data/raw/space_weather/.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "space_weather"
KP_API = "https://kp.gfz-potsdam.de/app/json/"
DST_BASE = "http://wdc.kugi.kyoto-u.ac.jp/dst_realtime"
F107_API = (
    "https://services.swpc.noaa.gov/json/solar-cycle/"
    "observed-solar-cycle-indices.json"
)

MAX_RETRIES = 3
BACKOFF = 5


class DataFetchError(RuntimeError):
    """Ошибка при скачивании данных."""


def _retry_get(url: str, **kwargs) -> requests.Response:
    """GET с retry-логикой."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=kwargs.pop("timeout", 60), **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                wait = BACKOFF * (2 ** attempt)
                print(f"[RETRY] Попытка {attempt + 1}/{MAX_RETRIES} "
                      f"не удалась: {e}. Ждём {wait}с...")
                time.sleep(wait)
    raise DataFetchError(
        f"Не удалось скачать {url} за {MAX_RETRIES} попыток. "
        f"Последняя ошибка: {last_err}"
    )


# ── Kp ───────────────────────────────────────────────────────────


def fetch_kp(start_date: str, end_date: str, out_dir: Path) -> Path:
    """Скачать Kp index с GFZ Potsdam.

    Kp — 3-часовой индекс геомагнитной активности (0–9).

    Args:
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        out_dir: куда сохранить CSV

    Returns:
        Path к сохранённому файлу.
    """
    start_iso = f"{start_date}T00:00:00Z"
    end_iso = f"{end_date}T00:00:00Z"

    r = _retry_get(KP_API, params={
        "start": start_iso,
        "end": end_iso,
        "index": "Kp",
    })

    data = r.json()
    if not isinstance(data, dict) or "Kp" not in data or "datetime" not in data:
        got = str(data)[:200]
        raise DataFetchError(
            f"Kp API: ожидался JSON с ключами 'Kp' и 'datetime', "
            f"получено: {got}"
        )

    df = pd.DataFrame({
        "timestamp": pd.to_datetime(data["datetime"]),
        "kp": [float(v) if v is not None else float("nan") for v in data["Kp"]],
    })

    if df.empty:
        raise DataFetchError(
            f"Kp API: пустой ответ для {start_date} – {end_date}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"kp_{start_date}_{end_date}.csv"
    df.to_csv(path, index=False)
    print(f"[OK] Kp: {len(df)} строк (3-часовых) -> {path.name}")
    return path


# ── Dst ──────────────────────────────────────────────────────────


def _parse_dst_line(line: str) -> list[tuple[int, int, int]] | None:
    """Разобрать строку вида DSTyymm*ddRRX020 0 v1 v2 ... v24.

    Формат:
        DSTyymm*ddRRRxx base_value hourly_0 ... hourly_23

    base_value пропускается (не используется в расчёте Dst).
    Возвращает список (day, hour, dst_nt) или None если не строка данных.
    """
    line = line.strip()
    if not line or line.startswith(("#", ":", "-", "<")):
        return None

    parts = line.split()
    if len(parts) < 3:
        return None

    header = parts[0]
    if not header.startswith("DST"):
        return None

    day_str = header.split("*")[1][:2] if "*" in header else None
    try:
        day = int(day_str)
    except (TypeError, ValueError):
        return None

    values = []
    for token in parts[1:]:
        try:
            values.append(int(token))
        except ValueError:
            continue

    hourly = values[1:25] if len(values) >= 25 else values[1:]
    if len(hourly) < 24:
        return None

    return [(day, h, v) for h, v in enumerate(hourly) if v != 9999]


def fetch_dst(start_date: str, end_date: str, out_dir: Path) -> Path:
    """Скачать Dst index с WDC Kyoto.

    Dst — часовой индекс геомагнитных возмущений (нТ).

    Реальные (final) данные доступны с задержкой в несколько месяцев;
    real-time (quicklook) — доступны через несколько дней. Скрипт
    использует real-time эндпоинт.
    """
    try:
        start_dt = pd.Timestamp(start_date, tz="UTC")
        end_dt = pd.Timestamp(end_date, tz="UTC")
    except Exception as e:
        raise DataFetchError(f"Dst: неверный формат даты: {e}") from e

    all_rows = []
    current = start_dt.replace(day=1)
    while current <= end_dt:
        yymm = f"{current.year % 100:02d}{current.month:02d}"
        url = f"{DST_BASE}/{current.year}{current.month:02d}/dst{yymm}.for.request"
        try:
            r = _retry_get(url)
        except DataFetchError as e:
            print(f"[SKIP] Dst {current.year}-{current.month:02d}: {e}")
            current = (current + pd.DateOffset(months=1)).replace(day=1)
            continue

        for line in r.text.splitlines():
            parsed = _parse_dst_line(line)
            if parsed is None:
                continue
            for day, hour, dst in parsed:
                ts = pd.Timestamp(
                    year=current.year, month=current.month,
                    day=day, hour=hour, tz="UTC",
                )
                if start_dt <= ts <= end_dt:
                    all_rows.append({"timestamp": ts, "dst_nt": dst})

        print(f"[INFO] Dst {current.year}-{current.month:02d}: "
              f"прочитано записей за месяц")
        current = (current + pd.DateOffset(months=1)).replace(day=1)

    if not all_rows:
        raise DataFetchError(
            f"Dst: нет данных за {start_date} – {end_date}. "
            "Проверьте даты: real-time данные есть только за последние "
            "несколько месяцев."
        )

    df = pd.DataFrame(all_rows).sort_values("timestamp").reset_index(drop=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"dst_{start_date}_{end_date}.csv"
    df.to_csv(path, index=False)
    print(f"[OK] Dst: {len(df)} строк (часовых) -> {path.name}")
    return path


# ── F10.7 ────────────────────────────────────────────────────────


def fetch_f107(start_date: str, end_date: str, out_dir: Path) -> Path:
    """Скачать F10.7 (солнечный радиопоток) с NOAA SWPC.

    F10.7 — дневной индекс солнечной активности (sfu = 10⁻²² W/m²/Hz).
    Источник даёт **месячные** средние значения. Для ежедневных значений
    нужен другой источник (см. TODO в fetch_all()).

    Args:
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        out_dir: куда сохранить CSV

    Returns:
        Path к сохранённому файлу.
    """
    try:
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)
    except Exception as e:
        raise DataFetchError(f"F10.7: неверный формат даты: {e}") from e

    r = _retry_get(F107_API)
    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        raise DataFetchError(f"F10.7 API: ожидался массив JSON, получено: {data!r}")

    rows = []
    for entry in data:
        time_tag = entry.get("time-tag", "")
        f107 = entry.get("f10.7", -1.0)
        if f107 is None or float(f107) <= 0:
            continue
        try:
            ts = pd.Timestamp(f"{time_tag}-15")  # середина месяца
        except Exception:
            continue
        if start_dt <= ts <= end_dt:
            rows.append({"date": ts, "f107": float(f107)})

    if not rows:
        raise DataFetchError(
            f"F10.7: нет данных за {start_date} – {end_date}."
        )

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"f107_{start_date}_{end_date}.csv"
    df.to_csv(path, index=False)
    print(f"[OK] F10.7: {len(df)} строк (месячных) -> {path.name}")
    print("[INFO] F10.7: данные МЕСЯЧНЫЕ. Для часовых значений "
          "заполните confounders.csv синтетикой или другим источником.")
    return path


# ── fetch_all ────────────────────────────────────────────────────


def fetch_all(start_date: str, end_date: str) -> dict[str, Path | None]:
    """Скачать все три индекса. Каждый — независимо от ошибок других.

    Returns:
        {"kp": Path | None, "dst": Path | None, "f107": Path | None}
    """
    results: dict[str, Path | None] = {}
    out_dir = RAW_DIR

    for name, fn in [("kp", fetch_kp), ("dst", fetch_dst), ("f107", fetch_f107)]:
        try:
            results[name] = fn(start_date, end_date, out_dir)
        except DataFetchError as e:
            print(f"[ERROR] {name}: {e}")
            results[name] = None

    return results


# ── CLI ──────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Скачать индексы космической погоды (Kp, Dst, F10.7)"
    )
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--indices", nargs="+", choices=["kp", "dst", "f107"],
        default=["kp", "dst", "f107"],
        help="Какие индексы скачивать (по умолчанию все)"
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Скачиваем с {args.start} по {args.end}")
    print(f"[INFO] Индексы: {', '.join(args.indices)}")
    print(f"[INFO] Сохраняем в {RAW_DIR}\n")

    funcs = {"kp": fetch_kp, "dst": fetch_dst, "f107": fetch_f107}
    ok = 0
    for name in args.indices:
        try:
            path = funcs[name](args.start, args.end, RAW_DIR)
            if path:
                ok += 1
        except DataFetchError as e:
            print(f"[ERROR] {name}: {e}")

    print(f"\n[DONE] Скачано: {ok}/{len(args.indices)} индексов.")


if __name__ == "__main__":
    main()