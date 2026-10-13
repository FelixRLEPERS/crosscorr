"""Held-out 40m absolute loss with block-bootstrap CI (Finding 1.3, phase 2c).

Downloads Jan-Mar 2026 WSPR hourly counts for band 40m (band index 7)
from wspr.live, merges with Kp from data/processed/unified.parquet,
computes mean(quiet value) - mean(storm value) with three-state labels
(storm kp>=5 / quiet kp<3 / unsettled excluded) and a 24h block
bootstrap CI (1000 resamples, seed 42). Cache: results/abs_loss_ci_heldout.json.
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
WSPR_API = "https://db1.wspr.live/"
BAND_40M = 7
PERIOD = ("2026-01-01", "2026-04-01")  # Jan-Mar 2026 held-out
SLEEP_S = 0.3


def download_wspr_day(date_str: str, band_idx: int) -> pd.DataFrame:
    sql = (
        f"SELECT toStartOfHour(time) AS hour, count() AS spots "
        f"FROM wspr.rx "
        f"WHERE time >= '{date_str} 00:00:00' AND time < '{date_str} 23:59:59' "
        f"AND band = {band_idx} "
        f"GROUP BY hour ORDER BY hour FORMAT JSONCompact"
    )
    headers = {"User-Agent": "ionosphere-research/1.0"}
    resp = requests.get(WSPR_API, params={"query": sql}, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    df = pd.DataFrame(data, columns=["hour", "spots"])
    if len(df) == 0:
        return df
    df["hour"] = pd.to_datetime(df["hour"], utc=True).dt.floor("1h")
    df["value"] = pd.to_numeric(df["spots"])
    return df[["hour", "value"]]


def block_bootstrap_mean_diff(values, labels, block=24, n_boot=1000, seed=42):
    """Block bootstrap 95% CI for mean(quiet) - mean(storm).

    Three-state labels: "storm" (kp >= 5), "quiet" (kp < 3),
    "unsettled" (excluded from both means). Input must be
    time-ordered. Point estimate uses the full series; only the
    resampling distribution uses the block-truncated part.
    """
    values = np.asarray(values, dtype=float)
    labels = np.asarray(labels)
    is_storm = labels == "storm"
    is_quiet = labels == "quiet"
    point = float(values[is_quiet].mean() - values[is_storm].mean())
    n = len(values)
    n_blocks = n // block
    vb = values[: n_blocks * block].reshape(n_blocks, block)
    sb = is_storm[: n_blocks * block].reshape(n_blocks, block)
    qb = is_quiet[: n_blocks * block].reshape(n_blocks, block)
    rng = np.random.default_rng(seed)
    diffs = np.full(n_boot, np.nan)
    for i in range(n_boot):
        idx = rng.integers(0, n_blocks, size=n_blocks)
        vr = vb[idx].ravel()
        sr = sb[idx].ravel()
        qr = qb[idx].ravel()
        if sr.any() and qr.any():
            diffs[i] = vr[qr].mean() - vr[sr].mean()
    lo, hi = np.percentile(diffs[~np.isnan(diffs)], [2.5, 97.5])
    return point, float(lo), float(hi)


def main() -> int:
    print("=== Held-out 40m absolute loss (Jan-Mar 2026, live-download) ===\n")

    # 1. Kp from parquet (2026 rows present)
    df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    kp = df[df["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    kp_h = kp.groupby("hour")["kp"].mean().reset_index()
    print(f"Kp from parquet: {len(kp_h)} hourly rows")

    # 2. Download 40m WSPR day by day
    days = pd.date_range(PERIOD[0], PERIOD[1], freq="D", inclusive="left")
    print(f"Downloading {len(days)} days for band=7 (40m) from {WSPR_API} ...")
    parts = []
    fails = 0
    for i, d in enumerate(days, 1):
        ds = d.strftime("%Y-%m-%d")
        try:
            day_df = download_wspr_day(ds, BAND_40M)
            if len(day_df) > 0:
                parts.append(day_df)
        except Exception as e:
            fails += 1
            print(f"  FAIL {ds}: {e}")
            if fails >= 3:
                print("ABORT: >=3 consecutive-style failures")
                return 1
        time.sleep(SLEEP_S)
        if i % 10 == 0:
            print(f"  ... {ds} ({i}/{len(days)})")
    wspr = pd.concat(parts, ignore_index=True).sort_values("hour").reset_index(drop=True)
    print(f"Downloaded rows: {len(wspr)} (failed days: {fails})")

    # 3. Merge with Kp
    merged = pd.merge(wspr, kp_h, on="hour", how="inner").sort_values("hour").reset_index(drop=True)
    kp_vals = merged["kp"].values
    labels = np.where(kp_vals >= 5, "storm", np.where(kp_vals < 3, "quiet", "unsettled"))
    n_total = len(merged)
    n_storm = int((labels == "storm").sum())
    n_quiet = int((labels == "quiet").sum())
    n_unsettled = int((labels == "unsettled").sum())
    print(
        f"\nMerged: N_total={n_total} N_storm={n_storm} N_quiet={n_quiet} N_unsettled={n_unsettled}"
    )
    if n_total < 500:
        print("STOP: N_total < 500 — download incomplete")
        return 1

    # 4. point + block CI
    point, lo, hi = block_bootstrap_mean_diff(merged["value"].values, labels)
    print(f"\npoint estimate = {point:.0f}  (hardcode 18304, delta={point - 18304:+.0f})")
    print(f"block-CI 95%  = [{lo:.0f}, {hi:.0f}]   (block=24h, n_boot=1000, seed=42)")

    # 5. Cache
    out = ROOT / "results" / "abs_loss_ci_heldout.json"
    out.parent.mkdir(exist_ok=True)
    payload = {
        "band_40m": {
            "point": round(float(point), 1),
            "ci_low": round(float(lo), 1),
            "ci_high": round(float(hi), 1),
            "n_storm": n_storm,
            "n_quiet": n_quiet,
            "block": 24,
            "n_boot": 1000,
            "seed": 42,
            "source": "live-download 2026-10-13",
        }
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
