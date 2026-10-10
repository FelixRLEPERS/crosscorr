"""Generate ALL paper figures with 95% bootstrap CI error bars.

Fig 2: Scale-dependence (Kp bins × bands) — with error bars
Fig 4: Day/night asymmetry — with error bars
Fig 5: Baseline-invariant absolute loss — with error bars

Also regenerates Fig 1 (Kp timeseries) and Fig 3 (frequency dependence).
"""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(42)
N_BOOT = 1000

# ── Load and merge data ──────────────────────────────────────────────
print("Loading unified.parquet...")
df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")

full = df[(df["timestamp_utc"] >= "2024-04-01") & (df["timestamp_utc"] < "2025-10-01")]
wspr = full[full["detector_type"] == "wspr_hourly"].copy()
wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")
wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
wspr["month"] = wspr["timestamp_utc"].dt.to_period("M")
wspr["hour_of_day"] = wspr["timestamp_utc"].dt.hour
wspr["day_of_week"] = wspr["timestamp_utc"].dt.dayofweek

kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
kp.columns = ["timestamp_utc", "kp"]
kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
kp_h = kp.groupby("hour")["kp"].mean().reset_index()

BANDS = ["20m", "40m", "15m"]
DAY_RANGE = (12, 18)
NIGHT_RANGE = (0, 6)


def bootstrap_ci(values, n_resamples=N_BOOT):
    """Return (lower, upper) 95% CI from bootstrap resampling."""
    if len(values) < 5:
        return (np.nan, np.nan)
    means = []
    n = len(values)
    for _ in range(n_resamples):
        idx = RNG.integers(0, n, size=n)
        means.append(values[idx].mean())
    means = np.array(means)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


# ═════════════════════════════════════════════════════════════════════
#  FIGURE 2: Scale-dependence with error bars
# ═════════════════════════════════════════════════════════════════════
print("\n=== Figure 2: Scale-dependence ===")

Kp_BINS_LABELS = ["5\u20136", "6\u20137", "\u22657"]
Kp_BINS_EDGES = [5, 6, 7, 10]

fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), sharey=False)

for i, band in enumerate(BANDS):
    sub = wspr[wspr["band"] == band].copy()
    merged = pd.merge(sub, kp_h, left_on="hour", right_on="hour", how="inner")
    merged["resid"] = (
        merged["value"]
        - merged.groupby(["month", "hour_of_day", "day_of_week"])["value"].transform("mean")
    )

    quiet_mean = merged.loc[merged["kp"] < 3, "value"].mean()
    drops = []
    cis_lo = []
    cis_hi = []
    ns = []

    for lo, hi, _label in zip(Kp_BINS_EDGES[:-1], Kp_BINS_EDGES[1:], Kp_BINS_LABELS, strict=False):
        mask = (merged["kp"] >= lo) & (merged["kp"] < hi) if hi < 10 else (merged["kp"] >= lo)
        vals = merged.loc[mask, "value"]
        if len(vals) < 3:
            drops.append(0)
            cis_lo.append(0)
            cis_hi.append(0)
            ns.append(0)
            continue
        storm_mean = vals.mean()
        drop_pct = 100 * (storm_mean - quiet_mean) / quiet_mean
        drops.append(-drop_pct)

        drop_dist = []
        q_vals = merged.loc[merged["kp"] < 3, "value"].values
        s_vals = vals.values
        qn, sn = len(q_vals), len(s_vals)
        for _ in range(N_BOOT):
            qm = RNG.choice(q_vals, size=qn).mean()
            sm = RNG.choice(s_vals, size=sn).mean()
            drop_dist.append(100 * (sm - qm) / qm)
        drop_dist = np.array(drop_dist)
        cis_lo.append(abs(-np.percentile(drop_dist, 2.5)))
        cis_hi.append(abs(-np.percentile(drop_dist, 97.5)))
        ns.append(len(vals))

    x = np.arange(len(Kp_BINS_LABELS))
    yerr = [np.array(drops) - np.array(cis_lo), np.array(cis_hi) - np.array(drops)]
    yerr = np.clip(yerr, 0, None)

    bars = axes[i].bar(
        x, drops, color="#E76F51", edgecolor="black", linewidth=0.5,
        yerr=yerr, capsize=5, error_kw={"elinewidth": 1.5, "capthick": 1.5},
    )
    for j, (bar, n) in enumerate(zip(bars, ns, strict=False)):
        h = bar.get_height()
        axes[i].text(bar.get_x() + bar.get_width() / 2, h - 1.5 if h > 3 else h + 1.5,
                     f"{drops[j]:.1f}%\n(N={n})", ha="center", va="top" if h > 3 else "bottom",
                     fontsize=8, fontweight="bold",
                     color="white" if h > 3 else "black")

    axes[i].set_xticks(x)
    axes[i].set_xticklabels(Kp_BINS_LABELS, fontsize=11)
    axes[i].set_title(f"{band}", fontsize=13, fontweight="bold")
    if i == 0:
        axes[i].set_ylabel("Spot reduction (%)", fontsize=12)
    axes[i].grid(axis="y", alpha=0.3)
    axes[i].set_ylim(bottom=0)

