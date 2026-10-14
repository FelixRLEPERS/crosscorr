"""Phase D.2-D.3: point estimate + block bootstrap CI for training live download.

Reading results/training_live_2026-10-13.parquet (39456 rows).
Three-state labels: storm kp>=5, quiet kp<3, unsettled excluded.
Point = mean(quiet spots) - mean(storm spots), value metric (no baseline).
Block bootstrap: 24h blocks, 1000 resamples, seed 42, time-sorted input.

Dependencies:
- Input: results/training_live_2026-10-13.parquet (gitignored;
  reproducible from scripts/training_live_2026-10-13.py via
  wspr.live download, ~30 min).

See audit/FINDING_HELDOUT_LIVE_2026-10-13.md for context.
"""

import numpy as np
import pandas as pd


def block_bootstrap_mean_diff(values, states, block=24, n_boot=1000, seed=42):
    """Block bootstrap 95% CI for mean(quiet) - mean(storm).

    values: array of spots per hour (sorted by time)
    states: array of 'storm'/'quiet'/'unsettled'
    block: 24 (hours)
    """
    rng = np.random.default_rng(seed)
    n = len(values)
    n_blocks = n // block
    v = values[: n_blocks * block].reshape(n_blocks, block)
    s = states[: n_blocks * block].reshape(n_blocks, block)

    is_storm = states == "storm"
    is_quiet = states == "quiet"
    point = values[is_quiet].mean() - values[is_storm].mean()

    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_blocks, n_blocks)
        v_b = v[idx].ravel()
        s_b = s[idx].ravel()
        is_s_b = s_b == "storm"
        is_q_b = s_b == "quiet"
        if is_s_b.sum() == 0 or is_q_b.sum() == 0:
            continue
        diffs.append(v_b[is_q_b].mean() - v_b[is_s_b].mean())

    diffs = np.array(diffs)
    ci_lo = np.percentile(diffs, 2.5)
    ci_hi = np.percentile(diffs, 97.5)
    return point, ci_lo, ci_hi, len(diffs)


df = pd.read_parquet("results/training_live_2026-10-13.parquet")
sub = df.dropna(subset=["kp"]).copy()
sub["state"] = "unsettled"
sub.loc[sub["kp"] >= 5, "state"] = "storm"
sub.loc[sub["kp"] < 3, "state"] = "quiet"
sub = sub.sort_values("hour_utc").reset_index(drop=True)

results = {}
print("=== D.3a: block bootstrap (24h, n_boot=1000, seed=42) ===")
for band in ["15m", "20m", "40m"]:
    b = sub[sub["band_mhz"] == band].sort_values("hour_utc").reset_index(drop=True)
    values = b["spots"].values
    states = b["state"].to_numpy(dtype=object)
    point, ci_lo, ci_hi, n_used = block_bootstrap_mean_diff(values, states)
    results[band] = {
        "point": point,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "n_boot_used": n_used,
        "n_quiet": int((states == "quiet").sum()),
        "n_storm": int((states == "storm").sum()),
    }
    print(f"  {band}: point={point:.0f} CI=[{ci_lo:.0f}, {ci_hi:.0f}] n_boot_used={n_used}")

print("\n=== vs paper frozen ===")
frozen = {"15m": 5178, "20m": 20421, "40m": 18285}
for band in ["15m", "20m", "40m"]:
    r = results[band]
    print(
        f"  {band}: live={r['point']:.0f} frozen={frozen[band]} "
        f"delta={r['point'] - frozen[band]:+.0f} "
        f"CI=[{r['ci_lo']:.0f}, {r['ci_hi']:.0f}] "
        f"covers_frozen={r['ci_lo'] <= frozen[band] <= r['ci_hi']}"
    )
