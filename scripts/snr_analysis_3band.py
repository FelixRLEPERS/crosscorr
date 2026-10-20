"""C3 (round-3 audit): SNR comparison storm vs quiet on 20/40/15 m.

Training period (Apr 2024 - Sep 2025): hourly mean SNR is pulled from the
wspr.live ClickHouse mirror in 14-day chunks (the server times out on
full-month scans). Held-out period (Jan - Mar 2026): read from the frozen
daily JSON extracts in data/raw/wspr_hourly/ (wspr_2026_*.json), which
already contain mean_snr.

Outputs:
    results/snr_hourly_3band_2024-2025_2026-10-20.parquet
    results/snr_analysis.json
"""

from __future__ import annotations

import glob
import json
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
API = "http://db1.wspr.live/"
HEADERS = {"User-Agent": "ionosphere-research/1.0"}
BAND_IDX = {7: "40m", 14: "20m", 21: "15m"}
TRAIN_START = date(2024, 4, 1)
TRAIN_END = date(2025, 10, 1)  # exclusive
CHUNK_DAYS = 14
BLOCK = 24
SEED = 42
N_BOOT = 1000


def fetch_chunk(d0: date, d1: date, depth: int = 0) -> list[list]:
    sql = (
        "SELECT band, toStartOfHour(time) AS hour, count() AS spots, avg(snr) AS mean_snr, "
        "countIf(snr < -20) AS n_low, countIf(snr < -24) AS n_verylow "
        f"FROM wspr.rx WHERE time >= '{d0.isoformat()} 00:00:00' "
        f"AND time < '{d1.isoformat()} 00:00:00' AND band IN (7,14,21) "
        "GROUP BY band, hour ORDER BY band, hour FORMAT JSONCompact"
    )
    try:
        r = requests.get(API, params={"query": sql}, headers=HEADERS, timeout=240)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        if (d1 - d0).days <= 1 or depth >= 4:
            print(f"  [WARN] chunk {d0}..{d1} failed permanently: {exc}")
            return []
        mid = d0 + (d1 - d0) / 2
        print(f"  [retry] splitting {d0}..{d1} at {mid}")
        left = fetch_chunk(d0, mid, depth + 1)
        right = fetch_chunk(mid, d1, depth + 1)
        return left + right


def pull_training() -> pd.DataFrame:
    rows: list[list] = []
    d = TRAIN_START
    while d < TRAIN_END:
        d1 = min(d + timedelta(days=CHUNK_DAYS), TRAIN_END)
        data = fetch_chunk(d, d1)
        rows.extend(data)
        print(f"  {d} .. {d1}: {len(data)} rows (total {len(rows)})")
        time.sleep(0.4)
        d = d1
    df = pd.DataFrame(rows, columns=["band", "hour", "spots", "mean_snr", "n_low", "n_verylow"])
    df["band"] = df["band"].astype(int).map(BAND_IDX)
    df["hour"] = pd.to_datetime(df["hour"], utc=True)
    for c in ("spots", "n_low", "n_verylow"):
        df[c] = pd.to_numeric(df[c])
    df["mean_snr"] = pd.to_numeric(df["mean_snr"])
    return df.sort_values(["band", "hour"]).reset_index(drop=True)


def load_kp_training() -> pd.DataFrame:
    df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    full = df[(df["timestamp_utc"] >= "2024-04-01") & (df["timestamp_utc"] < "2025-10-01")]
    kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    return kp.groupby("hour")["kp"].mean().reset_index()


def weighted_mean(snr: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(snr * w) / np.sum(w))


def block_boot_weighted(values: np.ndarray, weights: np.ndarray, states: np.ndarray, seed=SEED):
    """CI for storm - quiet weighted mean SNR (24-epoch blocks, on the merged epoch grid)."""
    rng = np.random.default_rng(seed)
    n = len(values) // BLOCK * BLOCK
    v = values[:n].reshape(-1, BLOCK)
    w = weights[:n].reshape(-1, BLOCK)
    s = (states[:n] == "storm").reshape(-1, BLOCK)
    q = (states[:n] == "quiet").reshape(-1, BLOCK)
    nb = v.shape[0]
    diff = np.full(N_BOOT, np.nan)
    for i in range(N_BOOT):
        idx = rng.integers(0, nb, nb)
        vv, ww, ss, qq = v[idx].ravel(), w[idx].ravel(), s[idx].ravel(), q[idx].ravel()
        if ss.sum() and qq.sum():
            diff[i] = weighted_mean(vv[ss], ww[ss]) - weighted_mean(vv[qq], ww[qq])
    return np.nanpercentile(diff, [2.5, 97.5])


