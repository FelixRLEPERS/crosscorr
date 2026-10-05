"""C6: дефект среза -(T-1) при T=1.

В _batch_max_stat_corr при T=1: n_fft=2, irfft даёт 2 столбца,
cc[:, -(T-1):] = cc[:, 0:] = 2 столбца, плюс cc[:, :T] = 1 столбец,
итого 3 столбца вместо ожидаемого T=1.
"""
import numpy as np

from crosscorr_lib.pairs import _batch_max_stat_corr

for T in (1, 2, 3):
    si = np.random.default_rng(0).normal(size=(2, T))
    sj = np.random.default_rng(1).normal(size=(2, T))

    B, TT = si.shape
    n_fft = 2 * TT
    Fsi = np.fft.rfft(si, n=n_fft, axis=1)
    Fsj = np.fft.rfft(sj, n=n_fft, axis=1)
    cc = np.fft.irfft(Fsi * np.conj(Fsj), n=n_fft, axis=1)
    cc2 = np.concatenate([cc[:, -(TT - 1):], cc[:, :TT]], axis=1) / TT
    print(f"T={T}: irfft cols={cc.shape[1]}, after concat cols={cc2.shape[1]}")

    try:
        out = _batch_max_stat_corr(si, sj)
        print(f"  _batch_max_stat_corr -> {out}")
    except Exception as e:
        print(f"  EXCEPTION {type(e).__name__}: {e}")

# прямой вызов при T=1
si1 = np.array([[3.0]])
sj1 = np.array([[5.0]])
print("T=1 constant surrogate, degenerate expected:")
try:
    print("  out =", _batch_max_stat_corr(si1, sj1))
except Exception as e:
    print("  EXCEPTION:", type(e).__name__, e)
print("  max_stat single =", __import__("crosscorr_lib.pairs", fromlist=["_max_stat_corr"])._max_stat_corr(np.array([3.0]), np.array([5.0])))
