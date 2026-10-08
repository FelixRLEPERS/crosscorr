"""Phase 4: EDA 18-month x 3-band with seasonal analysis."""
import pandas as pd, numpy as np, matplotlib, json
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'eda'
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'unified.parquet')
full = df[(df['timestamp_utc'] >= '2024-04-01') & (df['timestamp_utc'] < '2025-10-01')]

wspr = full[full['detector_type'] == 'wspr_hourly'].copy()
wspr['band'] = wspr['detector_id'].astype(str).str.replace('wspr_hourly_', '')
wspr['hour'] = wspr['timestamp_utc'].dt.floor('1h')
wspr['month_num'] = wspr['timestamp_utc'].dt.month
wspr['month'] = wspr['timestamp_utc'].dt.to_period('M')
wspr['hour_of_day'] = wspr['timestamp_utc'].dt.hour
wspr['season'] = wspr['month_num'].map({
    12: 'winter', 1: 'winter', 2: 'winter',
    3: 'spring', 4: 'spring', 5: 'spring',
    6: 'summer', 7: 'summer', 8: 'summer',
    9: 'autumn', 10: 'autumn', 11: 'autumn',
})

kp = full[full['detector_type'] == 'kp'][['timestamp_utc', 'value']].copy()
kp.columns = ['timestamp_utc', 'kp']
kp['hour'] = kp['timestamp_utc'].dt.floor('1h')
kp_h = kp.groupby('hour')['kp'].mean().reset_index()

all_results = {}

for band in ['20m', '40m', '15m']:
    sub = wspr[wspr['band'] == band].copy()
    merged = pd.merge(sub, kp_h, on='hour', how='inner').sort_values('hour').reset_index(drop=True)
    merged['resid'] = merged['value'] - merged.groupby(
        ['month', 'hour_of_day'])['value'].transform('mean')

    bins_labels = ['Kp<3', '3-4', '4-5', 'Kp>=5']
    bins = pd.cut(merged['kp'], bins=[-0.1, 3, 4, 5, 10], labels=bins_labels)
    grp = merged.groupby(bins, observed=True)
    binned = pd.DataFrame({
        'N': grp['resid'].count(),
        'mean_resid': grp['resid'].mean().round(0),
        'std_resid': grp['resid'].std().round(0),
        'mean_abs': grp['value'].mean().round(0),
    })

    N = len(merged)
    storm_N = (merged['kp'] >= 5).sum()
    quiet_N = (merged['kp'] < 3).sum()
    storm_mean = merged.loc[merged['kp'] >= 5, 'value'].mean()
    quiet_mean = merged.loc[merged['kp'] < 3, 'value'].mean()
    drop = 100 * (storm_mean - quiet_mean) / quiet_mean

    print(f"\n=== {band} ===")
    print(f"N={N}, storm={storm_N}, quiet={quiet_N}")
    print(binned.to_string())
    print(f"Absolute drop: {drop:.1f}%")

    all_results[band] = {'N': N, 'N_storm': int(storm_N), 'drop_pct': round(drop, 1),
                         'binned': {str(k): int(v) for k, v in zip(bins_labels, binned['mean_resid'])}}

    # Single-band plot
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['steelblue', 'skyblue', 'coral', 'firebrick']
    ax.bar(range(len(binned)), binned['mean_resid'], color=colors, edgecolor='black', linewidth=0.5)
    ax.set_xticks(range(len(binned)))
    ax.set_xticklabels(bins_labels)
    ax.axhline(0, color='gray', ls='--')
    ax.set_ylabel('Mean residual (spots/hour)')
    ax.set_title(f'{band}: Kp effect, 18 months (N={N}, drop={drop:.1f}%)')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(OUT / f'binned_18mo_{band}.png'), dpi=100)
    plt.close()

# Bands comparison plot
fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=False)
for i, band in enumerate(['20m', '40m', '15m']):
    sub = wspr[wspr['band'] == band].copy()
    merged = pd.merge(sub, kp_h, on='hour', how='inner')
    merged['resid'] = merged['value'] - merged.groupby(['month', 'hour_of_day'])['value'].transform('mean')
    grp = merged.groupby(pd.cut(merged['kp'], bins=[-0.1, 3, 4, 5, 10],
                                labels=['Kp<3', '3-4', '4-5', 'Kp>=5']), observed=True)
    bv = grp['resid'].mean()
    colors = ['steelblue', 'skyblue', 'coral', 'firebrick']
    axes[i].bar(range(len(bv)), bv.values, color=colors, edgecolor='black', linewidth=0.5)
    axes[i].set_xticks(range(len(bv)))
    axes[i].set_xticklabels(bv.index.astype(str), fontsize=8)
    axes[i].axhline(0, color='gray', ls='--')
    axes[i].set_title(band)
    axes[i].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(str(OUT / 'bands_comparison_18mo.png'), dpi=100)
plt.close()
print("\n[OK] bands_comparison_18mo.png")

# Seasonal analysis
print("\n=== Seasonal Analysis ===")
seasons = ['winter', 'spring', 'summer', 'autumn']
seasonal = {}
for band in ['20m', '40m', '15m']:
    seasonal[band] = {}
    for season in seasons:
        sm = merged[merged['season'] == season] if band == '15m' else pd.merge(
            wspr[wspr['band'] == band], kp_h, on='hour', how='inner').assign(
            season=lambda x: x['hour'].dt.month.map({
                12: 'winter', 1: 'winter', 2: 'winter',
                3: 'spring', 4: 'spring', 5: 'spring',
                6: 'summer', 7: 'summer', 8: 'summer',
                9: 'autumn', 10: 'autumn', 11: 'autumn',
            })).query(f'season == "{season}"')
        if len(sm) < 10: continue
        sm['resid'] = sm['value'] - sm.groupby('hour_of_day')['value'].transform('mean')
        n5 = (sm['kp'] >= 5).sum()
        n0 = (sm['kp'] < 3).sum()
        if n5 < 2 or n0 < 5: continue
        delta = sm.loc[sm['kp'] >= 5, 'resid'].mean() - sm.loc[sm['kp'] < 3, 'resid'].mean()
        seasonal[band][season] = {'N': len(sm), 'N_storm': int(n5), 'delta': round(float(delta))}

for band in ['20m', '40m', '15m']:
    print(f"\n  {band}:")
    for s in seasons:
        d = seasonal[band].get(s)
        if d:
            print(f"    {s}: N={d['N']}, storm={d['N_storm']}, delta={d['delta']}")

# Save
with open(str(OUT / 'eda_18mo_summary.json'), 'w') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
with open(str(OUT / 'seasonal_18mo.json'), 'w') as f:
    json.dump(seasonal, f, indent=2, ensure_ascii=False)

print(f"\nSummary: 20m={all_results['20m']['drop_pct']}%, "
      f"40m={all_results['40m']['drop_pct']}%, 15m={all_results['15m']['drop_pct']}%")