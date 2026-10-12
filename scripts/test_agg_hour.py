import io

import pandas as pd
import requests

BASE_URL = "http://db1.wspr.live/"
sql = """
SELECT
    toStartOfHour(time) AS hour,
    toInt16(FLOOR(rx_lat / 2.0) * 2.0) AS lat_bin,
    toInt16(FLOOR(rx_lon / 10.0) * 10.0) AS lon_bin,
    COUNT(*) AS n
FROM wspr.rx
WHERE time >= '2024-05-10 12:00:00'
  AND time <  '2024-05-10 13:00:00'
  AND band = 14
GROUP BY 1, 2, 3
FORMAT CSV
"""
r = requests.get(BASE_URL, params={"query": sql}, timeout=120)
print("HTTP:", r.status_code, "size:", len(r.content))
if r.status_code == 200:
    df = pd.read_csv(io.BytesIO(r.content),
                     header=None,
                     names=["hour", "lat_bin", "lon_bin", "n"])
    print("Rows:", len(df))
    print(df.head(10))
    print("Lat range:", df['lat_bin'].min(), "-", df['lat_bin'].max())
    us = df[(df['lon_bin'].between(-100, -60)) & (df['lat_bin'].between(25, 60))]
    print("US East rows:", len(us), "total spots:", us['n'].sum())
else:
    print("FAIL:", r.text[:300])
