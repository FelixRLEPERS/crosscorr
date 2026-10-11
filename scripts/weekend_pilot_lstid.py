import requests
import pandas as pd
import io
import time
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

BASE_URL = "http://db1.wspr.live/"
STORM_DATE = '2024-05-10'
QUIET_DATES = ['2024-05-05', '2024-05-06', '2024-05-07']
BAND = 14  # 20 m

LON_MIN, LON_MAX = -100, -60
LAT_MIN, LAT_MAX = 25, 60

COLS = ["hour", "lat_bin", "lon_bin", "n"]


def fetch_day_agg(date_str):
    """Один запрос в день. GROUP BY на сервере -> ~200 КБ вместо ~60 МБ."""
    sql = f"""
        SELECT
            toStartOfHour(time) AS hour,
            toInt16(FLOOR(rx_lat / 2.0) * 2.0) AS lat_bin,
            toInt16(FLOOR(rx_lon / 10.0) * 10.0) AS lon_bin,
            COUNT(*) AS n
        FROM wspr.rx
        WHERE time >= '{date_str} 00:00:00'
          AND time <  '{date_str} 23:59:59'
          AND band = {BAND}
        GROUP BY 1, 2, 3
        FORMAT CSV
    """
    r = requests.get(BASE_URL, params={"query": sql}, timeout=(30, 300))
    if r.status_code != 200:
        print(f"  FAIL {date_str}: HTTP {r.status_code}")
        return pd.DataFrame(columns=COLS)
    df = pd.read_csv(io.BytesIO(r.content), header=None, names=COLS)
    print(f"  {date_str}: {len(df)} agg rows, {df['n'].sum():,} spots")
    return df


print(f"=== STEP 1: Download storm day {STORM_DATE} ===")
df_storm = fetch_day_agg(STORM_DATE)
df_storm.to_parquet('storm_day_agg.parquet', index=False)
print()

print("=== STEP 2: Download quiet days ===")
quiet_frames = []
for d in QUIET_DATES:
    df_q = fetch_day_agg(d)
    df_q.to_parquet(f'quiet_{d}_agg.parquet', index=False)
    quiet_frames.append(df_q)
quiet_all = pd.concat(quiet_frames, ignore_index=True)
quiet_all.to_parquet('quiet_all_agg.parquet', index=False)
print(f"Quiet total: {len(quiet_all)} agg rows\n")

print("=== STEP 3: Regional filter + aggregation ===")


def regional_filter(df):
    return df[(df['lon_bin'] >= LON_MIN) & (df['lon_bin'] <= LON_MAX) &
              (df['lat_bin'] >= LAT_MIN) & (df['lat_bin'] <= LAT_MAX)]


storm_reg = regional_filter(df_storm)
quiet_reg = regional_filter(quiet_all)

storm_g = storm_reg.groupby(['hour', 'lat_bin'])['n'].sum().reset_index()
storm_g['hour_utc'] = pd.to_datetime(storm_g['hour']).dt.hour
storm_g = storm_g.drop(columns='hour')

quiet_g = quiet_reg.copy()
quiet_g['hour_utc'] = pd.to_datetime(quiet_g['hour']).dt.hour
quiet_g = quiet_g.groupby(['hour_utc', 'lat_bin'], as_index=False)['n'].sum()
quiet_g['n'] = quiet_g['n'] / len(QUIET_DATES)

df_m = pd.merge(storm_g, quiet_g,
                on=['hour_utc', 'lat_bin'],
                suffixes=('_storm', '_quiet'),
                how='outer').fillna(0)
df_m['delta'] = df_m['n_storm'] - df_m['n_quiet']

print(f"Storm regional spots:  {storm_reg['n'].sum():,}")
print(f"Quiet regional (avg/day): {quiet_reg['n'].sum()/len(QUIET_DATES):,.0f}")
print(f"Delta (storm - quiet):   {df_m['delta'].sum():,.0f}\n")

print("=== STEP 4: Heatmap ===")
pivot = df_m.pivot(index='lat_bin', columns='hour_utc', values='delta')
pivot = pivot.sort_index(ascending=False)

fig, ax = plt.subplots(figsize=(14, 8))
sns.heatmap(pivot, cmap='RdBu_r', center=0,
            cbar_kws={'label': 'Delta Spots (Storm - Quiet avg)', 'shrink': 0.8},
            linewidths=0.5, linecolor='gray', ax=ax)
ax.set_title(f'LSTID Pilot: WSPR 20m (US East Coast)\n'
             f'Storm {STORM_DATE} (G5) vs avg of {len(QUIET_DATES)} quiet days',
             fontsize=14, fontweight='bold')
ax.set_xlabel('Hour UTC')
ax.set_ylabel('Receiver latitude (deg N)')
ax.axvline(x=23.5, color='black', ls='--', alpha=0.7, label='~Sunset')
ax.axvline(x=9.5, color='black', ls='--', alpha=0.7, label='~Sunrise')
ax.legend(loc='upper right')
plt.tight_layout()
plt.savefig('lstid_pilot_may2024.png', dpi=300)
print("\nDONE: lstid_pilot_may2024.png")