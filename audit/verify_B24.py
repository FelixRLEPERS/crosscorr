"""B24: n_obs считается после интерполяции NaN в preprocess.

cross_correlation_pairs_with_max_stat применяет preprocess (интерполяция)
к каждой колонке ДО подсчёта n_obs. Поэтому n_obs == полная длина ряда,
хотя часть точек была интерполирована.
"""
import numpy as np
import pandas as pd

from crosscorr_lib.analysis.cross_correlation import (
    cross_correlation_pairs_with_max_stat,
)

rng = np.random.default_rng(0)
n = 200
a = rng.normal(size=n)
b = 0.5 * a + rng.normal(size=n)
a[10:60] = np.nan  # 50 пропусков
wide = pd.DataFrame({"a": a, "b": b})

raw_valid = int((~np.isnan(a) & ~np.isnan(b)).sum())
df = cross_correlation_pairs_with_max_stat(
    wide, max_lag=10, n_surrogates=30, seed=1,
)
print("row length (series size) =", n)
print("raw valid pairs (drop)   =", raw_valid)
print("n_obs in output          =", int(df["n_obs"].iloc[0]))
print("n_obs > raw_valid ?      =", int(df["n_obs"].iloc[0]) > raw_valid)
