"""Training-period WSPR live download: 2026-10-13, 18 months x 3 bands.

Finding HELDOUT-LIVE-REVISION follow-up: re-download training data from
current wspr.live to compare apples-to-apples with live held-out numbers.

SQL byte-for-byte from replication_2026.download_wspr_day (HTTPS added).
Cache schema: hour_utc, band_mhz, spots, kp (Kp merged from frozen
unified.parquet at save time). Resumable: after EVERY successful day,
CACHE is rewritten. Failed days: 3 retries (10 s pause), then skipped
and logged to FAILED_LOG. Download + Kp merge only — no point/CI.
"""

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

WSPR_API = "https://db1.wspr.live/"
BANDS = {"20m": 14, "40m": 7, "15m": 21}
START = date(2024, 4, 1)
END = date(2025, 9, 30)  # inclusive
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "results" / "training_live_2026-10-13.parquet"
FAILED_LOG = ROOT / "results" / "training_live_2026-10-13.failed.txt"
KP_PARQUET = ROOT / "data" / "processed" / "unified.parquet"
SLEEP_S = 0.3
RETRY = 3
RETRY_PAUSE = 10


def load_kp() -> pd.DataFrame:
    """Frozen Kp hourly means from unified.parquet (single source)."""
    kp = pd.read_parquet(KP_PARQUET)
    kp = kp[kp["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    return kp.groupby("hour")["kp"].mean().reset_index()


def download_wspr_day(d: date, band_name: str, band_idx: int) -> pd.DataFrame:
    """Exact copy of replication_2026.download_wspr_day with HTTPS URL."""
    date_str = d.strftime("%Y-%m-%d")
    sql = (
        f"SELECT toStartOfHour(time) AS hour, count() AS spots, "
        f"avg(snr) AS mean_snr, max(distance) AS max_distance "
        f"FROM wspr.rx "
        f"WHERE time >= '{date_str} 00:00:00' AND time < '{date_str} 23:59:59' "
        f"AND band = {band_idx} "
        f"GROUP BY hour ORDER BY hour FORMAT JSONCompact"
    )
    headers = {"User-Agent": "ionosphere-research/1.0"}
    resp = requests.get(WSPR_API, params={"query": sql}, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    df = pd.DataFrame(data, columns=["hour", "spots", "mean_snr", "max_distance"])
    if len(df) == 0:
        return df
    df["hour"] = pd.to_datetime(df["hour"], utc=True).dt.floor("1h")
    df["spots"] = pd.to_numeric(df["spots"])
    df["band"] = band_name
    return df[["hour", "band", "spots"]]


def build_cache(raw_frames: list[pd.DataFrame], kp_h: pd.DataFrame) -> pd.DataFrame:
    """Concat raw downloads, rename to cache schema, merge frozen Kp."""
    out = pd.concat(raw_frames, ignore_index=True)
    out = out.rename(columns={"hour": "hour_utc", "band": "band_mhz"})
    merged = pd.merge(out, kp_h, left_on="hour_utc", right_on="hour", how="left")
    merged = merged.drop(columns=["hour"])
    merged = merged.sort_values(["hour_utc", "band_mhz"]).reset_index(drop=True)
    return merged[["hour_utc", "band_mhz", "spots", "kp"]]


def main() -> int:
    print("=== Training live download 2024-04-01 .. 2025-09-30 (18mo x 3 bands) ===")
    print(f"URL: {WSPR_API}  sleep={SLEEP_S}s\n")

    kp_h = load_kp()
    print(f"Frozen Kp hourly rows: {len(kp_h)}")

    # Resume: set of (date, band_name) already in cache
    done: set[tuple[str, str]] = set()
    raw_frames: list[pd.DataFrame] = []
    if CACHE.exists():
        cached = pd.read_parquet(CACHE)
        for _, row in cached.iterrows():
            ds = pd.Timestamp(row["hour_utc"]).strftime("%Y-%m-%d")
            done.add((ds, row["band_mhz"]))
        # reconstruct raw frame (hour/band/spots) from cache for append
        raw = cached.rename(columns={"hour_utc": "hour", "band_mhz": "band"})
        raw_frames.append(raw[["hour", "band", "spots"]])
        print(f"Resume: cache {len(cached)} rows, {len(done)} (day,band) pairs")
    else:
        print("Resume: no cache, starting fresh")

    # Enumerate jobs
    jobs: list[tuple[date, str, int]] = []
    d = START
    while d <= END:
        for band_name, band_idx in BANDS.items():
            jobs.append((d, band_name, band_idx))
        d += timedelta(days=1)
    remaining = sum(1 for jd, bn, _ in jobs if (jd.strftime("%Y-%m-%d"), bn) not in done)
    print(f"Total jobs: {len(jobs)}  done: {len(done)}  remaining: {remaining}\n")

    CACHE.parent.mkdir(exist_ok=True)
    failed: list[tuple[str, str, str]] = []
    new_jobs = 0
    for i, (jd, band_name, band_idx) in enumerate(jobs, 1):
        ds = jd.strftime("%Y-%m-%d")
        if (ds, band_name) in done:
            continue
        success = False
        for attempt in range(1, RETRY + 1):
            try:
                day_df = download_wspr_day(jd, band_name, band_idx)
                if len(day_df) > 0:
                    raw_frames.append(day_df)
                success = True
                new_jobs += 1
                break
            except Exception as e:
                if attempt < RETRY:
                    print(f"  retry {attempt}/{RETRY} {ds} band={band_idx}: {e}")
                    time.sleep(RETRY_PAUSE)
                else:
                    failed.append((ds, band_name, str(e)))
                    print(f"  FAILED {ds} band={band_idx} after {RETRY} retries: {e}")
        time.sleep(SLEEP_S)
        if success:
            # Resumable: rewrite cache after EVERY successful download
            build_cache(raw_frames, kp_h).to_parquet(CACHE, index=False)
        if i % 30 == 0:
            print(f"  ... job {i}/{len(jobs)}, new={new_jobs}, failed={len(failed)}")

    # Summary
    print("\n=== Summary ===")
    if raw_frames:
        out = build_cache(raw_frames, kp_h)
        print(f"N_total rows: {len(out)}")
        print(f"Date range: {out['hour_utc'].min()} .. {out['hour_utc'].max()}")
        print(f"Per band: {out.groupby('band_mhz').size().to_dict()}")
        print(f"Rows with Kp merged: {int(out['kp'].notna().sum())} / {len(out)}")
    else:
        print("EMPTY: no frames collected")

    if failed:
        print(f"\nFailed jobs ({len(failed)}):")
        for f in failed:
            print(f"  {f[0]} band={f[1]}: {f[2]}")
        with open(FAILED_LOG, "w", encoding="utf-8") as fh:
            for f in failed:
                fh.write(f"{f[0]}\t{f[1]}\t{f[2]}\n")
        if len(failed) > len(jobs) * 0.10:
            print(f"STOP: failed >10% ({len(failed)}/{len(jobs)})")
            return 1
    else:
        print("\nNo failed days.")

    print(f"\nCache: {CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
