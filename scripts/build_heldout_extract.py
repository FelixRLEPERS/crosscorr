"""Two-phase builder of the extended held-out extract (Jan-Jun 2026).

Reads WSPR hourly spot counts (data/raw/wspr/, data/raw/wspr_hourly/) and Kp
(data/raw/space_weather/kp_*.csv), assigns one hourly count per native 3-hourly
Kp epoch (hours 00,03,...,21), labels storm kp>=5 / quiet kp<3 / unsettled
otherwise -- the exact construction of the frozen extract
results/heldout_3band_<band>_2026-10-15.parquet (Jan-Mar 2026).

Phase 1 (verify, default): coverage report per band/day, Kp storm/quiet counts
per sub-period, and -- once the extract exists -- the Jan-Mar consistency check
against the frozen 2026-10-15 files (N_storm must be 47).

Phase 2 (--apply): writes results/heldout_3band_<band>_<suffix>.parquet for
each band (default suffix 2026h1). The frozen 2026-10-15 files are never
overwritten.

Usage:
    python scripts/build_heldout_extract.py
    python scripts/build_heldout_extract.py --apply --start 2026-01-01 --end 2026-06-30
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WSPR_DIR = ROOT / "data" / "raw" / "wspr"
WH_DIR = ROOT / "data" / "raw" / "wspr_hourly"
SPACE_DIR = ROOT / "data" / "raw" / "space_weather"
RESULTS = ROOT / "results"
BANDS = ["20m", "40m", "15m"]
EPOCH_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]
EPOCHS_PER_DAY = 8  # native 3-h Kp epochs per day


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--start", default="2026-01-01", help="window start YYYY-MM-DD (inclusive)")
    p.add_argument("--end", default="2026-06-30", help="window end YYYY-MM-DD (inclusive)")
    p.add_argument("--suffix", default="2026h1", help="output suffix (default: 2026h1)")
    p.add_argument(
        "--bands",
        nargs="+",
        default=BANDS,
        help=f"bands (default: {' '.join(BANDS)})",
    )
    p.add_argument("--apply", action="store_true", help="phase 2: write the parquet files")
    return p.parse_args()


def all_days(start: str, end: str) -> list[str]:
    days = []
    d = pd.Timestamp(start)
    stop = pd.Timestamp(end)
    if stop < d:
        raise SystemExit(f"--end {end} before --start {start}")
    while d <= stop:
        days.append(d.strftime("%Y-%m-%d"))
        d += pd.Timedelta(days=1)
    return days


def day_from_stem(stem: str, prefix: str) -> tuple[str, str] | None:
    if not stem.startswith(prefix):
        return None
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    day, band = parts[-2], parts[-1]
    if len(day) == 10 and day[4] == "-":
        return day, band
    return None


def json_day_band(stem: str) -> tuple[str, str] | None:
    if not stem.startswith("wspr_"):
        return None
    rest = stem[len("wspr_") :]
    band = None
    for b in BANDS:
        if rest.endswith("_" + b):
            band = b
            rest = rest[: -(len(b) + 1)]
            break
    if band is None:
        return None
    day = rest.replace("_", "-")
    if len(day) == 10 and day[4] == "-":
        return day, band
    return None


def load_day_csv(path: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(path)
    except Exception:  # noqa: BLE001
        return None
    if df.empty:
        return pd.DataFrame(columns=["hour", "value"])
    hour_col = next((c for c in ("hour", "time", "timestamp") if c in df.columns), None)
    val_col = next((c for c in ("spots", "value", "count") if c in df.columns), None)
    if hour_col is None or val_col is None:
        return None
    return pd.DataFrame({"hour": df[hour_col], "value": df[val_col]})


def load_day_json(path: Path) -> pd.DataFrame | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    rows = []
    for r in data:
        if isinstance(r, dict):
            hour = r.get("hour") or r.get("time")
            spots = r.get("spots", r.get("value", r.get("count")))
        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            hour, spots = r[0], r[1]
        else:
            continue
        if hour is not None and spots is not None:
            rows.append({"hour": hour, "value": spots})
    if not rows:
        return pd.DataFrame(columns=["hour", "value"])
    return pd.DataFrame(rows)


def load_hourly(band: str, days: list[str]) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Load hourly spot counts for band over days.

    Priority: canonical data/raw/wspr_hourly/wspr_hourly_*.csv > legacy
    data/raw/wspr/wspr_hourly_*.csv > JSON. Returns (frame, source_stats).
    """
    per_day: dict[str, list[pd.DataFrame]] = {}
    stats = {"csv": 0, "json": 0, "empty": 0}
    for day in days:
        candidates: list[pd.DataFrame] = []
        canon = WH_DIR / f"wspr_hourly_{day}_{band}.csv"
        if canon.exists():
            df = load_day_csv(canon)
            if df is not None and len(df) > 0:
                candidates.append(df)
                stats["csv"] += 1
        legacy = WSPR_DIR / f"wspr_hourly_{day}_{band}.csv"
        if legacy.exists() and not candidates:
            df = load_day_csv(legacy)
            if df is not None and len(df) > 0:
                candidates.append(df)
                stats["csv"] += 1
        if not candidates:
            for pat in (
                f"wspr_2026_{day}_{band}.json",
                f"wspr_{day}_{band}.json",
                f"wspr_{day.replace('-', '_')}_{band}.json",
            ):
                p = WH_DIR / pat
                if p.exists():
                    df = load_day_json(p)
                    if df is not None and len(df) > 0:
                        candidates.append(df)
                        stats["json"] += 1
                        break
        if not candidates:
            stats["empty"] += 1
        else:
            per_day[day] = candidates
    if not per_day:
        return pd.DataFrame(columns=["hour", "value"]), stats
    frames = []
    for _day, cands in sorted(per_day.items()):
        # merge candidates by hour (canonical wins for shared hours)
        merged: dict[str, float] = {}
        for df in reversed(cands):  # lower priority first
            d = df.copy()
            d["hour"] = pd.to_datetime(d["hour"], utc=True, errors="coerce")
            d = d.dropna(subset=["hour"]).drop_duplicates(subset=["hour"], keep="last")
            for _, row in d.iterrows():
                merged[row["hour"]] = row["value"]
        frames.append(pd.DataFrame({"hour": list(merged.keys()), "value": list(merged.values())}))
    hourly = pd.concat(frames, ignore_index=True)
    hourly = hourly.drop_duplicates(subset=["hour"], keep="last").sort_values("hour")
    return hourly.reset_index(drop=True), stats


