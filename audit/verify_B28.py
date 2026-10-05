"""B28: общий mask занижает IAT обоих рядов.

Проверяем: если x и y имеют NaN в разных позициях, то
integrated_autocorrelation_time, посчитанный на x под ОБЩИМ mask
(строки, где NaN в любом из рядов), отличается от IAT на x под
СОБСТВЕННЫМ mask x. Ожидание: общий mask режет валидные точки x и
снижает tau (анти-консервативно).
"""
import numpy as np

from crosscorr_lib.analysis.effective_sample import (
    integrated_autocorrelation_time as iat,
)


def ar1(n, phi, rng):
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + rng.normal()
    return x


rng = np.random.default_rng(0)
n = 2000
x = ar1(n, 0.9, rng)
y = ar1(n, 0.9, rng)

# x: NaN в блоке [100:400]; y: NaN в блоке [1000:1300]
x_nan = x.copy()
y_nan = y.copy()
x_nan[100:400] = np.nan
y_nan[1000:1300] = np.nan

mask_x = ~np.isnan(x_nan)
mask_y = ~np.isnan(y_nan)
mask_joint = mask_x & mask_y

tau_x_own = iat(x_nan[mask_x])
tau_x_joint = iat(x_nan[mask_joint])
tau_y_own = iat(y_nan[mask_y])
tau_y_joint = iat(y_nan[mask_joint])

print("n_x_own   =", int(mask_x.sum()), " tau_x_own   =", round(tau_x_own, 4))
print("n_x_joint =", int(mask_joint.sum()), " tau_x_joint =", round(tau_x_joint, 4))
print("n_y_own   =", int(mask_y.sum()), " tau_y_own   =", round(tau_y_own, 4))
print("n_y_joint =", int(mask_joint.sum()), " tau_y_joint =", round(tau_y_joint, 4))
print("tau_x_own - tau_x_joint =", round(tau_x_own - tau_x_joint, 4))
print("tau_y_own - tau_y_joint =", round(tau_y_own - tau_y_joint, 4))
