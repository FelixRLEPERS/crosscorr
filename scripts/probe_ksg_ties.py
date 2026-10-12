"""Probe the KSG-ties failure mode of crosscorr_lib.analysis.mutual_info.

Standalone diagnostic for Finding 2 (audit/BACKLOG_2026-10-12.md).
No pytest, no file writes: prints one table to stdout.
Deterministic (seed=42). Exit 0 = probe ran; nonzero = probe crashed.

Quantization: each series is scaled to [min, max] and rounded onto
N_q equally spaced levels (1000 ~ near-continuous, 3 ~ heavily discrete).
Reference: analytic MI of the pre-quantization bivariate Gaussian,
I = -0.5 * ln(1 - rho^2).
"""

from __future__ import annotations

import sys
import warnings

import numpy as np

from crosscorr_lib.analysis.mutual_info import mutual_information

LEVELS = [1000, 100, 30, 20, 15, 10, 5, 3]
N = 1000
RHO = 0.5
SEED = 42
K = 5


def quantize(series: np.ndarray, n_q: int) -> np.ndarray:
    """Round a series onto n_q equally spaced levels over [min, max]."""
    lo = float(series.min())
    hi = float(series.max())
    return np.round((series - lo) / (hi - lo) * (n_q - 1))


def _warn_text(caught: list[warnings.WarningMessage]) -> str:
    """Unique warning category names from a catch_warnings block."""
    if not caught:
        return "-"
    names = sorted({w.category.__name__ for w in caught})
    return f"{','.join(names)}(x{len(caught)})"


def probe_level(x: np.ndarray, y: np.ndarray, mi_true: float) -> tuple[str, str, str, str]:
    """Run mutual_information on one quantization level.

    Returns (mi_text, ratio_text, status, warnings_text).
    status: ok | bad-ratio | nan | inf | EXC:<name>
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            mi = mutual_information(x, y, k=K)
        except Exception as exc:
            return "n/a", "n/a", f"EXC:{type(exc).__name__}", _warn_text(caught)

    mi_text = f"{mi:.6f}"
    if not np.isfinite(mi):
        status = "nan" if np.isnan(mi) else "inf"
        return mi_text, "n/a", status, _warn_text(caught)

    ratio = mi / mi_true
    status = "bad-ratio" if abs(ratio) < 0.5 else "ok"
    return mi_text, f"{ratio:.3f}", status, _warn_text(caught)


def main() -> int:
    rng = np.random.default_rng(SEED)
    z1 = rng.normal(size=N)
    z2 = RHO * z1 + np.sqrt(1.0 - RHO**2) * rng.normal(size=N)
    mi_true = -0.5 * np.log(1.0 - RHO**2)

    print(f"# KSG-ties probe  n={N}  rho={RHO}  k={K}  seed={SEED}")
    print(f"# MI_true (analytic bivariate Gaussian) = {mi_true:.6f} nats")
    print(f"{'levels':>6} | {'MI_value':>14} | {'ratio':>7} | {'status':<14} | warnings")
    print("-" * 76)

    flagged: list[int] = []
    for n_q in LEVELS:
        x = quantize(z1, n_q)
        y = quantize(z2, n_q)
        mi_t, ratio_t, status, warn_t = probe_level(x, y, mi_true)
        print(f"{n_q:>6} | {mi_t:>14} | {ratio_t:>7} | {status:<14} | {warn_t}")
        if status != "ok":
            flagged.append(n_q)

    print("-" * 76)
    print(f"levels with failure or bad-ratio (<0.5): {flagged or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())