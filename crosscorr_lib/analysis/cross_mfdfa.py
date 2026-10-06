"""Cross-MFDFA (Podobnik-Stanley) — generalized cross-Hurst exponent.

Классический фрактальный аналог log-scaling entanglement entropy
(см. docs/methodology.md). Обобщает MFDFA на две серии и даёт
h_xy(q). Реализация self-contained (не зависит от ``mfdfa.py``).

Алгоритм (Podobnik & Stanley, 2008; Zhou, 2008):

1. Профили X(i) = cumsum(x - mean(x)), Y(i) = cumsum(y - mean(y)).
2. Разбить на 2*N_s окна длины s (вперёд и назад).
3. В каждом окне — локальный линейный тренд; ковариация остатков:
       F_xy^2(s) = (1/s) * sum (X_k - Xfit_k)(Y_k - Yfit_k)
4. Флуктуационная функция:
       F_xy(q) = [ (1/(2N_s)) sum sign(F_xy^2) |F_xy^2|^{q/2} ]^{1/q}
   для q != 0; для q = 0 — exp( 0.5 * mean(ln|x|) ).

References
----------
Podobnik & Stanley (2008), Phys. Rev. Lett. 100, 084102.
Zhou (2008), Phys. Rev. E 77, 066211.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence

import numpy as np

DEFAULT_Q = (-5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0)

# TODO(XM-1, XM-2): формула для знаковых кросс-ковариаций
# требует reference-валидации. См. audit/AUDIT_v4.md, секция 1.4.
# Варианты конвенции — в отчёте. Не выбирать без научной проверки.


def _default_scales(n: int) -> np.ndarray:
    """Логарифмически распределённые масштабы от 10 до n//4."""
    hi = max(10, n // 4)
    base = np.unique(np.round(np.logspace(np.log10(10), np.log10(hi), 20)))
    return base[(base >= 10) & (base <= hi)].astype(int)


def _profile(x: np.ndarray) -> np.ndarray:
    return np.cumsum(x - np.mean(x))


def _detrended_cov(px: np.ndarray, py: np.ndarray, s: int) -> np.ndarray:
    """Ковариация локально-детрендированных сегментов длины s (оба конца)."""
    n = len(px)
    ns = n // s
    if ns < 2:
        return np.array([])
    t = np.arange(s, dtype=np.float64)
    vals = []
    for v in (0, 1):
        if v == 1:
            sx = px[::-1]
            sy = py[::-1]
        else:
            sx = px
            sy = py
        for k in range(ns):
            seg_y = sx[k * s:(k + 1) * s]
            seg_x = sy[k * s:(k + 1) * s]
            # линейный тренд по индексу для каждой серии
            cx = np.polyfit(t, seg_y, 1)
            cy = np.polyfit(t, seg_x, 1)
            rx = seg_y - np.polyval(cx, t)
            ry = seg_x - np.polyval(cy, t)
            vals.append(float(np.mean(rx * ry)))
    return np.array(vals)


def cross_mfdfa(
    x: np.ndarray,
    y: np.ndarray,
    q_values: Sequence[float] = DEFAULT_Q,
    scales: Sequence[int] | None = None,
) -> dict:
    """Cross-MFDFA: generalized cross-Hurst exponent h_xy(q).

    # TODO(XM-1, XM-2): знак cross-fluctuation требует
     reference-валидации. См. audit/AUDIT_v4.md, секция 1.4.

    Parameters
    ----------
    x, y : array-like
        Одномерные ряды равной длины.
    q_values : sequence of float
        Порядки q (default -5..5).
    scales : sequence of int, optional
        Масштабы s; по умолчанию — лог-сетка от 10 до n//4.

    Returns
    -------
    dict
        Ключи: ``scales``, ``q``, ``F_q`` (форма (len(q), len(scales))),
        ``h_q``, ``tau_q`` = q*h_q - 1, ``r_squared`` (R² линейного фита
        log F vs log scale для каждого q, NaN если fit невозможен),
        ``n_scales`` (сколько масштабов реально использовано).

    References
    ----------
    Podobnik & Stanley (2008), Phys. Rev. Lett. 100, 084102.
    """
    xa = np.asarray(x, dtype=np.float64).ravel()
    ya = np.asarray(y, dtype=np.float64).ravel()
    if xa.size != ya.size:
        raise ValueError(
            f"разные длины x и y: {xa.size} и {ya.size} (должны быть равны)"
        )
    if not np.all(np.isfinite(xa)) or not np.all(np.isfinite(ya)):
        raise ValueError(
            "x и y должны содержать только конечные значения (NaN/Inf "
            "недопустимы)"
        )
    n = xa.size
    if n < 100:
        raise ValueError("ряды слишком короткие для cross-MFDFA")

    q = np.asarray(q_values, dtype=np.float64)
    if q.size == 0 or not np.all(np.isfinite(q)):
        raise ValueError(
            "q_values: пустая последовательность или nonfinite-значения "
            "недопустимы"
        )

    if scales is not None:
        s_raw = np.asarray(scales, dtype=np.float64).ravel()
        if s_raw.size == 0 or not np.all(np.isfinite(s_raw)):
            raise ValueError(
                "scales: пустая последовательность или nonfinite-значения "
                "недопустимы"
            )
        s_arr = np.sort(s_raw.astype(int))
    else:
        s_arr = _default_scales(n)
    if np.any(s_arr <= 0) or np.any(s_arr > n):
        raise ValueError(
            f"scales: все значения должны быть > 0 и <= n={n}"
        )

    px = _profile(xa)
    py = _profile(ya)

    # F_xy^2(s) -> F_xy(q)
    fq = np.full((q.size, s_arr.size), np.nan, dtype=np.float64)
    for si, s in enumerate(s_arr):
        covs = _detrended_cov(px, py, int(s))
        if covs.size == 0:
            continue
        abs_cov = np.abs(covs)
        abs_cov = np.where(abs_cov > 0, abs_cov, np.finfo(float).tiny)
        sign_cov = np.sign(covs)
        for qi, qv in enumerate(q):
            if qv == 0.0:
                fq[qi, si] = np.exp(0.5 * np.mean(np.log(abs_cov)))
            else:
                term = sign_cov * abs_cov ** (qv / 2.0)
                fq[qi, si] = np.sign(np.mean(term)) * (
                    np.mean(np.abs(term)) ** (1.0 / qv)
                ) if np.mean(term) != 0 else np.nan
        # Для положительно определённой F_xy(q) используем модуль:
        fq[:, si] = np.abs(fq[:, si])

    # h_q из наклона log F_q vs log s с fit-диагностикой
    h_q = np.full(q.size, np.nan, dtype=np.float64)
    r_squared = np.full(q.size, np.nan, dtype=np.float64)
    log_s = np.log(s_arr)
    for qi in range(q.size):
        yv = np.log(fq[qi])
        good = np.isfinite(yv)
        if good.sum() >= 3:
            slope, intercept = np.polyfit(log_s[good], yv[good], 1)
            h_q[qi] = float(slope)
            ss_res = float(
                np.sum((yv[good] - (slope * log_s[good] + intercept)) ** 2)
            )
            ss_tot = float(np.sum((yv[good] - yv[good].mean()) ** 2))
            if ss_tot > 0.0:
                r_squared[qi] = float(1.0 - ss_res / ss_tot)

    n_scales = int(np.any(np.isfinite(fq), axis=0).sum())

    bad = np.isfinite(r_squared) & (r_squared < 0.95)
    if bad.any():
        warnings.warn(
            f"Cross-MFDFA: R² < 0.95 для q={q[bad].tolist()}; линейная "
            "зависимость log F vs log scale ненадёжна",
            UserWarning,
            stacklevel=2,
        )

    tau_q = q * h_q - 1.0

    return {
        "scales": s_arr,
        "q": q,
        "F_q": fq,
        "h_q": h_q,
        "tau_q": tau_q,
        "r_squared": r_squared,
        "n_scales": n_scales,
    }


def cross_mfdfa_spectrum(cross_mfdfa_result: dict) -> dict:
    """Мультифрактальный спектр f(alpha) из h(q).

    alpha = h(q) + q * h'(q); f(alpha) = q * alpha - tau(q).

    Returns
    -------
    dict
        Ключи ``alpha``, ``f``.
    """
    q = np.asarray(cross_mfdfa_result["q"], dtype=np.float64)
    h = np.asarray(cross_mfdfa_result["h_q"], dtype=np.float64)
    tau = np.asarray(cross_mfdfa_result["tau_q"], dtype=np.float64)

    good = np.isfinite(h)
    q, h, tau = q[good], h[good], tau[good]
    if q.size < 3:
        return {"alpha": np.array([]), "f": np.array([])}

    order = np.argsort(q)
    q, h, tau = q[order], h[order], tau[order]
    h_prime = np.gradient(h, q)
    alpha = h + q * h_prime
    f = q * alpha - tau
    return {"alpha": alpha, "f": f}
