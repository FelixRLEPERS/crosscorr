"""Spatial resolution of the storm/quiet WSPR contrast: great-circle midpoint.

Audit 1.5.0 / Task 1 (spatial): does the storm-time drop depend on WHERE the
great-circle midpoint sits -- auroral (>60 deg), mid-latitude (30-60) or
low-latitude (<30) paths?

Two-phase (verify -> apply) per AGENTS.md:

    python scripts/spatial_analysis.py            # Phase 1: verify, read-only
    python scripts/spatial_analysis.py --apply    # Phase 2: compute + write

Sources (--source)
------------------
api (default)
    Hourly spot counts binned by |great-circle midpoint latitude|, aggregated
    server-side on db1.wspr.live (ClickHouse). The SQL expression mirrors the
    local vector/haversine midpoint exactly; Phase 1 cross-checks SQL bins
    against locally computed bins for a sample of spots joined with
    data/processed/stations_geo.csv (so the local reference is exercised, not
    bypassed silently). Rationale for server-side binning: pair-level dumps
    (GROUP BY hour, tx_sign, rx_sign) do not answer within 300 s even for a
    single day on this public endpoint, while the binned aggregation answers
    in <1 s per day -- months of data are feasible only this way.
local
    Raw spot CSVs data/raw/wspr/wspr_YYYY-MM-DD_<band>.csv joined with
    stations_geo.csv on tx_call/rx_call, midpoint computed locally.
    NOTE: local spot files are truncated at 100k rows (~1.4 h of one day),
    so local mode validates the pipeline but cannot support storm/quiet
    statistics on its own.

Statistic (identical definitions to scripts/perm_test_18mo_3band.py)
---------------------------------------------------------------------
* epochs: 3-hourly (Kp cadence), inner join on Kp hours;
* drop% = 100 * (mean_storm - mean_quiet) / mean_quiet on RAW hourly counts;
* p     = two-sided block permutation (24-epoch blocks, add-one correction)
  over month x hour-of-day x day-of-week residuals;
* BH-FDR across the three latitude groups.

Outputs: results/spatial_lat_groups.json (+ tables on stdout).
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
WSPR_API = "http://db1.wspr.live/"
HEADERS = {"User-Agent": "ionosphere-research/1.0"}
STATIONS_PATH = ROOT / "data" / "processed" / "stations_geo.csv"
UNIFIED_PATH = ROOT / "data" / "processed" / "unified.parquet"
RAW_SPOTS_DIR = ROOT / "data" / "raw" / "wspr"
OUT_JSON = ROOT / "results" / "spatial_lat_groups.json"

BAND_IDX = {7: "40m", 14: "20m", 21: "15m"}
GROUPS = ("high", "mid", "low")
GROUP_LABEL = {
    "high": "High-lat (>60, auroral)",
    "mid": "Mid-lat (30-60)",
    "low": "Low-lat (<30)",
}
RETRY_BACKOFF = (5, 15, 30)
HTTP_TIMEOUT = 240


# --------------------------------------------------------------------------- #
# Great-circle midpoint (two implementations that must agree)
# --------------------------------------------------------------------------- #
def mid_lat_deg(tx_lat, tx_lon, rx_lat, rx_lon) -> np.ndarray:
    """Midpoint latitude (deg) of the great-circle arc TX -> RX.

    Vector (haversine-equivalent) formula: for unit vectors v1, v2 the
    midpoint direction is v1 + v2, so lat_mid = asin((v1_z + v2_z) / |v1+v2|).
    pyproj is intentionally not required (pure numpy).
    """
    lat1, lon1, lat2, lon2 = (
        np.radians(np.asarray(x, dtype=float)) for x in (tx_lat, tx_lon, rx_lat, rx_lon)
    )
    vx = np.cos(lat1) + np.cos(lat2) * np.cos(lon2 - lon1)
    vy = np.cos(lat2) * np.sin(lon2 - lon1)
    vz = np.sin(lat1) + np.sin(lat2)
    norm = np.sqrt(vx * vx + vy * vy + vz * vz)
    ratio = np.where(norm > 0, vz / np.where(norm > 0, norm, 1.0), 0.0)
    return np.degrees(np.arcsin(np.clip(ratio, -1.0, 1.0)))


def _mid_lat_sql(columns: tuple[str, ...] = ("lat1", "lon1", "lat2", "lon2")) -> str:
    """Same formula in ClickHouse SQL over the given radian column aliases."""
    lat1, lon1, lat2, lon2 = columns
    vz = f"(sin({lat1}) + sin({lat2}))"
    vx = f"(cos({lat1}) + cos({lat2}) * cos({lon2} - {lon1}))"
    vy = f"(cos({lat2}) * sin({lon2} - {lon1}))"
    norm = f"sqrt({vx} * {vx} + {vy} * {vy} + {vz} * {vz})"
    return f"degrees(asin(least(1.0, greatest(-1.0, {vz} / {norm}))))"


def _latbin_sql(expr: str) -> str:
    """multiIf wrapper: bins on |midpoint latitude| (auroral zones are NH+SH).

    Boundaries match bin_series(): >60 high, 30-60 mid, <30 low.
    """
    return f"multiIf(abs({expr}) > 60, 'high', abs({expr}) >= 30, 'mid', 'low')"


def bin_series(lat_deg: np.ndarray) -> np.ndarray:
    """Vector lat -> group label; boundaries: >60 high, 30-60 mid, <30 low."""
    a = np.abs(np.asarray(lat_deg, dtype=float))
    return np.select([a > 60, a >= 30], ["high", "mid"], default="low")


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def ch_query(sql: str, timeout: int = HTTP_TIMEOUT, retries: int = 3) -> list:
    """GET a SQL query against db1.wspr.live with backoff retries."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(WSPR_API, params={"query": sql}, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("data", [])
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries - 1:
                backoff = RETRY_BACKOFF[attempt]
                print(
                    f"  [retry {attempt + 1}/{retries}] {type(exc).__name__}: {exc}; "
                    f"sleep {backoff}s"
                )
                time.sleep(backoff)
    raise RuntimeError(f"wspr.live query failed after {retries} attempts: {last_error}")


