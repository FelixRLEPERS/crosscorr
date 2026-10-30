#!/usr/bin/env python3
"""Compare block=8 spatial rerun against canonical block=24.

Reads two JSON files produced by scripts/spatial_analysis.py:
  - canonical: results/spatial_lat_groups.json (block=24, no flares)
  - block8:    results/spatial_lat_groups_block8.json (block=8, no flares)

Prints a side-by-side table (pooled + per-band cells), then checks:
  1. Conservativeness: p_block8 <= p_block24 for every cell
     (block=24 is conservative → its p-value is never smaller).
  2. drop_pct identical between runs (same data, flare-filter identical).
  3. flare_filter.exclude_flares == True in both (guards against
     accidentally running block8 with --no-exclude-flares).

Exit code 0 = all checks passed; exit code 2 = any violation.

Usage:
    python scripts/compare_block8.py
    python scripts/compare_block8.py --canonical path.json --block8 path.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "results" / "spatial_lat_groups.json"
BLOCK8 = ROOT / "results" / "spatial_lat_groups_block8.json"

P_FLOOR = 5e-5  # add-one correction floor: 1 / (20000 + 1) ≈ 5e-5


def load_json(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"[ERROR] file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_p(p: float) -> str:
    if p <= P_FLOOR * 1.1:
        return f"{p:.1e} (floor)"
    return f"{p:.4e}"


def fmt_drop(d: float) -> str:
    return f"{d:+.1f}"


def build_rows(canon: dict, b8: dict) -> list[tuple[str, dict, dict]]:
    """Yield (label, cell_canonical, cell_block8) for pooled + per-band cells."""
    rows: list[tuple[str, dict, dict]] = []

    # Pooled
    for group in ("high", "mid", "low"):
        c = canon["pooled"][group]
        b = b8["pooled"][group]
        label = f"Pooled {group.capitalize()}"
        rows.append((label, c, b))

    # Per-band
    for band in ("40m", "20m", "15m"):
        for group in ("high", "mid", "low"):
            c = canon["per_band"][band][group]
            b = b8["per_band"][band][group]
            label = f"{band} {group.capitalize()}"
            rows.append((label, c, b))

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare block=8 vs block=24 spatial results")
    parser.add_argument("--canonical", type=Path, default=CANONICAL)
    parser.add_argument("--block8", type=Path, default=BLOCK8)
    args = parser.parse_args()

    canon = load_json(args.canonical)
    b8 = load_json(args.block8)

    print("=" * 80)
    print("Block-size sensitivity check: block=8 vs block=24")
    print("=" * 80)
    print(f"Canonical: {args.canonical}")
    print(
        f"  block={canon['params']['block']}  "
        f"flare_filter.exclude_flares={canon['params']['flare_filter'].get('exclude_flares', 'MISSING')}"
    )
    print(
        f"  n_spots_total={canon['n_spots_total']:,}  "
        f"n_storm={canon['n_storm_epochs']}  n_quiet={canon['n_quiet_epochs']}"
    )
    print(f"Block8:    {args.block8}")
    print(
        f"  block={b8['params']['block']}  "
        f"flare_filter.exclude_flares={b8['params']['flare_filter'].get('exclude_flares', 'MISSING')}"
    )
    print(
        f"  n_spots_total={b8['n_spots_total']:,}  "
        f"n_storm={b8['n_storm_epochs']}  n_quiet={b8['n_quiet_epochs']}"
    )
    print()

    # Guard: flare filter must be ON in both
    violations: list[str] = []
    for name, data in [("canonical", canon), ("block8", b8)]:
        ff = data["params"]["flare_filter"]
        if not ff.get("exclude_flares", False):
            violations.append(f"{name}: flare_filter.exclude_flares must be True")

    # Guard: data unchanged
    if canon["n_spots_total"] != b8["n_spots_total"]:
        violations.append(
            f"n_spots_total mismatch: canonical={canon['n_spots_total']:,} "
            f"block8={b8['n_spots_total']:,} (data changed?)"
        )
    if canon["n_storm_epochs"] != b8["n_storm_epochs"]:
        violations.append(f"n_storm mismatch: {canon['n_storm_epochs']} vs {b8['n_storm_epochs']}")
    if canon["n_quiet_epochs"] != b8["n_quiet_epochs"]:
        violations.append(f"n_quiet mismatch: {canon['n_quiet_epochs']} vs {b8['n_quiet_epochs']}")

    # Build comparison table
    rows = build_rows(canon, b8)

    header = (
        f"{'Group':<20} {'p (b=24)':<14} {'p (b=8)':<14} {'Drop% (b=24)':<14} {'Drop% (b=8)':<14}"
    )
    print(header)
    print("-" * len(header))

    floor_count_24 = 0
    floor_count_8 = 0
    for label, c, b in rows:
        p24 = c["p_value"]
        p8 = b["p_value"]
        d24 = c["drop_pct"]
        d8 = b["drop_pct"]

        if p24 <= P_FLOOR * 1.1:
            floor_count_24 += 1
        if p8 <= P_FLOOR * 1.1:
            floor_count_8 += 1

        # Conservativeness check: p_block8 <= p_block24 (block=24 never less significant)
        if p8 > p24 * 1.05:  # 5% tolerance for float noise
            violations.append(
                f"{label}: p_block8 ({p8:.4e}) > p_block24 ({p24:.4e}) — block=24 NOT conservative"
            )

        # drop_pct must be identical (same data)
        if abs(d24 - d8) > 0.01:
            violations.append(f"{label}: drop_pct mismatch: {d24:+.2f} vs {d8:+.2f}")

        print(
            f"{label:<20} {fmt_p(p24):<14} {fmt_p(p8):<14} {fmt_drop(d24):<14} {fmt_drop(d8):<14}"
        )

    print()
    print(f"P-floor count (b=24): {floor_count_24}/12 cells")
    print(f"P-floor count (b=8):  {floor_count_8}/12 cells")
    print()

    if violations:
        print("=" * 80)
        print("VIOLATIONS:")
        for v in violations:
            print(f"  [FAIL] {v}")
        print("=" * 80)
        return 2

    print("[OK] All checks passed: block=24 is uniformly conservative, data unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
