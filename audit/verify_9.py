import numpy as np
from crosscorr_lib.analysis.effective_sample import correlation_pvalue_with_ess

rng = np.random.default_rng(0)
n = 2000
x = rng.normal(size=n)
y = x + 1e-2 * rng.normal(size=n)

r, p, n_eff = correlation_pvalue_with_ess(x, y, method="pearson")
print("r      =", r)
print("n_eff  =", n_eff)
print("p      =", p)
print("p == 0.0:", bool(p == 0.0))

from scipy import stats
t = r * np.sqrt(n_eff - 2) / np.sqrt(1 - r * r)
print("t      =", t)
print("2*(1-cdf) =", 2 * (1 - stats.t.cdf(abs(t), df=n_eff - 2)))
print("2*sf      =", 2 * stats.t.sf(abs(t), df=n_eff - 2))
