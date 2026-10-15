"""Recompute held-out (Jan-Mar 2026) Table 8 p-values with the residual block
permutation test of Section 3.3 (residual = value - mean(month, hod, dow)).

Writes results/heldout_resid_2026-10-15.json and prints a verification table.
Decision: audit #5 blocker B3, option (ii).
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="Converting to PeriodArray")

ROOT = Path(__file__).resolve().parents[1]
N_ITER = 50000
BLOCK = 24
SEED = 42
BANDS = ["20m", "40m", "15m"]

EXPECT_P = {"20m": 1.99996e-05, "40m": 1.99996e-04, "15m": 7.99984e-05}


def block_perm(resid, storm_mask, quiet_mask, n_iter=N_ITER, block=BLOCK, seed=SEED):
    """Block permutation on the residual series, add-one (Davison-Hinkley) p."""
    n = len(resid)
    nb = n // block
    vb = resid[: nb * block].reshape(nb, block)
    sm = storm_mask[: nb * block]
    qm = quiet_mask[: nb * block]
    obs = float(resid[storm_mask].mean() - resid[quiet_mask].mean())
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_iter):
        order = rng.permutation(nb)
        rp = vb[order].ravel()
        if abs(rp[sm].mean() - rp[qm].mean()) >= abs(obs):
            cnt += 1
    p = (1 + cnt) / (1 + n_iter)
    return obs, float(p), cnt


def main():
    out = {
        "config": {
            "method": "residual block permutation (Section 3.3)",
            "residual": "value - mean(month, hour_of_day, day_of_week)",
            "n_iter": N_ITER,
            "block_size": BLOCK,
            "seed": SEED,
            "add_one": True,
            "period": "2026-01-01 .. 2026-04-01",
            "source": "results/heldout_3band_<band>_2026-10-15.parquet",
        }
    }

    print("=" * 84)
    print("Held-out Table 8 under the Section 3.3 residual permutation (50 000 iters)")
    print("=" * 84)
    print(f"{'band':<6} {'p_resid':>12} {'exceed':>7} {'obs_resid':>12} {'drop%':>8} {'N':>12}")
    ok = True
    for band in BANDS:
        d = pd.read_parquet(ROOT / "results" / f"heldout_3band_{band}_2026-10-15.parquet")
        d["hour"] = pd.to_datetime(d["hour"])
        d = d.sort_values("hour").reset_index(drop=True)
        d["month"] = d["hour"].dt.to_period("M")
        d["hod"] = d["hour"].dt.hour
        d["dow"] = d["hour"].dt.dayofweek
        d["resid"] = d["value"] - d.groupby(["month", "hod", "dow"])["value"].transform("mean")

        sm = (d["kp"] >= 5).to_numpy()
        qm = (d["kp"] < 3).to_numpy()
        obs, p, cnt = block_perm(d["resid"].to_numpy(float), sm, qm)
        drop = (
            100
            * (d.loc[d["kp"] >= 5, "value"].mean() - d.loc[d["kp"] < 3, "value"].mean())
            / d.loc[d["kp"] < 3, "value"].mean()
        )

        exp = EXPECT_P[band]
        match = abs(p - exp) < 1e-12
        ok = ok and match
        out[band] = {
            "p_resid": round(p, 8),
            "exceedances": cnt,
            "obs_resid": round(obs, 1),
            "drop_pct": round(float(drop), 2),
            "N_total": int(len(d)),
            "N_storm": int(sm.sum()),
            "N_quiet": int(qm.sum()),
        }
        print(
            f"{band:<6} {p:>12.6g} {cnt:>7} {obs:>12.1f} {drop:>8.2f} "
            f"{sm.sum():>4}/{qm.sum():<7} {'OK' if match else 'MISMATCH vs Phase 0'}"
        )

    path = ROOT / "results" / "heldout_resid_2026-10-15.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] {path}")
    if not ok:
        print("[STOP] p-values differ from Phase 0 diagnostics -- do not edit the paper")
        raise SystemExit(1)
    print("[VERIFY] all three p_resid match Phase 0 (2e-5 / 2e-4 / 8e-5)")


if __name__ == "__main__":
    main()
