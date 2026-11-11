"""TimesFM MVP: 20m band, walk-forward validation.

Two experiments:
  A) Baseline: train WITH storm epochs -> forecast quality (MAE)
  B) Storm-aware: train WITHOUT storm epochs -> anomaly detection (recall)

Usage:
  .venv-timesfm\\Scripts\\python.exe scripts\\timesfm_mvp_20m.py --experiment A
  .venv-timesfm\\Scripts\\python.exe scripts\\timesfm_mvp_20m.py --experiment B
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument(
    "--experiment",
    choices=["A", "B"],
    required=True,
    help="A = baseline (train with storms), B = storm-aware (train without storms)",
)
parser.add_argument(
    "--pseudo-test-months",
    type=int,
    default=3,
    help="Number of months for pseudo-test (default: 3 = Jan-Mar 2025)",
)
parser.add_argument(
    "--context-window",
    type=int,
    default=512,
    help="TimesFM context window in hours (default: 512)",
)
parser.add_argument(
    "--horizons",
    type=int,
    nargs="+",
    default=[1, 6, 24],
    help="Forecast horizons in hours (default: 1 6 24)",
)
parser.add_argument(
    "--anomaly-threshold",
    type=float,
    default=2.0,
    help="Anomaly threshold in std (default: 2.0)",
)
parser.add_argument(
    "--out",
    default=None,
    help="Output JSON path (default: results/timesfm_mvp_20m_exp<EXPERIMENT>.json)",
)
args = parser.parse_args()
if args.out is None:
    args.out = str(ROOT / "results" / f"timesfm_mvp_20m_exp{args.experiment}.json")

print(f"[config] Experiment {args.experiment}")
print(f"[config] Pseudo-test: {args.pseudo_test_months} months")
print(f"[config] Context window: {args.context_window}h")
print(f"[config] Horizons: {args.horizons}h")
print(f"[config] Anomaly threshold: {args.anomaly_threshold}")

# ============================================================
# 1. Load data
# ============================================================
print("\n[load] Reading unified.parquet...")
df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")

# Filter 20m WSPR hourly
wspr = df[df["detector_type"] == "wspr_hourly"].copy()
wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")
w20 = wspr[wspr["band"] == "20m"].copy()


def parse_n_tx(meta_str):
    """n_unique_tx out of the unified.parquet meta JSON string (NaN if absent)."""
    try:
        obj = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
        v = obj.get("n_unique_tx") if isinstance(obj, dict) else None
        return float(v)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return float("nan")


w20["n_unique_tx"] = w20["meta"].apply(parse_n_tx)

# Normalization: spots / n_unique_tx (same as paper --norm-tx)
w20["value_norm"] = w20["value"] / w20["n_unique_tx"]
w20 = w20.dropna(subset=["value_norm"]).sort_values("timestamp_utc").reset_index(drop=True)

print(f"[load] 20m WSPR hourly: {len(w20)} rows")
print(f"[load] Time range: {w20['timestamp_utc'].min()} -> {w20['timestamp_utc'].max()}")

# Load Kp (ground truth)
kp = df[df["detector_type"] == "kp"].copy()
kp["kp_value"] = kp["value"].astype(float)
kp = kp[["timestamp_utc", "kp_value"]].rename(columns={"timestamp_utc": "hour"})
kp["hour"] = kp["hour"].dt.floor("1h")
kp = kp.groupby("hour")["kp_value"].mean().reset_index()

# Merge Kp
w20 = w20.merge(kp, left_on="timestamp_utc", right_on="hour", how="left")
w20["is_storm"] = w20["kp_value"] >= 5.0

# ============================================================
# 2. Define splits
# ============================================================
print("\n[split] Defining train/pseudo-test splits...")

# Train: Apr 2024 - Sep 2025
train_mask = (w20["timestamp_utc"] >= "2024-04-01") & (w20["timestamp_utc"] < "2025-10-01")

# Pseudo-test: first N months of 2025 (walk-forward)
pseudo_end = f"2025-{args.pseudo_test_months + 1:02d}-01"
pseudo_mask = (w20["timestamp_utc"] >= "2025-01-01") & (w20["timestamp_utc"] < pseudo_end)

train = w20[train_mask].copy()
pseudo = w20[pseudo_mask].copy()

print(
    f"[split] Train: {len(train)} hours ({train['timestamp_utc'].min()} -> {train['timestamp_utc'].max()})"
)
print(
    f"[split] Pseudo-test: {len(pseudo)} hours ({pseudo['timestamp_utc'].min()} -> {pseudo['timestamp_utc'].max()})"
)
print(f"[split] Train storms: {int(train['is_storm'].sum())}")
print(f"[split] Pseudo-test storms: {int(pseudo['is_storm'].sum())}")

# Experiment B: Remove storms from train
if args.experiment == "B":
    n_before = len(train)
    train = train[~train["is_storm"]].copy()
    n_removed = n_before - len(train)
    print(f"[experiment B] Removed {n_removed} storm hours from train")
    print(
        f"[experiment B] Train now: {len(train)} hours, {int(train['is_storm'].sum())} storms (should be 0)"
    )

# ============================================================
# 3. TimesFM inference (zero-shot, context-window)
# ============================================================
print("\n[inference] Running TimesFM forecast...")

import timesfm  # noqa: E402

horizons = sorted(set(args.horizons))
max_h = max(horizons)

print("[timesfm] Device: cpu (venv torch is CPU-only, CUDA unavailable)")
print("[timesfm] Loading model (first run downloads weights ~800 MB)...")

# timesfm 3.0.2 API: from_pretrained -> compile(ForecastConfig) -> forecast().
# torch_compile=False is REQUIRED on Windows (torch.compile needs triton).
model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
    "google/timesfm-2.5-200m-pytorch", torch_compile=False
)
model.compile(
    timesfm.ForecastConfig(
        max_context=args.context_window,
        max_horizon=max_h,
        per_core_batch_size=8,
    )
)

# Full normalized series (time-sorted). Prediction points = pseudo-test rows.
full_values = w20["value_norm"].to_numpy()
full_storms = w20["is_storm"].to_numpy()
full_ts = w20["timestamp_utc"].to_numpy()

# Index of the first pseudo-test hour (Jan 1, 2025) in the full series.
# NOTE: pseudo-test (Jan-Mar 2025) lies INSIDE the train window (Apr 2024 -
# Sep 2025), so it is NOT len(train) -- count rows before 2025-01-01 instead.
pseudo_start_idx = int((w20["timestamp_utc"] < "2025-01-01").sum())
_pseudo_end_idx = pseudo_start_idx + len(pseudo) - 1
assert (
    len(pseudo) > 0
    and str(w20["timestamp_utc"].iloc[pseudo_start_idx])[:10] >= "2025-01-01"
    and str(w20["timestamp_utc"].iloc[_pseudo_end_idx])[:10] < "2025-04-01"
), "pseudo-test index mapping is wrong"

# Experiment B: storm epochs are excluded from the CONTEXT history (the
# zero-shot analogue of "train without storms" -- TimesFM has no fine-tuning
# on our data, so its only 'training' input is the context window).
nonstorm_idx = np.flatnonzero(~full_storms)


def build_context(g: int) -> np.ndarray | None:
    """Context for prediction origin g (value at g is never included)."""
    if args.experiment == "B":
        left = int(np.searchsorted(nonstorm_idx, g, side="left"))
        idx = nonstorm_idx[max(0, left - args.context_window) : left]
    else:
        idx = np.arange(max(0, g - args.context_window), g)
    if len(idx) < 24:
        return None
    return full_values[idx]


print(
    f"[timesfm] Experiment {args.experiment}: {len(pseudo)} pseudo-test hours "
    f"(context={args.context_window}h, horizons={horizons})"
)

contexts: list[np.ndarray] = []
origins: list[int] = []
for i in range(len(pseudo)):
    g = pseudo_start_idx + i
    if g + max_h > len(full_values):
        continue
    ctx = build_context(g)
    if ctx is None:
        continue
    contexts.append(ctx)
    origins.append(g)

if not contexts:
    raise RuntimeError("no forecast origins -- check splits")

# Batched forecast: model.forecast pads each call up to global_batch_size
# and strips the padding from the returned array.
points: list[np.ndarray] = []
chunk_size = 64  # multiple of global_batch_size (8)
n_chunks = -(-len(contexts) // chunk_size)
for c in range(n_chunks):
    chunk = contexts[c * chunk_size : (c + 1) * chunk_size]
    point, _quantile = model.forecast(max_h, chunk)
    points.append(np.asarray(point, dtype=np.float64))
    print(f"  batch {c + 1}/{n_chunks}")
forecast_arr = np.concatenate(points, axis=0)  # [n_origins, max_h]

records = []
for j, g in enumerate(origins):
    rec = {
        "ts": str(full_ts[g]),
        "actual": float(full_values[g]),
        "is_storm": bool(full_storms[g]),
    }
    for h in horizons:
        rec[f"pred_{h}h"] = float(forecast_arr[j, h - 1])
        rec[f"actual_{h}h"] = float(full_values[g + h - 1])
    records.append(rec)

print(f"[timesfm] Generated forecasts for {len(records)} hours")

# Per-hour forecasts (for visualization / post-hoc analysis)
records_path = Path(args.out).with_name(Path(args.out).stem + "_records.csv")
pd.DataFrame(records).to_csv(records_path, index=False, encoding="utf-8")
print(f"[save] Records -> {records_path}")

# ============================================================
# 4. Metrics
# ============================================================
print("\n[metrics] Computing metrics...")

results = {
    "config": {
        "experiment": args.experiment,
        "pseudo_test_months": args.pseudo_test_months,
        "context_window": args.context_window,
        "horizons": horizons,
        "anomaly_threshold": args.anomaly_threshold,
        "train_hours": int(len(train)),
        "pseudo_test_hours": int(len(pseudo)),
        "train_storms": int(train["is_storm"].sum()),
        "pseudo_test_storms": int(pseudo["is_storm"].sum()),
        "n_forecasts": len(records),
    },
    "metrics": {},
}

if not records:
    results["metrics"]["error"] = "no forecasts generated"
else:
    # Experiment A: forecast quality (MAE/RMSE per horizon)
    if args.experiment == "A":
        print("[metrics] Experiment A: MAE by horizon")
        for h in horizons:
            pred_k, act_k = f"pred_{h}h", f"actual_{h}h"
            pairs = [(r[pred_k], r[act_k]) for r in records if pred_k in r and act_k in r]
            if not pairs:
                continue
            p = np.array([x[0] for x in pairs])
            a = np.array([x[1] for x in pairs])
            mae = float(np.mean(np.abs(p - a)))
            rmse = float(np.sqrt(np.mean((p - a) ** 2)))
            results["metrics"][f"horizon_{h}h"] = {
                "mae": mae,
                "rmse": rmse,
                "n_samples": int(len(p)),
            }
            print(f"  {h}h: MAE={mae:.4f}, RMSE={rmse:.4f}, N={len(p)}")

    # Experiment B: anomaly detection on 1h residuals
    elif args.experiment == "B":
        print("[metrics] Experiment B: Anomaly detection")
        h = horizons[0]
        pairs = [
            (r[f"pred_{h}h"], r[f"actual_{h}h"], r["is_storm"])
            for r in records
            if f"pred_{h}h" in r
        ]
        pred = np.array([x[0] for x in pairs])
        act = np.array([x[1] for x in pairs])
        storms = np.array([x[2] for x in pairs])

        residuals = act - pred
        # Rolling std of |residual| over 7-day window (168 hours)
        roll = (
            pd.Series(np.abs(residuals))
            .rolling(window=168, min_periods=24, center=True)
            .std()
            .bfill()
            .ffill()
            .to_numpy()
        )
        anomalies = np.abs(residuals) > (args.anomaly_threshold * roll)

        tp = int(np.sum(anomalies & storms))
        fp = int(np.sum(anomalies & ~storms))
        fn = int(np.sum(~anomalies & storms))
        tn = int(np.sum(~anomalies & ~storms))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        results["metrics"]["detection"] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "n_storms": int(storms.sum()),
            "n_anomalies": int(anomalies.sum()),
        }
        print(f"  Precision: {precision:.3f}")
        print(f"  Recall: {recall:.3f}")
        print(f"  F1: {f1:.3f}")
        print(f"  TP={tp}, FP={fp}, FN={fn}, TN={tn}")
        print(f"  Storms: {int(storms.sum())}, Anomalies: {int(anomalies.sum())}")

        if recall >= 0.6:
            results["interpretation"] = "TimesFM catches storms without Kp (recall >= 0.6)"
        elif recall >= 0.3:
            results["interpretation"] = "TimesFM partially catches storms (0.3-0.6 recall)"
        else:
            results["interpretation"] = "TimesFM does NOT replace Kp-based detection (<0.3 recall)"
        print(f"\n[interpretation] {results['interpretation']}")

# ============================================================
# 5. Save results
# ============================================================
print(f"\n[save] Writing {args.out}...")
with open(args.out, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"[save] Saved to {args.out}")

# ============================================================
# 6. Summary
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Experiment: {args.experiment}")
print(f"Train: {results['config']['train_hours']} hours")
print(f"Pseudo-test: {results['config']['pseudo_test_hours']} hours")
print(f"Metrics: {json.dumps(results['metrics'], indent=2)}")
if "interpretation" in results:
    print(f"\nInterpretation: {results['interpretation']}")
print("=" * 60)
