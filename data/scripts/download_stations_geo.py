"""Download the local station coordinate reference from wspr.live (db1 ClickHouse).

Two-phase (verify -> apply) per AGENTS.md:

    python data/scripts/download_stations_geo.py           # Phase 1: probes
    python data/scripts/download_stations_geo.py --apply   # Phase 2: fetch + write

Output: data/processed/stations_geo.csv with columns (callsign, lat, lon),
one row per callsign -- so later analyses can resolve TX/RX coordinates
locally instead of hitting the API for every spot pair.

Query modes (--mode)
--------------------
distinct (default)
    The two task queries, executed on 1-day windows with a band filter:

        SELECT DISTINCT tx_sign, tx_lat, tx_lon FROM wspr.rx
        WHERE tx_lat IS NOT NULL AND band IN (..) AND time >= .. AND time < ..
        SELECT DISTINCT rx_sign, rx_lat, rx_lon FROM wspr.rx
        WHERE rx_lat IS NOT NULL AND band IN (..) AND time >= .. AND time < ..

    Phase-1 probing established the operating envelope of the public
    db1.wspr.live endpoint:
    * unbounded whole-table DISTINCT never answers (client timeout at 45-300 s);
    * windows >= 2 days time out for both roles;
    * 1-day windows answer in 0.2-0.4 s, BUT only with a band filter on the
      TX side -- unfiltered and combined multi-band TX queries time out at
      45 s, so TX is fetched band-by-band while RX is fetched as one
      combined query;
    * the endpoint is load-dependent: identical queries can pass or time out
      minutes apart, so Phase 2 still retries with backoff and falls back to
      halving/single-band queries on failure.
argmax
    Per-callsign most recent coordinates (GROUP BY sign + argMax(col, time)).
    Nicer semantics (latest known position), but observed to suffer the same
    execution kill as DISTINCT on this endpoint -- kept as an explicit option
    for endpoints that allow it.
any
    Per-callsign coordinate pair taken from one arbitrary row of the window:

        SELECT tx_sign, any((tx_lat, tx_lon)) FROM wspr.rx
        WHERE tx_lat IS NOT NULL AND time >= .. AND time < ..
        GROUP BY tx_sign

    `any(tuple)` keeps lat/lon from the SAME spot row (two per-column any()
    calls could mix coordinates from different rows). Station positions are
    effectively static, so an arbitrary historic row is adequate for the
    30-degree latitude binning this reference serves. Same window/band
    envelope as `distinct` (1-day + band filter).
auto (default)
    Probes `distinct` with the proven query shapes (TX single-band,
    RX combined, 1-day window); falls back to `any` when they do not
    answer within --probe-timeout. The chosen mode is reported in Phase 1.

Coverage: the default window is the analysis era (2024-04 .. 2026-10) and
the default bands are the three analysis bands (40/20/15 m); widen via
--start/--end/--bands. Keep --chunk-days at 1 for this endpoint -- larger
windows time out (Phase 2 halves adaptively, but every failed attempt costs
a full client timeout).

Merging rules
-------------
* chunks are processed chronologically; a callsign seen again in a later
  chunk keeps the later chunk's record (the most recent activity window);
* TX and RX results are merged into one table; on conflicting coordinates
  the record from the later chunk wins (RX probed after TX within a chunk),
  and the number of conflicting callsigns is reported;
* coordinates are rounded to 6 decimals (~0.1 m -- far below the 30 deg
  binning resolution of the spatial analysis).

Resume / checkpointing
----------------------
Every completed query is immediately written as a small CSV part under
`data/processed/stations_geo_parts/` (tmp file + atomic rename). A rerun
skips tasks whose part already exists, so the multi-hour download survives
process/session kills: just re-run the same `--apply` command. The parts
directory is deleted only after the final CSV is written with no failed
windows left; `--clean` discards checkpoints and starts from scratch.
"""

from __future__ import annotations

import argparse
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
WSPR_API = "http://db1.wspr.live/"
HEADERS = {"User-Agent": "ionosphere-research/1.0"}
OUT_PATH = ROOT / "data" / "processed" / "stations_geo.csv"
PARTS_DIR = ROOT / "data" / "processed" / "stations_geo_parts"

