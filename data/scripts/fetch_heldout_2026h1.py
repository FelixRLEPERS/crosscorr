"""Two-phase fetch of missing WSPR hourly data for an arbitrary period.

Phase 1 (verify, default): READ-ONLY inventory of data/raw/wspr/ (legacy CSV)
and data/raw/wspr_hourly/ (canonical CSV + JSON) for --start..--end over
--bands; prints which day/band files are missing and validates the band index
mapping against ``SELECT DISTINCT band FROM wspr.rx`` (network metadata query,
no file writes).

Phase 2 (--apply): downloads only the missing day-band hourly spot series from
http://db1.wspr.live/ (ClickHouse, GET, JSONCompact), normalising both known
JSON shapes -- array[4] = [hour, spots, mean_snr, max_dist] and array[2] =
[hour, spots] -- plus dict rows into a canonical CSV
(hour, spots, mean_snr, max_distance) with a sha256 sidecar, following
data/scripts/download_wspr.py (retry + backoff + sidecar) and
data/scripts/download_wspr_parallel.py (thread pool) patterns.

Note: 2026 held-out hourly data lives in data/raw/wspr_hourly/, not in
data/raw/wspr/ (which holds training-era wspr_hourly_*.csv up to 2026-01-19),
so both directories are scanned as a union.

Usage:
    python data/scripts/fetch_heldout_2026h1.py --start 2026-01-01 --end 2026-06-30
    python data/scripts/fetch_heldout_2026h1.py --start 2026-01-01 --end 2026-06-30 --apply
    python data/scripts/fetch_heldout_2026h1.py --start 2026-05-01 --end 2026-06-30 --bands 15m --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
WSPR_DIR = ROOT / "data" / "raw" / "wspr"
DEFAULT_OUT_DIR = ROOT / "data" / "raw" / "wspr_hourly"
API = "http://db1.wspr.live/"
HEADERS = {"User-Agent": "ionosphere-research/1.0"}
DEFAULT_BANDS = ["15m", "20m", "40m"]
BAND_INDEX = {"20m": 14, "15m": 21, "40m": 7}
CANONICAL_COLS = ["hour", "spots", "mean_snr", "max_distance"]
RETRY_BACKOFF = [5, 15, 30]  # seconds between attempts (4 attempts total)
DEFAULT_WORKERS = 4
DEFAULT_TIMEOUT = 60.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--start", required=True, help="start date YYYY-MM-DD (inclusive)")
    p.add_argument("--end", required=True, help="end date YYYY-MM-DD (inclusive)")
    p.add_argument(
        "--bands",
        nargs="+",
        default=DEFAULT_BANDS,
        help=f"band suffixes (default: {' '.join(DEFAULT_BANDS)})",
    )
    p.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="directory for canonical CSV files (default: data/raw/wspr_hourly)",
    )
    p.add_argument("--apply", action="store_true", help="phase 2: download the missing files")
    p.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="parallel threads")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout, s")
    p.add_argument(
        "--skip-band-check",
        action="store_true",
        help="skip the SELECT DISTINCT band validation query",
    )
    return p.parse_args()


def date_range(start: str, end: str) -> list[str]:
    days: list[str] = []
    d = pd.Timestamp(start)
    stop = pd.Timestamp(end)
    if stop < d:
        raise SystemExit(f"--end {end} is before --start {start}")
    while d <= stop:
        days.append(d.strftime("%Y-%m-%d"))
        d += pd.Timedelta(days=1)
    return days


def day_from_stem(stem: str, prefix: str) -> tuple[str, str] | None:
    """Parse <prefix>YYYY-MM-DD_BAND from a file stem."""
    if not stem.startswith(prefix):
        return None
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    day, band = parts[-2], parts[-1]
    if len(day) == 10 and day[4] == "-":
        return day, band
    return None


def json_candidates(out_dir: Path, day: str, band: str) -> list[Path]:
    """Known JSON naming variants (dload_2026/bg_dload_2026 use wspr_2026_...)."""
    return [
        out_dir / f"wspr_2026_{day}_{band}.json",
        out_dir / f"wspr_{day}_{band}.json",
        out_dir / f"wspr_{day.replace('-', '_')}_{band}.json",
    ]


def count_rows(path: Path) -> int | None:
    """Rows in a source file; None = absent/unreadable (=> needs fetch)."""
    if not path.exists():
        return None
    try:
        if path.suffix == ".csv":
            df = pd.read_csv(path)
            return int(len(df)) if "hour" in df.columns else None
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(len(data)) if isinstance(data, list) else None
    except Exception:  # noqa: BLE001
        return None


def inventory(
    days: list[str], bands: list[str], out_dir: Path
) -> tuple[list[tuple[str, str]], dict]:
    """READ-ONLY: missing (day, band) tasks + per-source statistics."""
    missing: list[tuple[str, str]] = []
    stats = {"canonical": 0, "legacy_csv": 0, "legacy_json": 0, "rows": 0}
    for day in days:
        for band in bands:
            n = count_rows(out_dir / f"wspr_hourly_{day}_{band}.csv")
            if n is not None:
                stats["canonical"] += 1
                stats["rows"] += n
                continue
            legacy_n = 0
            legacy_kind = None
            csv_n = count_rows(WSPR_DIR / f"wspr_hourly_{day}_{band}.csv")
            if csv_n is not None:
                legacy_n, legacy_kind = csv_n, "legacy_csv"
            else:
                for jp in json_candidates(out_dir, day, band):
                    jn = count_rows(jp)
                    if jn is not None and jn > legacy_n:
                        legacy_n, legacy_kind = jn, "legacy_json"
            if legacy_kind and legacy_n:
                stats[legacy_kind] += 1
                stats["rows"] += legacy_n
            else:
                missing.append((day, band))
    return missing, stats


def verify_band_indices(days: list[str], bands: list[str], timeout: float) -> list[str]:
    """SELECT DISTINCT band FROM wspr.rx over the first 3 days; returns problems."""
    if not days:
        return ["empty date range"]
    lo = days[0]
    hi = (pd.Timestamp(days[min(2, len(days) - 1)]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    sql = (
        f"SELECT DISTINCT band FROM wspr.rx WHERE time >= '{lo} 00:00:00' "
        f"AND time < '{hi} 00:00:00' ORDER BY band FORMAT JSONCompact"
    )
    try:
        resp = requests.get(API, params={"query": sql}, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        observed = {int(r[0]) for r in data if r}
    except Exception as exc:  # noqa: BLE001
        return [f"band validation query failed: {exc}"]
    problems = []
    for band in bands:
        idx = BAND_INDEX.get(band)
        if idx is None:
            problems.append(f"unknown band {band!r} (not in BAND_INDEX)")
        elif idx not in observed:
            problems.append(
                f"band {band} (index {idx}) not returned by wspr.rx "
                f"for {lo}..{hi}; observed={sorted(observed)}"
            )
    return problems


def normalise_rows(data) -> pd.DataFrame:
    """Normalise array[4], array[2] or dict rows into the canonical frame."""
    rows = []
    for r in data:
        if isinstance(r, dict):
            hour = r.get("hour") or r.get("time")
            spots = r.get("spots", r.get("value", r.get("count")))
            mean_snr = r.get("mean_snr")
            max_distance = r.get("max_dist", r.get("max_distance"))
        elif isinstance(r, (list, tuple)):
            if len(r) >= 4:
                hour, spots, mean_snr, max_distance = r[0], r[1], r[2], r[3]
            elif len(r) == 2:  # array[2] = [hour, spots]
                hour, spots, mean_snr, max_distance = r[0], r[1], None, None
            else:
                continue
        else:
            continue
        if hour is None or spots is None:
            continue
        rows.append(
            {
                "hour": hour,
                "spots": spots,
                "mean_snr": mean_snr,
                "max_distance": max_distance,
            }
        )
    df = pd.DataFrame(rows, columns=CANONICAL_COLS)
    if df.empty:
        return df
    df["hour"] = pd.to_datetime(df["hour"], utc=True, errors="coerce")
    df = df.dropna(subset=["hour"]).drop_duplicates(subset=["hour"], keep="last")
    df["hour"] = (
        df["hour"].dt.tz_convert("UTC").dt.tz_localize(None).dt.strftime("%Y-%m-%d %H:%M:%S")
    )
    return df.sort_values("hour").reset_index(drop=True)


def write_canonical(out_dir: Path, day: str, band: str, df: pd.DataFrame) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"wspr_hourly_{day}_{band}.csv"
    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False, encoding="utf-8", lineterminator="\n")
    tmp.replace(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix(".csv.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return path


def fetch_day(
    day: str, band: str, out_dir: Path, timeout: float
) -> tuple[str, str, int, str | None]:
    """Download one day-band hourly series. Returns (day, band, rows, error)."""
    idx = BAND_INDEX[band]
    sql = (
        f"SELECT toStartOfHour(time) AS hour, count() AS spots, "
        f"avg(snr) AS mean_snr, max(distance) AS max_distance "
        f"FROM wspr.rx WHERE time >= '{day} 00:00:00' AND time < '{day} 23:59:59' "
        f"AND band = {idx} GROUP BY hour ORDER BY hour FORMAT JSONCompact"
    )
    last_err: str | None = None
    for attempt in range(len(RETRY_BACKOFF) + 1):
        try:
            resp = requests.get(API, params={"query": sql}, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data", []) if isinstance(payload, dict) else payload
            df = normalise_rows(data)
            if not df.empty:
                day_ts = pd.Timestamp(day)
                hours = pd.to_datetime(df["hour"])
                df = df[(hours >= day_ts) & (hours < day_ts + pd.Timedelta(days=1))]
            write_canonical(out_dir, day, band, df)
            return day, band, int(len(df)), None
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt < len(RETRY_BACKOFF):
                time.sleep(RETRY_BACKOFF[attempt])
    return day, band, 0, last_err


def main() -> int:
    args = parse_args()
    days = date_range(args.start, args.end)
    out_dir = Path(args.out_dir)
    unknown = [b for b in args.bands if b not in BAND_INDEX]
    print(f"period {args.start}..{args.end}: {len(days)} days x bands {args.bands}")
    if unknown:
        print(f"WARNING: bands not in BAND_INDEX (will be skipped): {unknown}")
    bands_ok = [b for b in args.bands if b in BAND_INDEX]

    # ---- phase 1: read-only inventory + band-index validation ----
    missing, stats = inventory(days, args.bands, out_dir)
    problems: list[str] = []
    print("== phase 1 (verify): inventory ==")
    print(f"  canonical CSV complete : {stats['canonical']}")
    print(f"  legacy CSV (wspr/)     : {stats['legacy_csv']}")
    print(f"  legacy JSON            : {stats['legacy_json']}")
    print(f"  total hourly rows seen : {stats['rows']}")
    print(f"  missing day-band tasks : {len(missing)}")
    by_band: dict[str, list[str]] = {}
    for day, band in missing:
        by_band.setdefault(band, []).append(day)
    for band, bdays in sorted(by_band.items()):
        print(f"  {band}: {len(bdays)} days missing -> {bdays[0]} .. {bdays[-1]}")
        print(f"      {', '.join(bdays)}")

    if not args.skip_band_check:
        problems = verify_band_indices(days, args.bands, args.timeout)
        if problems:
            for msg in problems:
                print(f"  BAND CHECK: {msg}")
        else:
            print(f"  BAND CHECK: OK {args.bands} -> {BAND_INDEX} confirmed via wspr.rx")

    if not args.apply:
        print("\nphase 2 skipped (run with --apply to download)")
        return 0
    if not missing:
        print("\nnothing to download; done")
        return 0
    if problems:
        print(
            "\nERROR: band-index validation failed; not downloading "
            "(use --skip-band-check to override)"
        )
        return 1

    # ---- phase 2: download only the missing tasks ----
    tasks = [(d, b) for d, b in missing if b in bands_ok]
    print(
        f"\n== phase 2 (apply): downloading {len(tasks)} day-band tasks "
        f"with {args.workers} workers =="
    )
    ok, failed = 0, []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(fetch_day, day, band, out_dir, args.timeout): (day, band)
            for day, band in tasks
        }
        for fut in as_completed(futures):
            day, band, rows, err = fut.result()
            if err is not None:
                failed.append((day, band, err))
                print(f"  FAIL {day} {band}: {err}")
            else:
                ok += 1
                print(f"  ok   {day} {band}: {rows} hours")
    elapsed = time.time() - t0
    print(f"\ndone: ok={ok}, failed={len(failed)} in {elapsed:.1f}s")
    if failed:
        print("failed tasks (rerun the same command to retry):")
        for day, band, err in failed:
            print(f"  {day} {band}: {err[:160]}")
        return 1

    # ---- post-download re-verify (read-only) ----
    missing_after, stats_after = inventory(days, args.bands, out_dir)
    print(
        f"\n== re-verify: missing after download = {len(missing_after)} "
        f"(canonical files now {stats_after['canonical']})"
    )
    if missing_after:
        for day, band in missing_after[:20]:
            print(f"  still missing: {day} {band}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
