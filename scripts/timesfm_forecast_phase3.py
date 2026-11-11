"""TimesFM Phase 3a: forecasting quality, 3 bands, extended pseudo-test.

Forecasting only (Experiment B detection is closed as a negative result).
Zero-shot TimesFM 2.5-200m on Jan-Dec 2025 pseudo-test for 20m/40m/15m.

Three baselines on identical origins/actuals:
  - persistence:    pred = values[g-1]            (hold last observed)
  - seasonal_naive: pred = values[g-(25-h)]       (same hour, previous day)
  - mean24:         pred = mean(values[g-24:g])    (trailing 24h mean)

Metrics per horizon (1/6/12/24h): MAE, RMSE, plus skill score
  skill = 1 - MAE_model / MAE_baseline   (vs seasonal-naive and vs persistence)

Phase 4 (frozen confirmation, same code path, one run, no new experiments):
  .venv-timesfm\\Scripts\\python.exe scripts\\timesfm_forecast_phase3.py --frozen

Usage:
  .venv-timesfm\\Scripts\\python.exe scripts\\timesfm_forecast_phase3.py
  .venv-timesfm\\Scripts\\python.exe scripts\\timesfm_forecast_phase3.py --bands 20m
  # recompute metrics from existing records CSVs (no model load):
  .venv-timesfm\\Scripts\\python.exe scripts\\timesfm_forecast_phase3.py --from-records
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument(
    "--bands",
    nargs="+",
    default=["20m", "40m", "15m"],
    help="Bands to forecast (default: 20m 40m 15m)",
)
parser.add_argument(
    "--pseudo-start",
    default="2025-01-01",
    help="Pseudo-test start (default: 2025-01-01)",
)
parser.add_argument(
    "--pseudo-end",
    default="2026-01-01",
    help="Pseudo-test end, exclusive (default: 2026-01-01 = Jan-Dec 2025)",
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
    default=[1, 6, 12, 24],
    help="Forecast horizons in hours (default: 1 6 12 24)",
)
parser.add_argument(
    "--from-records",
    action="store_true",
    help="Skip model inference; recompute metrics from existing per-band records CSVs",
)
parser.add_argument(
    "--frozen",
    action="store_true",
    help=(
        "Phase 4: frozen Jan-Mar 2026 confirmation run. Overrides the pseudo-test "
        "window and output names (results/timesfm_phase4_frozen.json)."
    ),
)
args = parser.parse_args()

# Phase 4: frozen held-out window (Jan-Mar 2026; actual data ends mid-Jan 2026)
records_prefix = "timesfm_phase3"
out_name = "timesfm_phase3_forecast.json"
if args.frozen:
    args.pseudo_start = "2026-01-01"
    args.pseudo_end = "2026-04-01"
    records_prefix = "timesfm_phase4_frozen"
    out_name = "timesfm_phase4_frozen.json"

horizons = sorted(set(args.horizons))
max_h = max(horizons)

print(f"[config] Bands: {args.bands}")
print(f"[config] Pseudo-test: {args.pseudo_start} -> {args.pseudo_end}")
print(f"[config] Context window: {args.context_window}h")
print(f"[config] Horizons: {horizons}h")

# ============================================================
# 1. Load data
# ============================================================
print("\n[load] Reading unified.parquet...")
df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
wspr = df[df["detector_type"] == "wspr_hourly"].copy()
wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")


def parse_n_tx(meta_str):
    """n_unique_tx out of the unified.parquet meta JSON string (NaN if absent)."""
    try:
        obj = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
        v = obj.get("n_unique_tx") if isinstance(obj, dict) else None
        return float(v)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return float("nan")


wspr["n_unique_tx"] = wspr["meta"].apply(parse_n_tx)
wspr["value_norm"] = wspr["value"] / wspr["n_unique_tx"]

# ============================================================
# 2. Load TimesFM (once for all bands; skipped by --from-records)
# ============================================================
model = None
chunk_size = 64  # multiple of global_batch_size (8)
if not args.from_records:
    print("\n[timesfm] Device: cpu (venv torch is CPU-only)")
    print("[timesfm] Loading model (cached ~800 MB)...")

    import timesfm  # noqa: E402

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


def compute_metrics(rec_df: pd.DataFrame) -> dict:
    """MAE/RMSE/baselines/skill per horizon from a records DataFrame."""
    metrics = {}
    for h in horizons:
        act = rec_df[f"actual_{h}h"].to_numpy()
        pred = rec_df[f"pred_{h}h"].to_numpy()
        mae = float(np.mean(np.abs(pred - act)))
        rmse = float(np.sqrt(np.mean((pred - act) ** 2)))

        base = {}
        for name, col in (
            ("persistence", f"persist_{h}h"),
            ("seasonal_naive", f"seasonal_{h}h"),
            ("mean24", f"mean24_{h}h"),
        ):
            bp = rec_df[col].to_numpy()
            mask = np.isfinite(bp)
            bmae = float(np.mean(np.abs(bp[mask] - act[mask])))
            base[name] = bmae

        # skill vs seasonal-naive and vs persistence (primary honest comparisons)
        skill_seasonal = (
            1.0 - mae / base["seasonal_naive"] if base["seasonal_naive"] > 0 else np.nan
        )
        skill_persist = 1.0 - mae / base["persistence"] if base["persistence"] > 0 else np.nan

        metrics[f"horizon_{h}h"] = {
            "mae": mae,
            "rmse": rmse,
            "n_samples": int(len(act)),
            "baseline_mae": base,
            "skill_vs_seasonal_naive": float(skill_seasonal),
            "skill_vs_persistence": float(skill_persist),
        }
        print(
            f"  {h}h: MAE={mae:.4f} RMSE={rmse:.4f} "
            f"| persist={base['persistence']:.3f} seasonal={base['seasonal_naive']:.3f} "
            f"mean24={base['mean24']:.3f} "
            f"| skill_seasonal={skill_seasonal:+.3f} skill_persist={skill_persist:+.3f}"
        )
    return metrics


def run_band(band: str) -> dict:
    """Forecast one band over the pseudo-test window; return results dict."""
    w = wspr[wspr["band"] == band].copy()
    w = w.dropna(subset=["value_norm"]).sort_values("timestamp_utc").reset_index(drop=True)
    full_values = w["value_norm"].to_numpy()
    full_ts = w["timestamp_utc"].to_numpy()

    # Prediction origins = pseudo-test rows.
    start_idx = int((w["timestamp_utc"] < args.pseudo_start).sum())
    end_idx = int((w["timestamp_utc"] < args.pseudo_end).sum())
    pseudo = w.iloc[start_idx:end_idx]

    assert len(pseudo) > 0, f"{band}: empty pseudo-test"
    assert str(w["timestamp_utc"].iloc[start_idx])[:10] >= args.pseudo_start, (
        f"{band}: bad start index"
    )

    print(f"\n[band {band}] {len(w)} total rows, {len(pseudo)} pseudo-test hours")
    print(f"[band {band}] range {w['timestamp_utc'].min()} -> {w['timestamp_utc'].max()}")

    contexts: list[np.ndarray] = []
    origins: list[int] = []
    for g in range(start_idx, end_idx):
        if g + max_h > len(full_values):
            continue
        ctx_start = max(0, g - args.context_window)
        ctx = full_values[ctx_start:g]
        if len(ctx) < 24:
            continue
        contexts.append(ctx)
        origins.append(g)

    if not contexts:
        raise RuntimeError(f"{band}: no forecast origins")

    points: list[np.ndarray] = []
    n_chunks = -(-len(contexts) // chunk_size)
    for c in range(n_chunks):
        chunk = contexts[c * chunk_size : (c + 1) * chunk_size]
        point, _quantile = model.forecast(max_h, chunk)
        points.append(np.asarray(point, dtype=np.float64))
        print(f"  [{band}] batch {c + 1}/{n_chunks}")
    forecast_arr = np.concatenate(points, axis=0)

    # Records: TimesFM prediction + three baselines, same origin g, same target g+h-1.
    records = []
    for j, g in enumerate(origins):
        rec = {"ts": str(full_ts[g])}
        for h in horizons:
            target_idx = g + h - 1
            rec[f"actual_{h}h"] = float(full_values[target_idx])
            rec[f"pred_{h}h"] = float(forecast_arr[j, h - 1])
            # persistence: always values[g-1]
            rec[f"persist_{h}h"] = float(full_values[g - 1])
            # seasonal-naive: values[g-(25-h)]; equals persistence when h==24
            s_lag = 25 - h
            rec[f"seasonal_{h}h"] = float(full_values[g - s_lag]) if g - s_lag >= 0 else np.nan
            # mean24: trailing 24h mean up to g-1
            rec[f"mean24_{h}h"] = float(np.mean(full_values[max(0, g - 24) : g]))
        records.append(rec)

    rec_df = pd.DataFrame(records)

    # Metrics (shared implementation with --from-records)
    print(f"[band {band}] Metrics:")
    metrics = compute_metrics(rec_df)

    # Save per-hour records for visualization
    rec_path = ROOT / "results" / f"{records_prefix}_{band}_records.csv"
    rec_df.to_csv(rec_path, index=False, encoding="utf-8")
    print(f"  [{band}] Records -> {rec_path}")

    return {
        "band": band,
        "n_total": int(len(w)),
        "n_pseudo": int(len(pseudo)),
        "n_forecasts": int(len(records)),
        "pseudo_start": args.pseudo_start,
        "pseudo_end": args.pseudo_end,
        "context_window": args.context_window,
        "horizons": horizons,
        "metrics": metrics,
    }


def from_records_band(band: str) -> dict:
    """Recompute metrics for one band from its existing records CSV (no model)."""
    rec_path = ROOT / "results" / f"{records_prefix}_{band}_records.csv"
    if not rec_path.exists():
        raise FileNotFoundError(f"{band}: {rec_path} not found; run inference first")
    rec_df = pd.read_csv(rec_path)
    print(f"\n[band {band}] Loaded {len(rec_df)} rows from {rec_path.name}")
    print(f"[band {band}] Metrics:")
    metrics = compute_metrics(rec_df)
    return {
        "band": band,
        "n_total": None,
        "n_pseudo": int(len(rec_df)),
        "n_forecasts": int(len(rec_df)),
        "pseudo_start": args.pseudo_start,
        "pseudo_end": args.pseudo_end,
        "context_window": args.context_window,
        "horizons": horizons,
        "metrics": metrics,
    }


# ============================================================
# 3. Run all bands
# ============================================================
results = {"config": vars(args), "bands": {}}
for band in args.bands:
    results["bands"][band] = from_records_band(band) if args.from_records else run_band(band)

# ============================================================
# 4. Save
# ============================================================
out_path = ROOT / "results" / out_name
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"\n[save] Saved {out_path}")

# Summary table
label = "PHASE 4 FROZEN CONFIRMATION" if args.frozen else "PHASE 3a SUMMARY"
print("\n" + "=" * 70)
print(f"{label} (skill = 1 - MAE_model / MAE_seasonal_naive)")
print("=" * 70)
for band in args.bands:
    b = results["bands"][band]
    print(f"\n{band} ({b['n_forecasts']} forecasts):")
    for h in horizons:
        m = b["metrics"][f"horizon_{h}h"]
        print(
            f"  {h:>2}h: MAE={m['mae']:7.3f}  skill_vs_seasonal={m['skill_vs_seasonal_naive']:+.3f}"
        )
print("=" * 70)