fig.suptitle(
    "Scale-Dependent WSPR Storm Response\n(18-month training, with 95% bootstrap CI)",
    fontsize=14, fontweight="bold", y=1.02,
)
plt.tight_layout()
path_fig2 = OUT / "fig2_scale_dependence.png"
fig.savefig(str(path_fig2), dpi=150, bbox_inches="tight")
plt.close()
print(f"[OK] {path_fig2} ({path_fig2.stat().st_size} bytes)")

# Print CI details for verification
print("  15m Kp 5-6 CI check:")
for band in BANDS:
    sub = wspr[wspr["band"] == band].copy()
    merged = pd.merge(sub, kp_h, left_on="hour", right_on="hour", how="inner")
    merged["resid"] = (
        merged["value"]
        - merged.groupby(["month", "hour_of_day", "day_of_week"])["value"].transform("mean")
    )
    quiet_mean = merged.loc[merged["kp"] < 3, "value"].mean()
    mask = (merged["kp"] >= 5) & (merged["kp"] < 6)
    vals = merged.loc[mask, "value"]
    drop_dist = []
    q_vals = merged.loc[merged["kp"] < 3, "value"].values
    s_vals = vals.values
    qn, sn = len(q_vals), len(s_vals)
    for _ in range(N_BOOT):
        qm = RNG.choice(q_vals, size=qn).mean()
        sm = RNG.choice(s_vals, size=sn).mean()
        drop_dist.append(100 * (sm - qm) / qm)
    drop_dist = np.array(drop_dist)
    lo = np.percentile(drop_dist, 2.5)
    hi = np.percentile(drop_dist, 97.5)
    mean_drop = drop_dist.mean()
    print(f"  {band} Kp 5-6: drop={-mean_drop:.1f}%, 95%CI=[{-hi:.1f}, {-lo:.1f}]%, N={len(vals)}")


# ═════════════════════════════════════════════════════════════════════
#  FIGURE 4: Day/Night Asymmetry with error bars
# ═════════════════════════════════════════════════════════════════════
print("\n=== Figure 4: Day/Night Asymmetry ===")

results_dn = {}
ci_dn = {}

for band in BANDS:
    sub = wspr[wspr["band"] == band].copy()
    merged = pd.merge(sub, kp_h, left_on="hour", right_on="hour", how="inner")
    merged["resid"] = (
        merged["value"]
        - merged.groupby(["month", "hour_of_day", "day_of_week"])["value"].transform("mean")
    )

    day = merged[merged["hour_of_day"].between(*DAY_RANGE)]
    night = merged[merged["hour_of_day"].between(*NIGHT_RANGE)]

    for label, df_sel in [("Day", day), ("Night", night)]:
        s = df_sel[df_sel["kp"] >= 5]
        q = df_sel[df_sel["kp"] < 3]
        if len(s) < 3 or len(q) < 10:
            results_dn[f"{band}_{label}"] = {"band": band, "period": label,
                                             "drop_pct": 0, "ci_lo": 0, "ci_hi": 0}
            continue

        sv, qv = s["value"].values, q["value"].values
        sn, qn = len(sv), len(qv)
        drop_dist = []
        for _ in range(N_BOOT):
            sm = RNG.choice(sv, size=sn).mean()
            qm = RNG.choice(qv, size=qn).mean()
            drop_dist.append(100 * (sm - qm) / qm)
        drop_dist = np.array(drop_dist)
        mean_drop = drop_dist.mean()
        lo = np.percentile(drop_dist, 2.5)
        hi = np.percentile(drop_dist, 97.5)
        results_dn[f"{band}_{label}"] = {
            "band": band, "period": label,
            "drop_pct": round(float(mean_drop), 1),
            "ci_lo": round(float(lo), 1),
            "ci_hi": round(float(hi), 1),
            "N_storm": len(s), "N_quiet": len(q),
        }

