import numpy as np
import pandas as pd
from scipy import stats
from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat
from crosscorr_lib.analysis.surrogate import max_lag_surrogate_pvalue

T, N, B, REPS = 300, 4, 100, 120
cols = ["a", "b", "c", "d"]
shared_pab, shared_pac, indep_pac = [], [], []

for s in range(REPS):
    rng = np.random.default_rng(s)
    wide = pd.DataFrame(rng.normal(size=(T, N)), columns=cols)
    df = cross_correlation_pairs_with_max_stat(
        wide, B=B, seed=s, n_jobs=1, method="phase",
    )
    d = {(r.detector_a, r.detector_b): r.p_value for r in df.itertuples()}
    shared_pab.append(d[("a", "b")])
    shared_pac.append(d[("a", "c")])
    _, p_indep, _ = max_lag_surrogate_pvalue(
        wide["a"].values, wide["c"].values,
        max_lag=72, n_surrogates=B, seed=10_000 + s,
    )
    indep_pac.append(p_indep)

r_shared = stats.spearmanr(shared_pab, shared_pac).statistic
r_indep = stats.spearmanr(shared_pab, indep_pac).statistic
print(f"REPS={REPS}")
print("rho(p_ab, p_ac) shared surrogates   =", round(float(r_shared), 4))
print("rho(p_ab, p_ac) independent surrog. =", round(float(r_indep), 4))
print("difference (shared - independent)   =", round(float(r_shared - r_indep), 4))
