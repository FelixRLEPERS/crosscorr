"""Generate paper figures: fig4 (day/night asymmetry) and fig5 (baseline invariance).

Uses training data from unified.parquet for fig4, and hard-coded replication
numbers from first_result.md for fig5.
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

# ── Load training data ──────────────────────────────────────────────
df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
full = df[
    (df["timestamp_utc"] >= "2024-04-01") & (df["timestamp_utc"] < "2025-10-01")
]

wspr = full[full["detector_type"] == "wspr_hourly"].copy()
wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")
wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
wspr["month"] = wspr["timestamp_utc"].dt.to_period("M")
wspr["hour_of_day"] = wspr["timestamp_utc"].dt.hour

kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
kp.columns = ["timestamp_utc", "kp"]
kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
kp_h = kp.groupby("hour")["kp"].mean().reset_index()

# ── Figure 4: Day/Night Asymmetry ───────────────────────────────────
BANDS = ["20m", "40m", "15m"]
DAY_RANGE = (12, 18)
NIGHT_RANGE = (0, 6)

results_dn = {}
for band in BANDS:
    sub = wspr[wspr["band"] == band].copy()
    merged = pd.merge(
        sub, kp_h, left_on="hour", right_on="hour", how="inner"
    )
    merged["resid"] = (
        merged["value"]
        - merged.groupby(["month", "hour_of_day"])["value"].transform("mean")
    )

    day = merged[merged["hour_of_day"].between(*DAY_RANGE)]
    night = merged[merged["hour_of_day"].between(*NIGHT_RANGE)]

    for label, df_sel in [("Day", day), ("Night", night)]:
        s = df_sel[df_sel["kp"] >= 5]
        q = df_sel[df_sel["kp"] < 3]
        if len(s) >= 3 and len(q) >= 10:
            drop = 100 * (s["value"].mean() - q["value"].mean()) / q["value"].mean()
            results_dn[f"{band}_{label}"] = {
                "band": band,
                "period": label,
                "drop_pct": round(drop, 1),
                "N_storm": len(s),
                "N_quiet": len(q),
            }

print("=== Day/Night Results ===")
for k, v in results_dn.items():
    print(
        f"  {k}: drop={v['drop_pct']:.1f}%, storm={v['N_storm']}, quiet={v['N_quiet']}"
    )

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(BANDS))
width = 0.35
day_drops = [results_dn[f"{b}_Day"]["drop_pct"] for b in BANDS]
night_drops = [results_dn[f"{b}_Night"]["drop_pct"] for b in BANDS]

bars1 = ax.bar(
    x - width / 2, [-d for d in day_drops], width,
    label="Day (12\u201318 UTC)", color="#FFB347", edgecolor="black", linewidth=0.5,
)
bars2 = ax.bar(
    x + width / 2, [-d for d in night_drops], width,
    label="Night (0\u20136 UTC)", color="#4A6FA5", edgecolor="black", linewidth=0.5,
)

for bar in bars1:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h - 1.2, f"{abs(h):.1f}%",
            ha="center", va="top", fontsize=9, color="white", fontweight="bold")
for bar in bars2:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h - 1.2, f"{abs(h):.1f}%",
            ha="center", va="top", fontsize=9, color="white", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(BANDS, fontsize=12)
ax.set_ylabel("Spot reduction during Kp\u22655 (%)", fontsize=12)
ax.set_title(
    "Day/Night Asymmetry of WSPR Storm Response\n"
    "(18-month training, April 2024 \u2013 September 2025)",
    fontsize=13, fontweight="bold",
)
ax.legend(fontsize=11, loc="lower left")
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(bottom=0)
plt.tight_layout()
path_fig4 = OUT / "fig4_day_night_asymmetry.png"
fig.savefig(str(path_fig4), dpi=150)
plt.close()
print(f"\n[OK] {path_fig4} ({path_fig4.stat().st_size} bytes)")

# ── Figure 5: Baseline-Invariant Absolute Loss ──────────────────────
band_abs = {
    "20m": {"train": -20421, "heldout": -15793, "ratio": 0.77, "growth": 17},
    "40m": {"train": -18285, "heldout": -18304, "ratio": 1.00, "growth": 38},
    "15m": {"train": -5178,  "heldout": -2181,  "ratio": 0.42, "growth": 25},
}

fig, ax = plt.subplots(figsize=(8, 5.5))
x = np.arange(2)
width = 0.25
colors = {"20m": "#E76F51", "40m": "#2A9D8F", "15m": "#264653"}
offsets = [-width, 0, width]

for i, band in enumerate(["20m", "40m", "15m"]):
    vals = [abs(band_abs[band]["train"]), abs(band_abs[band]["heldout"])]
    bars = ax.bar(
        x + offsets[i], vals, width,
        label=f"{band} (ratio={band_abs[band]['ratio']:.2f}\u00d7)",
        color=colors[band], edgecolor="black", linewidth=0.5,
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
    "Baseline-Invariant Absolute Spot Loss:\n"
    "40m loss unchanged despite 38% network growth",
    fontsize=13, fontweight="bold",
)
ax.legend(fontsize=10, loc="upper right")
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(bottom=0, top=24000)

# Annotate the key invariance
ax.annotate(
    "40m: identical!\n(\u221218 300 spots/h)",
    xy=(0.5, 18304), xytext=(1.0, 21000),
    fontsize=10, fontweight="bold", color="#2A9D8F",
    arrowprops=dict(arrowstyle="->", color="#2A9D8F", lw=1.5),
    ha="center",
)
ax.annotate(
    "15m: ×0.42 dilution\n(MUF ceiling effect)",
    xy=(1.5, 2181), xytext=(1.6, 6000),
    fontsize=10, fontweight="bold", color="#264653",
    arrowprops=dict(arrowstyle="->", color="#264653", lw=1.5),
    ha="center",
)

plt.tight_layout()
path_fig5 = OUT / "fig5_baseline_invariance.png"
fig.savefig(str(path_fig5), dpi=150)
plt.close()
print(f"[OK] {path_fig5} ({path_fig5.stat().st_size} bytes)")

print("\nDone: 2 figures generated.")