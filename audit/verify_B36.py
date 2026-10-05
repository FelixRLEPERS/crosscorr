"""B36: max_lag не принимается из вызывающего кода.

Проверяем, что integrated_autocorrelation_time и
effective_sample_size действительно НЕ дают прокинуть max_lag.
"""
import inspect
import numpy as np

from crosscorr_lib.analysis import effective_sample as es

print("iat.signature      =", inspect.signature(es.integrated_autocorrelation_time))
print("ess.signature      =", inspect.signature(es.effective_sample_size))
print("iat has max_lag    =", "max_lag" in inspect.signature(es.integrated_autocorrelation_time).parameters)
print("ess has max_lag    =", "max_lag" in inspect.signature(es.effective_sample_size).parameters)

rng = np.random.default_rng(0)
x = rng.normal(size=500)
r1 = es.integrated_autocorrelation_time(x, max_lag=5)
r2 = es.integrated_autocorrelation_time(x, max_lag=100)
print("iat(max_lag=5)     =", round(r1, 4))
print("iat(max_lag=100)   =", round(r2, 4))
print("max_lag respected  =", r1 != r2)