def load_kp(start: str, end: str) -> pd.DataFrame:
    frames = []
    for f in sorted(SPACE_DIR.glob("kp_*.csv")):
        df = pd.read_csv(f)
        time_col = next((c for c in ("time", "timestamp", "hour") if c in df.columns), None)
        kp_col = next((c for c in ("kp", "Kp") if c in df.columns), None)
        if time_col is None or kp_col is None:
            continue
        frames.append(pd.DataFrame({"hour": df[time_col], "kp": df[kp_col]}))
    if not frames:
        raise SystemExit("no Kp data found in data/raw/space_weather/")
    kp = pd.concat(frames, ignore_index=True)
    kp["hour"] = pd.to_datetime(kp["hour"], utc=True, errors="coerce")
    kp = kp.dropna(subset=["hour"]).drop_duplicates(subset=["hour"], keep="last")
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    kp = kp[(kp["hour"] >= lo) & (kp["hour"] < hi)].sort_values("hour")
    return kp.reset_index(drop=True)


def build_band(band: str, hourly: pd.DataFrame, kp: pd.DataFrame) -> pd.DataFrame:
    """Inner-join hourly counts with Kp at native 3-h epochs; label states."""
    kp_epochs = kp[kp["hour"].dt.hour.isin(EPOCH_HOURS)].copy()
    epochs = kp_epochs.copy()
    epochs["state"] = "unsettled"
    epochs.loc[epochs["kp"] >= 5, "state"] = "storm"
    epochs.loc[epochs["kp"] < 3, "state"] = "quiet"
    # hourly value at the epoch-start hour only (one count per epoch, frozen logic)
    h = hourly.copy()
    h["hour"] = pd.to_datetime(h["hour"], utc=True)
    h = h[h["hour"].dt.hour.isin(EPOCH_HOURS)]
    out = epochs.merge(h, on="hour", how="inner", suffixes=("", "_h"))
    if "value_h" in out.columns:
        out["value"] = out["value_h"]
    out = out[["hour", "value", "kp", "state"]].sort_values("hour").reset_index(drop=True)
    return out


