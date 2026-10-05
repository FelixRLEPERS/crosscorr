"""Cross-correlation pair analysis with parallel surrogate generation via shared memory.

This module provides `cross_correlation_pairs_with_max_stat`, which computes
max-statistic cross-correlations between all detector pairs using phase-randomization
surrogate tests, with FDR correction via Benjamini–Hochberg.

Surrogates and the data matrix X are pre-generated once in the main process and
shared across worker processes via `multiprocessing.shared_memory`. This avoids
pickling large arrays into each loky worker.

Architecture:
    - shm_surr : (N, B, T) float32 — ALL surrogates for ALL detectors in ONE block.
    - shm_X    : (T, N)   float64  — the full data matrix.

Worker receives TWO shared memory names and slices views into them.

Methods:
    - "shuffle": random permutation of time axis per surrogate.
    - "phase":   phase-randomization in Fourier domain (preserves spectrum).
    - "ar":      AR(1) surrogate via IIR filter (scipy.signal.lfilter).

Output verdicts:
    - "INVARIANT" if q_value < 0.01
    - "CANDIDATE" if 0.01 <= q_value < 0.05
    - "NOISE" otherwise
"""

import multiprocessing.shared_memory as shm_module
from collections.abc import Callable

import numpy as np
import pandas as pd

try:
    from joblib import Parallel, delayed
    _HAS_JOBLIB = True
except ImportError:
    _HAS_JOBLIB = False
    Parallel = None
    delayed = None

from scipy.signal import lfilter


def _make_surrogates(x: np.ndarray, method: str, B: int, seed: int) -> np.ndarray:
    """Generate B surrogates for a single detector.

    Args:
        x: 1D array of length T.
        method: "shuffle" | "phase" | "ar".
        B: number of surrogates.
        seed: RNG sub-seed.

    Returns:
        (B, T) float64 array of surrogate samples.
    """
    rng = np.random.default_rng(seed)

    # NaN-safe: интерполировать пропуски (аналог surrogate.py)
    x = np.asarray(x, dtype=float)
    if np.isnan(x).any():
        idx = np.arange(len(x))
        good = np.isfinite(x)
        if good.sum() < 2:
            raise ValueError("too few finite samples in surrogate input")
        x = np.interp(idx, idx[good], x[good])

    T = len(x)

    if method == "shuffle":
        out = np.empty((B, T), dtype=np.float64)
        for b in range(B):
            perm = rng.permutation(T)
            out[b] = x[perm]
        return out

    if method == "phase":
        F = np.fft.rfft(x)
        mag = np.abs(F)
        K = len(F)
        out = np.empty((B, T), dtype=np.float64)
        for b in range(B):
            ph = rng.uniform(-np.pi, np.pi, size=K)
            ph[0] = 0.0
            if T % 2 == 0:
                ph[-1] = 0.0
            out[b] = np.fft.irfft(mag * np.exp(1j * ph), n=T)
        return out

    if method == "ar":
        if x.std() > 0:
            phi = float(np.corrcoef(x[:-1], x[1:])[0, 1])
        else:
            phi = 0.0
        sigma = float(x.std() * np.sqrt(max(1e-12, 1 - phi**2)))

        eps = rng.normal(0, sigma, size=(B, T))
        out = lfilter([1.0], [1.0, -phi], eps, axis=1)

        return out

    raise ValueError(f"Unknown method: {method!r}")


def _batch_max_stat_corr(si: np.ndarray, sj: np.ndarray) -> np.ndarray:
    """Compute max-statistic correlation for B surrogates of two detectors.

    Uses FFT-based convolution (no loop over B). Both inputs are z-scored.

    Args:
        si: (B, T) surrogate samples for detector i.
        sj: (B, T) surrogate samples for detector j.

    Returns:
        (B,) array of max(|corr|) values over all lags.
    """
    B, T = si.shape
    EPS = 1e-12

    std_i = si.std(axis=1, keepdims=True)
    std_j = sj.std(axis=1, keepdims=True)
    degenerate = (std_i <= EPS) | (std_j <= EPS)

    si_z = (si - si.mean(axis=1, keepdims=True)) / (std_i + EPS)
    sj_z = (sj - sj.mean(axis=1, keepdims=True)) / (std_j + EPS)

    n_fft = 2 * T
    Fsi = np.fft.rfft(si_z, n=n_fft, axis=1)
    Fsj = np.fft.rfft(sj_z, n=n_fft, axis=1)
    cc = np.fft.irfft(Fsi * np.conj(Fsj), n=n_fft, axis=1)

    # Circular shift to linear correlation: [(T-1) tail, T head] / T
    cc = np.concatenate([cc[:, -(T - 1):], cc[:, :T]], axis=1) / T

    out = np.max(np.abs(cc), axis=1)
    out[degenerate[:, 0]] = 0.0
    return out


