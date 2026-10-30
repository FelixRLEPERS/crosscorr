"""
Загрузка индексов космической погоды: Kp, Dst, F10.7 + GOES X-ray.

Четыре независимых источника — каждый скачивается отдельно.
Если один падает, остальные продолжают.

Источники:
- Kp:  GFZ Potsdam JSON API  (3-часовой)
- Dst: WDC Kyoto text        (часовой)
- F107: NOAA SWPC JSON       (месячный)
- GOES X-ray: NOAA NCEI XRS L2 (1-минутные средние NetCDF -> почасовой максимум)

Сохраняет CSV-файлы в data/raw/space_weather/.
"""

from __future__ import annotations

import argparse
import re
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "space_weather"
KP_API = "https://kp.gfz-potsdam.de/app/json/"
DST_BASE = "http://wdc.kugi.kyoto-u.ac.jp/dst_provisional"
F107_API = "https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json"

#: GOES-R XRS Level-2 (1-minute averages), дневные NetCDF на NCEI.
GOES_XRS_BASE = "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes"
GOES_PRODUCT = "l2/data/xrsf-l2-avg1m"
#: Приоритет спутников: GOES-18 покрывает весь период 2024-2025 целиком,
#: GOES-16 (до 2025-04) и GOES-19 (с 2025-01) — резерв на выпадающие дни.
GOES_SATS = ("goes18", "goes16", "goes19")
#: Канал 1-8 Angstrom («long») — именно им определяется класс флейра.
GOES_CHANNEL_VAR = "xrsb_flux"
GOES_FLAG_VAR = "xrsb_flag"
#: Имя файла вида dn_xrsf-l2-avg1m_g18_d20240510_v2-2-2.nc (версия плавает).
GOES_NC_RE = re.compile(r"([\w.-]+_d(\d{8})_v[\w.-]+\.nc)")

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
                wait = BACKOFF * (2**attempt)
                print(
                    f"[RETRY] Попытка {attempt + 1}/{MAX_RETRIES} не удалась: {e}. Ждём {wait}с..."
                )
                time.sleep(wait)
    raise DataFetchError(
        f"Не удалось скачать {url} за {MAX_RETRIES} попыток. Последняя ошибка: {last_err}"
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

    r = _retry_get(
        KP_API,
        params={
            "start": start_iso,
            "end": end_iso,
            "index": "Kp",
        },
    )

    data = r.json()
    if not isinstance(data, dict) or "Kp" not in data or "datetime" not in data:
        got = str(data)[:200]
        raise DataFetchError(f"Kp API: ожидался JSON с ключами 'Kp' и 'datetime', получено: {got}")

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(data["datetime"]),
            "kp": [float(v) if v is not None else float("nan") for v in data["Kp"]],
        }
    )

    if df.empty:
        raise DataFetchError(f"Kp API: пустой ответ для {start_date} – {end_date}")

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
                    year=current.year,
                    month=current.month,
                    day=day,
                    hour=hour,
                    tz="UTC",
                )
                if start_dt <= ts <= end_dt:
                    all_rows.append({"timestamp": ts, "dst_nt": dst})

        print(f"[INFO] Dst {current.year}-{current.month:02d}: прочитано записей за месяц")
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
        raise DataFetchError(f"F10.7: нет данных за {start_date} – {end_date}.")

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"f107_{start_date}_{end_date}.csv"
    df.to_csv(path, index=False)
    print(f"[OK] F10.7: {len(df)} строк (месячных) -> {path.name}")
    print(
        "[INFO] F10.7: данные МЕСЯЧНЫЕ. Для часовых значений "
        "заполните confounders.csv синтетикой или другим источником."
    )
    return path


# ── GOES X-ray (XRS) ─────────────────────────────────────────────


def _try_get(url: str, timeout: int = 60) -> requests.Response | None:
    """GET без retry; ``None`` на 404 (недоступные месяцы/спутники — это норма)."""
    try:
        r = requests.get(url, timeout=timeout)
    except requests.RequestException as e:
        raise DataFetchError(f"Не удалось скачать {url}: {e}") from e
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r