# --------------------------------------------------------------------------- #
# Phase 1: verify (read-only, prints ALL problems, gates Phase 2)
# --------------------------------------------------------------------------- #
def verify(args: argparse.Namespace) -> bool:
    problems: list[str] = []

    def check(ok: bool, label: str, detail: str, required: bool = True) -> None:
        mark = "OK  " if ok else ("FAIL" if required else "WARN")
        print(f"[{mark}] {label}: {detail}")
        if not ok and required:
            problems.append(label)

    print("=" * 78)
    print("Phase 1 (verify): spatial analysis preflight")
    print("=" * 78)

    # 1. stations reference
    stations = pd.DataFrame()
    if STATIONS_PATH.exists():
        stations = pd.read_csv(STATIONS_PATH)
        cols_ok = list(stations.columns) == ["callsign", "lat", "lon"]
        check(cols_ok, "stations_geo schema", f"columns={list(stations.columns)}")
        if cols_ok:
            dup = int(stations["callsign"].duplicated().sum())
            lat_ok = stations["lat"].between(-90, 90).all()
            lon_ok = stations["lon"].between(-180, 180).all()
            check(
                dup == 0,
                "stations_geo uniqueness",
                f"{len(stations)} rows, duplicate callsigns={dup}",
            )
            check(
                bool(lat_ok and lon_ok),
                "stations_geo ranges",
                f"lat[{stations['lat'].min():.3f},{stations['lat'].max():.3f}] "
                f"lon[{stations['lon'].min():.3f},{stations['lon'].max():.3f}]",
            )
    else:
        check(
            False,
            "stations_geo",
            f"missing: {STATIONS_PATH} (run data/scripts/download_stations_geo.py first)",
        )

    # 2. Kp coverage for the requested window (Kp cadence is 3-hourly --
    #    compare against 3-hourly epochs, not hourly, or coverage caps at 33%)
    kp_ok = False
    if UNIFIED_PATH.exists():
        unified = pd.read_parquet(UNIFIED_PATH, columns=["timestamp_utc", "detector_type", "value"])
        kp = unified[unified["detector_type"] == "kp"]
        kp_win = kp[
            (kp["timestamp_utc"].dt.tz_convert(None) >= args.start)
            & (kp["timestamp_utc"].dt.tz_convert(None) < args.end)
        ]
        kp_hours = pd.DatetimeIndex(
            kp_win["timestamp_utc"].dt.tz_convert(None).dt.floor("1h")
        ).unique()
        want = pd.date_range(args.start, args.end, freq="3h", inclusive="left")
        cover = len(want.intersection(kp_hours)) / max(len(want), 1)
        n_storm = int((kp_win["value"] >= 5).sum())
        n_quiet = int((kp_win["value"] < 3).sum())
        kp_ok = cover > 0.9 and n_storm >= 10
        check(
            kp_ok,
            "Kp coverage",
            f"{args.start}..{args.end}: coverage={cover:.1%}, "
            f"storm_hours={n_storm}, quiet_hours={n_quiet}",
        )
    else:
        check(False, "unified.parquet", f"missing: {UNIFIED_PATH}")

    # 3. local spot files (informational for --source local)
    local_files = (
        sorted(p for p in RAW_SPOTS_DIR.glob("wspr_*.csv") if "hourly" not in p.name)
        if RAW_SPOTS_DIR.exists()
        else []
    )
    check(
        bool(local_files),
        "local spot CSVs",
        f"{len(local_files)} files in {RAW_SPOTS_DIR}",
        required=args.source == "local",
    )

    # 4. API: sample spots with coordinates, cross-check three ways
    if args.source == "api" and len(stations) > 0:
        t0 = pd.Timestamp(args.start) + pd.Timedelta(hours=args.sample_hour)
        t1 = t0 + pd.Timedelta(hours=1)
        raw_cols = (
            "radians(tx_lat) AS lat1, radians(tx_lon) AS lon1, "
            "radians(rx_lat) AS lat2, radians(rx_lon) AS lon2"
        )
        bands = ",".join(str(b) for b in args.bands)
        sample_sql = (
            "SELECT tx_sign, rx_sign, tx_lat, tx_lon, rx_lat, rx_lon, "
            f"{_latbin_sql(_mid_lat_sql())} AS sql_bin "
            "FROM (SELECT tx_sign, rx_sign, tx_lat, tx_lon, rx_lat, rx_lon, "
            f"{raw_cols} FROM wspr.rx WHERE time >= '{t0}' AND time < '{t1}' "
            f"AND band IN ({bands}) ORDER BY id LIMIT {args.sample_n}) "
            "FORMAT JSONCompact"
        )
        if getattr(args, "skip_crosscheck", False):
            rows = []
            check(
                True,
                "API reachability",
                "SKIPPED (--skip-crosscheck): heavy sample deferred; Phase 2 unaffected",
            )
        else:
            try:
                rows = ch_query(sample_sql, timeout=60)
                check(
                    True,
                    "API reachability",
                    f"sampled {len(rows)} spots for {t0} (1 h window)",
                )
            except RuntimeError as exc:
                rows = []
                check(False, "API reachability", str(exc))

        if rows:
            sample = pd.DataFrame(
                rows,
                columns=["tx_sign", "rx_sign", "tx_lat", "tx_lon", "rx_lat", "rx_lon", "sql_bin"],
            )
            # (a) SQL bin vs local formula on SERVER coords -- pure math check
            py_server = bin_series(
                mid_lat_deg(sample["tx_lat"], sample["tx_lon"], sample["rx_lat"], sample["rx_lon"])
            )
            agree_math = float((py_server == sample["sql_bin"].values).mean())
            check(
                agree_math >= 0.999,
                "SQL bin vs local haversine (server coords)",
                f"agreement={agree_math:.4%} on {len(sample)} spots",
            )

            # (b) full local pipeline: join stations_geo.csv + local formula
            ref = stations.drop_duplicates("callsign").set_index("callsign")
            sample = sample.join(ref, on="tx_sign", rsuffix="_tx_ref")
            sample = sample.join(ref, on="rx_sign", rsuffix="_rx_ref")
            have_tx = sample["lat"].notna()
            have_rx = (
                sample["lat_rx_ref"].notna() if "lat_rx_ref" in sample else sample["lat"].notna()
            )
            coverage = float((have_tx & have_rx).mean())
            check(
                coverage >= 0.90,
                "stations_geo coverage of sampled spots",
                f"both endpoints found={coverage:.2%}",
            )

            both = sample[have_tx & have_rx]
            if len(both):
                coord_match = float(
                    (
                        np.isclose(both["tx_lat"], both["lat"], atol=1e-3)
                        & np.isclose(both["tx_lon"], both["lon"], atol=1e-3)
                        & np.isclose(both["rx_lat"], both["lat_rx_ref"], atol=1e-3)
                        & np.isclose(both["rx_lon"], both["lon_rx_ref"], atol=1e-3)
                    ).mean()
                )
                py_ref = bin_series(
                    mid_lat_deg(both["lat"], both["lon"], both["lat_rx_ref"], both["lon_rx_ref"])
                )
                agree_ref = float((py_ref == both["sql_bin"].values).mean())
                check(
                    agree_ref >= 0.95,
                    "stations_geo join + haversine vs SQL bin",
                    f"agreement={agree_ref:.2%}, raw coord match={coord_match:.2%} "
                    "(mismatch = callsign with multiple historic coordinates)",
                )

            # (c) server-side binned totals for the same hour must equal count()
            hour_sql = (
                f"SELECT count() AS n FROM wspr.rx WHERE time >= '{t0}' "
                f"AND time < '{t1}' AND band IN ({bands}) FORMAT JSONCompact"
            )
            try:
                n_all = int(ch_query(hour_sql, timeout=60)[0][0])
                lat_mid = _mid_lat_sql(
                    ("radians(tx_lat)", "radians(tx_lon)", "radians(rx_lat)", "radians(rx_lon)")
                )
                bin_sql = (
                    "SELECT sum(spots) AS n FROM ("
                    "SELECT count() AS spots FROM wspr.rx "
                    f"WHERE time >= '{t0}' AND time < '{t1}' AND band IN ({bands}) "
                    f"GROUP BY {_latbin_sql(lat_mid)}) FORMAT JSONCompact"
                )
                n_binned = int(ch_query(bin_sql, timeout=60)[0][0])
                check(
                    n_all == n_binned,
                    "latbin aggregation loses no spots",
                    f"count()={n_all}, binned={n_binned}",
                )
            except (RuntimeError, IndexError, TypeError) as exc:
                check(False, "latbin aggregation consistency", str(exc))

    print("-" * 78)
    if problems:
        print(f"Phase 1 FAILED: {len(problems)} problem(s): {', '.join(problems)}")
        print("Phase 2 (--apply) is blocked. Fix the problems above and rerun.")
        return False
    print("Phase 1: all OK. Phase 2 plan:")
    print(f"  period   : {args.start} .. {args.end} (UTC, exclusive end)")
    print(f"  bands    : {[BAND_IDX.get(b, str(b)) for b in args.bands]}")
    print(f"  source   : {args.source}")
    print("  groups   : |mid lat| > 60 high / 30-60 mid / < 30 low")
    print(
        f"  test     : block permutation, block={args.block}, "
        f"n_iter={args.n_iter}, seed={args.seed}"
    )
    print(f"  output   : {OUT_JSON}")
    return True


