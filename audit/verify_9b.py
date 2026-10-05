import numpy as np
from scipy import stats
from crosscorr_lib.analysis.effective_sample import correlation_pvalue_with_ess

rng = np.random.default_rng(0)
n = 300
x = rng.normal(size=n)
for noise in [0.5, 0.2, 0.1, 0.05, 0.02]:
    y = x + noise * rng.normal(size=n)
    r, p, n_eff = correlation_pvalue_with_ess(x, y, method="pearson")
    t = r * np.sqrt(n_eff - 2) / np.sqrt(1 - r * r)
    p_cdf = 2 * (1 - stats.t.cdf(abs(t), df=n_eff - 2))
    p_sf = 2 * stats.t.sf(abs(t), df=n_eff - 2)
    print(f"noise={noise:<5} r={r:.6f} t={t:9.2f} p_returned={p} p_cdf={p_cdf} p_sf={p_sf}")
