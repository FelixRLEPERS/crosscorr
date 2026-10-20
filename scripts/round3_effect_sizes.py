"""Round-3 audit, Batch B: effect sizes with confidence intervals and
covariate-adjusted storm drops (training + held-out, three bands).

Implements:
  B1  quiet-only and cross-fitted cell baselines + NB GLM adjusted drops
  B2  covariate balance summaries (month / UTC hour / day-of-week)
  B3  raw drops with iid and block-bootstrap CIs; Delta with block CIs;
      Kp-bin drops with iid CIs; held-out drops with block CIs; ratio CIs
  C1  negative-binomial GLM rate ratios with episode-clustered SE
  C2  seasonal decomposition (incl. summer-excluded 15 m)

Output: results/round3_effect_sizes.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
BANDS = ("20m", "40m", "15m")
TRAIN_START = "2024-04-01"
TRAIN_END = "2025-10-01"
BLOCK = 24
SEED = 42
N_BOOT = 1000
N_PERM = 20000

SEASONS = {
    12: "DJF",
    1: "DJF",
    2: "DJF",
    3: "MAM",
    4: "MAM",
    5: "MAM",
    6: "JJA",
    7: "JJA",
    8: "JJA",
    9: "SON",
    10: "SON",
    11: "SON",
}


def load_epochs(band: str, window: tuple[str, str] = (TRAIN_START, TRAIN_END)) -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    full = df[(df["timestamp_utc"] >= window[0]) & (df["timestamp_utc"] < window[1])]
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
    m["season"] = m["month"].str[-2:].astype(int).map(SEASONS)
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


def drop_pct(values: np.ndarray, states: np.ndarray) -> float:
    s = values[states == "storm"]
    q = values[states == "quiet"]
    if not len(s) or not len(q):
        return float("nan")
    return 100.0 * (s.mean() - q.mean()) / q.mean()


def iid_bootstrap_drop(values, states, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    q = values[states == "quiet"]
    s = values[states == "storm"]
    out = np.empty(n_boot)
    for i in range(n_boot):
        qm = rng.choice(q, len(q)).mean()
        sm = rng.choice(s, len(s)).mean()
        out[i] = 100.0 * (sm - qm) / qm
    return np.nanpercentile(out, [2.5, 97.5])


def block_bootstrap_drop(values, states, n_boot=N_BOOT, block=BLOCK, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(values) // block * block
    v = values[:n].reshape(-1, block)
    s = (states[:n] == "storm").reshape(-1, block)
    q = (states[:n] == "quiet").reshape(-1, block)
    nb = v.shape[0]
    out = np.full(n_boot, np.nan)
    for i in range(n_boot):
        idx = rng.integers(0, nb, nb)
        vv, ss, qq = v[idx].ravel(), s[idx].ravel(), q[idx].ravel()
        if ss.sum() and qq.sum():
            out[i] = 100.0 * (vv[ss].mean() - vv[qq].mean()) / vv[qq].mean()
    return np.nanpercentile(out, [2.5, 97.5])


def block_bootstrap_loss(values, states, n_boot=N_BOOT, block=BLOCK, seed=SEED):
    """CI for mean(quiet) - mean(storm); replicates scripts/abs_loss_ratio_ci.py."""
    rng = np.random.default_rng(seed)
    n = len(values) // block * block
    v = values[:n].reshape(-1, block)
    s = (states[:n] == "storm").reshape(-1, block)
    q = (states[:n] == "quiet").reshape(-1, block)
    nb = v.shape[0]
    out = np.full(n_boot, np.nan)
    for i in range(n_boot):
        idx = rng.integers(0, nb, nb)
        vv, ss, qq = v[idx].ravel(), s[idx].ravel(), q[idx].ravel()
        if ss.sum() and qq.sum():
            out[i] = vv[qq].mean() - vv[ss].mean()
    return np.nanpercentile(out, [2.5, 97.5])


def quiet_cell_baseline(quiet: pd.DataFrame, target: pd.DataFrame) -> np.ndarray:
    """Quiet-only (month x hour x DOW) cell mean with hierarchical fallback."""
    cell = quiet.groupby(["month", "hod", "dow"])["value"].agg(["mean", "count"])
    mh = quiet.groupby(["month", "hod"])["value"].mean()
    mm = quiet.groupby("month")["value"].mean()
    gm = quiet["value"].mean()
    out = np.empty(len(target))
    for i, row in enumerate(target.itertuples()):
        key = (row.month, row.hod, row.dow)
        if key in cell.index:
            out[i] = cell.loc[key, "mean"]
        elif (row.month, row.hod) in mh.index:
            out[i] = mh.loc[(row.month, row.hod)]
        elif row.month in mm.index:
            out[i] = mm.loc[row.month]
        else:
            out[i] = gm
    return out


def crossfit_cell_baseline(quiet: pd.DataFrame, target: pd.DataFrame) -> np.ndarray:
    """Leave-one-month-out (hour x DOW) shape; own-month quiet level."""
    out = np.empty(len(target))
    for month in target["month"].unique():
        tr = quiet[quiet["month"] != month]
        shape = tr.groupby(["hod", "dow"])["value"].mean()
        overall = tr["value"].mean()
        te_mask = (target["month"] == month).to_numpy()
        qm = quiet.loc[quiet["month"] == month, "value"]
        level = qm.mean() if len(qm) else overall
        sub = target.loc[te_mask]
        pred = np.array(
            [level + (shape.get((r.hod, r.dow), overall) - overall) for r in sub.itertuples()]
        )
        out[te_mask] = pred
    return out


def glm_adjusted(m: pd.DataFrame) -> dict:
    """Negative-binomial GLM with month/hour/DOW fixed effects + storm indicator."""
    d = m[m["state"].isin(["storm", "quiet"])].copy()
    d["storm"] = (d["state"] == "storm").astype(int)
    d["ep"] = episode_ids(m)[d.index]
    d["cluster"] = np.where(d["storm"] == 1, "ep" + d["ep"].astype(str), "m" + d["month"])
    formula = "value ~ C(month) + C(hod) + C(dow) + storm"
    res = smf.negativebinomial(formula, data=d).fit(disp=0, maxiter=200)
    res_cr = smf.negativebinomial(formula, data=d).fit(
        disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": d["cluster"]}
    )
    rr = float(np.exp(res_cr.params["storm"]))
    ci = np.exp(res_cr.conf_int().loc["storm"]).to_numpy()
    d2 = d.copy()
    d2["storm"] = 0
    pred = res.predict(d2)
    sm = d["storm"] == 1
    mean_storm = float(d.loc[sm, "value"].mean())
    mean_pred = float(np.asarray(pred)[sm.to_numpy()].mean())
    mean_quiet = float(d.loc[d["storm"] == 0, "value"].mean())
    return {
        "rr": rr,
        "rr_ci95": [float(ci[0]), float(ci[1])],
        "alpha": float(res.params.get("alpha", float("nan"))),
        "adjusted_drop_pct": 100.0 * (rr - 1.0),
        "adjusted_drop_ci95": [100.0 * (float(ci[0]) - 1.0), 100.0 * (float(ci[1]) - 1.0)],
        "audit_formula_drop_pct": 100.0 * (mean_storm - mean_pred) / mean_quiet,
        "mean_storm": mean_storm,
        "mean_pred_counterfactual": mean_pred,
        "mean_quiet": mean_quiet,
    }


def balance_summary(m: pd.DataFrame) -> dict:
    storm = m[m["state"] == "storm"]
    quiet = m[m["state"] == "quiet"]
    out: dict = {"N_storm": int(len(storm)), "N_quiet": int(len(quiet)), "covariates": {}}
    for col in ("month", "hod", "dow", "season"):
        a = storm[col].value_counts().sort_index()
        b = quiet[col].value_counts().sort_index()
        idx = sorted(set(a.index) | set(b.index), key=str)
        rows = {
            str(k): {
                "N_storm": int(a.get(k, 0)),
                "N_quiet": int(b.get(k, 0)),
                "share_storm": float(a.get(k, 0) / len(storm)),
                "share_quiet": float(b.get(k, 0) / len(quiet)),
            }
            for k in idx
        }
        max_diff = max(abs(r["share_storm"] - r["share_quiet"]) for r in rows.values())
        out["covariates"][col] = {"levels": rows, "max_abs_share_diff": max_diff}
    return out


def main() -> None:
    out: dict = {
        "method": {
            "training": [TRAIN_START, TRAIN_END],
            "state": "storm Kp>=5, quiet Kp<3",
            "iid_bootstrap": f"{N_BOOT} resamples, seed {SEED}",
            "block_bootstrap": f"{N_BOOT} resamples, {BLOCK}-epoch blocks, seed {SEED}",
            "glm": "negative binomial, C(month)+C(hod)+C(dow)+storm, "
            "SE clustered by storm episode (storm) and month (quiet)",
        },
        "training": {},
        "heldout": {},
        "seasonal": {},
        "ratio": {},
    }

    for band in BANDS:
        m = load_epochs(band)
        v = m["value"].to_numpy(float)
        st = m["state"].to_numpy(object)
        ep = episode_ids(m)
        m["ep"] = ep
        storm, quiet = st == "storm", st == "quiet"
        quiet_mean = v[quiet].mean()
        storm_mean = v[storm].mean()
        delta = storm_mean - quiet_mean
        block_ci = block_bootstrap_drop(v, st)
        loss_ci = block_bootstrap_loss(v, st)

        pred_q = quiet_cell_baseline(m[quiet], m[storm])
        adj_q = 100.0 * (storm_mean - pred_q.mean()) / quiet_mean
        pred_cf = crossfit_cell_baseline(m[quiet], m[storm])
        adj_cf = 100.0 * (storm_mean - pred_cf.mean()) / quiet_mean
        glm = glm_adjusted(m)

        bins = {
            "5-6": (m["kp"] >= 5) & (m["kp"] < 6),
            "6-7": (m["kp"] >= 6) & (m["kp"] < 7),
            "7+": m["kp"] >= 7,
            "6+": np.asarray(m["kp"] >= 6),
        }
        bin_stats = {}
        for name, mask in bins.items():
            mask = pd.Series(mask, index=m.index)
            st2 = np.where(mask, "storm", np.where(quiet, "quiet", "other")).astype(object)
            ci = iid_bootstrap_drop(v, st2)
            bin_eps = int(np.unique(ep[mask.to_numpy() & (ep > 0)]).size)
            bin_stats[name] = {
                "N_epochs": int(mask.sum()),
                "N_episodes": bin_eps,
                "drop_pct": drop_pct(v, st2),
                "ci95_iid": [float(ci[0]), float(ci[1])],
                "quiet_reference_mean": float(quiet_mean),
            }

        out["training"][band] = {
            "N": int(len(m)),
            "N_storm": int(storm.sum()),
            "N_quiet": int(quiet.sum()),
            "N_episodes": int(ep.max()),
            "storm_mean": float(storm_mean),
            "quiet_mean": float(quiet_mean),
            "delta_signed": float(delta),
            "loss": float(quiet_mean - storm_mean),
            "loss_ci95": [float(loss_ci[0]), float(loss_ci[1])],
            "drop_pct": drop_pct(v, st),
            "drop_ci95_block": [float(block_ci[0]), float(block_ci[1])],
            "drop_ci95_iid": [float(x) for x in iid_bootstrap_drop(v, st)],
            "adjusted": {
                "quiet_cell_baseline_drop_pct": float(adj_q),
                "crossfit_cell_baseline_drop_pct": float(adj_cf),
                "glm": glm,
            },
            "bins": bin_stats,
            "balance": balance_summary(m),
            "seasonal": {
                s: {
                    "N_storm": int(((m["season"] == s) & storm).sum()),
                    "N_quiet": int(((m["season"] == s) & quiet).sum()),
                    "drop_pct": drop_pct(v, np.where(m["season"] == s, st, "other").astype(object)),
                    "ci95_iid": [
                        float(x)
                        for x in iid_bootstrap_drop(
                            v, np.where(m["season"] == s, st, "other").astype(object)
                        )
                    ],
                }
                for s in ("DJF", "MAM", "JJA", "SON")
            },
            "seasonal_excl_jja": {
                "N_storm": int(((m["season"] != "JJA") & storm).sum()),
                "N_quiet": int(((m["season"] != "JJA") & quiet).sum()),
                "drop_pct": drop_pct(v, np.where(m["season"] != "JJA", st, "other").astype(object)),
                "ci95_iid": [
                    float(x)
                    for x in iid_bootstrap_drop(
                        v, np.where(m["season"] != "JJA", st, "other").astype(object)
                    )
                ],
            },
        }
        b = out["training"][band]
        print(
            f"[train {band}] raw={b['drop_pct']:.1f}% blockCI="
            f"[{b['drop_ci95_block'][0]:.1f},{b['drop_ci95_block'][1]:.1f}] "
            f"adjGLM={glm['adjusted_drop_pct']:.1f}% "
            f"CI=[{glm['adjusted_drop_ci95'][0]:.1f},{glm['adjusted_drop_ci95'][1]:.1f}] "
            f"(crossfit {adj_cf:.1f}%, quietcell {adj_q:.1f}%)"
        )

    # held-out
    for band in BANDS:
        h = pd.read_parquet(ROOT / "results" / f"heldout_3band_{band}_2026-10-15.parquet")
        h = h.sort_values("hour").reset_index(drop=True)
        v = h["value"].to_numpy(float)
        st = np.where(h["kp"] >= 5, "storm", np.where(h["kp"] < 3, "quiet", "other")).astype(object)
        h["state"] = st
        h["month"] = h["hour"].dt.strftime("%Y-%m")
        h["hod"] = h["hour"].dt.hour
        h["dow"] = h["hour"].dt.dayofweek
        h["resid"] = v - h.groupby(["month", "hod", "dow"])["value"].transform("mean")
        ci = block_bootstrap_drop(v, st)
        entry = {
            "N_total": int(len(h)),
            "N_storm": int((st == "storm").sum()),
            "N_quiet": int((st == "quiet").sum()),
            "drop_pct": drop_pct(v, st),
            "drop_ci95_block": [float(ci[0]), float(ci[1])],
            "bins": {
                name: {
                    "N_epochs": int(((h["kp"] >= lo) & (h["kp"] < hi)).sum()),
                    "drop_pct": drop_pct(
                        v,
                        np.where(
                            (h["kp"] >= lo) & (h["kp"] < hi),
                            "storm",
                            np.where(h["kp"] < 3, "quiet", "other"),
                        ).astype(object),
                    ),
                }
                for name, lo, hi in (("5-6", 5, 6), ("6-7", 6, 7), ("7+", 7, 99))
            },
        }
        try:
            entry["adjusted"] = glm_adjusted(h)
        except Exception as exc:  # noqa: BLE001
            entry["adjusted"] = {"error": str(exc)}
        out["heldout"][band] = entry
        print(f"[heldout {band}] raw={entry['drop_pct']:.1f}% CI={entry['drop_ci95_block']}")

    ratio_path = ROOT / "results" / "abs_loss_ratio_ci.json"
    if ratio_path.exists():
        rr = json.loads(ratio_path.read_text(encoding="utf-8"))
        out["ratio"] = {
            b: {
                "point": d["ratio"]["point"],
                "ci95": d["ratio"]["ci95"],
                "expected": d["expected_ratio_from_quiet_growth"],
            }
            for b, d in rr["bands"].items()
        }

    out_path = ROOT / "results" / "round3_effect_sizes.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