ROLES = ("tx", "rx")
DEFAULT_START = "2024-04-01"  # analysis era; widen via --start/--end
DEFAULT_END = "2026-10-01"
RETRY_BACKOFF = (5, 15)


def ch_query(sql: str, timeout: int, retries: int = 1) -> list:
    """GET a SQL query against db1.wspr.live; raises on timeout/HTTP error."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(WSPR_API, params={"query": sql}, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("data", [])
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(RETRY_BACKOFF[attempt])
    raise RuntimeError(str(last_error) if last_error else "unknown query failure")


def chunk_sql(
    role: str, d0: pd.Timestamp, d1: pd.Timestamp, mode: str, bands: list[int] | None = None
) -> str:
    """Time-bounded station query for one role ('tx' or 'rx')."""
    bounds = f"time >= '{d0}' AND time < '{d1}'"
    not_null = f"{role}_lat IS NOT NULL"
    band_filter = f" AND band IN ({','.join(str(b) for b in bands)})" if bands else ""
    if mode == "distinct":
        return (
            f"SELECT DISTINCT {role}_sign AS callsign, {role}_lat AS lat, "
            f"{role}_lon AS lon FROM wspr.rx WHERE {not_null} AND {bounds}{band_filter} "
            "FORMAT JSONCompact"
        )
    if mode == "argmax":
        return (
            f"SELECT {role}_sign AS callsign, argMax({role}_lat, time) AS lat, "
            f"argMax({role}_lon, time) AS lon, max(time) AS last_seen "
            f"FROM wspr.rx WHERE {not_null} AND {bounds}{band_filter} "
            f"GROUP BY {role}_sign FORMAT JSONCompact"
        )
    return (
        f"SELECT {role}_sign AS callsign, any(({role}_lat, {role}_lon)) AS pair "
        f"FROM wspr.rx WHERE {not_null} AND {bounds}{band_filter} "
        f"GROUP BY {role}_sign FORMAT JSONCompact"
    )


def probe_distinct_day(timeout: int, bands: list[int] | None) -> tuple[bool, str]:
    """Probe the two proven query shapes on a 1-day window.

    TX is probed single-band (combined/unfiltered TX times out on this
    endpoint), RX with the combined band filter. Note: the endpoint runs in
    readonly mode, so `SETTINGS max_execution_time` is rejected (HTTP 500) --
    the client timeout is the only guard.
    """
    d0, d1 = pd.Timestamp(DEFAULT_END) - timedelta(days=1), pd.Timestamp(DEFAULT_END)
    band_filter = f" AND band IN ({','.join(str(b) for b in bands)})" if bands else ""
    shapes = [
        (
            "tx",
            f"SELECT DISTINCT tx_sign, tx_lat, tx_lon FROM wspr.rx "
            f"WHERE tx_lat IS NOT NULL{band_filter} AND time >= '{d0}' "
            f"AND time < '{d1}' FORMAT JSONCompact",
        ),
        (
            "rx",
            f"SELECT DISTINCT rx_sign, rx_lat, rx_lon FROM wspr.rx "
            f"WHERE rx_lat IS NOT NULL{band_filter} AND time >= '{d0}' "
            f"AND time < '{d1}' FORMAT JSONCompact",
        ),
    ]
    details: list[str] = []
    for role, sql in shapes:
        if role == "tx":
            # TX: one query per band (the proven shape)
            for band in bands or [None]:
                single = sql if band is None else sql.replace(band_filter, f" AND band = {band}")
                started = time.time()
                try:
                    rows = ch_query(single, timeout=timeout, retries=2)
                except RuntimeError as exc:
                    return False, f"tx band={band} no answer in {timeout}s ({str(exc)[:70]})"
                details.append(f"tx b{band}: {time.time() - started:.1f}s/{len(rows)}")
        else:
            started = time.time()
            try:
                rows = ch_query(sql, timeout=timeout, retries=2)
            except RuntimeError as exc:
                return False, f"rx no answer in {timeout}s ({str(exc)[:70]})"
            details.append(f"rx: {time.time() - started:.1f}s/{len(rows)}")
    return True, "; ".join(details)


def fetch_window(
    role: str,
    d0: pd.Timestamp,
    d1: pd.Timestamp,
    mode: str,
    timeout: int,
    depth: int = 0,
    max_depth: int = 8,
    bands: list[int] | None = None,
) -> list[pd.DataFrame]:
    """Fetch one [d0, d1) window; retry with backoff, then split band-wise,
    then halve down to 1-hour granularity.

    Failure ladder (mirrors the endpoint's empirical behaviour):
      1. up to 3 attempts with increasing backoff (the endpoint is
         load-dependent -- identical queries pass or time out minutes apart);
      2. if the window still fails and TX is band-filtered, fall back to
         one query per band (the shape that passes reliably on TX);
      3. halve the window, down to 1-hour sub-windows, then raise --
         the caller collects failures instead of aborting the whole run.
    """
    sql = chunk_sql(role, d0, d1, mode, bands)
    rows: list | None = None
    last_exc: RuntimeError | None = None
    for attempt in range(3):
        if attempt:
            time.sleep((5, 20)[attempt - 1])  # load-dependent endpoint
        try:
            rows = ch_query(sql, timeout=timeout, retries=1)
            break
        except RuntimeError as exc:
            last_exc = exc
    if rows is None:
        assert last_exc is not None
        # band-wise fallback: TX combined queries time out on this endpoint
        if role == "tx" and bands and len(bands) > 1:
            print(f"    [band-split] {role} {d0.date()}..{d1.date()} -> one query per band")
            frames: list[pd.DataFrame] = []
            for band in bands:
                frames.extend(
                    fetch_window(role, d0, d1, mode, timeout, depth + 1, max_depth, [band])
                )
            return frames
        if (d1 - d0) <= timedelta(hours=1) or depth >= max_depth:
            raise RuntimeError(
                f"{role} {d0}..{d1} failed at 1-hour granularity: {last_exc}"
            ) from last_exc
        mid = d0 + (d1 - d0) / 2
        print(f"    [split] {role} {d0}..{d1} too slow -> halve at {mid}")
        return fetch_window(role, d0, mid, mode, timeout, depth + 1, max_depth, bands) + (
            fetch_window(role, mid, d1, mode, timeout, depth + 1, max_depth, bands)
        )
    if mode == "any":
        # rows: [callsign, [lat, lon]] -- unpack the tuple pair
        df = pd.DataFrame(
            {
                "callsign": [r[0] for r in rows],
                "lat": [r[1][0] if isinstance(r[1], (list, tuple)) else None for r in rows],
                "lon": [r[1][1] if isinstance(r[1], (list, tuple)) else None for r in rows],
            }
        )
    else:
        columns = ["callsign", "lat", "lon"] + (["last_seen"] if mode == "argmax" else [])
        df = pd.DataFrame(rows, columns=columns)
    df["chunk_seq"] = int(d0.timestamp())  # chronological merge key (epoch seconds)
    return [df]


# --------------------------------------------------------------------------- #
# Phase 1: verify (read-only probes; prints ALL problems, gates Phase 2)
# --------------------------------------------------------------------------- #
def verify(args: argparse.Namespace) -> tuple[bool, str]:
    """Phase 1 probes. Returns (all_ok, mode); mode is 'auto'-resolved."""
    problems: list[str] = []

    def check(ok: bool, label: str, detail: str, required: bool = True) -> None:
        mark = "OK  " if ok else ("FAIL" if required else "WARN")
        print(f"[{mark}] {label}: {detail}")
        if not ok and required:
            problems.append(label)

    print("=" * 78)
    print("Phase 1 (verify): stations_geo download preflight")
    print("=" * 78)

    # 1. API sanity (small aggregate)
    try:
        n = ch_query(
            "SELECT uniqExact(tx_sign) FROM wspr.rx "
            "WHERE time >= '2026-01-01 00:00:00' AND time < '2026-01-02 00:00:00' "
            "FORMAT JSONCompact",
            timeout=30,
            retries=3,
        )
        check(True, "API reachability", f"1-day unique TX = {n[0][0]:,}")
    except RuntimeError as exc:
        check(False, "API reachability", str(exc))

    # 2. DISTINCT feasibility probe (Phase-2 query shapes: TX single-band,
    #    RX combined, 1-day window)
    distinct_ok, distinct_msg = probe_distinct_day(args.probe_timeout, args.bands)
    if args.mode == "distinct":
        check(distinct_ok, "mode=distinct (forced)", distinct_msg)
        mode = "distinct"
    elif args.mode in ("argmax", "any"):
        check(True, f"mode={args.mode} (forced)", "DISTINCT probe skipped")
        mode = args.mode
    else:
        mode = "distinct" if distinct_ok else "any"
        check(True, "mode=auto", f"probe DISTINCT (1 day): {distinct_msg} -> mode = {mode}")

    # 3. First-chunk cost probe in the chosen mode (same band-wise TX shape
    #    as Phase 2, no halving -- capability check only)
    d0 = pd.Timestamp(args.start)
    probe_days = min(args.chunk_days, 7)
    d1 = d0 + timedelta(days=probe_days)
    started = time.time()
    try:
        rows = 0
        for subset in [[b] for b in args.bands] if args.bands else [None]:
            frames = fetch_window(
                "tx", d0, d1, mode, timeout=args.probe_timeout, max_depth=0, bands=subset
            )
            rows += sum(len(f) for f in frames)
        elapsed = time.time() - started
        span_days = (pd.Timestamp(args.end) - d0).days
        n_chunks = max(1, -(-span_days // args.chunk_days))
        # TX runs len(bands) queries + RX one combined per chunk
        tx_per_chunk = elapsed / probe_days * args.chunk_days
        est_min = n_chunks * tx_per_chunk * (1 + 1 / max(1, len(args.bands or [1]))) / 60
        check(
            elapsed < args.probe_timeout,
            "first-chunk probe",
            f"{d0.date()}..{d1.date()} ({mode}): {rows} rows in {elapsed:.1f}s; "
            f"~{n_chunks} chunks, rough estimate {est_min:.0f} min total",
        )
    except RuntimeError as exc:
        check(False, "first-chunk probe", str(exc))

    # 4. Output target
    check(OUT_PATH.parent.exists(), "output dir", str(OUT_PATH.parent))
    if OUT_PATH.exists():
        existing = len(pd.read_csv(OUT_PATH))
        print(f"       note: existing file has {existing} rows (will be overwritten in Phase 2)")

    print("-" * 78)
    if problems:
        print(f"Phase 1 FAILED: {len(problems)} problem(s): {', '.join(problems)}")
        print("Phase 2 (--apply) is blocked.")
        return False, mode
    print("Phase 1: all OK. Phase 2 plan:")
    print(f"  mode     : {mode}")
    print(f"  bands    : {args.bands or 'all'}")
    print(
        f"  period   : {args.start} .. {args.end} (chunk = {args.chunk_days} d, "
        f"adaptive halving on timeout)"
    )
    print(f"  output   : {OUT_PATH}")
    return True, mode


# --------------------------------------------------------------------------- #
# Phase 2: fetch, merge, write
# --------------------------------------------------------------------------- #
def part_path(role: str, d0: pd.Timestamp, d1: pd.Timestamp, subset: list[int] | None) -> Path:
    """Checkpoint file for one task (atomic tmp+rename on write)."""
    bandkey = "all" if not subset else "-".join(str(b) for b in subset)
    return PARTS_DIR / f"{role}_{d0:%Y%m%dT%H%M}_{d1:%Y%m%dT%H%M}_b{bandkey}.csv"


def fetch_part(
    role: str,
    d0: pd.Timestamp,
    d1: pd.Timestamp,
    mode: str,
    timeout: int,
    subset: list[int] | None,
) -> int:
    """Fetch one task and checkpoint it; returns the row count."""
    frames = fetch_window(role, d0, d1, mode, timeout=timeout, bands=subset)
    if frames:
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.DataFrame(columns=["callsign", "lat", "lon", "chunk_seq"])
    path = part_path(role, d0, d1, subset)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(df.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    tmp.replace(path)
    return len(df)


def apply(args: argparse.Namespace, mode: str) -> None:
    print("=" * 78)
    print(f"Phase 2 (apply): downloading station coordinates (mode={mode})")
    print("=" * 78)

    start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
    # TX: one query per band (combined TX queries time out on this endpoint);
    # RX: single combined band-filtered query (answers in ~0.3 s)
    band_sets: dict[str, list[list[int] | None]] = {
        "tx": [[b] for b in args.bands] if args.bands else [None],
        "rx": [args.bands],
    }
    role_frames: dict[str, pd.DataFrame] = {}
    if args.clean and PARTS_DIR.exists():
        for p in PARTS_DIR.glob("*.csv"):
            p.unlink()
        print(f"[clean] removed checkpoints in {PARTS_DIR}")

    # task list = (role, d0, d1, band subset) for every chunk; each completed
    # task is checkpointed to its own part file, so an interrupted run
    # resumes by simply re-running the same command
    tasks: list[tuple[str, pd.Timestamp, pd.Timestamp, list[int] | None]] = []
    d0 = start
    while d0 < end:
        d1 = min(d0 + timedelta(days=args.chunk_days), end)
        for role in ROLES:
            for subset in band_sets[role]:
                tasks.append((role, d0, d1, subset))
        d0 = d1

    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    pending = [t for t in tasks if not part_path(*t).exists()]
    print(
        f"tasks: {len(tasks)} total, {len(tasks) - len(pending)} checkpointed, "
        f"{len(pending)} to fetch (jobs={args.jobs})",
        flush=True,
    )

    failed: list[tuple[str, pd.Timestamp, pd.Timestamp, list[int] | None]] = []
    t_all = time.time()
    if pending:
        # bounded parallelism: every task writes its own part file, so the
        # threads share no state (Phase-1 concurrent probes hit no rate limit)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futs = {
                pool.submit(fetch_part, r, a, b, mode, args.chunk_timeout, s): (r, a, b, s)
                for (r, a, b, s) in pending
            }
            n_done = 0
            for fut in as_completed(futs):
                task = futs[fut]
                n_done += 1
                try:
                    n = fut.result()
                    tag = "ok"
                except Exception as exc:  # noqa: BLE001 -- keep other tasks alive
                    failed.append(task)
                    n = 0
                    tag = f"FAIL: {type(exc).__name__}: {exc}"
                print(
                    f"  [{n_done}/{len(pending)}] {tag} {task[0]} {task[1].date()}.."
                    f"{task[2].date()} b={task[3]} -> {n} rows "
                    f"({time.time() - t_all:.0f}s elapsed)",
                    flush=True,
                )

    # retry passes (sequential, longer patience) -- endpoint load usually clears
    for pass_i in range(2):
        if not failed:
            break
        print("-" * 78, flush=True)
        print(f"retry pass {pass_i + 1}: {len(failed)} failed task(s)", flush=True)
        still: list[tuple[str, pd.Timestamp, pd.Timestamp, list[int] | None]] = []
        for task in failed:
            time.sleep(5)
            try:
                n = fetch_part(task[0], task[1], task[2], mode, args.chunk_timeout, task[3])
                print(f"    [OK] {task[0]} {task[1]}..{task[2]} b={task[3]} -> {n}", flush=True)
            except Exception as exc:  # noqa: BLE001 -- keep retrying the rest
                print(f"    [FAIL] {type(exc).__name__}: {exc}", flush=True)
                still.append(task)
        failed = still
    if failed:
        print(
            "WARNING: "
            f"{len(failed)} task(s) still failed -- coverage gaps in stations_geo.csv: "
            + ", ".join(f"{r} {a}..{b} b={s}" for r, a, b, s in failed),
            flush=True,
        )

    # assemble from part files in TASK ORDER (chronological; per chunk tx band
    # subsets come before rx -- preserves the merge semantics documented above)
    for role in ROLES:
        parts = [
            pd.read_csv(part_path(r, a, b, s))
            for (r, a, b, s) in tasks
            if r == role and part_path(r, a, b, s).exists()
        ]
        if not parts:
            raise RuntimeError(f"no checkpoint data for role={role}")
        role_frames[role] = pd.concat(parts, ignore_index=True)

    # merge TX + RX: chronological chunks, later record wins per callsign;
    # within one chunk RX rows follow TX rows (stable sort keeps that order,
    # keep='last' therefore prefers the RX coordinate on ties)
    combined = pd.concat([role_frames["tx"], role_frames["rx"]], ignore_index=True)
    combined = combined.dropna(subset=["lat", "lon"])
    combined = combined.sort_values(["callsign", "chunk_seq"], kind="stable")
    sizes = combined.groupby("callsign").size()
    n_multi = int((sizes > 1).sum())
    merged = combined.drop_duplicates("callsign", keep="last")

    ref = merged[["callsign", "lat", "lon"]].copy()
    ref["lat"] = ref["lat"].astype(float).round(6)
    ref["lon"] = ref["lon"].astype(float).round(6)
    n_bad = int((~(ref["lat"].between(-90, 90) & ref["lon"].between(-180, 180))).sum())
    ref = ref[ref["lat"].between(-90, 90) & ref["lon"].between(-180, 180)]
    ref = ref.sort_values("callsign").reset_index(drop=True)

    tx_set = set(role_frames["tx"]["callsign"])
    rx_set = set(role_frames["rx"]["callsign"])
    both = len(tx_set & rx_set)

    print("-" * 78)
    print(f"unique callsigns : {len(ref):,}")
    print(f"  TX only        : {len(tx_set - rx_set):,}")
    print(f"  RX only        : {len(rx_set - tx_set):,}")
    print(f"  both TX and RX : {both:,}")
    print(f"  re-resolved    : {n_multi:,} callsigns seen more than once (kept most recent record)")
    if n_bad:
        print(f"  dropped        : {n_bad} rows with out-of-range coordinates")
    print(
        f"  coord range     : lat [{ref['lat'].min():.4f}, {ref['lat'].max():.4f}], "
        f"lon [{ref['lon'].min():.4f}, {ref['lon'].max():.4f}]"
    )

    # single write at the end (two-phase lesson): LF endings, trailing newline
    csv_text = ref.to_csv(index=False, lineterminator="\n")
    OUT_PATH.write_bytes(csv_text.encode("utf-8"))
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"\nWrote {OUT_PATH} ({size_kb:.0f} KiB, sha256={digest[:16]}...)")
    if not failed:
        for p in PARTS_DIR.glob("*.csv"):
            p.unlink()
        PARTS_DIR.rmdir()
        print(f"checkpoints cleared ({PARTS_DIR})")
    else:
        print(
            f"checkpoints kept in {PARTS_DIR} -- re-run --apply to retry the "
            "failed tasks only (--clean starts from scratch)"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="run Phase 2 (without this flag only probes run)"
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "distinct", "argmax", "any"],
        default="auto",
        help="query strategy (default auto: probe DISTINCT, fall back to any(tuple))",
    )
    parser.add_argument(
        "--bands",
        type=int,
        nargs="+",
        default=[7, 14, 21],
        help="band indices to scan (default 7 14 21 = 40m/20m/15m; "
        "wider scans need smaller --chunk-days)",
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START,
        help="coverage window start, inclusive (default %(default)s)",
    )
    parser.add_argument(
        "--end", default=DEFAULT_END, help="coverage window end, exclusive (default %(default)s)"
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=1,
        help="window size in days (default 1: the endpoint times out on >=2-day "
        "DISTINCT windows; larger values rely on adaptive halving)",
    )
    parser.add_argument(
        "--probe-timeout", type=int, default=45, help="client timeout for Phase-1 probes, seconds"
    )
    parser.add_argument(
        "--chunk-timeout",
        type=int,
        default=60,
        help="client timeout for Phase-2 chunk fetches, seconds",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="parallel query threads in Phase 2 (checkpoints make threads "
        "independent; lower this if the endpoint starts rate-limiting)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="discard part-file checkpoints and refetch everything",
    )
    args = parser.parse_args()

    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be after --start")

    ok, mode = verify(args)
    if not ok:
        return 1
    if not args.apply:
        print("\nPhase 1 passed. Re-run with --apply to execute Phase 2.")
        return 0
    apply(args, mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