def _goes_month_index(sat: str, year: int, month: int) -> dict[str, str]:
    """Индекс дневных файлов XRS за месяц: ``{"20240510": "<filename>.nc", ...}``.

    Пустой словарь, если каталога нет (спутник ещё не запущен / уже снят).
    """
    url = f"{GOES_XRS_BASE}/{sat}/{GOES_PRODUCT}/{year:04d}/{month:02d}/"
    r = _try_get(url)
    if r is None:
        return {}
    return {m.group(2): m.group(1) for m in GOES_NC_RE.finditer(r.text)}


def _hourly_max_from_nc(path: Path) -> pd.DataFrame:
    """Почасовой максимум XRS-B (1-8 Angstrom) из дневного NetCDF.

    Валидны минуты с ``flag == 0`` и конечным потоком. Часы без валидных
    минут не попадают в результат (пропуск, а не ноль).

    Returns:
        DataFrame с колонками ``timestamp`` (naive UTC) и ``flux_long`` (W/m2).

    Raises:
        DataFetchError: netCDF4 не установлен или неожиданный формат времени.
    """
    try:
        import netCDF4
    except ImportError as e:
        raise DataFetchError(
            "netCDF4 не установлен (нужен для чтения архива GOES XRS): pip install netCDF4"
        ) from e

    with netCDF4.Dataset(str(path)) as ds:
        tvar = ds.variables["time"]
        units = str(getattr(tvar, "units", ""))
        m = re.match(r"seconds since (.+)", units)
        if not m:
            raise DataFetchError(f"{path.name}: неожиданные единицы времени {units!r}")
        base = pd.Timestamp(m.group(1).strip().replace("UTC", "").strip().rstrip("Z"))
        times = np.asarray(tvar[:], dtype=float)
        flux = np.ma.filled(np.ma.asarray(ds.variables[GOES_CHANNEL_VAR][:]), np.nan)
        flux = np.asarray(flux, dtype=float)
        if GOES_FLAG_VAR in ds.variables:
            flags = np.ma.filled(np.ma.asarray(ds.variables[GOES_FLAG_VAR][:]), -1)
            flags = np.asarray(flags)
        else:
            flags = np.zeros_like(times, dtype=int)

    stamps = base + pd.to_timedelta(times, unit="s")
    valid = (flags == 0) & np.isfinite(flux)
    df = pd.DataFrame({"timestamp": stamps[valid], "flux_long": flux[valid]})
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "flux_long"])
    df["timestamp"] = df["timestamp"].dt.floor("1h")
    hourly = df.groupby("timestamp", as_index=False)["flux_long"].max()
    return hourly


