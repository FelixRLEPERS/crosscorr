"""Phase 5: Permutation test 18mo x 3 band."""
import pandas as pd, numpy as np, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(42)
N_ITER = 5000
BLOCK = 24

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'unified.parquet')
full = df[(df['timestamp_utc'] >= '2024-04-01') & (df['timestamp_utc'] < '2025-10-01')]

wspr = full[full['detector_type'] == 'wspr_hourly'].copy()
wspr['band'] = wspr['detector_id'].astype(str).str.replace('wspr_hourly_', '')
wspr['hour'] = wspr['timestamp_utc'].dt.floor('1h')
wspr['month'] = wspr['timestamp_utc'].dt.to_period('M')
wspr['hour_of_day'] = wspr['timestamp_utc'].dt.hour

kp = full[full['detector_type'] == 'kp'][['timestamp_utc', 'value']].copy()
kp.columns = ['timestamp_utc', 'kp']
kp['hour'] = kp['timestamp_utc'].dt.floor('1h')
kp_h = kp.groupby('hour')['kp'].mean().reset_index()


def block_perm_test(merged, block_size=BLOCK, n_iter=N_ITER):
    merged = merged.copy()
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
        s = kpv >= 5; q = kpv < 3
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

out = {'config': {'n_iter': N_ITER, 'block_size': BLOCK, 'period': '2024-04-01 .. 2025-09-30'},
       'results': results}
(ROOT / 'results').mkdir(exist_ok=True)
with open(str(ROOT / 'results' / 'perm_test_18mo_3band.json'), 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f"\n[OK] results/perm_test_18mo_3band.json")