import numpy as np
from crosscorr_lib.analysis.surrogate import (
    _time_shift,
    _lagged_cc,
    _count_valid_at_lag,
)

rng = np.random.default_rng(0)
n, max_lag = 200, 10
x = rng.normal(size=n)
y = 0.5 * x + rng.normal(size=n)

lags, _, _ = _lagged_cc(x, y, max_lag)
n_obs = np.array([_count_valid_at_lag(x, y, int(t)) for t in lags])

y_surr = _time_shift(y, rng)
_, _, _ = _lagged_cc(x, y_surr, max_lag)
n_surr = np.array([_count_valid_at_lag(x, y_surr, int(t)) for t in lags])

print("n_obs  :", n_obs.tolist())
print("n_surr :", n_surr.tolist())
print("equal:", bool(np.array_equal(n_obs, n_surr)))
print("nan in surrogate edges:", int(np.isnan(y_surr).sum()))