def fetch_goes_xray(start_date: str, end_date: str, out_dir: Path) -> Path:
    """Скачать GOES X-ray (1-8 Angstrom) и агрегировать до почасового максимума.

    Источник: NOAA NCEI, GOES-R XRS Level-2, 1-минутные средние (NetCDF-4,
    ~290 КБ/день). Перебираются спутники в порядке :data:`GOES_SATS`; день
    считается пропущенным, если файла нет ни у одного.

    Агрегация — **максимум за час**: класс флейра (M/X) определяется по
    пиковому значению, среднее за час пик размазало бы и флейр прошёл бы
    мимо порога. Часы без валидных минут не выводятся.

    Требует ``pip install netCDF4``.

    Args:
        start_date: YYYY-MM-DD (включительно)
        end_date: YYYY-MM-DD (включительно)
        out_dir: куда сохранить CSV

    Returns:
        Path к сохранённому файлу ``goes_xray_<start>_<end>.csv``
        с колонками ``timestamp, flux_long``.
    """
    try:
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)
    except Exception as e:
        raise DataFetchError(f"GOES X-ray: неверный формат даты: {e}") from e

    days = pd.date_range(start_dt.normalize(), end_dt.normalize(), freq="D")
    index_cache: dict[tuple[str, int, int], dict[str, str]] = {}
    frames: list[pd.DataFrame] = []
    n_missing = 0

    for i, day in enumerate(days):
        day_key = day.strftime("%Y%m%d")
        url = None
        for sat in GOES_SATS:
            key = (sat, day.year, day.month)
            if key not in index_cache:
                index_cache[key] = _goes_month_index(sat, day.year, day.month)
            fname = index_cache[key].get(day_key)
            if fname:
                url = f"{GOES_XRS_BASE}/{sat}/{GOES_PRODUCT}/{day.year:04d}/{day.month:02d}/{fname}"
                break

        if url is None:
            n_missing += 1
            print(f"[SKIP] GOES X-ray {day.date()}: файла нет ни у одного спутника")
            continue

        try:
            r = _retry_get(url, timeout=120)
        except DataFetchError as e:
            n_missing += 1
            print(f"[SKIP] GOES X-ray {day.date()}: {e}")
            continue

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as fh:
                fh.write(r.content)
                tmp_path = Path(fh.name)
            hourly = _hourly_max_from_nc(tmp_path)
        except DataFetchError as e:
            n_missing += 1
            print(f"[SKIP] GOES X-ray {day.date()}: {e}")
            continue
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

        if hourly.empty:
            n_missing += 1
            print(f"[SKIP] GOES X-ray {day.date()}: нет валидных минут")
            continue

        frames.append(hourly)
        if (i + 1) % 10 == 0:
            print(f"[INFO] GOES X-ray: обработано {i + 1}/{len(days)} дней...")

    if not frames:
        raise DataFetchError(
            f"GOES X-ray: нет данных за {start_date} – {end_date}. "
            "Проверьте даты: архив NCEI покрывает период с 2010-х годов, "
            "файлы появляются с задержкой в несколько дней после наблюдения."
        )

    df = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"goes_xray_{start_date}_{end_date}.csv"
    df.to_csv(path, index=False)
    n_days = len(frames)
    print(
        f"[OK] GOES X-ray: {len(df)} строк (часовых максимумов), "
        f"дней {n_days}/{len(days)}, пропущено {n_missing} -> {path.name}"
    )
    print(
        f"[INFO] GOES X-ray: максимум потока за период = {df['flux_long'].max():.3e} W/m2 "
        "(канал 1-8 Angstrom, агрегация — максимум за час)"
    )
    return path


# ── fetch_all ────────────────────────────────────────────────────


def fetch_all(start_date: str, end_date: str) -> dict[str, Path | None]:
    """Скачать все индексы. Каждый — независимо от ошибок других.

    Returns:
        {"kp": Path | None, "dst": Path | None, "f107": Path | None,
         "goes_xray": Path | None}
    """
    results: dict[str, Path | None] = {}
    out_dir = RAW_DIR

    funcs = {
        "kp": fetch_kp,
        "dst": fetch_dst,
        "f107": fetch_f107,
        "goes_xray": fetch_goes_xray,
    }
    for name, fn in funcs.items():
        try:
            results[name] = fn(start_date, end_date, out_dir)
        except DataFetchError as e:
            print(f"[ERROR] {name}: {e}")
            results[name] = None

    return results


# ── CLI ──────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Скачать индексы космической погоды (Kp, Dst, F10.7, GOES X-ray)"
    )
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--indices",
        nargs="+",
        choices=["kp", "dst", "f107", "goes_xray"],
        default=["kp", "dst", "f107", "goes_xray"],
        help="Какие индексы скачивать (по умолчанию все)",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Скачиваем с {args.start} по {args.end}")
    print(f"[INFO] Индексы: {', '.join(args.indices)}")
    print(f"[INFO] Сохраняем в {RAW_DIR}\n")

    funcs = {
        "kp": fetch_kp,
        "dst": fetch_dst,
        "f107": fetch_f107,
        "goes_xray": fetch_goes_xray,
    }
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
