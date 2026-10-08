"""Phase 5: Permutation test 18mo x 3 band."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(42)
N_ITER = 10000
BLOCK = 24

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'unified.parquet')
full = df[(df['timestamp_utc'] >= '2024-04-01') & (df['timestamp_utc'] < '2025-10-01')]

wspr = full[full['detector_type'] == 'wspr_hourly'].copy()
wspr['band'] = wspr['detector_id'].astype(str).str.replace('wspr_hourly_', '')
wspr['hour'] = wspr['timestamp_utc'].dt.floor('1h')
wspr['month'] = wspr['timestamp_utc'].dt.to_period('M')
wspr['hour_of_day'] = wspr['timestamp_utc'].dt.hour
wspr['day_of_week'] = wspr['timestamp_utc'].dt.dayofweek

kp = full[full['detector_type'] == 'kp'][['timestamp_utc', 'value']].copy()
kp.columns = ['timestamp_utc', 'kp']
kp['hour'] = kp['timestamp_utc'].dt.floor('1h')
kp_h = kp.groupby('hour')['kp'].mean().reset_index()


def block_perm_test(merged, block_size=BLOCK, n_iter=N_ITER):
    merged = merged.copy()
    if 'day_of_week' in merged.columns:
        merged['resid'] = merged['value'] - merged.groupby(
            ['month', 'hour_of_day', 'day_of_week'])['value'].transform('mean')
    else:
        merged['resid'] = merged['value'] - merged.groupby(
            ['month', 'hour_of_day'])['value'].transform('mean')
    sm = (merged['kp'] >= 5).values
    qm = (merged['kp'] < 3).values
    if sm.sum() < 3 or qm.sum() < 10:
        return None, None, None

    obs = merged['resid'].values[sm].mean() - merged['resid'].values[qm].mean()
    resid = merged['resid'].values
    kpv = merged['kp'].values
    n = len(resid)
    nb = n // block_size
    rblocks = resid[:nb * block_size].reshape(nb, block_size)
    kpv = kpv[:nb * block_size]
    stats = []
    for _ in range(n_iter):
        order = RNG.permutation(nb)
        rp = rblocks[order].ravel()
        s = kpv >= 5
        q = kpv < 3
        if s.sum() == 0 or q.sum() == 0:
            continue
        stats.append(rp[s].mean() - rp[q].mean())
    stats = np.array(stats)
    p = (np.abs(stats) >= np.abs(obs)).mean()
    return float(obs), float(p), len(stats)


results = {}
print("=== 18mo Permutation Test ===\n")
for band in ['20m', '40m', '15m']:
    sub = wspr[wspr['band'] == band].copy()
    merged = pd.merge(sub, kp_h, on='hour', how='inner').sort_values('hour').reset_index(drop=True)
    merged['day_of_week'] = merged['hour'].dt.dayofweek
    N = len(merged)
    storm_N = (merged['kp'] >= 5).sum()
    quiet_N = (merged['kp'] < 3).sum()

    obs, p, n_valid = block_perm_test(merged)
    if obs is None:
        print(f"[{band}] Insufficient storm data")
        continue

    storm_m = merged.loc[merged['kp'] >= 5, 'value'].mean()
    quiet_m = merged.loc[merged['kp'] < 3, 'value'].mean()
    drop = 100 * (storm_m - quiet_m) / quiet_m

    print(f"  {band}: N={N}, storm={storm_N}, quiet={quiet_N}, "
          f"blocks={N//BLOCK}, n_perm={n_valid}")
    print(f"         delta={obs:.0f}, drop={drop:.1f}%, p={p:.4f}")
    results[band] = {
        'N': N, 'N_storm': int(storm_N), 'N_quiet': int(quiet_N),
        'delta': round(float(obs)), 'drop_pct': round(float(drop), 1),
        'p_value': round(float(p), 4),
    }

# Compare with 6mo
sixmo = {'20m': {'delta': -17917, 'drop': -20.5, 'p': 0.0001},
         '40m': {'delta': -18000, 'drop': -21.9, 'p': 0.0001},
         '15m': {'delta': -6177, 'drop': -35.8, 'p': 0.0001}}

print("\n=== Comparison: 6mo vs 18mo ===")
for band in ['20m', '40m', '15m']:
    r = results.get(band, {})
    s = sixmo[band]
    d_chg = r.get('drop_pct', 0) - s['drop']
    print(f"  {band}: drop = {s['drop']}% -> {r.get('drop_pct', '?')}% ({d_chg:+.1f}pp), "
          f"storm = {s.get('N_storm', '?') if 'N_storm' in s else '49'} -> {r.get('N_storm', '?')}")

def pairwise_perm_test(merged, kp_low, kp_high, band, block_size=BLOCK, n_iter=N_ITER):
    """
    Compare drop for two Kp bins.
    H0: drop(Kp_low) == drop(Kp_high)

    Only includes hours where Kp falls into [kp_low, kp_high) or [kp_high, kp_high+1).
    Permutes block-level labels to test if mean residual differs between bins.
    """
    merged = merged.copy()
    if 'day_of_week' in merged.columns:
        merged['resid'] = merged['value'] - merged.groupby(
            ['month', 'hour_of_day', 'day_of_week'])['value'].transform('mean')
    else:
        merged['resid'] = merged['value'] - merged.groupby(
            ['month', 'hour_of_day'])['value'].transform('mean')

    # Select only the two bins
    mask_low = (merged['kp'] >= kp_low[0]) & (merged['kp'] < kp_low[1])
    mask_high = (merged['kp'] >= kp_high[0]) & (merged['kp'] < kp_high[1])

    n_low = mask_low.sum()
    n_high = mask_high.sum()

    if n_low < 3 or n_high < 3:
        return None, None, None, n_low, n_high

    # Observed difference: mean(resid | high) - mean(resid | low)
    obs_diff = merged.loc[mask_high, 'resid'].mean() - merged.loc[mask_low, 'resid'].mean()

    resid = merged['resid'].values
    kpv = merged['kp'].values
    n = len(resid)
    nb = n // block_size
    rblocks = resid[:nb * block_size].reshape(nb, block_size)
    kpv_trim = kpv[:nb * block_size]

    stats = []
    for _ in range(n_iter):
        order = RNG.permutation(nb)
        rp = rblocks[order].ravel()
        s_low = (kpv_trim >= kp_low[0]) & (kpv_trim < kp_low[1])
        s_high = (kpv_trim >= kp_high[0]) & (kpv_trim < kp_high[1])
        if s_low.sum() == 0 or s_high.sum() == 0:
            continue
        stats.append(rp[s_high].mean() - rp[s_low].mean())

    stats = np.array(stats)
    p = (np.abs(stats) >= np.abs(obs_diff)).mean()
    return float(obs_diff), float(p), len(stats), n_low, n_high


print("\n=== Pairwise Kp Bin Comparison (scale-dependence) ===\n")
pairwise_results = {}
bins = [
    ((5, 6), (6, 7), 'Kp 5-6 vs Kp 6-7'),
    ((6, 7), (7, 99), 'Kp 6-7 vs Kp 7+'),
    ((5, 6), (7, 99), 'Kp 5-6 vs Kp 7+'),
]

for band in ['20m', '40m', '15m']:
    sub = wspr[wspr['band'] == band].copy()
    merged = pd.merge(sub, kp_h, on='hour', how='inner').sort_values('hour').reset_index(drop=True)
    merged['day_of_week'] = merged['hour'].dt.dayofweek

    for (k_lo_0, k_lo_1), (k_hi_0, k_hi_1), label in bins:
        diff, p, n_valid, n_low, n_high = pairwise_perm_test(
            merged, (k_lo_0, k_lo_1), (k_hi_0, k_hi_1), band)
        if diff is None:
            print(f"  [{band}] {label}: INSUFFICIENT DATA (N_low={n_low}, N_high={n_high})")
            continue
        sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else 'ns'))
        print(f"  [{band}] {label}: delta={diff:.0f}, p={p:.4f} {sig} "
              f"(N_low={n_low}, N_high={n_high})")

        pairwise_results.setdefault(band, {})[label] = {
            'delta': round(float(diff)),
            'p_value': round(float(p), 4),
            'p_significant': bool(p < 0.05),
            'N_low': int(n_low),
            'N_high': int(n_high),
        }

# Save results
out = {'config': {'n_iter': N_ITER, 'block_size': BLOCK, 'period': '2024-04-01 .. 2025-09-30'},
       'results': results,
       'pairwise_bins': pairwise_results}
(ROOT / 'results').mkdir(exist_ok=True)
with open(str(ROOT / 'results' / 'perm_test_18mo_3band.json'), 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\n[OK] results/perm_test_18mo_3band.json")
