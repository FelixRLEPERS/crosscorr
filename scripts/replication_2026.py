"""Independent replication on held-out period (2026-01-01 .. 2026-06-30)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(42)
N_ITER = 5000
BLOCK = 24
WSPR_API = "http://db1.wspr.live/"
REPLICATION_PERIOD = ("2026-01-01", "2026-06-30")
BANDS = {"20m": 14, "40m": 7, "15m": 21}


def download_wspr_day(date_str: str, band_name: str, band_idx: int) -> pd.DataFrame:
    sql = (
        f"SELECT toStartOfHour(time) AS hour, count() AS spots, "
        f"avg(snr) AS mean_snr, max(distance) AS max_distance "
        f"FROM wspr.rx "
        f"WHERE time >= '{date_str} 00:00:00' AND time < '{date_str} 23:59:59' "
        f"AND band = {band_idx} "
        f"GROUP BY hour ORDER BY hour FORMAT JSONCompact"
    )
    headers = {"User-Agent": "ionosphere-research/1.0"}
    resp = requests.get(WSPR_API, params={"query": sql}, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    df = pd.DataFrame(data, columns=["hour", "spots", "mean_snr", "max_distance"])
    if len(df) == 0:
        return df
    df["hour"] = pd.to_datetime(df["hour"], utc=True).dt.floor("1h")
    df["spots"] = pd.to_numeric(df["spots"])
    df["band"] = band_name
    return df[["hour", "band", "spots"]]


def block_perm_test(merged, block_size=BLOCK, n_iter=N_ITER):
    merged = merged.copy()
    merged["resid"] = (
        merged["value"] - merged.groupby(["month", "hour_of_day"])["value"].transform("mean")
    )
    sm = (merged["kp"] >= 5).values
    qm = (merged["kp"] < 3).values
    if sm.sum() < 3 or qm.sum() < 10:
        return None, None, None, None, None

    obs = merged["resid"].values[sm].mean() - merged["resid"].values[qm].mean()
    resid = merged["resid"].values
    kpv = merged["kp"].values
    n = len(resid)
    nb = n // block_size
    rblocks = resid[: nb * block_size].reshape(nb, block_size)
    kpv = kpv[: nb * block_size]
    stats = []
    for _ in range(n_iter):
        order = RNG.permutation(nb)
        rp = rblocks[order].ravel()
        s = kpv >= 5
        q = kpv < 3
        if s.sum() == 0 or q.sum() == 0:
            continue
        stats.append(rp[s].mean() - rp[q].mean())
    stats = np.array(stats)
    p = (np.abs(stats) >= np.abs(obs)).mean()

    storm_m = merged.loc[sm, "value"].mean()
    quiet_m = merged.loc[qm, "value"].mean()
    drop = 100 * (storm_m - quiet_m) / quiet_m
    return float(obs), float(p), int(sm.sum()), int(qm.sum()), float(drop)


def main():
    print("=== Independent Replication: 2026-01-01 .. 2026-06-30 ===\n")

    # Load existing unified parquet (has Kp/Dst for 2026)
    df = pd.read_parquet(ROOT / "data" / "processed" / "unified.parquet")
    full = df[
        (df["timestamp_utc"] >= "2026-01-01") & (df["timestamp_utc"] < "2026-07-01")
    ]

    # Extract Kp
    kp = full[full["detector_type"] == "kp"][["timestamp_utc", "value"]].copy()
    kp.columns = ["timestamp_utc", "kp"]
    kp["hour"] = kp["timestamp_utc"].dt.floor("1h")
    kp_h = kp.groupby("hour")["kp"].mean().reset_index()
    print(f"Kp: {len(kp)} rows, Kp>=5: {(kp['kp']>=5).sum()} hours\n")

    # Download WSPR for each month
    all_wspr = []
    for y, m in [(2026, m) for m in range(1, 7)]:
        ndays = pd.Timestamp(y, m, 1).days_in_month
        for day in range(1, ndays + 1):
            date_str = f"{y}-{m:02d}-{day:02d}"
            for band_name, band_idx in BANDS.items():
                try:
                    day_df = download_wspr_day(date_str, band_name, band_idx)
                    if len(day_df) > 0:
                        all_wspr.append(day_df)
                except Exception as e:
                    print(f"  FAIL {date_str} {band_name}: {e}")
            if day % 5 == 0:
                print(f"  ... {date_str} done, total rows: {sum(len(d) for d in all_wspr)}")

    wspr = pd.concat(all_wspr, ignore_index=True)
    wspr = wspr.rename(columns={"hour": "hour_bin", "spots": "value"})
    wspr["month"] = wspr["hour_bin"].dt.to_period("M")
    wspr["hour_of_day"] = wspr["hour_bin"].dt.hour
    print(f"\nTotal WSPR rows: {len(wspr)}")
    print(f"Per band: {wspr.groupby('band')['value'].count().to_dict()}\n")

    # Merge WSPR with Kp and run tests
    results = {}
    print("=== Permutation Test Results ===\n")
    for band in ["20m", "40m", "15m"]:
        sub = wspr[wspr["band"] == band].copy()
        merged = pd.merge(
            sub, kp_h, left_on="hour_bin", right_on="hour", how="inner"
        ).sort_values("hour").reset_index(drop=True)
        if len(merged) < 100:
            print(f"  {band}: insufficient data (N={len(merged)})")
            continue

        obs, p, storm_N, quiet_N, drop = block_perm_test(merged)
        if obs is None:
            print(f"  {band}: insufficient storm data")
            continue

        results[band] = {
            "N_total": len(merged),
            "N_storm": storm_N,
            "N_quiet": quiet_N,
            "delta": round(obs),
            "drop_pct": round(drop, 1),
            "p_value": round(p, 4),
        }
        print(
            f"  {band}: N={len(merged)}, storm={storm_N}, quiet={quiet_N}, "
            f"delta={obs:.0f}, drop={drop:.1f}%, p={p:.4f}"
        )

    # Day/night asymmetry check
    print("\n=== Day/Night Asymmetry ===\n")
    for band in ["20m", "40m", "15m"]:
        sub = wspr[wspr["band"] == band].copy()
        merged = pd.merge(
            sub, kp_h, left_on="hour_bin", right_on="hour", how="inner"
        )
        peak = merged[merged["hour_of_day"].between(12, 18)]
        night = merged[merged["hour_of_day"].between(0, 6)]
        for period, df_sel in [("Day 12-18h", peak), ("Night 0-6h", night)]:
            s = df_sel[df_sel["kp"] >= 5]
            q = df_sel[df_sel["kp"] < 3]
            if len(s) >= 3 and len(q) >= 10:
                drop_tod = 100 * (s["value"].mean() - q["value"].mean()) / q["value"].mean()
                print(f"  {band} {period}: drop={drop_tod:.1f}%, N_storm={len(s)}")
            else:
                print(f"  {band} {period}: insuff N_storm={len(s)}")

    # Save
    out = {
        "config": {
            "period": "2026-01-01 .. 2026-06-30",
            "n_iter": N_ITER,
            "block_size": BLOCK,
            "type": "independent_replication_held_out",
        },
        "results": results,
    }
    (ROOT / "results").mkdir(exist_ok=True)
    with open(str(ROOT / "results" / "replication_2026.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\n[OK] results/replication_2026.json")


if __name__ == "__main__":
    main()
