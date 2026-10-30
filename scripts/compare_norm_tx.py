#!/usr/bin/env python3
"""Compare raw-count vs n_unique_tx-normalised runs (Phase B, selection bias).

Reads four JSONs (canonical raw runs + --norm-tx runs):
  - perm test (per band):    results/perm_test_18mo_3band{,_norm_tx}.json
  - spatial (per lat group): results/spatial_lat_groups{,_norm_tx}.json

Prints:
  1. per-band Drop% / p (raw vs norm) from the permutation test;
  2. per-latitude-group Drop% / p (raw vs norm), pooled and per band;
  3. a verdict: is the sign, the significance and the band / latitude
     gradient preserved after normalising by active transmitters?

Read-only reporter (no --apply needed). Exits non-zero when a guard fails:
missing file, norm flag absent/mismatched, or flare-filter settings differ
between the compared runs.

Usage:
  python scripts/compare_norm_tx.py
  python scripts/compare_norm_tx.py --perm-raw ... --perm-norm ... \
      --spatial-raw ... --spatial-norm ...
"""

from __future__ import annotations

import argparse
import json
import sys
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


def flare_ok(cfg: dict) -> bool:
    return bool(cfg.get("flare_filter", {}).get("exclude_flares"))


def norm_enabled(cfg: dict, nested: str | None = None) -> bool:
    node = cfg.get(nested, cfg) if nested else cfg
    return bool(node.get("norm_tx", {}).get("enabled"))


def fmt_p(p: float | None) -> str:
    return f"{p:.2e}" if p is not None else "n/a"


def fmt_drop(d: float | None) -> str:
    return f"{d:+.1f}" if d is not None else "n/a"