def adjusted_snr_diff(g: pd.DataFrame, st: np.ndarray) -> dict:
    """Spot-weighted OLS: mean_snr ~ month + hour + DOW + storm."""
    d = g.copy()
    d["storm"] = (st == "storm").astype(int)
    formula = "mean_snr ~ C(month) + C(hod) + C(dow) + storm"
    res = smf.wls(formula, data=d, weights=d["spots"]).fit()
    ci = res.conf_int().loc["storm"]
    return {
        "diff_adjusted": float(res.params["storm"]),
        "diff_adjusted_ci95": [float(ci[0]), float(ci[1])],
    }


def summarize_epoch_frame(epochs: pd.DataFrame, label: str) -> dict:
    out: dict = {"label": label, "bands": {}}
    for band, g in epochs.groupby("band", sort=False):
        g = g.dropna(subset=["mean_snr"]).copy()
        st = g["state"].to_numpy(object)
        snr = g["mean_snr"].to_numpy(float)
        spots = g["spots"].to_numpy(float)
        stats = {
            "N_epochs": int(len(g)),
            "N_storm": int((st == "storm").sum()),
            "N_quiet": int((st == "quiet").sum()),
            "mean_snr_storm": weighted_mean(snr[st == "storm"], spots[st == "storm"]),
            "mean_snr_quiet": weighted_mean(snr[st == "quiet"], spots[st == "quiet"]),
            "frac_below_minus20_storm": float(
                g.loc[st == "storm", "n_low"].sum() / spots[st == "storm"].sum()
            ),
            "frac_below_minus20_quiet": float(
                g.loc[st == "quiet", "n_low"].sum() / spots[st == "quiet"].sum()
            ),
            "frac_below_minus24_storm": float(
                g.loc[st == "storm", "n_verylow"].sum() / spots[st == "storm"].sum()
            ),
            "frac_below_minus24_quiet": float(
                g.loc[st == "quiet", "n_verylow"].sum() / spots[st == "quiet"].sum()
            ),
        }
        ci = block_boot_weighted(snr, spots, st)
        stats["diff_storm_minus_quiet"] = stats["mean_snr_storm"] - stats["mean_snr_quiet"]
        stats["diff_ci95"] = [float(ci[0]), float(ci[1])]
        stats.update(adjusted_snr_diff(g, st))
        out["bands"][band] = stats
        print(
            f"  [{label}] {band}: SNR storm={stats['mean_snr_storm']:.2f} "
            f"quiet={stats['mean_snr_quiet']:.2f} diff={stats['diff_storm_minus_quiet']:.2f} "
            f"CI=[{ci[0]:.2f},{ci[1]:.2f}] adj={stats['diff_adjusted']:.2f} "
            f"CI=[{stats['diff_adjusted_ci95'][0]:.2f},{stats['diff_adjusted_ci95'][1]:.2f}]"
        )
    return out


