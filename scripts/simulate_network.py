"""Simulate a heterogeneous sensor network with hidden correlations.

Generates N detectors with random lat/lon, AR(1) noise, and n_hidden
injected correlations with known lags. Runs cross-correlation analysis
via crosscorr_lib.pairs and reports detection metrics.

Saves to results/network_simulation/:
    detectors.csv       -- id, type, lat, lon
    pairs.csv           -- all pairs with C_obs, p_value, q_value, verdict
    hidden_pairs.csv    -- ground-truth hidden pairs
    metrics.csv         -- TP, FP, FN, precision, recall, f1
    summary.txt         -- human-readable report
    network_map.png     -- world map with detections
    pvalue_hist.png     -- p-value distribution
    corr_matrix.png     -- correlation heatmap (first 20 detectors)

Example:
    python scripts/simulate_network.py
    python scripts/simulate_network.py --n-detectors 100 --B 500
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat


DETECTOR_TYPES = ["wspr", "magnetometer", "gnss", "ionosonde", "ephemeris"]
TRUE_LAGS = [3, 6, 12, 18, 24]


# --------------------------------------------------------------------------- #
# Data generation
# --------------------------------------------------------------------------- #

def _generate_ar1(rng: np.random.Generator, n: int,
                  phi: float = 0.85, sigma: float = 1.0) -> np.ndarray:
    """Generate AR(1) noise with given phi."""
    eps = rng.normal(0, sigma, size=n)
    out = np.zeros(n)
    for t in range(1, n):
        out[t] = phi * out[t - 1] + eps[t]
    return out


def _generate_detectors(rng, n, T):
    """Generate n detectors with lat/lon, type, AR(1) noise."""
    lats = rng.uniform(-70, 70, size=n)
    lons = rng.uniform(-180, 180, size=n)
    types = rng.choice(DETECTOR_TYPES, size=n)

    X = np.zeros((T, n))
    for i in range(n):
        X[:, i] = _generate_ar1(rng, T)

    names = [f"det_{i:03d}" for i in range(n)]
    return X, names, lats, lons, types


def _inject_hidden_pairs(rng, X, n_hidden, coupling):
    """Inject n_hidden correlations into X. Returns list of (i, j, tau)."""
    N = X.shape[1]
    T = X.shape[0]

    all_pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
    chosen = rng.choice(len(all_pairs), size=n_hidden, replace=False)

    hidden = []
    for idx in chosen:
        i, j = all_pairs[idx]
        tau = int(rng.choice(TRUE_LAGS))
        X[tau:, j] += coupling * X[:-tau, i]
        hidden.append((i, j, tau))
    return hidden


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #

def _run_analysis(X, names, B, seed, n_jobs):
    wide = pd.DataFrame(X, columns=names)
    return cross_correlation_pairs_with_max_stat(
        wide, B=B, seed=seed, method="phase", n_jobs=n_jobs,
    )


def _compute_metrics(result, hidden, names):
    sig = result[result["q_value"] < 0.05].copy()
    sig_pairs = set()
    for _, row in sig.iterrows():
        a, b = row["detector_a"], row["detector_b"]
        sig_pairs.add(tuple(sorted([a, b])))

    hidden_pairs = set()
    hidden_info = {}
    for i, j, tau in hidden:
        a, b = names[i], names[j]
        key = tuple(sorted([a, b]))
        hidden_pairs.add(key)
        hidden_info[key] = tau

    TP = len(sig_pairs & hidden_pairs)
    FP = len(sig_pairs - hidden_pairs)
    FN = len(hidden_pairs - sig_pairs)

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    return {
        "TP": TP, "FP": FP, "FN": FN,
        "precision": precision, "recall": recall, "f1": f1,
        "n_significant": len(sig_pairs),
        "n_hidden": len(hidden_pairs),
        "hidden_info": hidden_info,
        "sig_pairs": sig_pairs,
    }


# --------------------------------------------------------------------------- #
# Saving
# --------------------------------------------------------------------------- #

def _save_results(out_dir, names, lats, lons, types,
                  result, hidden, metrics, params, elapsed):
    out_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame({
        "id": names, "type": types, "lat": lats, "lon": lons,
    }).to_csv(out_dir / "detectors.csv", index=False)

    result.to_csv(out_dir / "pairs.csv", index=False)

    hidden_rows = [
        {"detector_a": names[i], "detector_b": names[j], "true_lag": tau}
        for i, j, tau in hidden
    ]
    pd.DataFrame(hidden_rows).to_csv(out_dir / "hidden_pairs.csv", index=False)

    pd.DataFrame([{
        "TP": metrics["TP"], "FP": metrics["FP"], "FN": metrics["FN"],
        "precision": round(metrics["precision"], 4),
        "recall": round(metrics["recall"], 4),
        "f1": round(metrics["f1"], 4),
    }]).to_csv(out_dir / "metrics.csv", index=False)

    lines = [
        "CrossCorr — Network Simulation Summary",
        "=" * 45,
        "",
        "Parameters:",
    ]
    for k, v in params.items():
        lines.append(f"  {k:20s} = {v}")
    lines += [
        "",
        "Results:",
        f"  Pairs tested        = {len(result)}",
        f"  Significant (q<0.05) = {metrics['n_significant']}",
        f"  Hidden pairs        = {metrics['n_hidden']}",
        f"  True positives      = {metrics['TP']}",
        f"  False positives     = {metrics['FP']}",
        f"  False negatives     = {metrics['FN']}",
        f"  Precision           = {metrics['precision']:.4f}",
        f"  Recall              = {metrics['recall']:.4f}",
        f"  F1                  = {metrics['f1']:.4f}",
        "",
        "Detected hidden pairs:",
    ]
    for key, tau in metrics["hidden_info"].items():
        found = "YES" if key in metrics["sig_pairs"] else "no"
        lines.append(f"  {key[0]} <-> {key[1]}  (true lag={tau})  found={found}")
    lines += ["", f"Time = {elapsed:.2f}s"]
    (out_dir / "summary.txt").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Plots
# --------------------------------------------------------------------------- #

def _plot_network_map(out_dir, names, lats, lons, types, metrics):
    fig, ax = plt.subplots(figsize=(12, 6))
    for t in set(types):
        mask = types == t
        ax.scatter(lons[mask], lats[mask], s=40, label=t, alpha=0.7)

    name_to_idx = {n: i for i, n in enumerate(names)}
    for key, tau in metrics["hidden_info"].items():
        ia, ib = name_to_idx[key[0]], name_to_idx[key[1]]
        found = key in metrics["sig_pairs"]
        color = "red" if found else "orange"
        lw = 2.0 if found else 1.0
        ax.plot([lons[ia], lons[ib]], [lats[ia], lats[ib]],
                color=color, lw=lw, alpha=0.6)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("CrossCorr — hidden pair detection (red=found, orange=missed)")
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "network_map.png", dpi=120)
    plt.close(fig)


def _plot_pvalue_hist(out_dir, result):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(result["p_value"], bins=50, color="steelblue", edgecolor="white")
    ax.axvline(0.05, color="red", linestyle="--", label="alpha=0.05")
    ax.set_xlabel("p-value")
    ax.set_ylabel("Count")
    ax.set_title("Distribution of p-values across all pairs")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "pvalue_hist.png", dpi=120)
    plt.close(fig)


def _plot_corr_matrix(out_dir, X, names):
    k = min(20, X.shape[1])
    sub = X[:, :k]
    sub_z = (sub - sub.mean(axis=0)) / (sub.std(axis=0) + 1e-12)
    corr = np.corrcoef(sub_z, rowvar=False)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_title(f"Cross-correlation matrix (first {k} detectors)")
    ax.set_xticks(range(k))
    ax.set_yticks(range(k))
    ax.set_xticklabels(names[:k], rotation=90, fontsize=6)
    ax.set_yticklabels(names[:k], fontsize=6)
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(out_dir / "corr_matrix.png", dpi=120)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Simulate sensor network for CrossCorr",
    )
    p.add_argument("--n-detectors", type=int, default=50)
    p.add_argument("--n-samples", type=int, default=2000)
    p.add_argument("--n-hidden", type=int, default=5)
    p.add_argument("--coupling", type=float, default=0.15)
    p.add_argument("--B", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-jobs", type=int, default=-1)
    p.add_argument("--out-dir", type=str, default="results/network_simulation")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rng = np.random.default_rng(args.seed)

    print(f"Generating {args.n_detectors} detectors, "
          f"{args.n_samples} samples, {args.n_hidden} hidden pairs...")

    X, names, lats, lons, types = _generate_detectors(
        rng, args.n_detectors, args.n_samples,
    )
    hidden = _inject_hidden_pairs(rng, X, args.n_hidden, args.coupling)

    print("Running cross-correlation analysis...")
    t0 = time.time()
    result = _run_analysis(X, names, args.B, args.seed, args.n_jobs)
    elapsed = time.time() - t0

    metrics = _compute_metrics(result, hidden, names)

    out_dir = Path(args.out_dir)
    params = {
        "n_detectors": args.n_detectors,
        "n_samples": args.n_samples,
        "n_hidden": args.n_hidden,
        "coupling": args.coupling,
        "B": args.B,
        "seed": args.seed,
    }
    _save_results(out_dir, names, lats, lons, types,
                  result, hidden, metrics, params, elapsed)

    _plot_network_map(out_dir, names, lats, lons, types, metrics)
    _plot_pvalue_hist(out_dir, result)
    _plot_corr_matrix(out_dir, X, names)

    print()
    print(f"Detectors:     {args.n_detectors}")
    print(f"Pairs tested:  {len(result)}")
    print(f"Significant:   {metrics['n_significant']}")
    print(f"Hidden pairs:  {metrics['n_hidden']}")
    print(f"Found:         {metrics['TP']} / {metrics['n_hidden']}")
    print(f"Precision:     {metrics['precision']:.2f}")
    print(f"Recall:        {metrics['recall']:.2f}")
    print(f"F1:            {metrics['f1']:.2f}")
    print(f"Time:          {elapsed:.1f}s")
    print()
    print(f"Saved results to {out_dir}")


if __name__ == "__main__":
    main()