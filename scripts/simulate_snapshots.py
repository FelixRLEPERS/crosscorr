"""Generate multi-snapshot dataset for the After Effects visualization.

Produces:
    aep/snapshots/manifest.json      -- config + detectors + hidden_pairs + snapshot list
    aep/snapshots/snapshot_XX.json   -- one file per snapshot (all 45 pairs)
    aep/snapshots/snapshots.js       -- same data as a JS literal for #include

Each snapshot is one analysis window of the SAME long series. Injected hidden
pairs stay significant (INVARIANT) across windows; noise pairs flicker.

Calibration note
----------------
The task suggested ``B=100``. That is statistically unusable here: with N=10
detectors there are M=45 tested pairs, and FDR (BH) gives a minimum attainable
q = p_min * M. With B=100, p_min = 1/101, so q_min = 45/101 = 0.445 -- no pair
can ever reach CANDIDATE or INVARIANT. Verified: B=100 -> all 45 pairs NOISE.

``B=2000`` gives p_min = 1/2001, q_min = 0.0225 for the smallest p, and the
tied best pairs land at q = 0.0075 < 0.01 -> INVARIANT. This yields stable
hidden pairs plus occasional noise flicker (window 07) in ~103 s total.

Example:
    python scripts/simulate_snapshots.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.cross_correlation import (
    lagged_cross_correlation,
)
from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
N_DETECTORS = 10
N_HIDDEN = 3
T_TOTAL = 24000
WINDOW_SIZE = 4000
STEP = 1500
N_SNAPSHOTS = 12
B = 2000                      # see calibration note (template said 100)
BASE_SEED = 42
COUPLING = 0.4
MAX_LAG = 72
FDR_LEVEL = 0.05
SECONDS_PER_SNAPSHOT = 5
OUT_DIR = Path("aep/snapshots")

# Hidden pairs (detector indices, true lag). Fixed so the signal is stable.
HIDDEN = [(3, 5, 18), (7, 8, 18), (8, 9, 24)]

# Detector geometry/types from aep/final.json detectors_synthetic.
DETECTOR_META = [
    ("det_000", "wspr",         38.353847, -46.512711),
    ("det_001", "ionosonde",    -8.557018, 153.635396),
    ("det_002", "ionosonde",    50.203709, 51.791443),
    ("det_003", "magnetometer", 27.631524, 116.194181),
    ("det_004", "wspr",        -56.815171, -20.370888),
    ("det_005", "ephemeris",    66.587129, -98.194060),
    ("det_006", "gnss",         36.559558, 19.650523),
    ("det_007", "ephemeris",    40.049003, -157.025788),
    ("det_008", "ionosonde",   -52.064091, 117.947222),
    ("det_009", "ionosonde",    -6.945969, 47.399184),
]


# --------------------------------------------------------------------------- #
# Data generation
# --------------------------------------------------------------------------- #
def _generate_ar1(rng: np.random.Generator, n: int,
                  phi: float = 0.85, sigma: float = 1.0) -> np.ndarray:
    """Generate AR(1) noise with the given phi."""
    eps = rng.normal(0, sigma, size=n)
    out = np.zeros(n)
    for t in range(1, n):
        out[t] = phi * out[t - 1] + eps[t]
    return out


def _generate_long_series():
    """Return (X, names) with X shape (T_TOTAL, N_DETECTORS)."""
    rng = np.random.default_rng(BASE_SEED)
    names = [m[0] for m in DETECTOR_META]
    X = np.zeros((T_TOTAL, N_DETECTORS))
    for i in range(N_DETECTORS):
        X[:, i] = _generate_ar1(rng, T_TOTAL)

    for (i, j, tau) in HIDDEN:
        X[tau:, j] += COUPLING * X[:-tau, i]
    return X, names


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def _analyze_window(X_window: np.ndarray, names, B: int, seed: int) -> dict:
    """Analyze one window; return pairs (all 45) + metrics."""
    wide = pd.DataFrame(X_window, columns=names)
    result = cross_correlation_pairs_with_max_stat(
        wide, B=B, seed=seed, method="phase", n_jobs=-1,
    )

    name_to_idx = {n: i for i, n in enumerate(names)}
    hidden_keys = set()
    for (i, j, _tau) in HIDDEN:
        hidden_keys.add(tuple(sorted([names[i], names[j]])))

    pairs = []
    sig_pairs = set()
    for _, row in result.iterrows():
        a, b = row["detector_a"], row["detector_b"]
        key = tuple(sorted([a, b]))
        verdict = str(row["verdict"])
        if verdict != "NOISE":
            sig_pairs.add(key)

        lag_val = 0
        try:
            lags, corrs, _p = lagged_cross_correlation(
                X_window[:, name_to_idx[a]],
                X_window[:, name_to_idx[b]],
                max_lag=MAX_LAG,
            )
            j = int(np.nanargmax(np.abs(corrs)))
            lag_val = int(lags[j])
        except (ValueError, IndexError):
            lag_val = 0

        pairs.append({
            "detector_a": a,
            "detector_b": b,
            "C": round(float(row["C_obs"]), 6),
            "lag": lag_val,
            "p_value": round(float(row["p_value"]), 6),
            "q_value": round(float(row["q_value"]), 6),
            "verdict": verdict,
        })

    TP = len(sig_pairs & hidden_keys)
    FP = len(sig_pairs - hidden_keys)
    FN = len(hidden_keys - sig_pairs)
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    return {
        "pairs": pairs,
        "metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "n_significant": len(sig_pairs),
        },
    }


# --------------------------------------------------------------------------- #
# JS export (for ExtendScript #include; no JSON.parse in old AE)
# --------------------------------------------------------------------------- #
def _write_snapshots_js(path: Path, snapshots: list, detectors: list,
                        hidden_pairs: list) -> None:
    lines = []
    lines.append("// Auto-generated by scripts/simulate_snapshots.py")
    lines.append("// Data for CrossCorr_Breathe (#include in CrossCorr_Master.js).")
    lines.append("var DETECTORS = [")
    det_rows = []
    for d in detectors:
        det_id = d["id"]
        det_type = d["type"]
        det_lat = round(d["lat"], 4)
        det_lon = round(d["lon"], 4)
        det_rows.append(
            f'  {{id:"{det_id}",type:"{det_type}",'
            f'lat:{det_lat},lon:{det_lon}}}'
        )
    lines.append(",\n".join(det_rows))
    lines.append("];")
    lines.append("var HIDDEN_PAIRS = [")
    hid_rows = []
    for h in hidden_pairs:
        h_a = h["detector_a"]
        h_b = h["detector_b"]
        h_lag = h["true_lag"]
        hid_rows.append(
            f'  {{a:"{h_a}",b:"{h_b}",true_lag:{h_lag}}}'
        )
    lines.append(",\n".join(hid_rows))
    lines.append("];")
    lines.append("var SNAPSHOTS = [")
    snap_blocks = []
    for s in snapshots:
        pr_rows = []
        for p in s["pairs"]:
            p_a = p["detector_a"]
            p_b = p["detector_b"]
            p_C = p["C"]
            p_lag = p["lag"]
            p_pv = p["p_value"]
            p_qv = p["q_value"]
            p_v = p["verdict"]
            pr_rows.append(
                f'{{a:"{p_a}",b:"{p_b}",C:{p_C},lag:{p_lag},'
                f'p:{p_pv},q:{p_qv},verdict:"{p_v}"}}'
            )
        m = s["metrics"]
        s_id = s["id"]
        s_ts = s["t_start"]
        s_te = s["t_end"]
        s_dur = s["duration_seconds"]
        pairs_joined = ",\n    ".join(pr_rows)
        m_p = m["precision"]
        m_r = m["recall"]
        m_f = m["f1"]
        m_n = m["n_significant"]
        snap_blocks.append(
            f'  {{id:{s_id},t_start:{s_ts},t_end:{s_te},'
            f'duration_seconds:{s_dur},pairs:[\n    {pairs_joined}\n  ],'
            f'metrics:{{precision:{m_p},recall:{m_r},f1:{m_f},'
            f'n_significant:{m_n}}}}}'
        )
    lines.append(",\n".join(snap_blocks))
    lines.append("];")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating long series: {T_TOTAL} x {N_DETECTORS}, "
          f"coupling={COUPLING}, hidden={HIDDEN}, B={B}...")
    X, names = _generate_long_series()

    detectors = [
        {"id": mid, "type": mtype, "lat": lat, "lon": lon}
        for (mid, mtype, lat, lon) in DETECTOR_META
    ]
    hidden_pairs = [
        {"detector_a": names[i], "detector_b": names[j], "true_lag": tau}
        for (i, j, tau) in HIDDEN
    ]

    snapshots = []
    for i in range(N_SNAPSHOTS):
        start = i * STEP
        end = start + WINDOW_SIZE
        if end > T_TOTAL:
            start = T_TOTAL - WINDOW_SIZE
            end = T_TOTAL
        window = X[start:end]
        seed_i = BASE_SEED + i

        analysis = _analyze_window(window, names, B, seed_i)
        snap = {
            "id": i,
            "t_start": int(start),
            "t_end": int(end),
            "duration_seconds": float(SECONDS_PER_SNAPSHOT),
            "pairs": analysis["pairs"],
            "metrics": analysis["metrics"],
        }
        with open(OUT_DIR / f"snapshot_{i:02d}.json", "w",
                  encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, ensure_ascii=False)

        # Console progress bar
        print(f"[{i+1:2d}/{N_SNAPSHOTS}] snapshot_{i:02d}.json ... "
              f"{len(snap['pairs'])} pairs, "
              f"{snap['metrics']['n_significant']} significant")

        snapshots.append(snap)

    _write_snapshots_js(OUT_DIR / "snapshots.js", snapshots,
                        detectors, hidden_pairs)

    elapsed = time.time() - t0
    manifest = {
        "config": {
            "n_snapshots": N_SNAPSHOTS,
            "duration_seconds": N_SNAPSHOTS * SECONDS_PER_SNAPSHOT,
            "seconds_per_snapshot": SECONDS_PER_SNAPSHOT,
            "n_detectors": N_DETECTORS,
            "n_pairs": N_DETECTORS * (N_DETECTORS - 1) // 2,
            "window_size": WINDOW_SIZE,
            "step": STEP,
            "B": B,
            "seed": BASE_SEED,
            "coupling": COUPLING,
        },
        "detectors": detectors,
        "hidden_pairs": hidden_pairs,
        "snapshots": [
            {
                "id": s["id"],
                "t_start": s["t_start"],
                "t_end": s["t_end"],
                "n_significant": s["metrics"]["n_significant"],
                "f1": s["metrics"]["f1"],
            }
            for s in snapshots
        ],
    }
    with open(OUT_DIR / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    print()
    print(f"Wrote {N_SNAPSHOTS} snapshots + manifest.json + snapshots.js "
          f"to {OUT_DIR}")
    print(f"Total runtime: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
