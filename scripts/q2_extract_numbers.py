#!/usr/bin/env python3
"""Dump the final Q2-sync numbers from the Phase-B norm runs (read-only).

Reads the canonical (raw, flare-controlled) and --norm-tx JSONs of both
headline analyses and prints every number needed for the manuscript sync:
  - permutation test per band (Drop%, p, N, N_storm, N_quiet);
  - spatial analysis: pooled and per-band latitude groups
    (Drop%, p, q(BH), n_epochs, n_storm, n_quiet).

Raw vs norm are printed side by side so the editor can verify each
replacement against the manuscript. No numbers are hardcoded: everything
comes from the JSON inputs.

Usage:
  python scripts/q2_extract_numbers.py
  python scripts/q2_extract_numbers.py --perm-raw ... --perm-norm ... \
      --spatial-raw ... --spatial-norm ...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANDS = ("20m", "40m", "15m")
GROUPS = ("high", "mid", "low")
GROUP_LABEL = {"high": "High-lat", "mid": "Mid-lat", "low": "Low-lat"}


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"[FAIL] missing input: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def p_str(p: float | None) -> str:
    return f"{p:.2e}" if p is not None else "n/a"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perm-raw", default=str(ROOT / "results" / "perm_test_18mo_3band.json"))
    parser.add_argument(
        "--perm-norm", default=str(ROOT / "results" / "perm_test_18mo_3band_norm_tx.json")
    )
    parser.add_argument("--spatial-raw", default=str(ROOT / "results" / "spatial_lat_groups.json"))
    parser.add_argument(
        "--spatial-norm",
        default=str(ROOT / "results" / "spatial_lat_groups_norm_tx.json"),
    )
    args = parser.parse_args()

    perm_raw = load(Path(args.perm_raw))
    perm_norm = load(Path(args.perm_norm))
    sp_raw = load(Path(args.spatial_raw))
    sp_norm = load(Path(args.spatial_norm))

    print("=" * 96)
    print("Q2 final numbers: raw (flare-controlled) vs norm-tx (spots / n_unique_tx)")
    print("=" * 96)

    # ---- permutation test -------------------------------------------------- #
    print()
    print("1. Permutation test (18 mo, block=24, no flares)")
    print("-" * 96)
    print(
        f"{'Band':<6} {'N':>6} {'N_storm':>8} {'N_quiet':>8} "
        f"{'Drop% raw':>10} {'Drop% norm':>11} {'p raw':>12} {'p norm':>12}"
    )
    for band in BANDS:
        r = perm_raw["results"].get(band, {})
        n = perm_norm["results"].get(band, {})
        print(
            f"{band:<6} {n.get('N', '?'):>6} {n.get('N_storm', '?'):>8} "
            f"{n.get('N_quiet', '?'):>8} "
            f"{r.get('drop_pct', float('nan')):>10.1f} "
            f"{n.get('drop_pct', float('nan')):>11.1f} "
            f"{p_str(r.get('p_value')):>12} {p_str(n.get('p_value')):>12}"
        )

    # ---- spatial ----------------------------------------------------------- #
    def print_spatial(title: str, raw_cells: dict, norm_cells: dict) -> None:
        print()
        print(title)
        print("-" * 96)
        print(
            f"{'Cell':<14} {'n_ep':>6} {'N_storm':>8} {'N_quiet':>8} "
            f"{'Drop% raw':>10} {'Drop% norm':>11} {'p raw':>12} {'p norm':>12} "
            f"{'q norm':>12}"
        )
        for g in GROUPS:
            r, n = raw_cells.get(g, {}), norm_cells.get(g, {})
            print(
                f"{GROUP_LABEL[g]:<14} {n.get('n_epochs', '?'):>6} "
                f"{n.get('n_storm', '?'):>8} {n.get('n_quiet', '?'):>8} "
                f"{r.get('drop_pct', float('nan')):>10.1f} "
                f"{n.get('drop_pct', float('nan')):>11.1f} "
                f"{p_str(r.get('p_value')):>12} {p_str(n.get('p_value')):>12} "
                f"{p_str(n.get('q_fdr')):>12}"
            )

    print_spatial("2. Spatial, bands pooled", sp_raw.get("pooled", {}), sp_norm.get("pooled", {}))
    for band in BANDS:
        pr = sp_raw.get("per_band", {}).get(band, {})
        pn = sp_norm.get("per_band", {}).get(band, {})
        if pr and pn:
            print_spatial(f"3. Spatial, per-band: {band}", pr, pn)

    # ---- provenance -------------------------------------------------------- #
    print()
    print("4. Provenance (from the norm JSONs)")
    print("-" * 96)
    cfg = perm_norm.get("config", {})
    print(f"    perm norm_tx   : {cfg.get('norm_tx')}")
    print(f"    perm flares    : {cfg.get('flare_filter')}")
    spp = sp_norm.get("params", {})
    print(f"    spatial norm_tx: {spp.get('norm_tx')}")
    print(f"    spatial flares : {spp.get('flare_filter')}")
    print(f"    spatial n_spots: {sp_norm.get('n_spots_total'):,}")
    print(
        f"    spatial epochs : storm={sp_norm.get('n_storm_epochs')}, "
        f"quiet={sp_norm.get('n_quiet_epochs')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
