import numpy as np
import pandas as pd
from scipy import stats
from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat

T, N, B = 300, 4, 100
cols = ["a", "b", "c", "d"]


def pvals(seed):
    rng = np.random.default_rng(seed)
    wide = pd.DataFrame(rng.normal(size=(T, N)), columns=cols)
    df = cross_correlation_pairs_with_max_stat(
        wide, B=B, seed=seed, n_jobs=1, method="phase",
    )
    d = {(r.detector_a, r.detector_b): r.p_value for r in df.itertuples()}
    return d


p01, p02, p23 = [], [], []
for s in range(60):
    d = pvals(s)
    p01.append(d[("a", "b")])
    p02.append(d[("a", "c")])
    p23.append(d[("c", "d")])

r_share = stats.spearmanr(p01, p02).statistic
r_disjoint = stats.spearmanr(p01, p23).statistic
print("share detector a: rho(p_ab, p_ac) =", round(float(r_share), 4))
print("disjoint:         rho(p_ab, p_cd) =", round(float(r_disjoint), 4))
print("share - disjoint  =", round(float(r_share - r_disjoint), 4))
