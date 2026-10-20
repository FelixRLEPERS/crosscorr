"""Round-3 audit, Batch B5-B6: merge/lag and block-permutation sensitivity.

B5  exact-hour join vs 3-h mean vs hourly forward-filled Kp; lag profile
B6  circular block permutation (random cut points), standardized residuals,
    and Kp-block permutation (residual series held fixed)

Output: results/round3_merge_sensitivity.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BANDS = ("20m", "40m", "15m")
BLOCK = 24
BLOCK_HOURLY = 72
SEED = 42
N_PERM = 50000
N_BOOT = 1000


def load_series():
    df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    full = df[(df["timestamp_utc"] >= "2024-04-01") & (df["timestamp_utc"] < "2025-10-01")]
    wspr = full[full["detector_type"] == "wspr_hourly"].copy()
    wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")
    wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
    kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    kp_h = kp.groupby("hour")["kp"].mean().reset_index()
    return wspr, kp_h


def build(wspr, kp_h, band: str, mode: str) -> pd.DataFrame:
    sub = wspr[wspr["band"] == band][["hour", "value"]].sort_values("hour").reset_index(drop=True)
    if mode == "exact":
        m = pd.merge(sub, kp_h, on="hour", how="inner")
    elif mode == "mean3":
        s = sub.set_index("hour")["value"]
        roll = s.rolling(3).mean().shift(-2)
        m = pd.merge(roll.rename("value").reset_index(), kp_h, on="hour", how="inner").dropna()
    elif mode == "ffill":
        hourly = pd.date_range(sub["hour"].min(), sub["hour"].max(), freq="h", tz="UTC")
        s = sub.set_index("hour")["value"].reindex(hourly)
        k = kp_h.set_index("hour")["kp"].reindex(hourly).ffill()
        m = pd.DataFrame({"hour": hourly, "value": s.to_numpy(), "kp": k.to_numpy()}).dropna()
    else:
        raise ValueError(mode)
    m = m.sort_values("hour").reset_index(drop=True)
    m["state"] = np.where(m["kp"] >= 5, "storm", np.where(m["kp"] < 3, "quiet", "other"))
    m["month"] = m["hour"].dt.strftime("%Y-%m")
    m["hod"] = m["hour"].dt.hour
    m["dow"] = m["hour"].dt.dayofweek
    m["resid"] = m["value"] - m.groupby(["month", "hod", "dow"])["value"].transform("mean")
    return m


def drop(v, st):
    s = v[st == "storm"]
    q = v[st == "quiet"]
    return 100.0 * (s.mean() - q.mean()) / q.mean()


def boot_ci(v, st, block):
    rng = np.random.default_rng(SEED)
    n = len(v) // block * block
    vv = v[:n].reshape(-1, block)
    ss = (st[:n] == "storm").reshape(-1, block)
    qq = (st[:n] == "quiet").reshape(-1, block)
    nb = vv.shape[0]
    out = np.full(N_BOOT, np.nan)
    for i in range(N_BOOT):
        idx = rng.integers(0, nb, nb)
        a, s, q = vv[idx].ravel(), ss[idx].ravel(), qq[idx].ravel()
        if s.sum() and q.sum():
            out[i] = 100.0 * (a[s].mean() - a[q].mean()) / a[q].mean()
    return [float(x) for x in np.nanpercentile(out, [2.5, 97.5])]


def perm_p(v, storm, quiet, kind: str, n_perm=N_PERM, seed=SEED):
    rng = np.random.default_rng(seed)
    obs = v[storm].mean() - v[quiet].mean()
    n = len(v) // BLOCK * BLOCK
    nb = n // BLOCK
    blocks = v[:n].reshape(nb, BLOCK)
    s = storm[:n]
    q = quiet[:n]
    count = 0
    for _ in range(n_perm):
        if kind == "circular":
            off = int(rng.integers(0, n))
            rot = np.roll(v, -off)[:n].reshape(nb, BLOCK)
            idx = rng.permutation(nb)
            vp = rot[idx].ravel()
            stat = vp[s].mean() - vp[q].mean()
        elif kind == "standard":
            idx = rng.permutation(nb)
            vp = blocks[idx].ravel()
            stat = vp[s].mean() - vp[q].mean()
        else:
            raise ValueError(kind)
        if abs(stat) >= abs(obs):
            count += 1
    return (1 + count) / (1 + n_perm)


def kp_perm_p(v, kp, n_perm=N_PERM, seed=SEED):
    """Residuals fixed; Kp blocks permuted."""
    rng = np.random.default_rng(seed)
    storm = kp >= 5
    quiet = kp < 3
    obs = v[storm].mean() - v[quiet].mean()
    n = len(v) // BLOCK * BLOCK
    nb = n // BLOCK
    vv = v[:n]
    kb = kp[:n].reshape(nb, BLOCK)
    count = 0
    for _ in range(n_perm):
        idx = rng.permutation(nb)
        kp_p = kb[idx].ravel()
        stat = vv[kp_p >= 5].mean() - vv[kp_p < 3].mean()
        if abs(stat) >= abs(obs):
            count += 1
    return (1 + count) / (1 + n_perm)


def main() -> None:
    wspr, kp_h = load_series()
    out = {"method": {"block_epochs": BLOCK, "n_perm": N_PERM, "seed": SEED}, "bands": {}}
    for band in BANDS:
        modes = {}
        for mode, block in (("exact", BLOCK), ("mean3", BLOCK), ("ffill", BLOCK_HOURLY)):
            m = build(wspr, kp_h, band, mode)
            v = m["value"].to_numpy(float)
            st = m["state"].to_numpy(object)
            modes[mode] = {
                "N": int(len(m)),
                "N_storm": int((st == "storm").sum()),
                "N_quiet": int((st == "quiet").sum()),
                "drop_pct": drop(v, st),
                "ci95_block": boot_ci(v, st, block),
                "block_size": block,
            }

        exact = build(wspr, kp_h, band, "exact")
        v = exact["value"].to_numpy(float)
        kp = exact["kp"].to_numpy(float)
        storm = kp >= 5
        quiet = kp < 3
        resid = exact["resid"].to_numpy(float)
        sd = (
            exact.groupby(["month", "hod", "dow"])["value"]
            .transform("std")
            .fillna(v.std())
            .to_numpy()
        )
        p_exact = perm_p(resid, storm, quiet, "standard")
        p_circ = perm_p(resid, storm, quiet, "circular")
        p_std = perm_p(resid / sd, storm, quiet, "standard")
        p_kp = kp_perm_p(resid, kp)

        lags = {}
        kp_series = exact.set_index("hour")["kp"]
        for lg in range(-3, 4):
            shifted = pd.Series(
                kp_series.to_numpy(), index=kp_series.index + pd.Timedelta(hours=3 * lg)
            )
            k2 = shifted.reindex(exact["hour"]).to_numpy()
            st2 = np.where(k2 >= 5, "storm", np.where(k2 < 3, "quiet", "other")).astype(object)
            lags[str(lg)] = {
                "drop_pct": drop(v, st2),
                "N_storm": int((st2 == "storm").sum()),
            }

        out["bands"][band] = {
            "modes": modes,
            "lag_epochs": lags,
            "permutation": {
                "standard_p": p_exact,
                "circular_p": p_circ,
                "standardized_p": p_std,
                "kp_block_p": p_kp,
            },
        }
        print(f"\n=== {band} ===")
        print("modes", {k: (round(v["drop_pct"], 1), v["ci95_block"]) for k, v in modes.items()})
        print("perms", out["bands"][band]["permutation"])
        print("lags", {k: round(x["drop_pct"], 1) for k, x in lags.items()})

    path = ROOT / "results" / "round3_merge_sensitivity.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
