"""Phase 1 readiness check for stations_geo.csv (read-only).

Verifies the background download_stations_geo.py is finished successfully
and that stations_geo.csv looks like a real directory, not a smoke-test stub.

Exit codes:
  0 READY            1 file missing       2 unreadable/malformed
  3 download running 4 exit code != 0     5 rows < --min-rows
  6 mtime predates --since (smoke-test stub)

Usage (at completion time, not now):
  python scripts/check_stations_geo.py --exit-code 0 --since 2026-10-29T08:08:00
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CANDIDATES = [
    ROOT / "data" / "stations_geo.csv",
    ROOT / "data" / "processed" / "stations_geo.csv",
    ROOT / "data" / "scripts" / "stations_geo.csv",
    ROOT / "stations_geo.csv",
]


def find_file(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def find_running_download() -> list[tuple[int, str]]:
    """Return [(pid, cmdline)] of live python download_stations_geo.py processes."""
    if os.name != "nt":
        print("[WARN] process scan is Windows-only; assuming no download is running")
        return []
    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match 'python' -and "
        "$_.CommandLine -match 'download_stations_geo' -and "
        "$_.CommandLine -notmatch 'check_stations_geo' } | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.SubprocessError, OSError) as e:
        print(f"[WARN] process scan failed: {e}")
        return []
    raw = (res.stdout or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    out: list[tuple[int, str]] = []
    for d in data:
        try:
            out.append((int(d["ProcessId"]), str(d.get("CommandLine", ""))))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def parse_since(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        print(f"[WARN] --since not ISO-8601: {value!r}")
        return None


def count_rows_and_header(path: Path) -> tuple[int, str]:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        header = f.readline().rstrip("\r\n")
        n = sum(1 for _ in f)
    return n, header


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=None)
    ap.add_argument("--min-rows", type=int, default=50_000)
    ap.add_argument("--max-age-hours", type=float, default=6.0)
    ap.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO start time of the download; mtime must be >= it",
    )
    ap.add_argument(
        "--exit-code",
        type=int,
        default=None,
        help="Exit code reported by the finished download process",
    )
    args = ap.parse_args(argv)

    print("=== Phase 1: stations_geo.csv readiness check ===")

    running = find_running_download()
    if running:
        for pid, cmd in running:
            print(f"[RUNNING] pid={pid} cmd={cmd[:120]}")
        print("RESULT: IN_PROGRESS (download_stations_geo.py still alive)")
        return 3
    print("[DEAD] no live download_stations_geo.py process")

    if args.exit_code is None:
        print("[WARN] --exit-code not provided; cannot verify download success")
    elif args.exit_code != 0:
        print(f"[FAIL] download exited with code {args.exit_code}")
        return 4

    path = args.file or find_file(DEFAULT_CANDIDATES)
    if path is None or not path.exists():
        print("[MISSING] stations_geo.csv not found; looked at:")
        for c in DEFAULT_CANDIDATES:
            print("   -", c)
        return 1
    print(f"[FOUND] {path}")

    st = path.stat()
    size_mb = st.st_size / 1024 / 1024
    mtime = datetime.fromtimestamp(st.st_mtime)
    print(f"  size = {st.st_size} bytes ({size_mb:.2f} MB)")
    print(f"  mtime = {mtime.isoformat(timespec='seconds')}")

    since_ts = parse_since(args.since)
    if since_ts is not None and st.st_mtime < since_ts:
        print(f"[STALE] mtime predates --since ({args.since}) — smoke-test stub?")
        return 6

    age_h = (time.time() - st.st_mtime) / 3600.0
    if age_h > args.max_age_hours:
        print(f"[WARN] mtime is {age_h:.1f}h old (> {args.max_age_hours}h)")

    try:
        n, header = count_rows_and_header(path)
    except OSError as e:
        print(f"[ERROR] cannot read file: {e}")
        return 2
    print(f"  header = {header!r}")
    print(f"  data rows = {n}")
    if "station" not in header.lower() and "lat" not in header.lower():
        print("[WARN] header does not look like a station directory")
    if n < args.min_rows:
        print(f"[LOW_ROWS] {n} < --min-rows={args.min_rows}")
        return 5

    print("\nRESULT: READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
