#!/usr/bin/env python
"""Re-fetch existing wspr_hourly_*.csv files to add the n_unique_tx column.

Phase 1 (default)  enumerate targets from data/raw/wspr (the date universe is
                   the set of EXISTING files - nothing new is ever created),
                   print the plan, probe ONE request to validate the SQL.
Phase 2 --apply    re-fetch each target through download_wspr.fetch_wspr_hourly
                   (uniqExact(tx_sign) AS n_unique_tx), verify spots_count
                   stability against the current file (drift -> warning),
                   write atomically (tmp -> replace) + sha256 sidecar, exactly
                   like ``download_wspr.py --mode hourly``.

Resume: files whose header already contains n_unique_tx are skipped unless
--force. Typical invocations:

  Phase T (smoke test, 3 days x 20m):
      python data/scripts/refetch_wspr_hourly.py \\
          --start 2025-06-01 --end 2025-06-04 --bands 20m --apply
  Phase F (everything that exists, 1701 files):
      python data/scripts/refetch_wspr_hourly.py --apply

After the re-pull, rebuild unified (python data/scripts/unify_schema.py) so
meta.n_unique_tx lands per row, then refresh the Zenodo staging.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from download_wspr import _write_checksum, fetch_wspr_hourly  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "raw" / "wspr"
PREFIX = "wspr_hourly_"
NEED_COL = "n_unique_tx"


def header_cols(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return fh.readline().rstrip("\n").split(",")


def enumerate_targets(
    bands: set[str], start: str | None, end: str | None, force: bool
) -> tuple[list[tuple[str, str]], int]:
    """Return ([(date, band), ...] to fetch, n_already_current)."""
    targets: list[tuple[str, str]] = []
    current = 0
    for f in sorted(RAW.glob(f"{PREFIX}*.csv")):
        parts = f.stem.split("_")  # wspr_hourly YYYY-MM-DD band
        if len(parts) != 4:
            continue
        date, band = parts[2], parts[3]
        if band not in bands:
            continue
        if start and date < start:
            continue
        if end and date >= end:  # end is exclusive, like other repo scripts
            continue
        if not force and NEED_COL in header_cols(f):
            current += 1
            continue
        targets.append((date, band))
    return targets, current


def probe(date: str, band: str) -> None:
    """One live request: validates SQL/columns before --apply."""
    df = fetch_wspr_hourly(dt.date.fromisoformat(date), band=band)
    if df.empty:
        raise SystemExit(f"[FAIL] probe {date} {band}: empty result from API")
    missing = [c for c in ("spots_count", NEED_COL) if c not in df.columns]
    if missing:
        raise SystemExit(f"[FAIL] probe {date} {band}: missing columns {missing}")
    nuniq = pd.to_numeric(df[NEED_COL], errors="coerce")
    if nuniq.isna().all() or (nuniq <= 0).all():
        raise SystemExit(f"[FAIL] probe {date} {band}: {NEED_COL} not positive")
    sample = df.head(3)[["timestamp", "spots_count", NEED_COL]]
    print(f"[OK] probe {date} {band}: columns={list(df.columns)}")
    print(f"[OK] sample rows:\n{sample.to_string(index=False)}")


def refresh_one(date: str, band: str) -> tuple[str, str, str | None]:
    """Re-fetch one day-band. Returns (date, band, error|None)."""
    path = RAW / f"{PREFIX}{date}_{band}.csv"
    try:
        new = fetch_wspr_hourly(dt.date.fromisoformat(date), band=band)
        if new.empty:
            return date, band, "API returned 0 rows (refusing to overwrite)"
        if NEED_COL not in new.columns:
            return date, band, f"response lacks {NEED_COL}"
        # spot-count stability: same source -> same counts (warn on drift)
        try:
            old = pd.read_csv(path, usecols=["timestamp", "spots_count"])
            old["timestamp"] = pd.to_datetime(old["timestamp"], utc=True, errors="coerce")
            merged = old.merge(
                pd.DataFrame(
                    {
                        "timestamp": pd.to_datetime(new["timestamp"], utc=True),
                        "spots_count_new": new["spots_count"],
                    }
                ),
                on="timestamp",
            )
            drift = int((merged["spots_count"] != merged["spots_count_new"]).sum())
            if drift:
                print(f"  [WARN] {date} {band}: spots_count drift in {drift} hours")
        except Exception as e:  # noqa: BLE001 - old file unreadable: overwrite anyway
            print(f"  [WARN] {date} {band}: could not compare with old file: {e}")
        tmp = path.with_suffix(".csv.tmp")
        new.to_csv(tmp, index=False)
        tmp.replace(path)
        _write_checksum(path)
        return date, band, None
    except Exception as e:  # noqa: BLE001 - collect per-file failures
        tmp = path.with_suffix(".csv.tmp")
        if tmp.exists():
            tmp.unlink()
        return date, band, f"{type(e).__name__}: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default=None, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD (exclusive)")
    parser.add_argument("--bands", default="15m,20m,40m", help="comma-separated")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="re-fetch even if current")
    parser.add_argument("--apply", action="store_true", help="execute (default: plan + probe)")
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

    bands = {b.strip() for b in args.bands.split(",") if b.strip()}
    unknown = bands - {"15m", "20m", "40m"}
    if unknown:
        raise SystemExit(f"unknown bands: {sorted(unknown)}")
    if not RAW.exists():
        raise SystemExit(f"missing {RAW}")

    targets, current = enumerate_targets(bands, args.start, args.end, args.force)
    print(f"dir      : {RAW}")
    print(f"bands    : {sorted(bands)}")
    print(f"range    : {args.start or '(first)'} .. {args.end or '(last)'} (end exclusive)")
    print(f"targets  : {len(targets)} files to fetch; {current} already have {NEED_COL}")
    if not targets:
        print("[SKIP] nothing to do")
        return 0

    dmin = min(d for d, _ in targets)
    dmax = max(d for d, _ in targets)
    print(f"span     : {dmin} .. {dmax}")

    # Phase 1: validate the SQL end-to-end with a single request
    probe(dmin, targets[0][1])
    if not args.apply:
        print("[CHECK] dry run only; re-run with --apply to re-fetch")
        return 0

    # Phase 2: parallel re-fetch
    ok = fail = 0
    errors: list[str] = []
    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(refresh_one, d, b) for d, b in targets]
        for i, fut in enumerate(cf.as_completed(futures), 1):
            date, band, err = fut.result()
            if err:
                fail += 1
                errors.append(f"{date} {band}: {err}")
                print(f"  [FAIL] {i}/{len(targets)} {date} {band}: {err}")
            else:
                ok += 1
                if i % 25 == 0 or i == len(targets):
                    print(f"  ... {i}/{len(targets)} done (ok={ok} fail={fail})")

    print(f"[DONE] ok={ok} fail={fail} of {len(targets)}")
    for line in errors[:20]:
        print(f"  {line}")
    if len(errors) > 20:
        print(f"  ... and {len(errors) - 20} more")
    if fail:
        print("[NEXT] fix failures and re-run (already-refreshed files are skipped)")
        return 2
    print("[NEXT] python data/scripts/unify_schema.py  # rebuild with meta.n_unique_tx")
    print("[NEXT] python scripts/prepare_zenodo_v11.py  # refresh staging before upload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
