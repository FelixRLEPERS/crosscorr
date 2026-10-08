"""Download all WSPR for 2026 held-out period."""
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "wspr_hourly"
OUT.mkdir(parents=True, exist_ok=True)
API = "http://db1.wspr.live/"
BANDS = {"20m": 14, "40m": 7, "15m": 21}

dates = []
cur = dt.datetime(2026, 1, 1)
while cur <= dt.datetime(2026, 6, 30):
    dates.append(cur.strftime("%Y-%m-%d"))
    cur += dt.timedelta(days=1)

tasks = [(d, b, bi) for d in dates for b, bi in BANDS.items()]
print(f"Tasks: {len(tasks)}")


def fetch(date_str, band_name, band_idx):
    fname = OUT / f"wspr_2026_{date_str}_{band_name}.json"
    if fname.exists() and fname.stat().st_size > 10:
        return len(json.loads(fname.read_text()))
    sql = (
        f"SELECT hour, spots, mean_snr, max_dist FROM ("
        f"SELECT toStartOfHour(time) AS hour, count() AS spots, "
        f"avg(snr) AS mean_snr, max(distance) AS max_dist "
        f"FROM wspr.rx WHERE time >= '{date_str} 00:00:00' "
        f"AND time < '{date_str} 23:59:59' AND band = {band_idx} "
        f"GROUP BY hour ORDER BY hour) FORMAT JSONCompact"
    )
    resp = requests.get(API, params={"query": sql}, headers={"User-Agent": "cr/1.0"}, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    fname.write_text(json.dumps(data))
    return len(data)


done = 0
with ThreadPoolExecutor(max_workers=20) as pool:
    fs = {pool.submit(fetch, d, b, bi): (d, b) for d, b, bi in tasks}
    for f in as_completed(fs):
        try:
            f.result()
        except Exception as e:
            d, b = fs[f]
            print(f"FAIL {d} {b}: {e}")
        done += 1
        if done % 60 == 0:
            print(f"  {done}/{len(tasks)}")

files = list(OUT.glob("wspr_2026*.json"))
print(f"Done! Files: {len(files)}")
