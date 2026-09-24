"""
Mathematical core of CrossCorr 2.0.

    C_ij(tau, d, f) -> Null Model -> p -> FDR -> robustness

Pipeline
--------
1. preprocess       : detrend + z-score
2. lagged_cc        : full lag curve + Fisher-weighted max-statistic
3. null model       : phase / IAAFT / block bootstrap / time shift
4. empirical p-value: from null distribution of the max-statistic
5. BH-FDR           : across pairs, NaN-safe
6. robustness       : windowed stability, distance dependence
7. synthetic        : AR(1) benchmark and power curve

Design decisions (v2.1)
-----------------------
- Lagged cross-correlation is the primary statistic.
- Max-statistic over lags gives correct p-values despite searching.
- Fisher weighting handles variable overlap across lags.
- Four null models; ``randomize_both=True`` by default for conservative
  tests (P0-2 fix).
- Block bootstrap guards against degeneracy with ``block_size <= n/4``
  (P0-1 fix), and provides a sane default ``n**(1/3)`` (P1-1).
- NaN in p-values propagate as NaN q-values (P1-2 fix).
- Each pair in ``analyze_all_pairs`` gets its own child RNG (P1-3).
- ``apply_preprocessing=False`` skips preprocess (P1-4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

import numpy as np
from scipy import stats


__all__ = [
    # data containers
    "Detector", "LagCurve", "PairResult",
    # preprocessing
    "preprocess",
    # correlation
    "lagged_cc",
    # null models
    "NULL_MODELS", "make_null", "null_max_distribution",
    # significance
    "empirical_pvalue", "fdr_bh",
    # pair-level
    "analyze_pair", "analyze_all_pairs",
    # robustness
    "windowed_stability", "distance_dependence",
    # synthetic
    "synthetic_ar1_pair", "benchmark",
    # exceptions
    "CrossCorrError", "PreprocessingError",
    "NullModelError", "InsufficientDataError",
]


# ------------------------------------------------------------------ #
#                          exceptions                                #
# ------------------------------------------------------------------ #

class CrossCorrError(Exception):
    """Base class for all CrossCorr errors."""


class PreprocessingError(CrossCorrError):
    """Input cannot be preprocessed."""


class NullModelError(CrossCorrError):
    """Null model misconfigured or unknown."""


class InsufficientDataError(CrossCorrError):
    """Not enough data for the requested analysis."""


# ------------------------------------------------------------------ #
#                          constants                                 #
# ------------------------------------------------------------------ #

DEFAULT_MIN_OVERLAP = 20
"""Minimum number of finite overlapping samples required to compute
a correlation at a given lag. Below this threshold the estimate is
too noisy to be useful."""


# ------------------------------------------------------------------ #
#                        preprocessing                               #
# ------------------------------------------------------------------ #

def preprocess(x: np.ndarray,
               detrend: bool = True,
               standardize: bool = True,
               robust: bool = False) -> np.ndarray:
    """
    Detrend and standardize a 1-D series.

    NaN/inf are ignored in the trend fit and standardization, but kept
    in place in the output (so downstream code can handle them).

    Parameters
    ----------
    x : array-like
        1-D series.
    detrend : bool
        Remove a linear trend (via OLS or Theil-Sen).
    standardize : bool
        Subtract mean and divide by std (ddof=1).
    robust : bool
        If True, use Theil-Sen for the trend fit. Slower but
        insensitive to outliers.
    """
    x = np.asarray(x, dtype=float).copy()
    n = len(x)
    if n == 0:
        raise PreprocessingError("empty input")

    if detrend:
        t = np.arange(n)
        good = np.isfinite(x)
        if good.sum() >= 2:
            if robust:
                slope, intercept, _, _ = stats.theilslopes(x[good], t[good])
            else:
                slope, intercept = np.polyfit(t[good], x[good], 1)
            x = x - (slope * t + intercept)

    if standardize:
        finite = np.isfinite(x)
        mu = float(np.mean(x[finite])) if finite.any() else 0.0
        sd = float(np.std(x[finite], ddof=1)) if finite.sum() > 1 else 0.0
        if sd > 0:
            x = (x - mu) / sd

    return x


# ------------------------------------------------------------------ #
#                       lagged cross-correlation                     #
# ------------------------------------------------------------------ #

@dataclass
class LagCurve:
    lags: np.ndarray
    rho: np.ndarray
    n: np.ndarray
    method: str
    lag_max: int
    rho_max: float
    n_at_max: int
    max_stat: float


def _cc_at_lag(x: np.ndarray, y: np.ndarray, tau: int,
               method: str, min_overlap: int):
    n = len(x)
    if tau >= 0:
        a = x[: n - tau] if tau > 0 else x
        b = y[tau:]
    else:
        a = x[-tau:]
        b = y[: n + tau]
    mask = np.isfinite(a) & np.isfinite(b)
    m = int(mask.sum())
    if m < min_overlap:
        return np.nan, m
    av, bv = a[mask], b[mask]
    if av.std() == 0 or bv.std() == 0:
        return np.nan, m
    if method == "spearman":
        r, _ = stats.spearmanr(av, bv)
    elif method == "pearson":
        r, _ = stats.pearsonr(av, bv)
    else:
        raise ValueError(f"unknown method: {method}")
    return float(r), m


def lagged_cc(x: np.ndarray, y: np.ndarray, max_lag: int,
              method: str = "spearman",
              fisher: bool = True,
              min_overlap: int = DEFAULT_MIN_OVERLAP) -> LagCurve:
    """
    Full lagged cross-correlation curve with a max-statistic.

    For each tau in [-max_lag, +max_lag], compute the correlation
    between x(t) and y(t + tau). The reported ``max_stat`` is the
    Fisher-weighted maximum of |rho| over lags; ``lag_max`` and
    ``rho_max`` correspond to the argmax.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) != len(y):
        raise ValueError("x and y must share the same time grid")
    if max_lag < 0:
        raise ValueError("max_lag must be >= 0")
    if max_lag >= len(x) // 2:
        raise InsufficientDataError(
            f"max_lag={max_lag} too large for n={len(x)}; "
            f"require max_lag < n/2"
        )

    lags = np.arange(-max_lag, max_lag + 1, dtype=int)
    rho = np.empty(len(lags))
    nn = np.empty(len(lags), dtype=int)
    for i, tau in enumerate(lags):
        r, m = _cc_at_lag(x, y, int(tau), method, min_overlap)
        rho[i] = r
        nn[i] = m

    finite = np.isfinite(rho)
    if not finite.any():
        return LagCurve(lags, rho, nn, method, 0, 0.0, 0, 0.0)

    if fisher:
        w = np.sqrt(np.maximum(nn - 3, 1.0))
        z = np.arctanh(np.clip(rho, -0.999999, 0.999999))
        score = np.where(finite, np.abs(z) * w, -np.inf)
    else:
        score = np.where(finite, np.abs(rho), -np.inf)

    idx = int(np.argmax(score))
    return LagCurve(
        lags=lags, rho=rho, n=nn, method=method,
        lag_max=int(lags[idx]), rho_max=float(rho[idx]),
        n_at_max=int(nn[idx]), max_stat=float(score[idx]),
    )