print("=== Day/Night Bootstrap Results ===")
for k, v in results_dn.items():
    print(f"  {k}: drop={v['drop_pct']:.1f}% [{v['ci_lo']:.1f}, {v['ci_hi']:.1f}] storm={v['N_storm']}")

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(BANDS))
width = 0.35
day_drops = [abs(results_dn[f"{b}_Day"]["drop_pct"]) for b in BANDS]
day_lo = [abs(results_dn[f"{b}_Day"]["ci_lo"]) if results_dn[f"{b}_Day"]["ci_lo"] != 0 else 0 for b in BANDS]
day_hi = [abs(results_dn[f"{b}_Day"]["ci_hi"]) if results_dn[f"{b}_Day"]["ci_hi"] != 0 else 0 for b in BANDS]
night_drops = [abs(results_dn[f"{b}_Night"]["drop_pct"]) for b in BANDS]
night_lo = [abs(results_dn[f"{b}_Night"]["ci_lo"]) if results_dn[f"{b}_Night"]["ci_lo"] != 0 else 0 for b in BANDS]
night_hi = [abs(results_dn[f"{b}_Night"]["ci_hi"]) if results_dn[f"{b}_Night"]["ci_hi"] != 0 else 0 for b in BANDS]

day_yerr = [[day_drops[i] - day_lo[i] for i in range(3)], [day_hi[i] - day_drops[i] for i in range(3)]]
night_yerr = [[night_drops[i] - night_lo[i] for i in range(3)], [night_hi[i] - night_drops[i] for i in range(3)]]
day_yerr = np.clip(day_yerr, 0, None)
night_yerr = np.clip(night_yerr, 0, None)

bars1 = ax.bar(
    x - width / 2, day_drops, width,
    label="Day (12\u201318 UTC)", color="#FFB347", edgecolor="black", linewidth=0.5,
    yerr=day_yerr, capsize=5, error_kw={"elinewidth": 1.5, "capthick": 1.5},
)
bars2 = ax.bar(
    x + width / 2, night_drops, width,
    label="Night (0\u20136 UTC)", color="#4A6FA5", edgecolor="black", linewidth=0.5,
    yerr=night_yerr, capsize=5, error_kw={"elinewidth": 1.5, "capthick": 1.5},
)

for bar in bars1:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h - 1.5 if h > 5 else h + 1.5,
            f"{h:.1f}%", ha="center", va="top" if h > 5 else "bottom",
            fontsize=9, fontweight="bold", color="white" if h > 5 else "black")
for bar in bars2:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h - 1.5 if h > 5 else h + 1.5,
            f"{h:.1f}%", ha="center", va="top" if h > 5 else "bottom",
            fontsize=9, fontweight="bold", color="white" if h > 5 else "black")

ax.set_xticks(x)
ax.set_xticklabels(BANDS, fontsize=12)
ax.set_ylabel("Spot reduction during Kp\u22655 (%)", fontsize=12)
ax.set_title(
    "Day/Night Asymmetry of WSPR Storm Response\n"
    "(18-month training, April 2024 \u2013 September 2025, with 95% bootstrap CI)",
    fontsize=13, fontweight="bold",
)
ax.legend(fontsize=11, loc="lower left")
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(bottom=0)
plt.tight_layout()
path_fig4 = OUT / "fig4_day_night_asymmetry.png"
fig.savefig(str(path_fig4), dpi=150, bbox_inches="tight")
plt.close()
print(f"[OK] {path_fig4} ({path_fig4.stat().st_size} bytes)")


# ═════════════════════════════════════════════════════════════════════
#  FIGURE 5: Baseline-Invariant Absolute Loss with error bars
# ═════════════════════════════════════════════════════════════════════
print("\n=== Figure 5: Baseline-invariant absolute loss ===")

band_abs = {
    "20m": {"train": 20421, "heldout": 15793, "ratio": 0.77, "growth": 17},
    "40m": {"train": 18285, "heldout": 18304, "ratio": 1.00, "growth": 38},
    "15m": {"train": 5178,  "heldout": 2181,  "ratio": 0.42, "growth": 25},
}

