"""C4 (round-3 audit): distance-resolved WSPR response (path-length proxy).

Pulls hourly spot counts by great-circle distance bin from wspr.live in
14-day chunks (the server times out on full-month scans), then compares
storm (Kp >= 5) and quiet (Kp < 3) means for each band and distance bin.

Bins: 0-2000, 2000-5000, 5000-10000, >10000 km.

Outputs:
    results/path_distance_hourly_2024-2025_2026-10-20.parquet
    results/path_distance_analysis.json
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
API = "http://db1.wspr.live/"
HEADERS = {"User-Agent": "ionosphere-research/1.0"}
BAND_IDX = {7: "40m", 14: "20m", 21: "15m"}
TRAIN_START = date(2024, 4, 1)
TRAIN_END = date(2025, 10, 1)
CHUNK_DAYS = 14
BLOCK = 24
SEED = 42
N_BOOT = 1000
DBINS = ("0-2000", "2000-5000", "5000-10000", ">10000")


def fetch_chunk(d0: date, d1: date, depth: int = 0) -> list[list]:
    sql = (
        "SELECT band, toStartOfHour(time) AS hour, "
        "multiIf(distance < 2000, '0-2000', distance < 5000, '2000-5000', "
        "distance < 10000, '5000-10000', '>10000') AS dbin, count() AS spots "
        f"FROM wspr.rx WHERE time >= '{d0.isoformat()} 00:00:00' "
        f"AND time < '{d1.isoformat()} 00:00:00' AND band IN (7,14,21) "
        "GROUP BY band, hour, dbin ORDER BY band, hour, dbin FORMAT JSONCompact"
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
        return fetch_chunk(d0, mid, depth + 1) + fetch_chunk(mid, d1, depth + 1)


def pull() -> pd.DataFrame:
    rows: list[list] = []
    d = TRAIN_START
    while d < TRAIN_END:
        d1 = min(d + timedelta(days=CHUNK_DAYS), TRAIN_END)
        data = fetch_chunk(d, d1)
        rows.extend(data)
        print(f"  {d} .. {d1}: {len(data)} rows (total {len(rows)})")
        time.sleep(0.4)
        d = d1
    df = pd.DataFrame(rows, columns=["band", "hour", "dbin", "spots"])
    df["band"] = df["band"].astype(int).map(BAND_IDX)
    df["hour"] = pd.to_datetime(df["hour"], utc=True)
    df["spots"] = pd.to_numeric(df["spots"])
    return df.sort_values(["band", "dbin", "hour"]).reset_index(drop=True)


def block_ci(drop_series: np.ndarray, states: np.ndarray) -> list[float]:
    rng = np.random.default_rng(SEED)
    n = len(drop_series) // BLOCK * BLOCK
    v = drop_series[:n].reshape(-1, BLOCK)
    s = (states[:n] == "storm").reshape(-1, BLOCK)
    q = (states[:n] == "quiet").reshape(-1, BLOCK)
    nb = v.shape[0]
    out = np.full(N_BOOT, np.nan)
    for i in range(N_BOOT):
        idx = rng.integers(0, nb, nb)
        vv, ss, qq = v[idx].ravel(), s[idx].ravel(), q[idx].ravel()
        if ss.sum() and qq.sum():
            out[i] = 100.0 * (vv[ss].mean() - vv[qq].mean()) / vv[qq].mean()
    return [float(x) for x in np.nanpercentile(out, [2.5, 97.5])]


def main() -> None:
    parquet = ROOT / "results" / "path_distance_hourly_2024-2025_2026-10-20.parquet"
    if parquet.exists():
        print(f"Loading cached {parquet.name}")
        df = pd.read_parquet(parquet)
    else:
        print("Pulling distance-binned WSPR counts (14-day chunks)...")
        df = pull()
        df.to_parquet(parquet, index=False)
        print(f"Wrote {parquet} ({len(df)} rows)")

    kp = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    kp = kp[(kp["timestamp_utc"] >= "2024-04-01") & (kp["timestamp_utc"] < "2025-10-01")]
    kp = kp[kp["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    kp_h = kp.groupby("hour")["kp"].mean().reset_index()

    m = pd.merge(df, kp_h, on="hour", how="inner")
    m["state"] = np.where(m["kp"] >= 5, "storm", np.where(m["kp"] < 3, "quiet", "other"))

    out = {
        "method": {
            "source": "wspr.live ClickHouse, 14-day chunks, 2026-10-20",
            "distance_bins_km": list(DBINS),
            "state": "storm Kp>=5, quiet Kp<3",
            "bootstrap": "24-epoch block bootstrap, 1000 resamples, seed 42",
        },
        "bands": {},
    }
    for band, g in m.groupby("band", sort=False):
        entry = {"bins": {}}
        total_storm = g.loc[g["state"] == "storm", "spots"].sum()
        total_quiet = g.loc[g["state"] == "quiet", "spots"].sum()
        for dbin in DBINS:
            b = g[g["dbin"] == dbin].sort_values("hour")
            st = b["state"].to_numpy(object)
            v = b["spots"].to_numpy(float)
            s = v[st == "storm"]
            q = v[st == "quiet"]
            drop = 100.0 * (s.mean() - q.mean()) / q.mean() if len(s) and len(q) else float("nan")
            entry["bins"][dbin] = {
                "N_epochs": int(len(b)),
                "N_storm": int((st == "storm").sum()),
                "N_quiet": int((st == "quiet").sum()),
                "mean_spots_storm": float(s.mean()) if len(s) else None,
                "mean_spots_quiet": float(q.mean()) if len(q) else None,
                "drop_pct": float(drop),
                "ci95_block": block_ci(v, st),
                "share_of_storm_spots": float(s.sum() / total_storm) if total_storm else None,
                "share_of_quiet_spots": float(q.sum() / total_quiet) if total_quiet else None,
            }
        out["bands"][band] = entry
        print(f"\n=== {band} ===")
        for dbin, x in entry["bins"].items():
            print(
                f"  {dbin:>10}: drop={x['drop_pct']:.1f}% CI={x['ci95_block']} "
                f"N={x['N_storm']}/{x['N_quiet']} share_storm={x['share_of_storm_spots']:.2f}"
            )

    path = ROOT / "results" / "path_distance_analysis.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
