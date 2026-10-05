import numpy as np
from crosscorr_lib.pairs import _make_surrogates, _batch_max_stat_corr

T, B, REPS = 300, 200, 40
rhos = []
for rep in range(REPS):
    rng = np.random.default_rng(rep)
    a = rng.normal(size=T)
    b = rng.normal(size=T)
    c = rng.normal(size=T)
    sa = _make_surrogates(a, "phase", B, seed=rep * 3 + 1)
    sb = _make_surrogates(b, "phase", B, seed=rep * 3 + 2)
    sc = _make_surrogates(c, "phase", B, seed=rep * 3 + 3)
    nab = _batch_max_stat_corr(sa, sb)
    nac = _batch_max_stat_corr(sa, sc)
    rhos.append(np.corrcoef(nab, nac)[0, 1])
rhos = np.array(rhos)
print("REPS =", REPS)
print("mean rho(null_ab, null_ac | share a) =", round(float(rhos.mean()), 4))
print("std  =", round(float(rhos.std()), 4))
print("fraction rho > 0:", round(float((rhos > 0).mean()), 3))