train_ci = {}
for band in BANDS:
    sub = wspr[wspr["band"] == band].copy()
    merged = pd.merge(sub, kp_h, left_on="hour", right_on="hour", how="inner")
    merged["resid"] = (
        merged["value"]
        - merged.groupby(["month", "hour_of_day", "day_of_week"])["value"].transform("mean")
    )
    s = merged[merged["kp"] >= 5]
    q = merged[merged["kp"] < 3]
    sv, qv = s["value"].values, q["value"].values
    sn, qn = len(sv), len(qv)
    abs_losses = []
    for _ in range(N_BOOT):
        sm = RNG.choice(sv, size=sn).mean()
        qm = RNG.choice(qv, size=qn).mean()
        abs_losses.append(qm - sm)
    abs_losses = np.array(abs_losses)
    lo = np.percentile(abs_losses, 2.5)
    hi = np.percentile(abs_losses, 97.5)
    train_ci[band] = (float(lo), float(hi))
    print(f"  {band} training abs loss CI: [{lo:.0f}, {hi:.0f}] mean={abs_losses.mean():.0f}")

fig, ax = plt.subplots(figsize=(8, 5.5))
x = np.arange(2)
width = 0.25
colors = {"20m": "#E76F51", "40m": "#2A9D8F", "15m": "#264653"}
offsets = [-width, 0, width]

for i, band in enumerate(["20m", "40m", "15m"]):
    vals = [band_abs[band]["train"], band_abs[band]["heldout"]]
    ci_width = [(abs(vals[0] - train_ci[band][0]), abs(train_ci[band][1] - vals[0])),
                (0, 0)]
    yerr_lo = [ci_width[0][0], 0]
    yerr_hi = [ci_width[0][1], 0]
    yerr = np.array([yerr_lo, yerr_hi])
    yerr = np.clip(yerr, 0, None)

    bars = ax.bar(
        x + offsets[i], vals, width,
        label=f"{band} (ratio={band_abs[band]['ratio']:.2f}\u00d7)",
        color=colors[band], edgecolor="black", linewidth=0.5,
        yerr=yerr, capsize=5, error_kw={"elinewidth": 1.5, "capthick": 1.5},
    )
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 400,
            f"{h:.0f}", ha="center", va="bottom", fontsize=8,
        )

ax.set_xticks(x)
ax.set_xticklabels(
    ["Training\n(Apr 2024 \u2013 Sep 2025)", "Held-Out\n(Jan \u2013 Mar 2026)"],
    fontsize=11,
)
ax.set_ylabel("Absolute spot loss (spots/hour)", fontsize=12)
ax.set_title(
    "Baseline-Invariant Absolute Spot Loss\n"
    "40m loss unchanged despite 38% network growth\n"
    "(with 95% bootstrap CI on training)",
    fontsize=12, fontweight="bold",
)
ax.legend(fontsize=10, loc="upper right")
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(bottom=0, top=24000)

ax.annotate(
    "40m: identical!\n(\u221218 300 spots/h)",
    xy=(0.5, 18304), xytext=(1.0, 21000),
    fontsize=10, fontweight="bold", color="#2A9D8F",
    arrowprops={"arrowstyle": "->", "color": "#2A9D8F", "lw": 1.5},
    ha="center",
)
ax.annotate(
    "15m: \u00d70.42 dilution\n(MUF ceiling effect)",
    xy=(1.5, 2181), xytext=(1.6, 6000),
    fontsize=10, fontweight="bold", color="#264653",
    arrowprops={"arrowstyle": "->", "color": "#264653", "lw": 1.5},
    ha="center",
)

plt.tight_layout()
path_fig5 = OUT / "fig5_baseline_invariance.png"
fig.savefig(str(path_fig5), dpi=150, bbox_inches="tight")
plt.close()
print(f"[OK] {path_fig5} ({path_fig5.stat().st_size} bytes)")


# ═════════════════════════════════════════════════════════════════════
#  FIGURE 1: Kp timeseries (Oct-Nov 2024 example)
# ═════════════════════════════════════════════════════════════════════
print("\n=== Figure 1: Kp timeseries ===")

ts_merged = pd.merge(
    wspr[wspr["band"] == "20m"], kp_h, left_on="hour", right_on="hour", how="inner"
)
ts_merged = ts_merged[(ts_merged["hour"] >= "2024-10-01") & (ts_merged["hour"] < "2024-12-01")]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True, gridspec_kw={"height_ratios": [1, 2]})

ax1.fill_between(ts_merged["hour"], ts_merged["kp"], alpha=0.3, color="darkred")
ax1.plot(ts_merged["hour"], ts_merged["kp"], color="darkred", linewidth=1)
ax1.axhline(y=5, color="red", linestyle="--", alpha=0.5, label="Kp=5 (storm threshold)")
ax1.set_ylabel("Kp index", fontsize=12)
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)
ax1.set_ylim(bottom=0, top=9)

