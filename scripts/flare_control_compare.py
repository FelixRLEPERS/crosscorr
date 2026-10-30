"""Compare storm/quiet results with and without the solar-flare exclusion.

Phase A of the Q1 audit excludes hours whose GOES XRS 1-8 A hourly max flux
reaches the M-class threshold. This script turns the two result JSONs (one
run with --exclude-flares, one with --no-exclude-flares) into a single
comparison table: how much did the drop% and the p-value move, and how many
hours were removed.

    python scripts/flare_control_compare.py \\
        --with-flares    results/perm_test_18mo_3band_with_flares.json \\
        --without-flares results/perm_test_18mo_3band.json \\
        --out            results/flare_control_comparison.csv

Input format (produced by scripts/perm_test_18mo_3band.py and
scripts/spatial_analysis.py): JSON with a "results" (perm test) or "pooled"
+ "per_band" (spatial) mapping of group -> {drop_pct, p_value, N_storm}.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_bands(path: Path) -> dict[str, dict]:
    """Extract {key: {drop_pct, p_value, n_storm}} from a result JSON.

    Supports both shapes produced by the analysis scripts:
      * the 18-month perm test ("results" mapping band -> metrics), plus the
        section's own metrics under the literal band key when nested;
      * the spatial analysis ("per_band" band -> {high, mid, low} -> metrics
        and "pooled" {high, mid, low}), flattened to "band/latgroup" keys
        (e.g. "40m/high", "pooled/mid").
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    def metrics(row: dict) -> dict:
        return {
            "drop_pct": row.get("drop_pct", row.get("drop")),
            "p_value": row.get("p_value", row.get("p")),
            "n_storm": row.get("N_storm", row.get("n_storm")),
            "n": row.get("N", row.get("n_epochs")),
        }

    def flatten(section: dict, prefix: str = "") -> dict[str, dict]:
        out: dict[str, dict] = {}
        for key, row in section.items():
            if not isinstance(row, dict):
                continue
            name = f"{prefix}/{key}" if prefix else key
            # Nested grouping (spatial: band -> latgroup -> metrics)?
            if any(isinstance(v, dict) for v in row.values()):
                out.update(flatten(row, name))
            else:
                out[name] = metrics(row)
        return out

    out: dict[str, dict] = {}
    section = data.get("results") or data.get("per_band")
    if section is not None:
        out.update(flatten(section))
    pooled = data.get("pooled")
    if isinstance(pooled, dict):
        out.update(flatten(pooled, "pooled"))
    if not out:
        raise SystemExit(f"{path}: no 'results', 'per_band' or 'pooled' section")
    return out


def _flare_info(path: Path) -> dict:
    """Read the flare_filter block written by either script (may be absent)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    params = data.get("params") or data.get("config") or {}
    info = params.get("flare_filter")
    return info if isinstance(info, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--with-flares", required=True, help="JSON of the --no-exclude-flares run")
    parser.add_argument("--without-flares", required=True, help="JSON of the --exclude-flares run")
    parser.add_argument(
        "--out",
        default=str(ROOT / "results" / "flare_control_comparison.csv"),
        help="output CSV path",
    )
    args = parser.parse_args()

    with_f = _load_bands(Path(args.with_flares))
    without_f = _load_bands(Path(args.without_flares))
    info_w = _flare_info(Path(args.without_flares))

    n_hours_excluded = info_w.get("n_hours_excluded")
    n_flare_hours = info_w.get("n_flare_hours_in_period")
    threshold = info_w.get("threshold_w_m2")

    rows = []

    def fmt(value, spec):
        if value is None:
            return "n/a"
        return format(value, spec) if isinstance(value, float) else str(value)

    print(
        f"{'Band':<10} {'Drop% (flares)':>15} {'Drop% (no flares)':>18} "
        f"{'d(drop)':>9} {'p (flares)':>12} {'p (no flares)':>14} {'d(N_storm)':>11}"
    )
    print("-" * 93)
    for band in sorted(with_f.keys() & without_f.keys()):
        a, b = with_f[band], without_f[band]
        drop_a, drop_b = a.get("drop_pct"), b.get("drop_pct")
        p_a, p_b = a.get("p_value"), b.get("p_value")
        ns_a, ns_b = a.get("n_storm"), b.get("n_storm")
        d_drop = (
            round(drop_b - drop_a, 2)
            if isinstance(drop_a, (int, float)) and isinstance(drop_b, (int, float))
            else None
        )
        d_ns = ns_b - ns_a if isinstance(ns_a, int) and isinstance(ns_b, int) else None
        rows.append(
            {
                "band": band,
                "drop_pct_with_flares": drop_a,
                "drop_pct_without_flares": drop_b,
                "drop_pct_delta": d_drop,
                "p_value_with_flares": p_a,
                "p_value_without_flares": p_b,
                "n_storm_with_flares": ns_a,
                "n_storm_without_flares": ns_b,
                "n_storm_delta": d_ns,
            }
        )
        print(
            f"{band:<10} {fmt(drop_a, '>15.1f')} {fmt(drop_b, '>18.1f')} "
            f"{fmt(d_drop, '>9.2f')} {fmt(p_a, '>12.2e')} {fmt(p_b, '>14.2e')} "
            f"{fmt(d_ns, '>11d')}"
        )

    print("-" * 93)
    print(
        f"flare filter: threshold={threshold} W/m2, "
        f"flare hours in period={n_flare_hours}, hours excluded={n_hours_excluded}"
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(
            [
                ",".join(rows[0].keys()) if rows else "",
                *[",".join(str(r[k]) for k in r) for r in rows],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\n[OK] {out_path}")


if __name__ == "__main__":
    main()
