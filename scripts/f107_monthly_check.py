"""Monthly F10.7 vs WSPR residuals — Spearman gate for Paper I §5.5.

Offline: uses only data/processed/unified.parquet (no network).
Note: source F10.7 in the parquet is MONTHLY (18 rows), not daily.
"""
import pandas as pd
from scipy import stats

PARQUET = "data/processed/unified.parquet"
OUT = "results/f107_spearman_monthly.txt"
WIN_START, WIN_END = "2024-04", "2025-09"

df = pd.read_parquet(PARQUET)

wspr = df[df["detector_type"] == "wspr_hourly"].copy()
wspr = wspr[(wspr["timestamp_utc"] >= "2024-04-01") &
            (wspr["timestamp_utc"] < "2025-10-01")]
wspr["month"] = wspr["timestamp_utc"].dt.strftime("%Y-%m")
monthly_resid = (wspr.groupby("month")["residual"]
                 .agg(["mean", "median", "count"])
                 .rename(columns={"mean": "residual_mean",
                                  "median": "residual_median"}))

f107 = df[df["detector_type"] == "f107"].copy()
f107["month"] = f107["timestamp_utc"].dt.strftime("%Y-%m")
f107 = f107[["month", "value"]].rename(columns={"value": "f107"})
f107 = f107[f107["month"].between(WIN_START, WIN_END)]

joined = monthly_resid.join(f107.set_index("month"), how="inner").dropna()

n = len(joined)
results = {}
for col in ("residual_mean", "residual_median"):
    r, p = stats.spearmanr(joined[col], joined["f107"])
    results[col] = (float(r), float(p))

r_mean, p_mean = results["residual_mean"]
r_med, p_med = results["residual_median"]

lines = [
    "F10.7 monthly gate — Paper I §5.5 (offline, unified.parquet)",
    f"window: {WIN_START} .. {WIN_END}",
    f"n (matched months): {n}",
    f"f107 range: {joined['f107'].min():.1f} .. {joined['f107'].max():.1f} sfu",
    "",
    f"Spearman r (monthly MEAN residual vs f107): {r_mean:+.4f}  p={p_mean:.4g}",
    f"Spearman r (monthly MEDIAN residual vs f107): {r_med:+.4f}  p={p_med:.4g}",
    "",
    f"r^2 (mean):  {r_mean**2:.4f}",
    f"r^2 (median): {r_med**2:.4f}",
    "",
    "Decision rule:",
]
gate_ok = (abs(r_mean) < 0.3) and (p_mean > 0.05)
verdict = "monthly-sufficient" if gate_ok else "daily-required"
lines.append(f"  |r| < 0.3 AND p > 0.05 -> {verdict}")
lines.append(f"  abs(r_mean)={abs(r_mean):.4f}, p_mean={p_mean:.4g} -> {verdict}")
lines += [
    "",
    "NOTE: F10.7 here is MONTHLY (18 rows in parquet), not daily.",
    "Gate based on residual MEAN; median reported for robustness.",
]

text = "\n".join(lines) + "\n"
print(text)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"written: {OUT}")
print(f"VERDICT: {verdict}")