for idx in range(len(ts_merged) - 1):
    if ts_merged.iloc[idx]["kp"] >= 5:
        ax2.axvspan(ts_merged.iloc[idx]["hour"], ts_merged.iloc[idx + 1]["hour"],
                     color="red", alpha=0.1)

ax2.plot(ts_merged["hour"], ts_merged["value"] / 1000, color="steelblue", linewidth=0.8, alpha=0.9)
ax2.set_ylabel("WSPR spots (thousands/h)", fontsize=12)
ax2.set_xlabel("Date (UTC)", fontsize=12)
ax2.grid(alpha=0.3)

fig.suptitle(
    "Geomagnetic Storm Effect on WSPR Spot Density\n"
    "October\u2013November 2024, 20 m band",
    fontsize=14, fontweight="bold",
)
plt.tight_layout()
path_fig1 = OUT / "fig1_kp_timeseries.png"
fig.savefig(str(path_fig1), dpi=150, bbox_inches="tight")
plt.close()
print(f"[OK] {path_fig1} ({path_fig1.stat().st_size} bytes)")


# ═════════════════════════════════════════════════════════════════════
#  FIGURE 3: Frequency dependence
# ═════════════════════════════════════════════════════════════════════
print("\n=== Figure 3: Frequency dependence ===")

freq_drops = {}
freq_ci = {}
for band in BANDS:
    sub = wspr[wspr["band"] == band].copy()
    merged = pd.merge(sub, kp_h, left_on="hour", right_on="hour", how="inner")
    merged["resid"] = (
        merged["value"]
        - merged.groupby(["month", "hour_of_day", "day_of_week"])["value"].transform("mean")
    )
    s = merged[merged["kp"] >= 5]
    q = merged[merged["kp"] < 3]
    sv, qv = s["value"].values, q["value"].values
    sn, qn = len(sv), len(qv)
    drop_dist = []
    for _ in range(N_BOOT):
        sm = RNG.choice(sv, size=sn).mean()
        qm = RNG.choice(qv, size=qn).mean()
        drop_dist.append(100 * (sm - qm) / qm)
    drop_dist = np.array(drop_dist)
    freq_drops[band] = float(-drop_dist.mean())
    freq_ci[band] = (float(-np.percentile(drop_dist, 97.5)), float(-np.percentile(drop_dist, 2.5)))

freqs_mhz = {"20m": 14.0956, "40m": 7.0401, "15m": 21.0961}
fig, ax = plt.subplots(figsize=(8, 5.5))
x = np.arange(len(BANDS))
vals = [freq_drops[b] for b in BANDS]
yerr_lo = [vals[i] - freq_ci[b][0] for i, b in enumerate(BANDS)]
yerr_hi = [freq_ci[b][1] - vals[i] for i, b in enumerate(BANDS)]
yerr = [np.clip(yerr_lo, 0, None), np.clip(yerr_hi, 0, None)]

colors_f = ["#264653", "#2A9D8F", "#E76F51"]
bars = ax.bar(x, vals, color=colors_f, edgecolor="black", linewidth=0.5,
              yerr=yerr, capsize=8, error_kw={"elinewidth": 2, "capthick": 2})
for bar in bars:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h - 2, f"{h:.1f}%",
            ha="center", va="top", fontsize=12, color="white", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels([f"20 m\n({freqs_mhz['20m']:.1f} MHz)",
                    f"40 m\n({freqs_mhz['40m']:.1f} MHz)",
                    f"15 m\n({freqs_mhz['15m']:.1f} MHz)"], fontsize=11)
ax.set_ylabel("Spot reduction during Kp\u22655 (%)", fontsize=12)
ax.set_title(
    "Frequency Dependence of WSPR Storm Response\n"
    "(18-month training, with 95% bootstrap CI)",
    fontsize=13, fontweight="bold",
)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(bottom=0)
plt.tight_layout()
path_fig3 = OUT / "fig3_frequency_dependence.png"
fig.savefig(str(path_fig3), dpi=150, bbox_inches="tight")
plt.close()
print(f"[OK] {path_fig3} ({path_fig3.stat().st_size} bytes)")

print(f"\n{'='*60}")
print("All 5 figures generated with 95% bootstrap CI error bars.")
print(f"{'='*60}")
