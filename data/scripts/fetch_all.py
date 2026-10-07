"""
fetch_all.py — оркестратор сбора данных CrossCorr.

Одна команда → всё, что можно автоматически, + инструкция по ручному.
Запускать из корня проекта:

    python data/scripts/fetch_all.py --start 2026-09-01 --end 2026-09-03

Даты и параметры по умолчанию читаются из data/scripts/config.yaml.
CLI-флаги переопределяют config.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import traceback
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.yaml"

ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

KNOWN_SOURCES = {"wspr", "horizons", "intermagnet", "kp", "dst", "f107"}

# Флаги, которые не должны конфликтовать с subparser
SKIP_UNIFY_HELP = "Не запускать unify_schema.py после загрузки."
SKIP_MANUAL_HELP = "Не печатать инструкцию по INTERMAGNET."
ONLY_HELP = "Только указанные источники (через запятую): wspr,horizons,intermagnet,kp,dst,f107."


def load_config(path: Path) -> dict:
    """Загрузить config.yaml или создать дефолтный."""
    if not path.exists():
        default = {
            "defaults": {"start": "2026-09-01", "end": "2026-09-15"},
            "wspr": {"band": "20m", "max_spots_per_day": 5000},
            "horizons": {"objects": ["sun", "moon"], "step": "1h"},
            "intermagnet": {"stations": ["MOS", "ESK", "OTT"]},
            "space_weather": {"indices": ["kp", "dst", "f107"]},
        }
        path.write_text(
            "# Настройки сбора данных CrossCorr\n"
            "# Меняй даты и станции здесь — не в коде!\n\n"
            + yaml.dump(default, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"[INFO] Создан дефолтный config: {path}")
        return default
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_sources(only: str | None, config: dict) -> set[str]:
    """Вернуть множество имён источников для загрузки.

    Если ``--only`` задан — только указанные (валидация имён).
    Иначе — всё из конфига: wspr, horizons, intermagnet,
    + индексы space_weather из config['space_weather']['indices'].
    """
    if only:
        requested = {s.strip() for s in only.split(",")}
        unknown = requested - KNOWN_SOURCES
        if unknown:
            raise SystemExit(
                f"Неизвестные источники: {', '.join(sorted(unknown))}. "
                f"Доступны: {', '.join(sorted(KNOWN_SOURCES))}"
            )
        return requested

    sources = {"wspr", "horizons", "intermagnet"}
    sw = config.get("space_weather", {}).get("indices", [])
    sources.update(sw)
    unknown_sw = set(sw) - KNOWN_SOURCES
    if unknown_sw:
        raise SystemExit(
            f"config.yaml: space_weather.indices содержит "
            f"неизвестные имена: {', '.join(sorted(unknown_sw))}"
        )
    return sources


def iter_dates(start: dt.date, end: dt.date):
    """Генератор дат от start до end включительно."""
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def iter_months(start: dt.date, end: dt.date):
    """Генератор пар (year, month) от start до end включительно."""
    current = start.replace(day=1)
    while current <= end:
        yield current.year, current.month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


# ─── WSPR ────────────────────────────────────────────────────────

def _fetch_wspr_range(start: dt.date, end: dt.date, config: dict) -> int:
    """Скачать WSPR за диапазон дат. Возвращает число успешных дней."""
    from data.scripts.download_wspr import fetch_wspr, normalize, RAW_DIR

    band = config.get("wspr", {}).get("band", "20m")
    limit = config.get("wspr", {}).get("max_spots_per_day", 5000)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    for date in iter_dates(start, end):
        try:
            df = fetch_wspr(date, band=band, limit=limit)
            if df.empty:
                print(f"[SKIP] WSPR {date.isoformat()}: пустой ответ")
                continue
            df = normalize(df)
            out = RAW_DIR / f"wspr_{date.isoformat()}_{band}.csv"
            df.to_csv(out, index=False)
            print(f"[OK]  WSPR {date.isoformat()}: {len(df)} строк -> {out.name}")
            ok += 1
        except Exception:
            print(f"[ERR] WSPR {date.isoformat()}: {traceback.format_exc().strip().splitlines()[-1]}")
    return ok


# ─── Horizons ────────────────────────────────────────────────────

def _fetch_horizons_range(start: str, end: str, config: dict) -> int:
    """Скачать эфемериды JPL Horizons. Возвращает число успешных объектов."""
    from data.scripts.download_horizons import fetch_ephemeris, RAW_DIR, PLANETS

    objects = config.get("horizons", {}).get("objects", ["sun", "moon"])
    step = config.get("horizons", {}).get("step", "1h")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    for obj in objects:
        try:
            table = fetch_ephemeris(obj, start, end, step)
            df = table.to_pandas()
            out = RAW_DIR / f"horizons_{obj}_{start}_{end}.csv"
            df.to_csv(out, index=False)
            print(f"[OK]  Horizons {obj}: {len(df)} строк -> {out.name}")
            ok += 1
        except Exception:
            print(f"[ERR] Horizons {obj}: {traceback.format_exc().strip().splitlines()[-1]}")
    return ok


# ─── INTERMAGNET ─────────────────────────────────────────────────

def _print_intermagnet_manual(start: dt.date, end: dt.date, config: dict):
    """Напечатать инструкцию по ручной загрузке INTERMAGNET."""
    from data.scripts.download_intermagnet import download_and_save_intermagnet

    stations = config.get("intermagnet", {}).get("stations", [])
    if not stations:
        print("[INFO] INTERMAGNET: станции не заданы в config.yaml.")
        return

    print()
    print("=" * 60)
    print("INTERMAGNET — требуется ручная загрузка с https://intermagnet.org")
    print("=" * 60)
    print()
    for station in stations:
        for year, month in iter_months(start, end):
            download_and_save_intermagnet(station, year, month)
    print()
    print(
        "После скачивания .min файлов запустите: python data/scripts/unify_schema.py"
    )
    print()


# ─── Space Weather ───────────────────────────────────────────────

def _fetch_space_weather(start: str, end: str, indices: set[str]) -> int:
    """Скачать индексы космической погоды. Возвращает число успешных."""
    from data.scripts.download_space_weather import (
        RAW_DIR,
        fetch_kp,
        fetch_dst,
        fetch_f107,
    )

    funcs = {"kp": fetch_kp, "dst": fetch_dst, "f107": fetch_f107}
    needed = {name for name in indices if name in funcs}
    if not needed:
        return 0

    ok = 0
    for name in sorted(needed):
        try:
            path = funcs[name](start, end, RAW_DIR)
            if path:
                ok += 1
        except Exception:
            print(f"[ERR] {name}: {traceback.format_exc().strip().splitlines()[-1]}")
    return ok


# ─── Unify ───────────────────────────────────────────────────────

def _run_unify():
    """Запустить unify_schema.py для сборки unified.parquet."""
    print()
    print("-" * 60)
    print("[STEP] Запуск unify_schema.py ...")
    try:
        from data.scripts import unify_schema
        unify_schema.main()
    except SystemExit as e:
        msg = str(e).strip() if e else ""
        print(f"[WARN] unify_schema завершился: {msg}")
    except Exception:
        print(f"[ERR] unify_schema: {traceback.format_exc().strip().splitlines()[-1]}")


# ─── Main ────────────────────────────────────────────────────────

def main() -> None:
    config = load_config(CONFIG_PATH)
    defaults = config.get("defaults", {})

    parser = argparse.ArgumentParser(
        description="Оркестратор сбора данных CrossCorr — скачать всё одной командой."
    )
    parser.add_argument(
        "--start",
        default=defaults.get("start", "2026-09-01"),
        help="Начальная дата YYYY-MM-DD (по умолчанию из config.yaml).",
    )
    parser.add_argument(
        "--end",
        default=defaults.get("end", "2026-09-15"),
        help="Конечная дата YYYY-MM-DD (по умолчанию из config.yaml).",
    )
    parser.add_argument("--skip-unify", action="store_true", help=SKIP_UNIFY_HELP)
    parser.add_argument("--skip-manual", action="store_true", help=SKIP_MANUAL_HELP)
    parser.add_argument("--only", default=None, help=ONLY_HELP)
    args = parser.parse_args()

    sources = resolve_sources(args.only, config)

    try:
        start_dt = dt.date.fromisoformat(args.start)
        end_dt = dt.date.fromisoformat(args.end)
    except ValueError as e:
        raise SystemExit(f"Неверный формат даты: {e}") from e

    if start_dt > end_dt:
        raise SystemExit(f"--start ({start_dt}) позже --end ({end_dt})")

    print(f"[INFO] Диапазон: {start_dt.isoformat()} -> {end_dt.isoformat()}")
    print(f"[INFO] Источники: {', '.join(sorted(sources))}")
    print()

    results: dict[str, str] = {}

    # WSPR
    if "wspr" in sources:
        print("--- WSPR ---")
        n = _fetch_wspr_range(start_dt, end_dt, config)
        results["wspr"] = f"{n} дней"
        print()

    # Horizons
    if "horizons" in sources:
        print("--- JPL Horizons ---")
        n = _fetch_horizons_range(args.start, args.end, config)
        results["horizons"] = f"{n} объектов"
        print()

    # Space weather (kp, dst, f107)
    sw_indices = sources & {"kp", "dst", "f107"}
    if sw_indices:
        print("--- Space Weather ---")
        n = _fetch_space_weather(args.start, args.end, sw_indices)
        results["space_weather"] = f"{', '.join(sorted(sw_indices))}: {n}/{len(sw_indices)}"
        print()

    # INTERMAGNET (manual)
    if "intermagnet" in sources:
        if args.skip_manual:
            results["intermagnet"] = "пропущен (--skip-manual)"
        else:
            _print_intermagnet_manual(start_dt, end_dt, config)
            results["intermagnet"] = "инструкция напечатана"

    # Итоги
    print()
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ:")
    for name, status in results.items():
        print(f"  {name:<20} {status}")
    print("=" * 60)

    # Unify
    if not args.skip_unify:
        _run_unify()
    else:
        print("[INFO] unify_schema.py пропущен (--skip-unify)")

    print()
    print("[DONE] fetch_all завершён.")


if __name__ == "__main__":
    main()