def verify_against_frozen(frames: dict[str, pd.DataFrame], start: str) -> bool:
    """Check Jan-Mar subset vs frozen 2026-10-15 extracts. Returns True if OK."""
    if start > "2026-01-01":
        print("  (start > 2026-01-01: frozen Jan-Mar comparison skipped)")
        return True
    print("\n== VERIFY: Jan-Mar 2026 vs frozen 2026-10-15 ==")
    ok = True
    for band, df in sorted(frames.items()):
        frozen_path = RESULTS / f"heldout_3band_{band}_2026-10-15.parquet"
        if not frozen_path.exists():
            print(f"  {band}: frozen file missing -> comparison skipped")
            continue
        fr = pd.read_parquet(frozen_path)
        fr["hour"] = pd.to_datetime(fr["hour"], utc=True)
        sub = df[
            (df["hour"] >= pd.Timestamp("2026-01-01", tz="UTC"))
            & (df["hour"] < pd.Timestamp("2026-04-01", tz="UTC"))
        ]
        ns_new = int((sub["state"] == "storm").sum())
        ns_old = int((fr["state"] == "storm").sum())
        nq_new = int((sub["state"] == "quiet").sum())
        nq_old = int((fr["state"] == "quiet").sum())
        # value comparison on common hours
        m = sub.merge(fr, on="hour", how="inner", suffixes=("_new", "_old"))
        exact = int((m["value_new"] == m["value_old"]).sum()) if len(m) else 0
        status = "OK"
        if ns_new != ns_old:
            status = "N_storm MISMATCH"
            ok = False
        if len(sub) != len(fr):
            status += f" | rows {len(sub)} vs {len(fr)}"
        print(
            f"  {band}: rows new={len(sub)} old={len(fr)}; "
            f"N_storm new={ns_new} old={ns_old}; N_quiet new={nq_new} old={nq_old}; "
            f"value exact_match={exact}/{len(m)} -> {status}"
        )
    return ok


def report_coverage(frames: dict[str, pd.DataFrame], days: list[str]) -> list[str]:
    print("== coverage (epoch-hours with data) ==")
    gaps_all: list[str] = []
    day_set = set(days)
    for band in sorted(frames):
        df = frames[band]
        if df.empty:
            print(f"  {band}: NO DATA")
            gaps_all.append(f"{band}: all {len(days)} days missing")
            continue
        have_days = {d.strftime("%Y-%m-%d") for d in df["hour"].dt.date.unique()}
        missing_days = sorted(day_set - have_days)
        print(
            f"  {band}: epochs={len(df)} (expected up to {len(days) * 8}), "
            f"days with data={len(have_days)}/{len(days)}, missing days={len(missing_days)}"
        )
        if missing_days:
            print(f"      missing: {', '.join(missing_days)}")
            gaps_all.extend(f"{band}:{d}" for d in missing_days)
    return gaps_all


