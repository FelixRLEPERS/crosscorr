import numpy as np
import pandas as pd
from crosscorr_lib.analysis.cross_correlation import (
    cross_correlation_pairs_with_max_stat,
)
from crosscorr_lib.analysis.surrogate import max_lag_surrogate_pvalue

seed, max_lag, B, T = 42, 10, 50, 300
rng = np.random.default_rng(7)
wide = pd.DataFrame({
    "a": rng.normal(size=T),
    "b": np.full(T, 5.0),
    "c": rng.normal(size=T),
    "d": rng.normal(size=T),
})
cols = ["a", "b", "c", "d"]

df = cross_correlation_pairs_with_max_stat(
    wide, max_lag=max_lag, n_surrogates=B, seed=seed,
    apply_preprocessing=False,
)
print("function rows:")
for r in df.itertuples():
    print(f"  ({r.detector_1},{r.detector_2}) p={r.p_value:.6f}")

parent = np.random.default_rng(seed)
children = parent.spawn(6)
seeds = [int(children[k].integers(0, 2**31)) for k in range(6)]
print("direct p for (a,c) across child seeds:")
for k in range(6):
    _, p, _ = max_lag_surrogate_pvalue(
        wide["a"].values, wide["c"].values,
        max_lag=max_lag, n_surrogates=B, seed=seeds[k],
    )
    print(f"  child[{k}] seed={seeds[k]} p={float(p):.6f}")