# --------------------------------------------------------------------------- #
# Phase 2: data loading
# --------------------------------------------------------------------------- #
def fetch_counts_api(args: argparse.Namespace) -> pd.DataFrame:
    """Hourly spot counts per (band, latbin) from db1.wspr.live, chunked."""
    bands = ",".join(str(b) for b in args.bands)
    lat_mid = _mid_lat_sql(
        ("radians(tx_lat)", "radians(tx_lon)", "radians(rx_lat)", "radians(rx_lon)")
    )
    parts: list[pd.DataFrame] = []
    d0 = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    chunk = timedelta(days=args.chunk_days)
    n_chunks = int(np.ceil((end - d0) / chunk))
    for i in range(n_chunks):
        d1 = min(d0 + chunk, end)
        sql = (
            "SELECT toStartOfHour(time) AS hour, band, "
            f"{_latbin_sql(lat_mid)} AS latbin, count() AS spots "
            "FROM wspr.rx WHERE time >= "
            f"'{d0}' AND time < '{d1}' AND band IN ({bands}) "
            "GROUP BY hour, band, latbin ORDER BY hour, band, latbin FORMAT JSONCompact"
        )
        t0 = time.time()
        rows = ch_query(sql)
        print(
            f"  chunk {i + 1}/{n_chunks} {d0.date()}..{d1.date()}: "
            f"{len(rows)} rows in {time.time() - t0:.1f}s"
        )
        if rows:
            parts.append(pd.DataFrame(rows, columns=["hour", "band", "latbin", "spots"]))
        d0 = d1
    if not parts:
        raise RuntimeError("no data returned for the requested period")
    out = pd.concat(parts, ignore_index=True)
    out["hour"] = pd.to_datetime(out["hour"])
    out["band"] = out["band"].astype(int)
    out["spots"] = out["spots"].astype(int)
    return out


