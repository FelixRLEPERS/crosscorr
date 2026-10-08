"""Phase 1: Download 40m + 15m for 12 new months."""
import sys

sys.path.insert(0, r'G:\crosscorr\data\scripts')
import datetime as dt
from pathlib import Path

from download_wspr import fetch_wspr_hourly

RAW = Path(r'G:\crosscorr\data\raw\wspr')
RAW.mkdir(parents=True, exist_ok=True)

months = [
    (2024,4,30),(2024,5,31),(2024,6,30),(2024,7,31),(2024,8,31),(2024,9,30),
    (2025,4,30),(2025,5,31),(2025,6,30),(2025,7,31),(2025,8,31),(2025,9,30),
]
bands = ['40m', '15m']

for band in bands:
    for yr,mo,days in months:
        ok = 0
        for d in range(1, days+1):
            dd = dt.date(yr,mo,d)
            f = RAW / f'wspr_hourly_{dd}_{band}.csv'
            if f.exists():
                ok += 1
                continue
            df = fetch_wspr_hourly(dd, band=band)
            if not df.empty:
                df.to_csv(f, index=False)
                ok += 1
        print(f'{yr}-{mo:02d} {band}: {ok}/{days}', flush=True)
    print(f'BAND {band} DONE', flush=True)
print('ALL DONE', flush=True)
