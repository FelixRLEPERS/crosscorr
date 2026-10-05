import numpy as np
from crosscorr_lib.analysis.surrogate import max_lag_surrogate_pvalue

rng = np.random.default_rng(0)
n = 20
x = rng.normal(size=n)
y = rng.normal(size=n)

print("n =", n, "max_lag = 30 (> n)")
try:
    out = max_lag_surrogate_pvalue(
        x, y, max_lag=30, n_surrogates=10, seed=42,
    )
    print("no exception, returned:", out)
except Exception as e:
    print("EXCEPTION:", type(e).__name__, "-", e)
