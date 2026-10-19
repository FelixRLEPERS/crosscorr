"""Block-bootstrap CI for the held-out/training absolute-loss ratio.

ratio = |mean(quiet) - mean(storm)| in the held-out period (Jan-Mar 2026)
      / |mean(quiet) - mean(storm)| in the training period (Apr 2024 - Sep 2025)

Both series use WSPR hourly spot counts assigned to the native 3-hourly Kp
epochs (one hourly count per epoch; storm kp >= 5, quiet kp < 3, unsettled
excluded), so one "epoch" is one 3-h slot. The training series is rebuilt from
data/processed/unified.parquet with the same construction as
scripts/perm_test_18mo_3band.py; the held-out series is read from the frozen
caches results/heldout_3band_<band>_2026-10-15.parquet.

Block bootstrap: non-overlapping blocks of 24 epochs (72 h); 1000 resamples;
seed 42; a fresh RNG(42) stream per series reproduces the component CIs of
Table 10 of the manuscript exactly. Training and held-out are resampled
independently; the ratio is formed per iteration index and the reported ratio
CI is the percentile (2.5/97.5) interval of the bootstrap ratio distribution.

Output: results/abs_loss_ratio_ci.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BANDS = ("20m", "40m", "15m")
BLOCK_EPOCHS = 24  # one epoch = 3 h -> 72 h blocks
N_BOOT = 1000
SEED = 42


def load_training_series(band: str) -> pd.DataFrame:
    """Rebuild the 3-hourly training series (hour, value, state) for one band."""
    df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    full = df[(df["timestamp_utc"] >= "2024-04-01") & (df["timestamp_utc"] < "2025-10-01")]
    wspr = full[full["detector_type"] == "wspr_hourly"].copy()
    wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")
    wspr = wspr[wspr["band"] == band].copy()
    wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
    kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    kp_h = kp.groupby("hour")["kp"].mean().reset_index()
    merged = pd.merge(wspr[["hour", "value"]], kp_h, on="hour", how="inner")
    merged = merged.sort_values("hour").reset_index(drop=True)
    merged["state"] = np.where(
        merged["kp"] >= 5, "storm", np.where(merged["kp"] < 3, "quiet", "unsettled")
    )
    return merged[["hour", "value", "state"]]


def load_heldout_series(band: str) -> pd.DataFrame:
    """Read the frozen held-out series (720 epochs: hour, value, state)."""
    path = ROOT / "results" / f"heldout_3band_{band}_2026-10-15.parquet"
    df = pd.read_parquet(path)
    df = df.sort_values("hour").reset_index(drop=True)
    return df[["hour", "value", "state"]]


def loss_point(values: np.ndarray, states: np.ndarray) -> float:
    """mean(quiet) - mean(storm) on the observed series."""
    q = values[states == "quiet"]
    s = values[states == "storm"]
    return float(q.mean() - s.mean())


def quiet_mean(values: np.ndarray, states: np.ndarray) -> float:
    return float(values[states == "quiet"].mean())


def bootstrap_losses(
    values: np.ndarray,
    states: np.ndarray,
    rng: np.random.Generator,
    n_boot: int = N_BOOT,
    block: int = BLOCK_EPOCHS,
) -> np.ndarray:
    """Block-bootstrap distribution of mean(quiet) - mean(storm).

    Non-overlapping blocks; the tail shorter than one block is dropped,
    matching scripts/training_live_phaseD_2026-10-13.py.
    """
    values = np.asarray(values, dtype=float)
    is_storm = np.asarray(states) == "storm"
    is_quiet = np.asarray(states) == "quiet"
    n_blocks = len(values) // block
    v = values[: n_blocks * block].reshape(n_blocks, block)
    s = is_storm[: n_blocks * block].reshape(n_blocks, block)
    q = is_quiet[: n_blocks * block].reshape(n_blocks, block)
    out = np.full(n_boot, np.nan)
    for i in range(n_boot):
        idx = rng.integers(0, n_blocks, n_blocks)
        pool = v[idx].ravel()
        qm = q[idx].ravel()
        sm = s[idx].ravel()
        if qm.sum() and sm.sum():
            out[i] = pool[qm].mean() - pool[sm].mean()
    return out


def main() -> None:
    results: dict = {
        "method": {
            "block_epochs": BLOCK_EPOCHS,
            "block_hours": BLOCK_EPOCHS * 3,
            "n_resamples": N_BOOT,
            "seed": SEED,
            "rng": "fresh default_rng(42) per series (reproduces Table 10 component CIs)",
            "resampling": "training and held-out independent; ratio formed per iteration index",
            "training_source": "data/processed/unified.parquet (3-hourly Kp epochs)",
            "heldout_source": "results/heldout_3band_<band>_2026-10-15.parquet",
        },
        "bands": {},
    }
    for band in BANDS:
        tr = load_training_series(band)
        hd = load_heldout_series(band)
        tr_values = tr["value"].to_numpy(dtype=float)
        tr_states = tr["state"].to_numpy(dtype=object)
        hd_values = hd["value"].to_numpy(dtype=float)
        hd_states = hd["state"].to_numpy(dtype=object)

        tr_loss = loss_point(tr_values, tr_states)
        hd_loss = loss_point(hd_values, hd_states)
        tr_quiet = quiet_mean(tr_values, tr_states)
        hd_quiet = quiet_mean(hd_values, hd_states)

        tr_dist = bootstrap_losses(tr_values, tr_states, np.random.default_rng(SEED))
        hd_dist = bootstrap_losses(hd_values, hd_states, np.random.default_rng(SEED))
        ratio_dist = np.abs(hd_dist) / np.abs(tr_dist)
        valid = ~np.isnan(ratio_dist)
        ratio_valid = ratio_dist[valid]

        tr_ci = np.percentile(tr_dist[~np.isnan(tr_dist)], [2.5, 97.5])
        hd_ci = np.percentile(hd_dist[~np.isnan(hd_dist)], [2.5, 97.5])
        ratio_ci = np.percentile(ratio_valid, [2.5, 97.5])

        results["bands"][band] = {
            "training": {
                "point": round(tr_loss, 1),
                "ci95": [round(float(tr_ci[0]), 1), round(float(tr_ci[1]), 1)],
                "n_epochs": int(len(tr_values)),
            },
            "heldout": {
                "point": round(hd_loss, 1),
                "ci95": [round(float(hd_ci[0]), 1), round(float(hd_ci[1]), 1)],
                "n_epochs": int(len(hd_values)),
            },
            "quiet_mean_training": round(tr_quiet, 1),
            "quiet_mean_heldout": round(hd_quiet, 1),
            "expected_ratio_from_quiet_growth": round(hd_quiet / tr_quiet, 4),
            "ratio": {
                "point": round(hd_loss / tr_loss, 4),
                "ci95": [round(float(ratio_ci[0]), 4), round(float(ratio_ci[1]), 4)],
                "n_valid_resamples": int(valid.sum()),
            },
        }
        b = results["bands"][band]
        print(
            f"{band}: training={b['training']['point']:.0f} "
            f"CI=[{b['training']['ci95'][0]:.0f},{b['training']['ci95'][1]:.0f}] | "
            f"heldout={b['heldout']['point']:.0f} "
            f"CI=[{b['heldout']['ci95'][0]:.0f},{b['heldout']['ci95'][1]:.0f}] | "
            f"ratio={b['ratio']['point']:.4f} "
            f"CI=[{b['ratio']['ci95'][0]:.4f},{b['ratio']['ci95'][1]:.4f}] | "
            f"expected={b['expected_ratio_from_quiet_growth']:.4f} | "
            f"n_valid={b['ratio']['n_valid_resamples']}"
        )

    out_path = ROOT / "results" / "abs_loss_ratio_ci.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