def report_n_storm(frames: dict[str, pd.DataFrame]) -> None:
    print("\n== N_storm / N_quiet per period ==")
    periods = [
        ("Jan-Mar", "2026-01-01", "2026-04-01"),
        ("Apr-Jun", "2026-04-01", "2026-07-01"),
        ("Jan-Jun", "2026-01-01", "2026-07-01"),
    ]
    for band in sorted(frames):
        df = frames[band]
        if df.empty:
            continue
        parts = []
        for label, lo, hi in periods:
            sub = df[
                (df["hour"] >= pd.Timestamp(lo, tz="UTC"))
                & (df["hour"] < pd.Timestamp(hi, tz="UTC"))
            ]
            ns = int((sub["state"] == "storm").sum())
            nq = int((sub["state"] == "quiet").sum())
            parts.append(f"{label}: N_storm={ns} N_quiet={nq} epochs={len(sub)}")
        print(f"  {band}: " + " | ".join(parts))


def main() -> int:
    args = parse_args()
    days = all_days(args.start, args.end)
    print(
        f"window {args.start}..{args.end}: {len(days)} days; bands={args.bands}; suffix={args.suffix}"
    )

    kp = load_kp(args.start, args.end)
    print(f"Kp epochs loaded: {len(kp)}")

    frames: dict[str, pd.DataFrame] = {}
    for band in args.bands:
        hourly, stats = load_hourly(band, days)
        frames[band] = build_band(band, hourly, kp)
        print(
            f"  {band}: hourly rows={len(hourly)} "
            f"(csv_days={stats['csv']}, json_days={stats['json']}, empty_days={stats['empty']})"
        )

    gaps = report_coverage(frames, days)
    report_n_storm(frames)

    jan_mar_ok = verify_against_frozen(frames, args.start)

    # Jan-Mar N_storm must equal 47 (frozen) when window starts 2026-01-01
    jan_mar_n47 = True
    if args.start <= "2026-01-01":
        for band, df in sorted(frames.items()):
            sub = df[
                (df["hour"] >= pd.Timestamp("2026-01-01", tz="UTC"))
                & (df["hour"] < pd.Timestamp("2026-04-01", tz="UTC"))
            ]
            ns = int((sub["state"] == "storm").sum())
            if ns != 47:
                jan_mar_n47 = False
                print(f"  CHECK FAIL {band}: Jan-Mar N_storm={ns} (expected 47)")
    if jan_mar_n47 and args.start <= "2026-01-01":
        print("  CHECK OK: Jan-Mar N_storm = 47 for all bands")

    if not args.apply:
        print("\nphase 2 skipped (run with --apply to write parquet files)")
        return 0 if not gaps and jan_mar_ok and jan_mar_n47 else 2

    if gaps:
        print(f"\nERROR: {len(gaps)} coverage gaps detected; refusing to write (see phase 1).")
        print("Run data/scripts/fetch_heldout_2026h1.py --apply first, then retry.")
        return 2
    if not jan_mar_ok or not jan_mar_n47:
        print("\nERROR: Jan-Mar consistency checks failed; not writing.")
        return 2

    RESULTS.mkdir(parents=True, exist_ok=True)
    written = []
    for band, df in sorted(frames.items()):
        out = RESULTS / f"heldout_3band_{band}_{args.suffix}.parquet"
        df.to_parquet(out, index=False)
        written.append((out, len(df)))
        print(f"wrote {out.relative_to(ROOT)} ({len(df)} rows)")

    # post-write verification: re-read and re-check Jan-Mar N_storm
    print("\n== post-write verification ==")
    ok = True
    for out, _n in written:
        band = out.stem.split("_")[2]
        df = pd.read_parquet(out)
        df["hour"] = pd.to_datetime(df["hour"], utc=True)
        sub = df[
            (df["hour"] >= pd.Timestamp("2026-01-01", tz="UTC"))
            & (df["hour"] < pd.Timestamp("2026-04-01", tz="UTC"))
        ]
        ns = int((sub["state"] == "storm").sum())
        expect = 47 if args.start <= "2026-01-01" else None
        status = "OK" if expect is None or ns == expect else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  {band}: rows={len(df)}, Jan-Mar N_storm={ns} expected={expect} -> {status}")
    print(f"\nextract ready: suffix={args.suffix}, files={len(written)}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