# ------------------------------------------------------------------ #
#                          null models                               #
# ------------------------------------------------------------------ #

def _phase_randomize(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    n = len(y)
    if not np.isfinite(y).all():
        idx = np.arange(n)
        good = np.isfinite(y)
        y = np.interp(idx, idx[good], y[good])
    mu = y.mean()
    Y = np.fft.rfft(y - mu)
    mags = np.abs(Y)
    phases = rng.uniform(0, 2 * np.pi, size=len(Y))
    phases[0] = 0.0
    if n % 2 == 0:
        phases[-1] = 0.0
    return np.fft.irfft(mags * np.exp(1j * phases), n=n) + mu


def _iaaft(y: np.ndarray, rng: np.random.Generator,
           n_iter: int = 50) -> np.ndarray:
    """IAAFT: preserves amplitude distribution and approx. spectrum."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    sorted_y = np.sort(y)
    x = _phase_randomize(y, rng)
    Y_mag = np.abs(np.fft.rfft(y - y.mean()))
    for _ in range(n_iter):
        X = np.fft.rfft(x - x.mean())
        X_new = Y_mag * np.exp(1j * np.angle(X))
        x_new = np.fft.irfft(X_new, n=n) + y.mean()
        ranks = np.argsort(np.argsort(x_new))
        x = sorted_y[ranks]
    return x


def _block_bootstrap(y: np.ndarray, rng: np.random.Generator,
                     block_size: Optional[int] = None) -> np.ndarray:
    """
    Non-overlapping block bootstrap that preserves local autocorrelation.

    Guards against degeneracy: the effective block size is capped at
    ``n // 4`` so at least 4 blocks are drawn. This prevents the
    silent "surrogate == original" bug when ``block_size >= n``.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 4:
        return y.copy()

    if block_size is None:
        block_size = max(2, int(round(n ** (1 / 3))))
    if n >= 8:
        block_size = int(max(2, min(block_size, n // 4)))
    else:
        block_size = 2

    n_blocks = int(np.ceil(n / block_size))
    max_start = n - block_size
    if max_start <= 0:
        return y.copy()
    starts = rng.integers(0, max_start + 1, size=n_blocks)
    out = np.concatenate([y[s: s + block_size] for s in starts])
    return out[:n]


def _time_shift(y: np.ndarray, rng: np.random.Generator,
                min_shift: int = 1) -> np.ndarray:
    """
    Cyclic shift by a random amount.

    Requires |shift| >= min_shift so short-range autocorrelation is
    actually destroyed (P2 fix from audit). The minimum is capped at
    ``n // 4`` to keep the shifted series from becoming degenerate.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 4:
        return y.copy()
    min_shift = int(max(1, min(min_shift, n // 4)))
    magnitude = int(rng.integers(min_shift, n - min_shift + 1))
    sign = 1 if rng.random() < 0.5 else -1
    return np.roll(y, sign * magnitude)


NULL_MODELS: dict[str, Callable] = {
    "phase":      _phase_randomize,
    "iaaft":      _iaaft,
    "block":      _block_bootstrap,
    "time_shift": _time_shift,
}


def _default_null_kwargs(name: str, n: int) -> dict:
    if name == "block":
        return {"block_size": max(2, int(round(n ** (1 / 3))))}
    if name == "iaaft":
        return {"n_iter": 50}
    if name == "time_shift":
        return {"min_shift": 1}
    return {}


def make_null(name: str, n: Optional[int] = None, **kwargs) -> Callable:
    """
    Build a null-model function with sensible defaults.

    If ``kwargs`` is empty and ``n`` is provided, model-specific
    defaults are filled in (e.g. ``block_size = n**(1/3)`` for the
    block bootstrap). Bad kwargs raise ``NullModelError`` instead of
    leaking a bare ``TypeError``.
    """
    if name not in NULL_MODELS:
        raise NullModelError(f"unknown null model: {name}")
    fn = NULL_MODELS[name]
    if not kwargs:
        if n is None:
            return fn
        kwargs = _default_null_kwargs(name, n)

    def wrapped(y, rng):
        try:
            return fn(y, rng, **kwargs)
        except TypeError as exc:
            raise NullModelError(
                f"bad kwargs for null model '{name}': {kwargs} ({exc})"
            ) from exc

    return wrapped


# ------------------------------------------------------------------ #
#                    significance and FDR                            #
# ------------------------------------------------------------------ #

def null_max_distribution(x: np.ndarray, y: np.ndarray, max_lag: int,
                          null_fn: Callable, n_surrogates: int = 200,
                          method: str = "spearman", fisher: bool = True,
                          rng: Optional[np.random.Generator] = None,
                          randomize_both: bool = True,
                          min_overlap: int = DEFAULT_MIN_OVERLAP) -> np.ndarray:
    """
    Null distribution of the Fisher-weighted max-statistic.

    ``randomize_both=True`` (default) randomizes both series under
    H0. This is conservative: when both series are autocorrelated,
    it inflates the null variance and reduces false positives.
    Set to False to fix x and randomize only y (classical
    cross-correlation null).
    """
    rng = rng or np.random.default_rng()
    out = np.empty(n_surrogates)
    for b in range(n_surrogates):
        y_s = null_fn(y, rng)
        x_s = null_fn(x, rng) if randomize_both else x
        out[b] = lagged_cc(x_s, y_s, max_lag,
                           method=method, fisher=fisher,
                           min_overlap=min_overlap).max_stat
    return out


def empirical_pvalue(observed: float, null_dist: np.ndarray) -> float:
    """Plus-one empirical p-value (one-sided, conservative)."""
    null_dist = np.asarray(null_dist)
    if len(null_dist) == 0:
        return 1.0
    return float((1 + np.sum(null_dist >= observed)) / (1 + len(null_dist)))


def fdr_bh(pvals: Sequence[float], alpha: float = 0.05) -> np.ndarray:
    """
    Benjamini-Hochberg q-values, NaN-safe.

    NaN inputs stay NaN in the output and are excluded from ranking,
    so undefined p-values are visible rather than silently mapped
    to "not significant".
    """
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    out = np.full(n, np.nan, dtype=float)
    finite = np.isfinite(p)
    if not finite.any():
        return out
    pf = p[finite]
    m = len(pf)
    order = np.argsort(pf)
    ranked = pf[order]
    q = ranked * m / (np.arange(m) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0.0, 1.0)
    tmp = np.empty(m)
    tmp[order] = q
    out[finite] = tmp
    return out


# ------------------------------------------------------------------ #
#                    pair-level analysis                             #
# ------------------------------------------------------------------ #

@dataclass
class Detector:
    detector_id: str
    detector_type: str
    residual: np.ndarray
    lat: Optional[float] = None
    lon: Optional[float] = None
    meta: dict = field(default_factory=dict)


@dataclass
class PairResult:
    detector_1: str
    detector_2: str
    lag_max: int
    rho_max: float
    n_at_max: int
    max_stat: float
    p_value: float
    q_value: float
    significant: bool
    null_model: str
    n_surrogates: int


def _spawn(rng: np.random.Generator, n: int) -> list[np.random.Generator]:
    """Return n independent child generators."""
    if hasattr(rng, "spawn"):
        try:
            return rng.spawn(n)
        except Exception:
            pass
    seeds = rng.integers(0, 2 ** 32 - 1, size=n)
    return [np.random.default_rng(int(s)) for s in seeds]


def analyze_pair(d1: Detector, d2: Detector, max_lag: int,
                 null_model_name: str = "time_shift",
                 n_surrogates: int = 200,
                 method: str = "spearman",
                 fisher: bool = True,
                 rng: Optional[np.random.Generator] = None,
                 null_kwargs: Optional[dict] = None,
                 apply_preprocessing: bool = True,
                 randomize_both: bool = True,
                 min_overlap: int = DEFAULT_MIN_OVERLAP) -> PairResult:
    """
    Full pair-level analysis with isolated RNG.

    If ``rng`` is None a fresh generator is created, so the function
    is safe to call in parallel without sharing state.
    """
    if rng is None:
        rng = np.random.default_rng()

    x = preprocess(d1.residual) if apply_preprocessing else np.asarray(d1.residual, float)
    y = preprocess(d2.residual) if apply_preprocessing else np.asarray(d2.residual, float)
    if len(x) != len(y):
        raise ValueError("detectors must be aligned to a common grid")

    curve = lagged_cc(x, y, max_lag, method=method,
                      fisher=fisher, min_overlap=min_overlap)

    null_fn = make_null(null_model_name, n=len(x), **(null_kwargs or {}))
    null_stats = null_max_distribution(
        x, y, max_lag, null_fn,
        n_surrogates=n_surrogates,
        method=method, fisher=fisher,
        rng=rng, randomize_both=randomize_both,
        min_overlap=min_overlap,
    )
    p = empirical_pvalue(curve.max_stat, null_stats)

    return PairResult(
        detector_1=d1.detector_id,
        detector_2=d2.detector_id,
        lag_max=curve.lag_max,
        rho_max=curve.rho_max,
        n_at_max=curve.n_at_max,
        max_stat=curve.max_stat,
        p_value=p,
        q_value=np.nan,
        significant=False,
        null_model=null_model_name,
        n_surrogates=n_surrogates,
    )


def analyze_all_pairs(detectors: Sequence[Detector], max_lag: int,
                      null_model_name: str = "time_shift",
                      n_surrogates: int = 200,
                      alpha: float = 0.05,
                      seed: int = 0,
                      **kwargs) -> list[PairResult]:
    """
    Analyze every unordered pair. Each pair gets its own child RNG
    derived from ``seed``, so results are deterministic but the
    analysis is safe to parallelize.
    """
    rng = np.random.default_rng(seed)
    pairs = [(i, j) for i in range(len(detectors))
             for j in range(i + 1, len(detectors))]
    if not pairs:
        return []

    children = _spawn(rng, len(pairs))
    results: list[PairResult] = []
    for (i, j), child in zip(pairs, children):
        results.append(analyze_pair(
            detectors[i], detectors[j],
            max_lag=max_lag,
            null_model_name=null_model_name,
            n_surrogates=n_surrogates,
            rng=child, **kwargs,
        ))

    q = fdr_bh([r.p_value for r in results], alpha=alpha)
    for r, qv in zip(results, q):
        r.q_value = float(qv) if np.isfinite(qv) else float("nan")
        r.significant = bool(np.isfinite(qv) and qv <= alpha)
    return results


# ------------------------------------------------------------------ #
#                          robustness                                #
# ------------------------------------------------------------------ #

def windowed_stability(x: np.ndarray, y: np.ndarray, max_lag: int,
                       n_windows: int = 6,
                       method: str = "spearman") -> dict:
    """Split into windows; check lag/rho stability across windows."""
    n = len(x)
    edges = np.linspace(0, n, n_windows + 1).astype(int)
    lags, rhos = [], []
    for k in range(n_windows):
        a = preprocess(x[edges[k]: edges[k + 1]])
        b = preprocess(y[edges[k]: edges[k + 1]])
        if len(a) <= 2 * max_lag + 5:
            continue
        c = lagged_cc(a, b, max_lag, method=method)
        lags.append(c.lag_max)
        rhos.append(c.rho_max)
    if not lags:
        return dict(n_windows_used=0)
    lags_arr = np.asarray(lags)
    rhos_arr = np.asarray(rhos)
    return dict(
        n_windows_used=len(lags_arr),
        lag_median=float(np.median(lags_arr)),
        lag_iqr=float(np.percentile(lags_arr, 75) - np.percentile(lags_arr, 25)),
        rho_sign_consistency=float(
            np.mean(np.sign(rhos_arr) == np.sign(np.median(rhos_arr)))
        ),
        rho_median=float(np.median(rhos_arr)),
    )


def distance_dependence(distances: Sequence[float],
                        rho_max: Sequence[float],
                        n_perm: int = 2000,
                        rng: Optional[np.random.Generator] = None) -> dict:
    """Permutation test: does |rho_max| depend on distance?"""
    rng = rng or np.random.default_rng()
    d = np.asarray(distances, dtype=float)
    r = np.abs(np.asarray(rho_max, dtype=float))
    obs = stats.spearmanr(d, r).statistic
    null = np.empty(n_perm)
    for k in range(n_perm):
        null[k] = stats.spearmanr(d, rng.permutation(r)).statistic
    p = float((1 + np.sum(np.abs(null) >= abs(obs))) / (1 + n_perm))
    return dict(observed_rho=float(obs), p_value=p, n_perm=n_perm)


# ------------------------------------------------------------------ #
#                          synthetic                                 #
# ------------------------------------------------------------------ #

def synthetic_ar1_pair(n: int = 4000, true_lag: int = 6,
                       coupling: float = 0.25,
                       ar: float = 0.85, noise: float = 1.0,
                       seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """x(t) = AR(1) + noise;  y(t) = c*x(t - true_lag) + AR(1) + noise."""
    rng = np.random.default_rng(seed)

    def ar1(n_, phi, sigma):
        e = rng.normal(0, sigma, size=n_)
        out = np.zeros(n_)
        for t in range(1, n_):
            out[t] = phi * out[t - 1] + e[t]
        return out

    x = ar1(n, ar, noise)
    y = ar1(n, ar, noise)
    y[true_lag:] += coupling * x[: -true_lag]
    return x, y


def benchmark(true_lag: int = 6, coupling: float = 0.25, n: int = 4000,
              max_lag: int = 24, n_surrogates: int = 200,
              null_model_name: str = "time_shift",
              seed: int = 0,
              randomize_both: bool = True) -> dict:
    """Single-seed synthetic benchmark."""
    x, y = synthetic_ar1_pair(n=n, true_lag=true_lag,
                              coupling=coupling, seed=seed)
    x = preprocess(x)
    y = preprocess(y)
    curve = lagged_cc(x, y, max_lag)
    null_fn = make_null(null_model_name, n=n)
    rng = np.random.default_rng(seed + 1)
    null_stats = null_max_distribution(
        x, y, max_lag, null_fn,
        n_surrogates=n_surrogates,
        rng=rng, randomize_both=randomize_both,
    )
    p = empirical_pvalue(curve.max_stat, null_stats)
    return dict(
        true_lag=true_lag,
        detected_lag=curve.lag_max,
        rho_max=curve.rho_max,
        p_value=p,
        hit=abs(curve.lag_max - true_lag) <= 1,
    )