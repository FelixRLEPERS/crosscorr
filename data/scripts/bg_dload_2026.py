"""Download 2026 WSPR hourly — single worker, resumable."""
import datetime as dt
import json
import time
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

existing = {f.stem for f in OUT.glob("wspr_2026*.json") if f.stat().st_size > 10}
tasks = [(d, b, bi) for d in dates for b, bi in BANDS.items() if f"wspr_2026_{d}_{b}" not in existing]
print(f"Tasks: {len(tasks)}", flush=True)

ok = 0
fail = 0
consecutive_fail = 0

for date_str, band_name, band_idx in tasks:
    try:
        sql = (
            f"SELECT hour, spots FROM ("
            f"SELECT toStartOfHour(time) AS hour, count() AS spots "
            f"FROM wspr.rx "
            f"WHERE time >= '{date_str} 00:00:00' "
            f"AND time < '{date_str} 23:59:59' "
            f"AND band = {band_idx} "
            f"GROUP BY hour ORDER BY hour) FORMAT JSONCompact"
        )
        resp = requests.get(API, params={"query": sql}, headers={"User-Agent": "cr/1.0"}, timeout=300)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        fpath = OUT / f"wspr_2026_{date_str}_{band_name}.json"
        fpath.write_text(json.dumps(data))
        ok += 1
        consecutive_fail = 0
        if ok % 5 == 0:
            print(f"  {ok} ok ({fail} fails)", flush=True)
    except Exception:
        fail += 1
        consecutive_fail += 1
        if fail <= 10 or fail % 10 == 0:
            print(f"FAIL {date_str} {band_name} ({fail} total)", flush=True)
        if consecutive_fail > 5:
            time.sleep(5)
        else:
            time.sleep(1)

print(f"Done: OK={ok} FAIL={fail}", flush=True)
