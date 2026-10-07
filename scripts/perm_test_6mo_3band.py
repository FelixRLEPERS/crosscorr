"""Phase 5-6: Permutation test + per-month robustness, 6 months x 3 bands."""
import pandas as pd, numpy as np, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(42)
N_ITER = 5000
BLOCK = 24

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'unified.parquet')

wspr = df[df['detector_type'] == 'wspr_hourly'].copy()
wspr['band'] = wspr['detector_id'].astype(str).str.replace('wspr_hourly_', '')
wspr['hour'] = wspr['timestamp_utc'].dt.floor('1h')
wspr['month'] = wspr['timestamp_utc'].dt.to_period('M')
wspr['hour_of_day'] = wspr['timestamp_utc'].dt.hour

kp = df[df['detector_type'] == 'kp'][['timestamp_utc', 'value']].copy()
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
        s = kpv >= 5
        q = kpv < 3
        if s.sum() == 0 or q.sum() == 0:
            continue
        stats.append(rp[s].mean() - rp[q].mean())

    stats = np.array(stats)
    p = (np.abs(stats) >= np.abs(obs)).mean()
    return float(obs), float(p), int(len(stats))


def per_month_check(merged, block_size=BLOCK, n_iter=N_ITER):
    results = []
    for month in sorted(merged['month'].unique()):
        mm = merged[merged['month'] == month].copy()
        if len(mm) < 30:
            continue
        sm = (mm['kp'] >= 5).sum()
        qm = (mm['kp'] < 3).sum()
        if sm < 1 or qm < 5:
            results.append({'month': str(month), 'N_storm': int(sm),
                           'status': 'insufficient'})
            continue
        obs, p, nv = block_perm_test(mm, block_size=BLOCK, n_iter=min(1000, n_iter))
        storm_m = mm.loc[mm['kp'] >= 5, 'value'].mean()
        quiet_m = mm.loc[mm['kp'] < 3, 'value'].mean()
        drop = 100 * (storm_m - quiet_m) / quiet_m if not pd.isna(storm_m) else None
        results.append({
            'month': str(month), 'N': len(mm),
            'N_storm': int(sm), 'N_quiet': int(qm),
            'delta': round(float(obs)) if obs else None,
            'drop_pct': round(float(drop), 1) if drop else None,
            'p_value': round(float(p), 4) if p else None,
        })
    return results


perm_results = {}
monthly_results = {}

for band in ['20m', '40m', '15m']:
    sub = wspr[wspr['band'] == band].copy()
    merged = pd.merge(sub, kp_h, on='hour', how='inner').sort_values('hour').reset_index(drop=True)

    N = len(merged)
    storm_N = (merged['kp'] >= 5).sum()
    quiet_N = (merged['kp'] < 3).sum()

    obs, p, nv = block_perm_test(merged)

    if obs is None:
        print(f"[{band}] Insufficient storm data (N_storm={storm_N})")
        perm_results[band] = {'status': 'insufficient', 'N': N}
        continue

    storm_m = merged.loc[merged['kp'] >= 5, 'value'].mean()
    quiet_m = merged.loc[merged['kp'] < 3, 'value'].mean()
    drop = 100 * (storm_m - quiet_m) / quiet_m

    print(f"\n=== {band} perm test ===")
    print(f"N={N}, storm={storm_N}, quiet={quiet_N}, blocks={N // BLOCK}")
    print(f"Delta: {obs:.0f}, drop: {drop:.1f}%, p={p:.4f} (n_perms={nv})")

    perm_results[band] = {
        'N': N, 'N_storm': int(storm_N), 'N_quiet': int(quiet_N),
        'delta': round(float(obs)), 'drop_pct': round(float(drop), 1),
        'p_value': round(float(p), 4),
    }

    monthly = per_month_check(merged)
    monthly_results[band] = monthly
    print(f"\n  Per-month:")
    for row in monthly:
        if 'delta' in row and row['delta'] is not None:
            print(f"    {row['month']}: N={row['N']}, storm={row['N_storm']}, "
                  f"delta={row['delta']}, drop={row.get('drop_pct','?')}%, p={row.get('p_value','??')}")
        else:
            print(f"    {row['month']}: N={row['N']}, storm={row['N_storm']} ({row.get('status','?')})")

out = {
    'config': {'n_iter': N_ITER, 'block_size': BLOCK},
    'permutation': perm_results,
    'per_month': {k: v for k, v in monthly_results.items()},
}

(ROOT / 'results').mkdir(exist_ok=True)
with open(str(ROOT / 'results' / 'perm_test_6mo_3band.json'), 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f"\n[OK] results/perm_test_6mo_3band.json")