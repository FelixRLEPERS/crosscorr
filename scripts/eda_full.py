"""EDA: WSPR spots/hour vs Kp/Dst — January + October combined.

Key features:
- Seasonal residual control: residual by (month x hour_of_day)
- Block permutation test (block=24h) to account for autocorrelation
- ESS estimation (AR(1))
- Separate analysis per month to check consistency
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "eda"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(42)
N_PERM = 10_000
BLOCK_HRS = 24

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
all_start = pd.Timestamp("2024-10-01", tz="UTC")
all_end = pd.Timestamp("2025-02-01", tz="UTC")

# --- WSPR hourly ---
wspr = df[(df["detector_type"] == "wspr_hourly")
          & (df["timestamp_utc"] >= all_start)
          & (df["timestamp_utc"] < all_end)].copy()
wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
wspr_h = wspr.groupby("hour")["value"].sum().reset_index()
wspr_h = wspr_h.rename(columns={"value": "spots"})

# --- Kp ---
kp = df[(df["detector_type"] == "kp")
        & (df["timestamp_utc"] >= all_start)
        & (df["timestamp_utc"] < all_end)].copy()
kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
kp_h = kp.groupby("hour")["value"].mean().reset_index()
kp_h = kp_h.rename(columns={"value": "kp"})

# --- Dst ---
dst = df[(df["detector_type"] == "dst")
         & (df["timestamp_utc"] >= all_start)
         & (df["timestamp_utc"] < all_end)].copy()
dst["hour"] = dst["timestamp_utc"].dt.floor("1h")
dst_h = dst.groupby("hour")["value"].mean().reset_index()
dst_h = dst_h.rename(columns={"value": "dst_nt"})

# ---------------------------------------------------------------------------
# Merge & residuals
# ---------------------------------------------------------------------------
# Kp merge
m_kp = pd.merge(wspr_h, kp_h, on="hour", how="inner")
m_kp["hour_of_day"] = m_kp["hour"].dt.hour
m_kp["month"] = m_kp["hour"].dt.to_period("M")

# Seasonal residual: subtract mean by (month x hour)
diurnal = m_kp.groupby(["month", "hour_of_day"])["spots"].transform("mean")
m_kp["spots_resid"] = m_kp["spots"] - diurnal

# Dst merge
m_dst = pd.merge(wspr_h, dst_h, on="hour", how="inner")
m_dst["hour_of_day"] = m_dst["hour"].dt.hour
m_dst["month"] = m_dst["hour"].dt.to_period("M")
diurnal_d = m_dst.groupby(["month", "hour_of_day"])["spots"].transform("mean")
m_dst["spots_resid"] = m_dst["spots"] - diurnal_d

# ---------------------------------------------------------------------------
# Block permutation test
# ---------------------------------------------------------------------------
def block_permutation_test(values, condition_mask, n_perm=10_000, block=24):
    """One-sided block permutation test: H0: no effect of condition.

    Statistic: mean(values | condition) - mean(values | ~condition).
    Blocks: every 'block' consecutive rows form a block (shuffled together).
    """
    n = len(values)
    n_blocks = n // block
    values = values[:n_blocks * block]
    condition_mask = condition_mask[:n_blocks * block]

    v = values.values if hasattr(values, "values") else np.array(values)
    c = condition_mask.values if hasattr(condition_mask, "values") else np.array(condition_mask)

    # Observed
    obs = v[c].mean() - v[~c].mean()

    # Permutation by blocks
    blocks_v = v.reshape(n_blocks, block)
    blocks_c = c.reshape(n_blocks, block)
    perm_stats = np.empty(n_perm)

    for i in range(n_perm):
        idx = RNG.permutation(n_blocks)
        cp = blocks_c[idx].ravel()
        perm_stats[i] = v[cp].mean() - v[~cp].mean()

    # p-value: fraction of |perm| >= |obs|
    p = np.mean(np.abs(perm_stats) >= np.abs(obs))
    return obs, p, perm_stats


def block_bootstrap(values, n_boot=1000, block=24):
    """Block bootstrap for CI."""
    n = len(values)
    n_blocks = n // block
    v = values[:n_blocks * block]
    blocks = v.reshape(n_blocks, block)
    means = np.empty(n_boot)
    for i in range(n_boot):
        idx = RNG.choice(n_blocks, size=n_blocks, replace=True)
        means[i] = blocks[idx].ravel().mean()
    return np.percentile(means, [2.5, 97.5])


def ess_ar1(series):
    """Effective sample size for AR(1) process."""
    x = series.dropna().values
    if len(x) < 2:
        return len(x)
    rho = np.corrcoef(x[:-1], x[1:])[0, 1]
    rho = max(min(rho, 0.99), -0.99)
    return int(len(x) * (1 - rho) / (1 + rho))


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------
print("=" * 60)
print("COMBINED ANALYSIS: October 2024 + January 2025")
print("=" * 60)

# --- Kp ---
print(f"\nKp merge: {len(m_kp)} rows")
for month in sorted(m_kp["month"].unique()):
    mm = m_kp[m_kp["month"] == month]
    print(f"  {month}: {len(mm)} rows, mean Kp={mm['kp'].mean():.2f}")

# Binned analysis
bins = [(0, 3, "KP < 3"), (3, 4, "KP 3-4"), (4, 5, "KP 4-5"),
        (5, 10, "KP >= 5"), (6, 10, "KP >= 6")]

print("\n--- Binned Kp (residuals) ---")
kp_low = m_kp["kp"] < 3
kp_high = m_kp["kp"] >= 5

obs_kp, p_kp_block, perm_stats_kp = block_permutation_test(
    m_kp["spots_resid"], kp_high, n_perm=N_PERM, block=BLOCK_HRS
)

# Naive permutation (no blocks)
obs_kp_naive = m_kp["spots_resid"][kp_high].mean() - m_kp["spots_resid"][kp_low].mean()
p_kp_naive = np.mean(np.abs(perm_stats_kp) >= np.abs(obs_kp_naive))

# ESS
ess = ess_ar1(m_kp["spots_resid"])
print(f"ESS (AR1): {ess} (raw N: {len(m_kp)})")
print(f"Autocorrelation ratio: {ess}/{len(m_kp)} = {ess/len(m_kp):.2f}")

for lo, hi, label in bins:
    mask = (m_kp["kp"] >= lo) & (m_kp["kp"] < hi)
    n = mask.sum()
    val = m_kp["spots_resid"][mask]
    mean_v = val.mean()
    ci = block_bootstrap(val.values) if n >= 24 else (np.nan, np.nan)
    print(f"  {label:12s}: N={n:4d}, mean={mean_v:+.0f}, "
          f"95%CI=[{ci[0]:.0f}, {ci[1]:.0f}]")

print(f"\nStatistic mean(KP>=5) - mean(KP<3): {obs_kp:+.0f}")
print(f"Block permutation p-value (block={BLOCK_HRS}h): {p_kp_block:.4f}")
print(f"Naive permutation p-value:                    {p_kp_naive:.4f}")

# --- Dst ---
print(f"\n--- Binned Dst (residuals) ---")
print(f"Dst merge: {len(m_dst)} rows")

dst_bins = [(-200, -50, "Dst < -50"), (-50, -20, "Dst -50..-20"),
            (-20, 0, "Dst -20..0"), (0, 20, "Dst 0..20")]

dst_low = m_dst["dst_nt"] < -50
dst_high = m_dst["dst_nt"] > -20

obs_dst, p_dst_block, _ = block_permutation_test(
    m_dst["spots_resid"], dst_low, n_perm=N_PERM, block=BLOCK_HRS
)

for lo, hi, label in dst_bins:
    mask = (m_dst["dst_nt"] >= lo) & (m_dst["dst_nt"] < hi)
    n = mask.sum()
    val = m_dst["spots_resid"][mask]
    mean_v = val.mean()
    ci = block_bootstrap(val.values) if n >= 24 else (np.nan, np.nan)
    print(f"  {label:15s}: N={n:4d}, mean={mean_v:+.0f}, "
          f"95%CI=[{ci[0]:.0f}, {ci[1]:.0f}]")

print(f"\nStatistic mean(Dst<-50) - mean(Dst>-20): {obs_dst:+.0f}")
print(f"Block permutation p-value:                   {p_dst_block:.4f}")

# ---------------------------------------------------------------------------
# Per-month check
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print("PER-MONTH CHECK")
print(f"{'='*60}")

for month in sorted(m_kp["month"].unique()):
    mm = m_kp[m_kp["month"] == month]
    k_low = mm["kp"] < 3
    k_high = mm["kp"] >= 5
    n_high = k_high.sum()
    obs_m, p_m, _ = block_permutation_test(
        mm["spots_resid"], k_high, n_perm=N_PERM, block=BLOCK_HRS
    )
    print(f"  {month}: Kp>=5 N={n_high}, obs={obs_m:+.0f}, "
          f"block-p={p_m:.4f}")

# Dst per month
for month in sorted(m_dst["month"].unique()):
    mm = m_dst[m_dst["month"] == month]
    d_low = mm["dst_nt"] < -50
    d_high = mm["dst_nt"] > -20
    n_low = d_low.sum()
    if n_low > 0:
        obs_dm, p_dm, _ = block_permutation_test(
            mm["spots_resid"], d_low, n_perm=N_PERM, block=BLOCK_HRS
        )
        print(f"  Dst {month}: Dst<-50 N={n_low}, obs={obs_dm:+.0f}, "
              f"block-p={p_dm:.4f}")
    else:
        print(f"  Dst {month}: Dst<-50 N=0 (skipped)")

# ---------------------------------------------------------------------------
# PLOTS
# ---------------------------------------------------------------------------

# Plot 1: Binned Kp
fig, axes = plt.subplots(1, 3, figsize=(20, 5))

k_bins = [("KP<3", m_kp["kp"] < 3, "steelblue"),
          ("KP 3-4", (m_kp["kp"] >= 3) & (m_kp["kp"] < 4), "skyblue"),
          ("KP 4-5", (m_kp["kp"] >= 4) & (m_kp["kp"] < 5), "coral"),
          ("KP>=5", m_kp["kp"] >= 5, "firebrick"),
          ("KP>=6", m_kp["kp"] >= 6, "darkred")]

ax = axes[0]
x_labels, x_means, x_ci_low, x_ci_high = [], [], [], []
for label, mask, color in k_bins:
    val = m_kp["spots_resid"][mask].values
    n = len(val)
    x_labels.append(f"{label}\nN={n}")
    x_means.append(val.mean())
    if n >= 24:
        ci = block_bootstrap(val, n_boot=1000, block=BLOCK_HRS)
        x_ci_low.append(ci[0])
        x_ci_high.append(ci[1])
    else:
        x_ci_low.append(np.nan)
        x_ci_high.append(np.nan)

xx = range(len(x_labels))
colors = ["steelblue", "skyblue", "coral", "firebrick", "darkred"]
for i in range(len(xx)):
    ax.bar(i, x_means[i], color=colors[i], edgecolor="black", linewidth=0.5)
    if not np.isnan(x_ci_low[i]):
        lo = max(x_means[i] - x_ci_low[i], 0)
        hi = max(x_ci_high[i] - x_means[i], 0)
        ax.errorbar(i, x_means[i], yerr=[[lo], [hi]], fmt="none", color="black", capsize=4)
ax.axhline(0, color="gray", ls="--", lw=0.8)
ax.set_xticks(xx)
ax.set_xticklabels(x_labels, fontsize=9)
ax.set_ylabel("Mean residual spots/hour")
ax.set_title(f"Kp bins (2 months)\nBlock-p(KP>=5 vs KP<3) = {p_kp_block:.4f}")
ax.grid(alpha=0.3, axis="y")

# Plot 2: Dst bins
ax = axes[1]
d_labels = ["Dst<-50", "-50..-20", "-20..0", "0..20"]
d_colors = ["firebrick", "coral", "skyblue", "steelblue"]
for i, (lo, hi, _) in enumerate(dst_bins):
    mask = (m_dst["dst_nt"] >= lo) & (m_dst["dst_nt"] < hi)
    val = m_dst["spots_resid"][mask].values
    n = len(val)
    mean_v = val.mean()
    ax.bar(i, mean_v, color=d_colors[i], edgecolor="black", linewidth=0.5)
    if n >= 24:
        ci = block_bootstrap(val)
        ax.errorbar(i, mean_v, yerr=[[max(mean_v - ci[0], 0)], [max(ci[1] - mean_v, 0)]],
                   fmt="none", color="black", capsize=4)
    ax.annotate(f"N={n}", (i, mean_v + 300), ha="center", fontsize=8)
ax.axhline(0, color="gray", ls="--", lw=0.8)
ax.set_xticks(range(4))
ax.set_xticklabels(d_labels)
ax.set_ylabel("Mean residual spots/hour")
ax.set_title(f"Dst bins (2 months)\nBlock-p(Dst<-50 vs Dst>-20) = {p_dst_block:.4f}")
ax.grid(alpha=0.3, axis="y")

# Plot 3: Scatter residual vs Kp
ax = axes[2]
ax.scatter(m_kp["kp"], m_kp["spots_resid"], alpha=0.3, s=10, c="coral")
ax.set_xlabel("Kp")
ax.set_ylabel("Residual spots (seasonal diurnal)")
spearman = m_kp["spots_resid"].corr(m_kp["kp"], method="spearman")
ax.set_title(f"Residual vs Kp\nSpearman = {spearman:+.3f}, Block-p = {p_kp_block:.4f}")
ax.axhline(0, color="gray", ls="--", lw=0.8)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(str(OUT / "binned_kp_dst_2months.png"), dpi=120)
plt.close()
print("\n[OK] binned_kp_dst_2months.png")

# Plot 4: Time series
fig, axes = plt.subplots(3, 1, figsize=(18, 10), sharex=True)

axes[0].plot(m_kp["hour"], m_kp["spots"], "b-", lw=0.4, alpha=0.7)
axes[0].set_ylabel("Spots/hour (20m)")
axes[0].set_title("October 2024 + January 2025")
axes[0].grid(alpha=0.3)
# Mark Kp>=5
for hour in m_kp[m_kp["kp"] >= 5]["hour"]:
    axes[0].axvline(hour, color="red", alpha=0.15, lw=0.5)

axes[1].plot(m_kp["hour"], m_kp["kp"], "r-", lw=0.6, drawstyle="steps-post")
axes[1].set_ylabel("Kp")
axes[1].axhline(5, color="red", ls="--", lw=0.8, alpha=0.5)
axes[1].grid(alpha=0.3)

axes[2].plot(m_kp["hour"], m_kp["spots_resid"], "coral", lw=0.4, alpha=0.7)
axes[2].set_ylabel("Residual spots")
axes[2].set_xlabel("Date")
axes[2].axhline(0, color="gray", ls="--", lw=0.8)
axes[2].grid(alpha=0.3)
for hour in m_kp[m_kp["kp"] >= 5]["hour"]:
    axes[2].axvline(hour, color="red", alpha=0.15, lw=0.5)

plt.tight_layout()
plt.savefig(str(OUT / "timeseries_2months.png"), dpi=120)
plt.close()
print("[OK] timeseries_2months.png")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"Period: {m_kp['hour'].min().date()} -- {m_kp['hour'].max().date()}")
print(f"Total Kp rows: {len(m_kp)}")
print(f"ESS: {ess} (autocorr={ess/len(m_kp):.2f})")
print(f"Hours KP>=5: {kp_high.sum()} (in {m_kp[ kp_high]['hour'].dt.date.nunique()} days)")
print(f"Hours KP>=6: {(m_kp['kp']>=6).sum()}")
print(f"Hours Dst<-50: {dst_low.sum()}")
print()
print("--- Kp results ---")
print(f"mean(KP>=5) - mean(KP<3): {obs_kp:+.0f}")
print(f"Block permutation p-value: {p_kp_block:.4f}")
print(f"Naive p-value:             {p_kp_naive:.4f}")
print(f"Significant (block-p<0.05)? {'YES' if p_kp_block < 0.05 else 'NO'}")
print(f"Significant (block-p<0.10)? {'YES' if p_kp_block < 0.10 else 'NO'}")
print()
print("--- Dst results ---")
print(f"mean(Dst<-50) - mean(Dst>-20): {obs_dst:+.0f}")
print(f"Block permutation p-value:      {p_dst_block:.4f}")
print(f"Significant (block-p<0.05)?     {'YES' if p_dst_block < 0.05 else 'NO'}")

# Save JSON
summary = {
    "period": f"{m_kp['hour'].min().date()} -- {m_kp['hour'].max().date()}",
    "total_kp_rows": len(m_kp),
    "total_dst_rows": len(m_dst),
    "ess": ess,
    "autocorr_ratio": float(ess / len(m_kp)),
    "hours_kp_ge_5": int(kp_high.sum()),
    "hours_kp_ge_6": int((m_kp["kp"] >= 6).sum()),
    "hours_dst_lt_minus50": int(dst_low.sum()),
    "kp_observed_diff": float(obs_kp),
    "kp_block_p_value": float(p_kp_block),
    "kp_naive_p_value": float(p_kp_naive),
    "kp_spearman_resid": float(spearman),
    "kp_significant_005": "yes" if p_kp_block < 0.05 else "no",
    "kp_significant_010": "yes" if p_kp_block < 0.10 else "no",
    "dst_observed_diff": float(obs_dst),
    "dst_block_p_value": float(p_dst_block),
    "dst_significant_005": "yes" if p_dst_block < 0.05 else "no",
}
with open(str(OUT / "summary_2months.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"\n[OK] summary_2months.json")
print("[DONE] All outputs saved to results/eda/")