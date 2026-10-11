import pandas as pd
import numpy as np
from scipy import stats

df_s = pd.read_parquet('storm_day_agg.parquet')
df_q = pd.read_parquet('quiet_all_agg.parquet')

# Региональный фильтр (US East)
for df in (df_s, df_q):
    df.drop(df[~df['lon_bin'].between(-100, -60) |
               ~df['lat_bin'].between(25, 60)].index, inplace=True)

df_s['hour_utc'] = pd.to_datetime(df_s['hour']).dt.hour
df_q['hour_utc'] = pd.to_datetime(df_q['hour']).dt.hour

agg_s = df_s.groupby(['lat_bin', 'hour_utc'])['n'].sum().rename('n_storm')
agg_q = (df_q.groupby(['lat_bin', 'hour_utc'])['n'].sum() / 3).rename('n_quiet')

merged = pd.concat([agg_s, agg_q], axis=1).fillna(0)
merged['delta'] = merged['n_storm'] - merged['n_quiet']
merged['pct'] = 100 * merged['delta'] / merged['n_quiet'].replace(0, np.nan)

# --- 1. Матрица % изменения: строки = широта, столбцы = час UTC ---
print("\n=== Матрица % изменения (storm vs quiet avg) ===")
print("      " + "".join(f"{h:>6d}" for h in range(24)))
for lat in sorted(merged.index.get_level_values(0).unique(), reverse=True):
    sub = merged.xs(lat, level=0).reindex(range(24))
    row = "".join(
        f"{'  --  ' if pd.isna(v) else f'{v:>+6.0f}'}" for v in sub['pct'].values
    )
    print(f"{lat:>4d}N {row}")

# --- 2. First-drop detection, но с двумя порогами ---
for threshold in (-30, -50):
    print(f"\n=== Первый час с падением < {threshold}% (только 15–23 UTC) ===")
    found_any = False
    for lat in sorted(merged.index.get_level_values(0).unique(), reverse=True):
        sub = merged.xs(lat, level=0)
        sub_afternoon = sub[(sub.index >= 15) & (sub.index <= 23)]
        big_drop = sub_afternoon[sub_afternoon['pct'] < threshold]
        if len(big_drop) > 0:
            first_hour = big_drop.index[0]
            pct_val = big_drop['pct'].iloc[0]
            print(f"  Lat {lat:3d}N: first drop at {first_hour:02d} UTC ({pct_val:+.0f}%)")
            found_any = True
    if not found_any:
        print(f"  (нет широт с падением < {threshold}% в 15–23 UTC)")

# --- 3. Ищем диагональ ---
print("\n=== Проверка на диагональ ===")
first_hours = []
for lat in sorted(merged.index.get_level_values(0).unique(), reverse=True):
    sub = merged.xs(lat, level=0)
    sub_afternoon = sub[(sub.index >= 15) & (sub.index <= 23)]
    big_drop = sub_afternoon[sub_afternoon['pct'] < -30]
    if len(big_drop) > 0:
        first_hours.append((lat, big_drop.index[0]))

if len(first_hours) >= 3:
    # Проверяем корреляцию lat vs hour
    lats = [x[0] for x in first_hours]
    hours = [x[1] for x in first_hours]
    if max(hours) - min(hours) >= 2:
        print(f"  ВИДНА ДИАГОНАЛЬ: hour варьируется {min(hours)}–{max(hours)} UTC")
        print(f"  Широты: {lats}")
        # Приблизительная скорость: Δhour × 3600 сек, Δlat × 111 км
        dlat_km = (max(lats) - min(lats)) * 111
        dt_sec = (max(hours) - min(hours)) * 3600
        if dt_sec > 0:
            v = dlat_km * 1000 / dt_sec
            print(f"  Оценка скорости: {v:.0f} м/с (LSTID ожидается 300–500 м/с)")
    else:
        print(f"  ВЕРТИКАЛЬ: hour почти одинаков ({min(hours)}–{max(hours)} UTC)")
        print("  -> Доминирует глобальный химический эффект / D-layer absorption.")
else:
    print("  Недостаточно широт с падением < -30% для оценки.")