"""EDA: WSPR spots/hour vs Kp index — January 2025.

Гипотеза: геомагнитная активность (Kp) влияет на число WSPR-спотов на 20m.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "eda"
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
jan_start = pd.Timestamp("2025-01-01", tz="UTC")
jan_end = pd.Timestamp("2025-02-01", tz="UTC")

wspr = df[(df["detector_type"] == "wspr_hourly")
          & (df["timestamp_utc"] >= jan_start)
          & (df["timestamp_utc"] < jan_end)].copy()
wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
wspr_hourly = wspr.groupby("hour")["value"].sum().reset_index()
wspr_hourly = wspr_hourly.rename(columns={"value": "spots"})

kp = df[(df["detector_type"] == "kp")
        & (df["timestamp_utc"] >= jan_start)
        & (df["timestamp_utc"] < jan_end)].copy()
kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
kp_hourly = kp.groupby("hour")["value"].mean().reset_index()
kp_hourly = kp_hourly.rename(columns={"value": "kp"})

merged = pd.merge(wspr_hourly, kp_hourly, on="hour", how="inner")
merged["hour_of_day"] = merged["hour"].dt.hour
merged["day"] = merged["hour"].dt.date

print(f"Merged rows: {len(merged)}")
print(f"Date range: {merged['hour'].min()} .. {merged['hour'].max()}")
print(f"Days with data: {merged['day'].nunique()}")

r_spearman = merged["spots"].corr(merged["kp"], method="spearman")
r_pearson = merged["spots"].corr(merged["kp"], method="pearson")

# === Plot 1: Time series ===
fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)

axes[0].plot(merged["hour"], merged["spots"], "b-", lw=0.6)
axes[0].set_ylabel("Spots per hour (20m)")
axes[0].set_title("January 2025 - WSPR hourly spots")
axes[0].grid(alpha=0.3)

axes[1].plot(merged["hour"], merged["kp"], "r-", lw=0.8, drawstyle="steps-post")
axes[1].set_ylabel("Kp index")
axes[1].set_xlabel("Date")
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(str(OUT_DIR / "timeseries_jan2025.png"), dpi=120)
plt.close()
print("[OK] timeseries_jan2025.png")

# === Plot 2: Scatter + heatmap ===
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

axes[0].scatter(merged["kp"], merged["spots"], alpha=0.3, s=12, c="steelblue")
axes[0].set_xlabel("Kp")
axes[0].set_ylabel("Spots per hour")
axes[0].set_title("Raw correlation: spots vs Kp")
axes[0].text(0.05, 0.95,
             f"Spearman r = {r_spearman:.3f}\nPearson r = {r_pearson:.3f}",
             transform=axes[0].transAxes, fontsize=11, va="top",
             bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8})
axes[0].grid(alpha=0.3)

merged["kp_bin"] = pd.cut(merged["kp"], bins=[0, 1, 2, 3, 4, 9],
                          labels=["0-1", "1-2", "2-3", "3-4", "4+"])
pivot = merged.pivot_table(values="spots", index="kp_bin",
                           columns="hour_of_day", aggfunc="mean")
im = axes[1].imshow(pivot.values, aspect="auto", cmap="YlOrRd",
                    origin="lower")
axes[1].set_xlabel("Hour of day (UTC)")
axes[1].set_title("Mean spots/hour by Kp bin x hour")
axes[1].set_yticks(range(len(pivot.index)))
axes[1].set_yticklabels(pivot.index)
cbar = plt.colorbar(im, ax=axes[1])
cbar.set_label("Mean spots/hour")

plt.tight_layout()
plt.savefig(str(OUT_DIR / "scatter_heatmap_jan2025.png"), dpi=120)
plt.close()
print("[OK] scatter_heatmap_jan2025.png")

# === Plot 3: Diurnal cycle ===
hourly_mean = merged.groupby("hour_of_day")["spots"].mean()
hourly_std = merged.groupby("hour_of_day")["spots"].std()

fig, ax = plt.subplots(figsize=(10, 5))
ax.errorbar(hourly_mean.index, hourly_mean.values, yerr=hourly_std.values,
            fmt="bo-", capsize=3, markersize=6)
ax.set_xlabel("Hour of day (UTC)")
ax.set_ylabel("Mean spots/hour +/- 1 sigma")
ax.set_title("Diurnal cycle - WSPR 20m (January 2025)")
ax.grid(alpha=0.3)
ax.set_xticks(range(0, 24, 2))
ax.set_xlim(-0.5, 23.5)
plt.tight_layout()
plt.savefig(str(OUT_DIR / "diurnal_cycle_jan2025.png"), dpi=120)
plt.close()
print("[OK] diurnal_cycle_jan2025.png")

# === Summary ===
daily_spots = merged.groupby("day")["spots"].sum()
daily_kp = merged.groupby("day")["kp"].mean()

print()
print("=== Key Numbers ===")
print(f"Total hours: {len(merged)}")
print(f"Mean spots/day: {daily_spots.mean():.0f}")
print(f"Std spots/day:  {daily_spots.std():.0f}")
print(f"Mean Kp: {merged['kp'].mean():.2f}")
print(f"Std Kp:  {merged['kp'].std():.2f}")
print(f"Max Kp:  {merged['kp'].max():.1f}")
print(f"Spearman rho(spots, Kp): {r_spearman:.4f}")
print(f"Pearson r(spots, Kp):     {r_pearson:.4f}")
print()

top_kp = daily_kp.nlargest(5)
print("=== Top-5 Kp days ===")
for day, kp_val in top_kp.items():
    spots_val = daily_spots[day]
    print(f"  {day}: Kp={kp_val:.1f}, spots={spots_val:.0f}")

print()
print("=== Diurnal profile (spots/hour) ===")
for h in range(24):
    val = hourly_mean.get(h)
    std = hourly_std.get(h)
    if pd.notna(val):
        print(f"  {h:02d} UTC: {val:.0f} +/- {std:.0f}")
    else:
        print(f"  {h:02d} UTC: no data")

with open(str(OUT_DIR / "summary_jan2025.json"), "w", encoding="utf-8") as f:
    json.dump({
        "hours": len(merged),
        "mean_spots_per_day": float(daily_spots.mean()),
        "std_spots_per_day": float(daily_spots.std()),
        "mean_kp": float(merged["kp"].mean()),
        "std_kp": float(merged["kp"].std()),
        "max_kp": float(merged["kp"].max()),
        "spearman_rho": float(r_spearman),
        "pearson_r": float(r_pearson),
    }, f, indent=2, ensure_ascii=False)

print()
print("[DONE] All plots saved to results/eda/")