def order_of(items: dict[str, float | None]) -> list[str]:
    """Sort keys by drop% descending (least negative = first). NaNs last."""
    valid = {k: v for k, v in items.items() if v is not None and v == v}
    return sorted(valid, key=valid.get, reverse=True)


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

    problems: list[str] = []
    perm_raw = load(Path(args.perm_raw))
    perm_norm = load(Path(args.perm_norm))
    sp_raw = load(Path(args.spatial_raw))
    sp_norm = load(Path(args.spatial_norm))

    # ---- guards ----------------------------------------------------------- #
    if not flare_ok(perm_raw["config"]) or not flare_ok(perm_norm["config"]):
        problems.append("perm: flare filter not active in both runs")
    if not flare_ok(sp_raw["params"]) or not flare_ok(sp_norm["params"]):
        problems.append("spatial: flare filter not active in both runs")
    if norm_enabled(perm_raw["config"]):
        problems.append("perm raw input unexpectedly has norm_tx enabled")
    if not norm_enabled(perm_norm["config"]):
        problems.append("perm norm input has norm_tx disabled")
    if norm_enabled(sp_raw["params"]):
        problems.append("spatial raw input unexpectedly has norm_tx enabled")
    if not norm_enabled(sp_norm["params"]):
        problems.append("spatial norm input has norm_tx disabled")

    print("=" * 78)
    print("Phase B comparison: raw spots vs spots / n_unique_tx")
    print("=" * 78)
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        return 2
    print("[OK] guards: flare filter on in all 4 inputs; norm flags as expected")

    # ---- table 1: perm test per band -------------------------------------- #
    print()
    print("1. Permutation test per band (18 mo, block=24, no flares)")
    print("-" * 78)
    print(
        f"{'Band':<6} {'Drop% raw':>10} {'Drop% norm':>11} {'d(pp)':>8} "
        f"{'p raw':>12} {'p norm':>12}"
    )
    perm_drops_raw: dict[str, float | None] = {}
    perm_drops_norm: dict[str, float | None] = {}
    perm_sig: list[bool] = []
    perm_ps: list[float] = []
    for band in BANDS:
        r = perm_raw["results"].get(band, {})
        n = perm_norm["results"].get(band, {})
        dr, dn = r.get("drop_pct"), n.get("drop_pct")
        perm_drops_raw[band], perm_drops_norm[band] = dr, dn
        d_pp = (dn - dr) if (dr is not None and dn is not None) else None
        pr, pn = r.get("p_value"), n.get("p_value")
        perm_sig.append(bool(pn is not None and pn < 0.05))
        perm_ps.append(float(pn) if pn is not None else 1.0)
        d_pp_s = f"{d_pp:+.1f}" if d_pp is not None else "n/a"
        print(
            f"{band:<6} {fmt_drop(dr):>10} {fmt_drop(dn):>11} {d_pp_s:>8} "
            f"{fmt_p(pr):>12} {fmt_p(pn):>12}"
        )

    # ---- table 2: spatial per latitude group ------------------------------ #
    print()
    print("2. Spatial analysis per latitude group (permutation, no flares)")
    print("-" * 78)
    print(
        f"{'Cell':<14} {'Drop% raw':>10} {'Drop% norm':>11} {'d(pp)':>8} "
        f"{'p raw':>12} {'p norm':>12}"
    )
    sp_drops_raw: dict[str, float | None] = {}
    sp_drops_norm: dict[str, float | None] = {}
    sp_sig: list[tuple[str, bool, float]] = []

    def sp_rows(label_prefix: str, raw_cell: dict, norm_cell: dict, track: bool) -> None:
        for g in GROUPS:
            r, n = raw_cell.get(g, {}), norm_cell.get(g, {})
            dr, dn = r.get("drop_pct"), n.get("drop_pct")
            pr, pn = r.get("p_value"), n.get("p_value")
            if track:
                sp_drops_raw[g], sp_drops_norm[g] = dr, dn
            if pn is not None:
                sp_sig.append((f"{label_prefix.strip()} {GROUP_LABEL[g]}", bool(pn < 0.05), pn))
            d_pp = (dn - dr) if (dr is not None and dn is not None) else None
            d_pp_s = f"{d_pp:+.1f}" if d_pp is not None else "n/a"
            print(
                f"{label_prefix + GROUP_LABEL[g]:<14} {fmt_drop(dr):>10} "
                f"{fmt_drop(dn):>11} {d_pp_s:>8} {fmt_p(pr):>12} {fmt_p(pn):>12}"
            )

    sp_rows("pooled ", sp_raw["pooled"], sp_norm["pooled"], track=True)
    for band in BANDS:
        pr_b = sp_raw.get("per_band", {}).get(band, {})
        pn_b = sp_norm.get("per_band", {}).get(band, {})
        if pr_b and pn_b:
            sp_rows(f"{band} ", pr_b, pn_b, track=False)

    # ---- verdict ----------------------------------------------------------- #
    print()
    print("3. Verdict")
    print("-" * 78)
    sign_ok = all(
        v is not None and v < 0 for v in [*perm_drops_norm.values(), *sp_drops_norm.values()]
    )
    print(f"    sign (all Drop% < 0 after norm)      : {'YES' if sign_ok else 'NO'}")
    perm_cells = [
        (f"perm {band}", ok, p) for band, ok, p in zip(BANDS, perm_sig, perm_ps, strict=True)
    ]
    all_cells = perm_cells + sp_sig
    n_sig = sum(1 for _, ok, _ in all_cells if ok)
    n_tot = len(all_cells)
    print(f"    significance (p < 0.05 after norm)   : {n_sig}/{n_tot} cells")
    weak = [(lab, p) for lab, ok, p in all_cells if not ok]
    for lab, p in weak:
        print(f"      [WEAK] {lab}: p={p:.2e} (>= 0.05) after norm")
    perm_order_raw = order_of(perm_drops_raw)
    perm_order_norm = order_of(perm_drops_norm)
    perm_same = perm_order_raw == perm_order_norm
    print(f"    band gradient order raw    : {' < '.join(perm_order_raw)}")
    print(
        f"    band gradient order norm   : {' < '.join(perm_order_norm)}"
        f"   -> {'PRESERVED' if perm_same else 'CHANGED'}"
    )
    sp_order_raw = order_of(sp_drops_raw)
    sp_order_norm = order_of(sp_drops_norm)
    sp_same = sp_order_raw == sp_order_norm
    print(f"    latitude order raw         : {' < '.join(GROUP_LABEL[g] for g in sp_order_raw)}")
    print(
        f"    latitude order norm        : {' < '.join(GROUP_LABEL[g] for g in sp_order_norm)}"
        f"   -> {'PRESERVED' if sp_same else 'CHANGED'}"
    )
    verdict_ok = sign_ok and n_sig == n_tot
    print()
    if verdict_ok:
        print(
            "[VERDICT] selection bias does NOT explain the effect: sign and "
            "significance survive normalisation by active transmitters."
        )
        return 0
    if sign_ok and n_sig >= max(1, n_tot - 2):
        print(
            "[VERDICT] MAIN effect survives normalisation (sign everywhere, "
            f"{n_sig}/{n_tot} cells significant), but the weak cell(s) listed "
            "above lose significance -- candidate selection-bias artifacts; "
            "flag them for the manuscript Limitations before Q2 sync."
        )
        return 0
    print(
        "[VERDICT] normalisation changed sign/significance broadly -- inspect "
        "the tables above before drawing conclusions."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
