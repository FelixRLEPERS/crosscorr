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
n_pairs = 6

df = cross_correlation_pairs_with_max_stat(
    wide, max_lag=max_lag, n_surrogates=B, seed=seed,
    apply_preprocessing=False,
)
row_ac = df[(df.detector_1 == "a") & (df.detector_2 == "c")].iloc[0]
print("function p(a,c) =", float(row_ac["p_value"]))

parent = np.random.default_rng(seed)
children = parent.spawn(n_pairs)
seeds = [int(children[k].integers(0, 2**31)) for k in range(n_pairs)]

x, y = wide["a"].values, wide["c"].values
for k in (0, 1):
    _, p, _ = max_lag_surrogate_pvalue(
        x, y, max_lag=max_lag, n_surrogates=B, seed=seeds[k],
    )
    print(f"direct seed=child[{k}] -> p = {float(p)}")