def main() -> None:
    parquet_path = ROOT / "results" / "snr_hourly_3band_2024-2025_2026-10-20.parquet"
    if parquet_path.exists():
        print(f"Loading cached {parquet_path.name}")
        train_snr = pd.read_parquet(parquet_path)
    else:
        print("Pulling training SNR from wspr.live (14-day chunks)...")
        train_snr = pull_training()
        train_snr.to_parquet(parquet_path, index=False)
        print(f"Wrote {parquet_path} ({len(train_snr)} rows)")

    kp = load_kp_training()
    tr = pd.merge(train_snr, kp, on="hour", how="inner")
    tr["state"] = np.where(tr["kp"] >= 5, "storm", np.where(tr["kp"] < 3, "quiet", "other"))
    tr["month"] = tr["hour"].dt.strftime("%Y-%m")
    tr["hod"] = tr["hour"].dt.hour
    tr["dow"] = tr["hour"].dt.dayofweek
    training = summarize_epoch_frame(tr, "training")

    # held-out
    rows = []
    for path in sorted(glob.glob(str(ROOT / "data" / "raw" / "wspr_hourly" / "wspr_2026_*.json"))):
        name = Path(path).name
        band = "20m" if "20m" in name else ("40m" if "40m" in name else "15m")
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] cannot read {name}: {exc}")
            continue
        for row in data:
            if len(row) < 3:
                continue
            h, spots, mean_snr = row[0], row[1], row[2]
            rows.append([band, h, spots, mean_snr])
    hd = pd.DataFrame(rows, columns=["band", "hour", "spots", "mean_snr"])
    hd["hour"] = pd.to_datetime(hd["hour"], utc=True)
    hd = hd[(hd["hour"] >= "2026-01-01") & (hd["hour"] < "2026-04-01")]
    hd["mean_snr"] = pd.to_numeric(hd["mean_snr"], errors="coerce")
    hd = hd.dropna(subset=["mean_snr"])
    hd = hd.groupby(["band", "hour"], as_index=False).agg({"spots": "sum", "mean_snr": "mean"})
    hd["n_low"] = np.nan
    hd["n_verylow"] = np.nan

    kp_files = []
    for band in ("20m", "40m", "15m"):
        p = ROOT / "results" / f"heldout_3band_{band}_2026-10-15.parquet"
        d = pd.read_parquet(p)[["hour", "kp"]]
        d["band"] = band
        kp_files.append(d)
    hd_kp = pd.concat(kp_files, ignore_index=True)
    hd2 = pd.merge(hd, hd_kp, on=["band", "hour"], how="inner")
    hd2["state"] = np.where(hd2["kp"] >= 5, "storm", np.where(hd2["kp"] < 3, "quiet", "other"))
    hd2["month"] = hd2["hour"].dt.strftime("%Y-%m")
    hd2["hod"] = hd2["hour"].dt.hour
    hd2["dow"] = hd2["hour"].dt.dayofweek

    # held-out fractions below thresholds are unavailable from the frozen
    # daily extracts (only mean_snr was stored); report NaN there.
    heldout = {"label": "heldout", "bands": {}}
    for band, g in hd2.groupby("band", sort=False):
        g = g.dropna(subset=["mean_snr"]).copy()
        st = g["state"].to_numpy(object)
        snr = g["mean_snr"].to_numpy(float)
        spots = g["spots"].to_numpy(float)
        s, q = st == "storm", st == "quiet"
        stats = {
            "N_epochs": int(len(g)),
            "N_storm": int(s.sum()),
            "N_quiet": int(q.sum()),
            "mean_snr_storm": weighted_mean(snr[s], spots[s]),
            "mean_snr_quiet": weighted_mean(snr[q], spots[q]),
            "diff_storm_minus_quiet": weighted_mean(snr[s], spots[s])
            - weighted_mean(snr[q], spots[q]),
        }
        ci = block_boot_weighted(snr, spots, st)
        stats["diff_ci95"] = [float(ci[0]), float(ci[1])]
        stats.update(adjusted_snr_diff(g, st))
        heldout["bands"][band] = stats
        print(
            f"  [heldout] {band}: SNR storm={stats['mean_snr_storm']:.2f} "
            f"quiet={stats['mean_snr_quiet']:.2f} diff={stats['diff_storm_minus_quiet']:.2f} "
            f"adj={stats['diff_adjusted']:.2f}"
        )

    result = {
        "method": {
            "training_source": "wspr.live ClickHouse, 14-day chunks, 2026-10-20",
            "heldout_source": "data/raw/wspr_hourly/wspr_2026_*.json (mean_snr)",
            "weighting": "spot-count-weighted hourly mean SNR",
            "bootstrap": "24-epoch (72 h) block bootstrap, 1000 resamples, seed 42",
            "state": "storm Kp>=5, quiet Kp<3",
        },
        "training": training,
        "heldout": heldout,
    }
    out_path = ROOT / "results" / "snr_analysis.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
