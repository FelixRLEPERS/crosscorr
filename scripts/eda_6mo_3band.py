"""Phase 4: EDA 6-month x 3-band analysis."""
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('Agg')
import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'eda'
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'unified.parquet')

wspr = df[df['detector_type'] == 'wspr_hourly'].copy()
wspr['band'] = wspr['detector_id'].str.replace('wspr_hourly_', '')
wspr['hour'] = wspr['timestamp_utc'].dt.floor('1h')
wspr['month'] = wspr['timestamp_utc'].dt.to_period('M')
wspr['hour_of_day'] = wspr['timestamp_utc'].dt.hour

kp = df[df['detector_type'] == 'kp'][['timestamp_utc', 'value']].copy()
kp.columns = ['timestamp_utc', 'kp']
kp['hour'] = kp['timestamp_utc'].dt.floor('1h')
kp_h = kp.groupby('hour')['kp'].mean().reset_index()

print("=== WSPR by band ===")
print(wspr['band'].value_counts().to_string())

all_results = {}

for band in ['20m', '40m', '15m']:
    sub = wspr[wspr['band'] == band].copy()
    if len(sub) == 0:
        print(f"[SKIP] {band}")
        continue

    merged = pd.merge(sub, kp_h, on='hour', how='inner')
    merged = merged.sort_values('hour').reset_index(drop=True)
    merged['resid'] = merged['value'] - merged.groupby(
        ['month', 'hour_of_day'])['value'].transform('mean')

    bins_labels = ['Kp<3', '3-4', '4-5', 'Kp>=5']
    bins = pd.cut(merged['kp'], bins=[-0.1, 3, 4, 5, 10], labels=bins_labels)
    grp = merged.groupby(bins, observed=True)
    binned = pd.DataFrame({
        'N': grp['resid'].count(),
        'mean_resid': grp['resid'].mean(),
        'std_resid': grp['resid'].std(),
        'mean_abs': grp['value'].mean(),
    })
    binned['sem'] = binned['std_resid'] / np.sqrt(binned['N'])

    print(f"\n=== {band} ===")
    N = len(merged)
    storm_N = (merged['kp'] >= 5).sum()
    quiet_N = (merged['kp'] < 3).sum()
    print(f"N={N}, storm={storm_N}, quiet={quiet_N}")
    print(binned[['N', 'mean_resid', 'sem', 'mean_abs']].to_string())

    storm_mean = merged.loc[merged['kp'] >= 5, 'value'].mean()
    quiet_mean = merged.loc[merged['kp'] < 3, 'value'].mean()
    drop = 100 * (storm_mean - quiet_mean) / quiet_mean
    print(f"Absolute drop: {drop:.1f}%")

    all_results[band] = {
        'N': N, 'N_storm': int(storm_N), 'N_quiet': int(quiet_N),
        'binned': {str(k): v for k, v in zip(bins_labels, binned['mean_resid'], strict=False)},
        'abs_drop_pct': round(drop, 1),
    }

    # Single-band plot
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(binned))
    colors = ['steelblue', 'skyblue', 'coral', 'firebrick']
    ax.bar(x, binned['mean_resid'], yerr=binned['sem'], capsize=5, color=colors,
           edgecolor='black', linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(bins_labels)
    ax.axhline(0, color='gray', ls='--')
    ax.set_ylabel('Mean residual (spots/hour)')
    ax.set_title(f'{band}: Kp effect, 6 months (N={len(merged)}, drop={drop:.1f}%)')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(OUT / f'binned_6mo_{band}.png'), dpi=100)
    plt.close()
    print(f"[OK] binned_6mo_{band}.png")

# Comparison plot
fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=False)
for i, band in enumerate(['20m', '40m', '15m']):
    sub = wspr[wspr['band'] == band].copy()
    merged = pd.merge(sub, kp_h, on='hour', how='inner')
    merged['resid'] = merged['value'] - merged.groupby(
        ['month', 'hour_of_day'])['value'].transform('mean')
    grp = merged.groupby(pd.cut(merged['kp'], bins=[-0.1, 3, 4, 5, 10],
                                labels=['Kp<3', '3-4', '4-5', 'Kp>=5']), observed=True)
    bv = grp['resid'].mean()
    colors = ['steelblue', 'skyblue', 'coral', 'firebrick']
    axes[i].bar(range(len(bv)), bv.values, color=colors, edgecolor='black', linewidth=0.5)
    axes[i].set_xticks(range(len(bv)))
    axes[i].set_xticklabels(bv.index.astype(str), fontsize=8)
    axes[i].axhline(0, color='gray', ls='--')
    axes[i].set_title(f'20m ({band})')
    axes[i].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(str(OUT / 'bands_comparison_6mo.png'), dpi=100)
plt.close()
print("[OK] bands_comparison_6mo.png")

# Summary
print("\n=== Summary ===")
for band, r in all_results.items():
    print(f"{band}: N={r['N']}, drop={r['abs_drop_pct']}%")

with open(str(OUT / 'eda_6mo_summary.json'), 'w') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
print("[DONE] eda_6mo_summary.json")
