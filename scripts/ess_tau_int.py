#!/usr/bin/env python3
"""Effective sample size via integrated autocorrelation time (tau_int).

Q1-audit narrative fix (Point 2): the manuscript section "Effective sample
size" must describe tau_int instead of the legacy AR(1) closed form, and the
reported ESS numbers must come from a reproducible run instead of being
inherited from the old formula N(1-rho1)/(1+rho1).

Construction mirrors scripts/perm_test_18mo_3band.py:
  * window [start, end) over data/processed/unified.parquet (wspr_hourly);
  * inner join with the Kp index on the hour -> one sampled hour per native
    3-h Kp epoch (N = 4349 epochs per band in the canonical window);
  * residual = value - mean(value | month, hour_of_day, day_of_week)
    (the diurnal-seasonal residual of manuscript section 3.1);
  * tau_int from crosscorr_lib.analysis.effective_sample
    (stop rule: 5 consecutive |rho(k)| below 1.96/sqrt(n));
  * ess = n_epochs / tau_int.

Output: JSON with per-band n_epochs, tau_int, ess_epochs (UTF-8, LF).
No flare filter is applied here: section 3.5 reports the ESS of the raw
18-month matched series (flare-included, N = 4349 epochs per band).
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.effective_sample import integrated_autocorrelation_time

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--start", default="2024-04-01", help="window start (inclusive)")
parser.add_argument("--end", default="2025-10-01", help="window end (exclusive)")
parser.add_argument(
    "--out",
    default=str(ROOT / "results" / "ess_tau_int.json"),
    help="output JSON path",
)
args = parser.parse_args()

df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
full = df[(df["timestamp_utc"] >= args.start) & (df["timestamp_utc"] < args.end)]

wspr = full[full["detector_type"] == "wspr_hourly"].copy()
if wspr.empty:
    raise SystemExit(
        "no wspr_hourly rows in window; rebuild data/processed/unified.parquet "
        "with: python data/scripts/unify_schema.py"
    )
wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")
wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
wspr["month"] = wspr["timestamp_utc"].dt.to_period("M")
wspr["hour_of_day"] = wspr["timestamp_utc"].dt.hour
wspr["day_of_week"] = wspr["timestamp_utc"].dt.dayofweek

kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
kp.columns = ["timestamp_utc", "kp"]
kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
kp_h = kp.groupby("hour")["kp"].mean().reset_index()
if kp_h.empty:
    raise SystemExit("no kp rows in window; fetch them with: python data/scripts/fetch_all.py")

print(f"[window] {args.start} .. {args.end} (no flare filter, raw spot counts)")
print("=== tau_int effective sample size ===")

results = {}
for band in ["20m", "40m", "15m"]:
    sub = wspr[wspr["band"] == band].copy()
    merged = pd.merge(sub, kp_h, on="hour", how="inner").sort_values("hour").reset_index(drop=True)
    merged["day_of_week"] = merged["hour"].dt.dayofweek
    if merged.empty:
        raise SystemExit(f"[{band}] no rows after the Kp join; check unified.parquet")

    resid = merged["value"] - merged.groupby(["month", "hour_of_day", "day_of_week"])[
        "value"
    ].transform("mean")
    x = resid.to_numpy(dtype=float)
    if np.isnan(x).any():
        raise SystemExit(
            f"[{band}] {int(np.isnan(x).sum())} NaN residuals; "
            "the diurnal-seasonal residual model produced empty cells"
        )

    n = len(x)
    tau = float(integrated_autocorrelation_time(x))
    ess = n / tau
    rho1 = float(pd.Series(x).autocorr(lag=1))
    results[band] = {
        "n_epochs": int(n),
        "tau_int": round(tau, 4),
        "ess_epochs": int(round(ess)),
        "rho_lag1": round(rho1, 3),
    }
    print(
        f"  {band}: n={n}, tau_int={tau:.3f}, ESS={ess:.1f} epochs "
        f"({int(round(ess)) * 3} h), rho1={rho1:.3f}, reduction x{n / ess:.1f}"
    )

out = {
    "config": {
        "window": [args.start, args.end],
        "source": "data/processed/unified.parquet (wspr_hourly, raw spot counts)",
        "flare_filter": "off (section 3.5 reports the flare-included matched series)",
        "kp_join": "inner join on the hour -> one sampled hour per native 3-h Kp epoch",
        "residual_model": "value - mean(value | month, hour_of_day, day_of_week)",
        "estimator": "tau_int = 1 + 2*sum rho(k); stop at 5 consecutive |rho| < 1.96/sqrt(n)",
        "ess_formula": "ess = n_epochs / tau_int",
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    },
    "results": results,
}
out_path = Path(args.out)
out_path.parent.mkdir(parents=True, exist_ok=True)
# LESSONS.md: text artifacts are written as UTF-8 bytes with explicit \n
# (write_text on Windows would silently produce CRLF).
out_path.write_bytes((json.dumps(out, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
print(f"\n[OK] {out_path}")