def _max_stat_corr(x: np.ndarray, y: np.ndarray) -> float:
    """Compute max absolute correlation over all lags for two scalar signals.

    Uses FFT-based convolution (O(T log T)) to match the batch version's scale.

    Args:
        x: 1D array (T,).
        y: 1D array (T,).

    Returns:
        float: max(|corr|) over lag ∈ [-(T-1), T-1].
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        return float("nan")

    x_std = x.std()
    y_std = y.std()
    if x_std <= 1e-12 or y_std <= 1e-12:
        return 0.0

    x = (x - x.mean()) / (x_std + 1e-12)
    y = (y - y.mean()) / (y_std + 1e-12)

    n_fft = 2 * len(x)
    Fx = np.fft.rfft(x, n=n_fft)
    Fy = np.fft.rfft(y, n=n_fft)
    cc = np.fft.irfft(Fx * np.conj(Fy), n=n_fft)

    # Circular shift to linear correlation: [(T-1) tail, T head] / T
    cc = np.concatenate([cc[-(len(x)-1):], cc[: len(x)]]) / len(x)

    return float(np.max(np.abs(cc)))


def cross_correlation_pairs_with_max_stat(
    wide: pd.DataFrame,
    *,
    seed: int = 42,
    method: str = "phase",
    B: int = 200,
    n_jobs: int = -1,
    pair_filter: Callable[[str, str], bool] | None = None,
    dtype: np.dtype = np.float32,
) -> pd.DataFrame:
    """Compute max-statistic cross-correlations between all detector pairs.

    Surrogates and the data matrix X are pre-generated once in the main process
    and shared across worker processes via `multiprocessing.shared_memory`. This
    avoids pickling large arrays into each loky worker.

    Args:
        wide: DataFrame with shape (T, N), where columns are detectors.
        seed: global RNG seed for reproducibility.
        method: surrogate generation method ("shuffle" | "phase" | "ar").
        B: number of surrogate replicates per detector.
        n_jobs: number of parallel workers (-1 = all CPUs).
        pair_filter: optional callable(name_a, name_b) → bool to filter pairs.
        dtype: storage dtype for surrogates (float32 recommended).

    Returns:
        DataFrame with columns:
            - detector_a, detector_b: column names from `wide`.
            - C_obs: observed max-statistic correlation.
            - p_value: empirical p-value via Davison–Hinkley rule (+1 in num/denom).
            - q_value: FDR-corrected q-value (Benjamini–Hochberg with monotonicity).
            - verdict: "INVARIANT" if q < 0.01, "CANDIDATE" if q < 0.05, else "NOISE".

    Notes:
        - The observed statistic C_obs is computed from the original data (not a surrogate).
        - p_value = (sum(C_null >= C_obs) + 1) / (B + 1), following Davison & Hinkley (1997).
        - FDR uses Benjamini–Hochberg with monotonicity enforcement via np.minimum.accumulate[::-1].
    """

    X = wide.values.astype(np.float64)
    if np.isnan(X).any():
        raise ValueError(
            "wide contains NaN; interpolate or drop missing rows "
            "before calling cross_correlation_pairs_with_max_stat"
        )
    T, N = X.shape
    detectors = list(wide.columns)

    # --- Step 0: Build pair list ---
    pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
    if pair_filter is not None:
        pairs = [pair for pair in pairs
                 if pair_filter(detectors[pair[0]], detectors[pair[1]])]

    if len(pairs) == 0:
        return pd.DataFrame(columns=["detector_a", "detector_b", "C_obs", "p_value", "q_value", "verdict"])

    # --- Step 1: Pre-generate surrogates and data in shared memory ---
    out = np.empty((N, B, T), dtype=dtype)
    rng = np.random.default_rng(seed)
    sub_seeds = rng.integers(0, 2**31 - 1, size=N)

    for i in range(N):
        out[i] = _make_surrogates(X[:, i], method, B, int(sub_seeds[i]))

    shm_surr = shm_module.SharedMemory(create=True, size=out.nbytes)
    view_surr = np.ndarray(out.shape, dtype=dtype, buffer=shm_surr.buf)
    view_surr[:] = out[:]

    # Wrap X in shared memory.
    shm_X = shm_module.SharedMemory(create=True, size=X.nbytes)
    view_X = np.ndarray(X.shape, dtype=np.float64, buffer=shm_X.buf)
    view_X[:] = X

    try:
        # --- Step 2 & 3: Parallel computation over pairs using shared memory ---
        if _HAS_JOBLIB and n_jobs != 1:
            results = Parallel(n_jobs=n_jobs, prefer="processes")(
                delayed(_worker)(
                    shm_surr.name,
                    shm_X.name,
                    out.shape,
                    X.shape,
                    i,
                    j,
                    detectors[i],
                    detectors[j],
                    B,
                    dtype,
                )
                for (i, j) in pairs
            )
        else:
            results = [
                _worker(
                    shm_surr.name,
                    shm_X.name,
                    out.shape,
                    X.shape,
                    i,
                    j,
                    detectors[i],
                    detectors[j],
                    B,
                    dtype,
                )
                for (i, j) in pairs
            ]

    finally:
        # Patch #1: close AND unlink BOTH shared memory blocks.
        shm_surr.close()
        shm_surr.unlink()
        shm_X.close()
        shm_X.unlink()

    # --- Step 4: Assemble results and compute FDR ---
    df = pd.DataFrame(results, columns=["detector_a", "detector_b", "C_obs", "p_value"])

    if len(df) == 0:
        return pd.DataFrame(columns=["detector_a", "detector_b", "C_obs", "p_value", "q_value", "verdict"])

    # FDR via Benjamini–Hochberg with monotonicity enforcement.
    p = df["p_value"].to_numpy()
    n = len(p)
    order = np.argsort(p)  # <-- preserve original order!
    p_sorted = p[order]
    q_sorted = p_sorted * n / np.arange(1, n + 1)
    q_sorted = np.minimum.accumulate(q_sorted[::-1])[::-1]
    q_sorted = np.clip(q_sorted, 0.0, 1.0)
    q = np.empty_like(q_sorted)
    q[order] = q_sorted  # <-- restore original order

    df["q_value"] = q

    def _verdict(q_val: float) -> str:
        if q_val < 0.01:
            return "INVARIANT"
        elif q_val < 0.05:
            return "CANDIDATE"
        else:
            return "NOISE"

    df["verdict"] = df["q_value"].apply(_verdict)

    return df


def _worker(
    shm_surr_name: str,
    shm_X_name: str,
    surr_shape: tuple[int, int, int],
    X_shape: tuple[int, int],
    i: int,
    j: int,
    name_a: str,
    name_b: str,
    B: int,
    dtype: np.dtype,
) -> dict:
    """Worker function for a single pair (i, j).

    Connects to two shared memory blocks and slices views into them.
    Computes C_obs from original data and p_value from surrogates.

    Args:
        shm_surr_name:   name of the surrogate shared memory block.
        shm_X_name:      name of the data shared memory block.
        surr_shape:      shape (N, B, T) of the surrogate block.
        X_shape:         shape (T, N) of the data block.
        i:               index of first detector in X.
        j:               index of second detector in X.
        name_a:          column name for detector i.
        name_b:          column name for detector j.
        B:               number of surrogates per detector.
        dtype:           storage dtype (float32 or float64) to use when reading from shm.

    Returns:
        dict with keys "detector_a", "detector_b", "C_obs", "p_value".
    """
    shm_s = shm_module.SharedMemory(name=shm_surr_name, create=False)
    shm_x = shm_module.SharedMemory(name=shm_X_name, create=False)

    try:
        surr = np.ndarray(surr_shape, dtype=dtype, buffer=shm_s.buf)
        X = np.ndarray(X_shape, dtype=np.float64, buffer=shm_x.buf)

        si = surr[i]  # (B, T) — view, no copy
        sj = surr[j]

        C_obs = _max_stat_corr(X[:, i], X[:, j])
        if not np.isfinite(C_obs):
            return {
                "detector_a": name_a,
                "detector_b": name_b,
                "C_obs": float("nan"),
                "p_value": 1.0,
            }
        C_null = _batch_max_stat_corr(si, sj)

        count_ge = np.sum(C_null >= C_obs)
        p_value = (float(count_ge) + 1.0) / (B + 1.0)

        return {
            "detector_a": name_a,
            "detector_b": name_b,
            "C_obs": float(C_obs),
            "p_value": float(p_value),
        }

    finally:
        shm_s.close()
        shm_x.close()


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    T, N = 5000, 5
    wide = pd.DataFrame(rng.standard_normal((T, N)), columns=[f"det_{i:02d}" for i in range(N)])

    s1 = rng.standard_normal(T) * 0.5
    wide["det_00"] += s1
    wide["det_04"] += s1

    s2 = rng.standard_normal(T) * 0.5
    wide["det_01"] += s2
    wide["det_03"] += s2

    df = cross_correlation_pairs_with_max_stat(wide, B=2000, seed=42)
    top = df.sort_values("q_value").head(5)
    print(top)
    # Ожидание: det_00/det_04 и det_01/det_03 — топ-2, verdict=INVARIANT (B=2000, пар=10, q_min ≈ 0.005 < 0.01).
