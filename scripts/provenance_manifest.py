"""Round-3 audit, Batch B7: provenance manifest for frozen analysis inputs.

Writes results/provenance_manifest_2026-10-20.json with sha256 checksums,
row counts, timestamp ranges and the git commit of the analysis code.

Extended held-out (2026-10-27): --out lets you write a fresh manifest (e.g.
results/provenance_manifest_2026-10-27.json) without overwriting the tracked
frozen one; the dataset/artifact lists include the 2026h1 extracts when they
exist (Jan-Jun 2026 held-out window).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        default=None,
        help="output JSON path, relative to the repo root or absolute "
        "(default: results/provenance_manifest_2026-10-20.json; pass a fresh "
        "name such as results/provenance_manifest_2026-10-27.json to keep the "
        "frozen manifest untouched)",
    )
    return p.parse_args()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe_parquet(path: Path) -> dict:
    df = pd.read_parquet(path)
    out = {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "rows": int(len(df)),
        "columns": list(df.columns),
    }
    if "timestamp_utc" in df.columns:
        out["first_timestamp"] = str(df["timestamp_utc"].min())
        out["last_timestamp"] = str(df["timestamp_utc"].max())
    if "hour" in df.columns:
        out["first_hour"] = str(df["hour"].min())
        out["last_hour"] = str(df["hour"].max())
    return out


def main() -> None:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        commit, dirty = None, None

    datasets = []
    for rel in (
        "data/processed/unified.parquet",
        "results/heldout_3band_15m_2026-10-15.parquet",
        "results/heldout_3band_20m_2026-10-15.parquet",
        "results/heldout_3band_40m_2026-10-15.parquet",
        "results/heldout_3band_15m_2026h1.parquet",
        "results/heldout_3band_20m_2026h1.parquet",
        "results/heldout_3band_40m_2026h1.parquet",
        "results/snr_hourly_3band_2024-2025_2026-10-20.parquet",
        "results/path_distance_hourly_2024-2025_2026-10-20.parquet",
    ):
        p = ROOT / rel
        if p.exists():
            datasets.append(describe_parquet(p))

    artifacts = []
    for rel in (
        "results/perm_test_18mo_3band.json",
        # Dst source for §3.6 (parallel to perm_test_18mo_3band.json for Kp)
        "results/perm_test_dst_50k.json",
        "results/heldout_resid_2026-10-15.json",
        "results/abs_loss_ratio_ci.json",
        "results/heldout_resid_2026h1.json",
        "results/abs_loss_ratio_ci_2026h1.json",
        "results/round3_effect_sizes.json",
        "results/round3_episode_robustness.json",
        "results/round3_merge_sensitivity.json",
        "results/snr_analysis.json",
        "results/path_distance_analysis.json",
        # Header-table sources (audit F3, 2026-10-31)
        "results/perm_test_18mo_3band_with_flares.json",
        "results/perm_test_18mo_3band_norm_tx.json",
        "results/spatial_lat_groups_norm_tx.json",
        # Legacy FDR artifact documented (audit F4, 2026-10-31)
        "results/perm_test_18mo_3band_fdr_README.md",
    ):
        p = ROOT / rel
        if p.exists():
            artifacts.append(
                {
                    "path": rel,
                    "sha256": sha256(p),
                    "bytes": p.stat().st_size,
                }
            )

    scripts = []
    for rel in (
        "scripts/round3_effect_sizes.py",
        "scripts/round3_episode_robustness.py",
        "scripts/round3_merge_sensitivity.py",
        "scripts/snr_analysis_3band.py",
        "scripts/path_distance_analysis.py",
        "scripts/provenance_manifest.py",
        "scripts/recompute_heldout_residual.py",
        "scripts/abs_loss_ratio_ci.py",
        "scripts/build_heldout_extract.py",
        "data/scripts/fetch_heldout_2026h1.py",
    ):
        p = ROOT / rel
        if p.exists():
            scripts.append(
                {
                    "path": rel,
                    "sha256": sha256(p),
                    "bytes": p.stat().st_size,
                }
            )

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "git_status_porcelain": dirty or "",
        "training_window": ["2024-04-01", "2025-10-01"],
        "heldout_window": ["2026-01-01", "2026-07-01"],
        "heldout_window_frozen": ["2026-01-01", "2026-04-01"],
        "datasets": datasets,
        "artifacts": artifacts,
        "scripts": scripts,
        "notes": {
            "unified": "Built from wspr.live hourly aggregates, GFZ Kp and WDC Kyoto "
            "provisional Dst; frozen after the 2026-10-07/08 download.",
            "heldout": "Published frozen extracts of the live wspr.live re-download "
            "of 2026-10-15 (720 3-h epochs per band).",
            "heldout_extended": "2026h1 extracts (Jan-Jun 2026, built 2026-10-27) "
            "from data/raw/wspr_hourly: 138 frozen canonical CSV + 206 legacy JSON "
            "day-band files + day-band CSVs downloaded 2026-10-27 for the gaps "
            "Apr 25/Jun 30; superset of the frozen 2026-10-15 extracts.",
            "snr": "Hourly mean SNR pulled from wspr.live on 2026-10-20 "
            "(14-day chunks) for the training window.",
        },
    }
    args = parse_args()
    if args.out:
        path = Path(args.out)
        if not path.is_absolute():
            path = ROOT / path
    else:
        path = ROOT / "results" / "provenance_manifest_2026-10-20.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    for ds in datasets:
        print(f"{ds['path']}: {ds['rows']} rows, sha256 {ds['sha256'][:16]}...")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
