import requests
import pandas as pd
import io

BASE_URL = "http://db1.wspr.live/"
sql = """
SELECT toStartOfHour(time) AS hour, rx_lat, rx_lon, snr
FROM wspr.rx
WHERE time >= '2024-05-10 12:00:00'
  AND time <  '2024-05-10 13:00:00'
  AND band = 14
FORMAT Parquet
"""
r = requests.get(BASE_URL, params={"query": sql}, timeout=120)
print("HTTP:", r.status_code, "size:", len(r.content))

if r.status_code == 200 and len(r.content) > 100:
    df = pd.read_parquet(io.BytesIO(r.content))
    print("Global rows:", len(df))

    # Региональный фильтр локально
    mask = (df['rx_lon'].between(-100, -60)) & (df['rx_lat'].between(25, 60))
    df_reg = df[mask]
    print("Regional rows:", len(df_reg))
    print("Columns:", list(df.columns))
    print("Lat range:", df_reg['rx_lat'].min(), "-", df_reg['rx_lat'].max())
    print(df_reg.head(3))
else:
    print("FAIL:", r.text[:300])