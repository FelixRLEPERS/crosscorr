#!/usr/bin/env python
"""Finding A: group storm hours (Kp >= 5) into episodes.

Read-only analysis over data/processed/unified.parquet.

Window matches the paper: 2024-04-01 <= t < 2025-10-01.
In this parquet Kp is stored 3-hourly, and after the inner merge
with hourly WSPR data (see scripts/eda_18mo_3band.py:44-52) the
198 Kp >= 5 slots coincide numerically with the paper's
"198 storm hours". Episodes are therefore grouped over these
3-hourly slots.

Episode rule: sort storm slots by time; a gap strictly greater
than --gap-hours between consecutive storm slots starts a new
episode.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARQUET = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results" / "storm_episodes.json"

WINDOW_START = "2024-04-01"
WINDOW_END = "2025-10-01"  # exclusive
DEFAULT_KP_THRESHOLD = 5.0
DEFAULT_GAP_HOURS = 12.0


def load_kp_window(parquet: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet)
    kp = df.loc[df["detector_type"] == "kp", ["timestamp_utc", "value"]].copy()
    kp = kp.rename(columns={"value": "kp"})
    kp["timestamp_utc"] = pd.to_datetime(kp["timestamp_utc"], utc=True)
    kp = kp.loc[(kp["timestamp_utc"] >= WINDOW_START) & (kp["timestamp_utc"] < WINDOW_END)]
    return kp.sort_values("timestamp_utc").reset_index(drop=True)


def group_episodes(storm: pd.DataFrame, gap_hours: float) -> pd.DataFrame:
    storm = storm.sort_values("timestamp_utc").copy()
    if storm.empty:
        storm["episode"] = pd.Series(dtype="int64")
        return storm
    diff = storm["timestamp_utc"].diff()
    new_episode = diff.isna() | (diff > pd.Timedelta(hours=gap_hours))
    storm["episode"] = new_episode.cumsum().astype(int)
    return storm


def summarize(storm: pd.DataFrame, gap_hours: float) -> dict:
    if storm.empty:
        return {
            "n_storm_hours": 0,
            "n_episodes": 0,
            "gap_hours": gap_hours,
            "episodes": [],
        }
    episodes = []
    for ep, group in storm.groupby("episode", sort=True):
        start = group["timestamp_utc"].min()
        end = group["timestamp_utc"].max()
        episodes.append(
            {
                "episode": int(ep),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "n_storm_hours": int(len(group)),
                "span_hours": float((end - start).total_seconds() / 3600.0),
                "kp_max": float(group["kp"].max()),
            }
        )
    return {
        "n_storm_hours": int(len(storm)),
        "n_episodes": int(storm["episode"].nunique()),
        "gap_hours": gap_hours,
        "episodes": episodes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--kp-threshold", type=float, default=DEFAULT_KP_THRESHOLD)
    parser.add_argument("--gap-hours", type=float, default=DEFAULT_GAP_HOURS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    kp = load_kp_window(args.parquet)
    storm = kp.loc[kp["kp"] >= args.kp_threshold].reset_index(drop=True)
    storm = group_episodes(storm, args.gap_hours)
    summary = summarize(storm, args.gap_hours)
    summary.update(
        {
            "parquet": str(args.parquet),
            "window": [WINDOW_START, WINDOW_END],
            "kp_threshold": args.kp_threshold,
        }
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Parquet:       {args.parquet}")
    print(f"Window:        {WINDOW_START} .. {WINDOW_END} (exclusive)")
    print(f"Kp threshold:  >= {args.kp_threshold}")
    print(f"Storm slots:   {summary['n_storm_hours']}  (Kp >= threshold)")
    print(f"Episodes:      {summary['n_episodes']}  (gap > {args.gap_hours} h)")
    print()
    for ep in summary["episodes"]:
        print(
            f"  {ep['episode']:>3}: {ep['start']} .. {ep['end']}  "
            f"n={ep['n_storm_hours']:>3}  span={ep['span_hours']:>5.0f} h  "
            f"Kp_max={ep['kp_max']:.2f}"
        )
    print()
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
