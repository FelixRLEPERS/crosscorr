import numpy as np
import pandas as pd
import crosscorr_lib.analysis.surrogate as S
import crosscorr_lib.analysis.cross_correlation as CC

orig = S.max_lag_surrogate_pvalue
calls = []


def wrapper(x, y, max_lag=72, n_surrogates=500, seed=42, **kw):
    calls.append(seed)
    return orig(x, y, max_lag=max_lag, n_surrogates=n_surrogates, seed=seed, **kw)


S.max_lag_surrogate_pvalue = wrapper

rng = np.random.default_rng(7)
T = 300
wide = pd.DataFrame({
    "a": rng.normal(size=T),
    "b": rng.normal(size=T),
    "c": np.full(T, 5.0),
    "d": rng.normal(size=T),
})
df = CC.cross_correlation_pairs_with_max_stat(
    wide, max_lag=10, n_surrogates=50, seed=42,
    apply_preprocessing=False,
)
parent = np.random.default_rng(42)
children = parent.spawn(6)
seeds = [int(children[k].integers(0, 2**31)) for k in range(6)]
print("successful pairs:", list(zip(df.detector_1, df.detector_2)))
print("seeds passed (pair order):", calls)
print("child seeds              :", seeds)
print("duplicate seeds used:", len(calls) != len(set(calls)))
