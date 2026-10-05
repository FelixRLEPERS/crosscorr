import numpy as np
import pandas as pd
from crosscorr_lib.analysis.surrogate import surrogate_test

rng = np.random.default_rng(0)
n = 200
x = rng.normal(size=n)
y = 0.6 * x + rng.normal(size=n)
wide = pd.DataFrame({"x": x, "y": y})
wide.loc[10:60, "x"] = np.nan
wide.loc[100:130, "y"] = np.nan

real_pairwise = wide.corr(method="spearman").loc["x", "y"]
filled = wide.fillna(wide.mean())
real_imputed = filled.corr(method="spearman").loc["x", "y"]

p = surrogate_test(wide, n_surrogates=50, seed=42)
print("wide.corr (pairwise drop)   r =", round(float(real_pairwise), 6))
print("filled.corr (mean-imputed)  r =", round(float(real_imputed), 6))
print("difference                  =", round(float(real_pairwise - real_imputed), 6))
print("surrogate_test p(x,y)       =", float(p.iloc[0, 1]))