def load_counts_local(args: argparse.Namespace) -> pd.DataFrame:
    """Local spot CSVs -> join stations_geo.csv -> local haversine midpoint."""
    if not STATIONS_PATH.exists():
        raise RuntimeError(f"missing {STATIONS_PATH}; run download_stations_geo.py")
    stations = pd.read_csv(STATIONS_PATH).drop_duplicates("callsign")
    tx = stations.rename(columns={"callsign": "tx_call", "lat": "tx_lat", "lon": "tx_lon"})
    rx = stations.rename(columns={"callsign": "rx_call", "lat": "rx_lat", "lon": "rx_lon"})

    files = sorted(p for p in RAW_SPOTS_DIR.glob("wspr_*.csv") if "hourly" not in p.name)
    if not files:
        raise RuntimeError(f"no spot CSVs in {RAW_SPOTS_DIR}")
    frames = []
    for path in files:
        df = pd.read_csv(path, usecols=["timestamp", "tx_call", "rx_call", "band"])
        frames.append(df)
    spots = pd.concat(frames, ignore_index=True)
    spots["hour"] = pd.to_datetime(spots["timestamp"], utc=True, errors="coerce").dt.tz_convert(
        None
    )
    spots = spots.dropna(subset=["hour"])
    spots = spots[(spots["hour"] >= args.start) & (spots["hour"] < args.end)]
    if args.bands:
        spots = spots[spots["band"].isin(args.bands)]
    if spots.empty:
        raise RuntimeError("no local spots inside the requested period/bands")

    n_before = len(spots)
    spots = spots.merge(tx, on="tx_call", how="inner").merge(rx, on="rx_call", how="inner")
    frac = len(spots) / n_before if n_before else 0.0
    print(f"  local join: {len(spots)}/{n_before} ({frac:.1%}) spots with both endpoints located")
    if frac < 0.90:
        print("  WARN: <90% of spots have both endpoints located. Check stations_geo.csv coverage.")
    spots = spots.dropna(subset=["tx_lat", "tx_lon", "rx_lat", "rx_lon"])
    spots["latbin"] = bin_series(
        mid_lat_deg(spots["tx_lat"], spots["tx_lon"], spots["rx_lat"], spots["rx_lon"])
    )
    counts = (
        spots.groupby([spots["hour"].dt.floor("1h"), "band", "latbin"], as_index=False)
        .size()
        .rename(columns={"size": "spots"})
    )
    return counts


