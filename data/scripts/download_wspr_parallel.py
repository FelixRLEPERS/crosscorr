"""Fast WSPR download for held-out period. Parallel by month/band."""
import argparse
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

WSPR_API = "http://db1.wspr.live/"
BANDS = {"20m": 14, "40m": 7, "15m": 21}
HEADERS = {"User-Agent": "ionosphere-research/1.0"}
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "wspr_hourly"


def fetch_day(date_str, band_idx):
    sql = (
        f"SELECT toStartOfHour(time) AS hour, count() AS spots, "
        f"avg(snr) AS mean_snr, max(distance) AS max_distance "
        f"FROM wspr.rx "
        f"WHERE time >= '{date_str} 00:00:00' AND time < '{date_str} 23:59:59' "
        f"AND band = {band_idx} "
        f"GROUP BY hour ORDER BY hour FORMAT JSONCompact"
    )
    resp = requests.get(WSPR_API, params={"query": sql}, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return [{"hour": r[0], "spots": int(r[1]), "mean_snr": float(r[2]), "max_dist": float(r[3])} for r in data]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    start = dt.datetime.strptime(args.start, "%Y-%m-%d")
    end = dt.datetime.strptime(args.end, "%Y-%m-%d")
    dates = []
    cur = start
    while cur <= end:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += dt.timedelta(days=1)

    tasks = [(d, band_idx, band_name) for d in dates for band_name, band_idx in BANDS.items()]
    print(f"Downloading {len(tasks)} files ({len(dates)} days x {len(BANDS)} bands) with {args.workers} workers...")

    done = 0
    fail = 0
    OUT.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {
            pool.submit(fetch_day, d, bidx): (d, bname)
            for d, bidx, bname in tasks
        }
        for f in as_completed(future_map):
            date_str, band_name = future_map[f]
            try:
                rows = f.result()
                if rows:
                    df = pd.DataFrame(rows)
                    fname = OUT / f"wspr_hourly_{date_str}_{band_name}.csv"
                    df.to_csv(fname, index=False)
                done += 1
            except Exception as e:
                fail += 1
                if fail <= 5:
                    print(f"  FAIL {date_str} {band_name}: {e}")
            if done % 30 == 0:
                print(f"  {done}/{len(tasks)} done ({fail} fails)")


    print(f"Done: {done}/{len(tasks)} ({fail} fails)")


if __name__ == "__main__":
    main()
