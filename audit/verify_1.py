import numpy as np
import pandas as pd
from crosscorr_lib.analysis.cross_correlation import (
    cross_correlation_pairs_with_max_stat,
)

rng = np.random.default_rng(0)
X = rng.normal(size=(500, 4))
wide = pd.DataFrame(X, columns=["a", "b", "c", "d"])

df = cross_correlation_pairs_with_max_stat(
    wide, max_lag=10, n_surrogates=50, seed=42,
)
c = df["correlation"]
print("max |correlation| =", float(c.abs().max()))
print("any > 1:", bool((c.abs() > 1).any()))
print("min:", float(c.min()))
print("max:", float(c.max()))
print("columns:", list(df.columns))