# --------------------------------------------------------------------------- #
# Phase 2: statistics
# --------------------------------------------------------------------------- #
def load_kp(args: argparse.Namespace) -> pd.DataFrame:
    unified = pd.read_parquet(UNIFIED_PATH, columns=["timestamp_utc", "detector_type", "value"])
    kp = unified[unified["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp["hour"] = kp["timestamp_utc"].dt.tz_convert(None).dt.floor("1h")
    kp = kp[(kp["hour"] >= args.start) & (kp["hour"] < args.end)]
    return kp[["hour", "value"]].rename(columns={"value": "kp"}).drop_duplicates("hour")


def block_perm_test(
    merged: pd.DataFrame, block_size: int, n_iter: int, rng: np.random.Generator
) -> tuple[float, float] | None:
    """Two-sided block permutation on month x hod x dow residuals (paper sec 3.3)."""
    merged = merged.copy()
    merged["resid"] = merged["value"] - merged.groupby(["month", "hour_of_day", "day_of_week"])[
        "value"
    ].transform("mean")
    storm = (merged["kp"] >= 5).values
    quiet = (merged["kp"] < 3).values
    if storm.sum() < 3 or quiet.sum() < 10:
        return None
    resid = merged["resid"].values
    kp_vals = merged["kp"].values
    obs = float(resid[storm].mean() - resid[quiet].mean())

    n = len(resid)
    n_blocks = n // block_size
    if n_blocks < 2:
        return None
    rblocks = resid[: n_blocks * block_size].reshape(n_blocks, block_size)
    kp_use = kp_vals[: n_blocks * block_size]
    stats = np.empty(n_iter)
    for i in range(n_iter):
        order = rng.permutation(n_blocks)
        rp = rblocks[order].ravel()
        s = kp_use >= 5
        q = kp_use < 3
        stats[i] = rp[s].mean() - rp[q].mean() if s.any() and q.any() else 0.0
    # add-one (Davison-Hinkley): a Monte-Carlo p is never exactly 0
    p = float((1 + (np.abs(stats) >= abs(obs)).sum()) / (1 + n_iter))
    return obs, p


def bh_fdr(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values (q), preserving input order."""
    n = len(pvals)
    arr = np.asarray(pvals, dtype=float)
    order = np.argsort(arr)
    ranked = arr[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(ranked, 1.0)
    return out.tolist()


def analyze_group(
    series: pd.DataFrame, kp: pd.DataFrame, args: argparse.Namespace, rng: np.random.Generator
) -> dict | None:
    """series: columns [hour, value] (raw counts, contiguous, zero-filled)."""
    merged = pd.merge(series, kp, on="hour", how="inner")
    merged = merged.sort_values("hour").reset_index(drop=True)
    merged["month"] = merged["hour"].dt.to_period("M")
    merged["hour_of_day"] = merged["hour"].dt.hour
    merged["day_of_week"] = merged["hour"].dt.dayofweek

    storm = merged["kp"] >= 5
    quiet = merged["kp"] < 3
    if storm.sum() < 3 or quiet.sum() < 10:
        return None
    storm_mean = float(merged.loc[storm, "value"].mean())
    quiet_mean = float(merged.loc[quiet, "value"].mean())
    drop_pct = 100.0 * (storm_mean - quiet_mean) / quiet_mean if quiet_mean else float("nan")
    test = block_perm_test(merged, args.block, args.n_iter, rng)
    if test is None:
        return None
    obs, p_value = test
    return {
        "n_epochs": int(len(merged)),
        "n_storm": int(storm.sum()),
        "n_quiet": int(quiet.sum()),
        "storm_mean": round(storm_mean, 1),
        "quiet_mean": round(quiet_mean, 1),
        "delta_resid": round(obs, 1),
        "drop_pct": round(drop_pct, 1),
        "p_value": round(p_value, 8),
    }


def build_group_series(
    counts: pd.DataFrame, args: argparse.Namespace, band_filter: int | None = None
) -> dict[str, pd.DataFrame]:
    """Counts -> zero-filled hourly series per latitude group (summed over bands).

    Hours absent from the counts table entirely are network outages and are
    NOT zero-filled: only hours where at least one group reported spots enter
    the series (a missing group within a reported hour means 0 spots there).
    """
    if band_filter is not None:
        counts = counts[counts["band"] == band_filter]
    if counts.empty:
        raise RuntimeError("no counts left after band filter")
    hours = pd.DatetimeIndex(sorted(counts["hour"].unique()))
    out: dict[str, pd.DataFrame] = {}
    for g in GROUPS:
        sub = counts[counts["latbin"] == g]
        s = sub.groupby("hour")["spots"].sum().reindex(hours, fill_value=0)
        out[g] = pd.DataFrame({"hour": hours, "value": s.values.astype(float)})
    return out


def run_stats(
    series_by_group: dict[str, pd.DataFrame],
    kp: pd.DataFrame,
    args: argparse.Namespace,
    rng: np.random.Generator,
) -> dict[str, dict]:
    results = {}
    for g in GROUPS:
        res = analyze_group(series_by_group[g], kp, args, rng)
        results[g] = (
            res
            if res is not None
            else {
                "n_epochs": 0,
                "n_storm": 0,
                "n_quiet": 0,
                "storm_mean": None,
                "quiet_mean": None,
                "delta_resid": None,
                "drop_pct": None,
                "p_value": None,
            }
        )
    valid = [r["p_value"] for r in results.values() if r["p_value"] is not None]
    if len(valid) == len(results):
        qvals = bh_fdr(valid)
        for g, q in zip(GROUPS, qvals, strict=True):
            results[g]["q_fdr"] = round(q, 8)
    return results


def print_table(results: dict[str, dict], title: str) -> None:
    print()
    print(title)
    print("-" * 62)
    print(f"{'Group':<26} {'N_storm':>8} {'Drop%':>9} {'p-value':>12} {'q(BH)':>10}")
    for g in GROUPS:
        r = results[g]
        p = f"{r['p_value']:.2e}" if r["p_value"] is not None else "n/a"
        q = f"{r.get('q_fdr', float('nan')):.2e}" if r.get("q_fdr") is not None else "n/a"
        drop = f"{r['drop_pct']:+.1f}" if r["drop_pct"] is not None else "n/a"
        print(f"{GROUP_LABEL[g]:<26} {r['n_storm']:>8} {drop:>9} {p:>12} {q:>10}")


# --------------------------------------------------------------------------- #
# Phase 2 entry point
# --------------------------------------------------------------------------- #
def apply(args: argparse.Namespace) -> None:
    rng = np.random.default_rng(args.seed)

    print("=" * 78)
    print("Phase 2 (apply): spatial storm/quiet analysis")
    print("=" * 78)

    if args.source == "api":
        print("Fetching hourly counts binned by midpoint latitude from wspr.live ...")
        counts = fetch_counts_api(args)
    else:
        print("Loading local spot CSVs + stations_geo.csv join ...")
        counts = load_counts_local(args)
    kp = load_kp(args)
    if kp.empty:
        raise RuntimeError(f"no Kp rows in {args.start}..{args.end} (unified.parquet)")
    total = int(counts["spots"].sum())
    print(
        f"Total spots: {total:,} in {counts['hour'].nunique()} hours, "
        f"bands={sorted(counts['band'].unique())}"
    )

    headline = run_stats(build_group_series(counts, args), kp, args, rng)
    print_table(headline, f"Heading table (bands pooled): {args.start} .. {args.end}")

    per_band: dict[str, dict] = {}
    for band in sorted(counts["band"].unique()):
        band_name = BAND_IDX.get(band, str(band))
        res = run_stats(build_group_series(counts, args, band_filter=band), kp, args, rng)
        per_band[band_name] = res
        print_table(res, f"Per-band: {band_name}")

    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period": {"start": args.start, "end": args.end},
        "bands": [BAND_IDX.get(b, str(b)) for b in sorted(counts["band"].unique())],
        "source": args.source,
        "n_spots_total": total,
        "params": {
            "block": args.block,
            "n_iter": args.n_iter,
            "seed": args.seed,
            "epoch_cadence": "3h (Kp)",
            "storm": "Kp >= 5",
            "quiet": "Kp < 3",
            "groups": "|midpoint lat| > 60 high / 30-60 mid / < 30 low",
        },
        "pooled": headline,
        "per_band": per_band,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="run Phase 2 (without this flag only verify runs)"
    )
    parser.add_argument(
        "--source",
        choices=["api", "local"],
        default="api",
        help="api = server-side latbin aggregation (default); "
        "local = spot CSVs + stations_geo.csv join",
    )
    parser.add_argument("--start", default="2024-04-01", help="period start (UTC, inclusive)")
    parser.add_argument("--end", default="2025-10-01", help="period end (UTC, exclusive)")
    parser.add_argument(
        "--bands",
        type=int,
        nargs="+",
        default=[7, 14, 21],
        help="band indices (default 7 14 21 = 40m/20m/15m)",
    )
    parser.add_argument("--chunk-days", type=int, default=14, help="API fetch chunk size in days")
    parser.add_argument("--block", type=int, default=24, help="permutation block size (epochs)")
    parser.add_argument("--n-iter", type=int, default=20000, help="permutation iterations")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument(
        "--sample-n", type=int, default=5000, help="Phase-1 API sample size (spots)"
    )
    parser.add_argument(
        "--sample-hour", type=int, default=0, help="Phase-1 sample window: hour offset from --start"
    )
    parser.add_argument(
        "--skip-crosscheck",
        action="store_true",
        help="skip heavy Phase-1 API cross-check (ORDER BY id LIMIT 5000 + radians); "
        "Phase 2 is unaffected. Use when the public endpoint exceeds budget on the sample.",
    )
    args = parser.parse_args()

    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be after --start")

    if not verify(args):
        return 1
    if not args.apply:
        print("\nPhase 1 passed. Re-run with --apply to execute Phase 2.")
        return 0
    apply(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
