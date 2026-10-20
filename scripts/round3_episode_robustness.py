"""Round-3 audit, Batch B4: episode-level robustness of the Kp-bin gradient.

 - number of independent storm episodes per Kp bin and per pairwise comparison
 - ordinal trend test (block permutation) on training residuals
 - episode-level trend test (one point per episode, by episode-max Kp)
 - leave-one-episode-out jackknife of the bin drops
 - cluster bootstrap by storm episode (bin-drop CIs)

Output: results/round3_episode_robustness.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BANDS = ("20m", "40m", "15m")
BLOCK = 24
SEED = 42
N_PERM = 20000
N_BOOT = 2000
BINS = (("5-6", 5, 6), ("6-7", 6, 7), ("7+", 7, 99))


def load_epochs(band: str) -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    full = df[(df["timestamp_utc"] >= "2024-04-01") & (df["timestamp_utc"] < "2025-10-01")]
    wspr = full[full["detector_type"] == "wspr_hourly"].copy()
    wspr["band"] = wspr["detector_id"].astype(str).str.replace("wspr_hourly_", "")
    wspr = wspr[wspr["band"] == band]
    wspr["hour"] = wspr["timestamp_utc"].dt.floor("1h")
    kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    kp_h = kp.groupby("hour")["kp"].mean().reset_index()
    m = pd.merge(wspr[["hour", "value"]], kp_h, on="hour", how="inner")
    m = m.sort_values("hour").reset_index(drop=True)
    m["month"] = m["hour"].dt.strftime("%Y-%m")
    m["hod"] = m["hour"].dt.hour
    m["dow"] = m["hour"].dt.dayofweek
    m["state"] = np.where(m["kp"] >= 5, "storm", np.where(m["kp"] < 3, "quiet", "other"))
    m["resid"] = m["value"] - m.groupby(["month", "hod", "dow"])["value"].transform("mean")
    return m


def episode_ids(m: pd.DataFrame, gap_hours: float = 12.0) -> np.ndarray:
    ids = np.full(len(m), -1, dtype=int)
    idx = np.where(m["state"].to_numpy() == "storm")[0]
    if not len(idx):
        return ids
    times = m["hour"].to_numpy()
    ep = 1
    ids[idx[0]] = ep
    for a, b in zip(idx[:-1], idx[1:], strict=False):
        if (times[b] - times[a]) / np.timedelta64(1, "h") > gap_hours:
            ep += 1
        ids[b] = ep
    return ids


def drop_for_mask(m: pd.DataFrame, mask: np.ndarray, keep: np.ndarray | None = None) -> float:
    quiet = (m["state"] == "quiet").to_numpy()
    if keep is not None:
        mask = mask & keep
        quiet = quiet & keep
    s = m.loc[mask, "value"]
    q = m.loc[quiet, "value"]
    if not len(s) or not len(q):
        return float("nan")
    return 100.0 * (s.mean() - q.mean()) / q.mean()


def trend_permutation(m: pd.DataFrame, n_perm: int = N_PERM, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    score = np.full(len(m), np.nan)
    score[(m["kp"] >= 5) & (m["kp"] < 6)] = 0.0
    score[(m["kp"] >= 6) & (m["kp"] < 7)] = 1.0
    score[m["kp"] >= 7] = 2.0
    resid = m["resid"].to_numpy()
    sm = ~np.isnan(score)
    x = score[sm]
    y = resid[sm]
    xm, ym = x.mean(), y.mean()
    obs = float(((x - xm) * (y - ym)).sum() / ((x - xm) ** 2).sum())

    n = len(resid) // BLOCK * BLOCK
    nb = n // BLOCK
    blocks = resid[:n].reshape(nb, BLOCK)
    sm_t = sm[:n]
    x_t = score[:n]
    xx = x_t[sm_t]
    xm2 = xx.mean()
    denom = ((xx - xm2) ** 2).sum()
    count = 0
    for _ in range(n_perm):
        idx = rng.permutation(nb)
        rp = blocks[idx].ravel()
        yy = rp[sm_t]
        slope = ((xx - xm2) * (yy - yy.mean())).sum() / denom
        if abs(slope) >= abs(obs):
            count += 1
    return {
        "slope_spots_per_bin": obs,
        "p_block_perm": (1 + count) / (1 + n_perm),
        "n_perm": n_perm,
    }


def episode_trend(m: pd.DataFrame, ep: np.ndarray) -> dict:
    """One point per episode: mean residual vs episode-max Kp (Spearman)."""
    d = m[ep > 0].copy()
    d["ep"] = ep[ep > 0]
    rows = []
    for e, g in d.groupby("ep"):
        rows.append(
            {
                "ep": int(e),
                "max_kp": float(g["kp"].max()),
                "mean_resid": float(g["resid"].mean()),
                "n_epochs": int(len(g)),
            }
        )
    e = pd.DataFrame(rows)
    rho = float(e["max_kp"].corr(e["mean_resid"], method="spearman"))
    rng = np.random.default_rng(SEED)
    vals = e["mean_resid"].to_numpy()
    count = 0
    for _ in range(N_PERM):
        perm = rng.permutation(vals)
        r = np.corrcoef(e["max_kp"].rank(), pd.Series(perm).rank())[0, 1]
        if abs(r) >= abs(rho):
            count += 1
    bins = {name: int(((e["max_kp"] >= lo) & (e["max_kp"] < hi)).sum()) for name, lo, hi in BINS}
    return {
        "n_episodes": int(len(e)),
        "spearman_rho": rho,
        "p_perm": (1 + count) / (1 + N_PERM),
        "episodes_by_max_kp": bins,
    }


def main() -> None:
    out = {
        "method": {"block": BLOCK, "n_perm": N_PERM, "n_boot": N_BOOT, "seed": SEED},
        "bands": {},
    }
    for band in BANDS:
        m = load_epochs(band)
        ep = episode_ids(m)
        m["ep"] = ep
        masks = {name: ((m["kp"] >= lo) & (m["kp"] < hi)).to_numpy() for name, lo, hi in BINS}
        counts = {
            name: {
                "N_epochs": int(mask.sum()),
                "N_episodes": int(np.unique(ep[mask & (ep > 0)]).size),
            }
            for name, mask in masks.items()
        }
        pairs = {}
        for i, (a, _, _) in enumerate(BINS):
            for b, _, _ in BINS[i + 1 :]:
                ea = set(ep[masks[a] & (ep > 0)])
                eb = set(ep[masks[b] & (ep > 0)])
                pairs[f"{a} vs {b}"] = {
                    "n_episodes_a": len(ea),
                    "n_episodes_b": len(eb),
                    "n_shared": len(ea & eb),
                }

        trend = trend_permutation(m)
        ep_trend = episode_trend(m, ep)

        # leave-one-episode-out
        loo = {}
        ordering = 0
        ne = int(ep.max())
        for name, mask in masks.items():
            vals = []
            for e in range(1, ne + 1):
                d = drop_for_mask(m, mask, keep=(ep != e))
                vals.append(d)
            loo[name] = {
                "min": float(np.nanmin(vals)),
                "max": float(np.nanmax(vals)),
                "range": float(np.nanmax(vals) - np.nanmin(vals)),
            }
        for e in range(1, ne + 1):
            keep = ep != e
            d56 = drop_for_mask(m, masks["5-6"], keep)
            d67 = drop_for_mask(m, masks["6-7"], keep)
            d7 = drop_for_mask(m, masks["7+"], keep)
            if d56 > d67 > d7:
                ordering += 1

        # cluster bootstrap by episode
        rng = np.random.default_rng(SEED)
        boot = {name: [] for name in masks}
        qvals = m.loc[m["state"] == "quiet", "value"].to_numpy()
        storm_frames = {
            name: m.loc[mask, ["ep", "value"]].to_numpy(object) for name, mask in masks.items()
        }
        eps = np.arange(1, ne + 1)
        for _ in range(N_BOOT):
            draw = rng.choice(eps, size=ne, replace=True)
            for name, arr in storm_frames.items():
                sel = np.isin(arr[:, 0].astype(int), draw)
                if not sel.any():
                    continue
                boot[name].append(
                    100.0 * (arr[sel, 1].astype(float).mean() - qvals.mean()) / qvals.mean()
                )
        boot_ci = {
            name: [float(x) for x in np.nanpercentile(v, [2.5, 97.5])]
            for name, v in boot.items()
            if len(v) > 10
        }

        out["bands"][band] = {
            "episodes_total": ne,
            "counts": counts,
            "pairwise_episodes": pairs,
            "trend": trend,
            "episode_trend": ep_trend,
            "leave_one_episode_out": loo,
            "ordering_preserved_fraction": ordering / ne,
            "cluster_bootstrap_ci95": boot_ci,
        }
        print(f"\n=== {band} ===")
        print("counts", counts)
        print("pairs", pairs)
        print("trend", trend, "episode trend", ep_trend)
        print("loo", loo, "ordering", ordering, "/", ne)
        print("cluster CI", boot_ci)

    path = ROOT / "results" / "round3_episode_robustness.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
