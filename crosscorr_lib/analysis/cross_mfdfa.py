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
from typing import Literal

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
    """Ковариация локально-детрендированных сегментов длины s (оба конца).

    Оптимизация XM-5: линейный тренд по каждому сегменту считается по
    закрытой OLS-формуле и сразу для всех сегментов (batched), без
    ``np.polyfit``/``np.polyval`` в цикле. Формула та же (МНК прямой),
    отличие от прежней реализации < 1e-13.
    """
    n = len(px)
    ns = n // s
    if ns < 2:
        return np.array([])
    t = np.arange(s, dtype=np.float64)
    st = t.sum()
    stt = (t * t).sum()
    denom = s * stt - st * st

    def _residuals(profile: np.ndarray) -> np.ndarray:
        # (ns, s): строка k — сегмент profile[k*s:(k+1)*s]
        seg = profile[: ns * s].reshape(ns, s)
        sy = seg.sum(axis=1)
        sty = seg @ t
        slope = (s * sty - st * sy) / denom
        intercept = (sy - slope * st) / s
        return seg - (slope[:, None] * t + intercept[:, None])

    vals = np.empty(2 * ns, dtype=np.float64)
    for offset, arr_x, arr_y in ((0, px, py), (ns, px[::-1], py[::-1])):
        rx = _residuals(arr_x)
        ry = _residuals(arr_y)
        vals[offset:offset + ns] = (rx * ry).mean(axis=1)
    return vals


_MIN_FIT_SCALES = 3


def _q_curve(covs: np.ndarray, q: np.ndarray) -> np.ndarray:
    """F_xy(q, s) по signed cross-ковариациям сегментов, magnitude-only.

    ``covs`` — уже отобранная группа сегментов (F²_v > 0 либо F²_v < 0).
    Возвращает массив формы (len(q),) для одного масштаба s:

    - q != 0: F_q = (1/(2m) * Σ_v |F²_v|^(q/2))^(1/q)
    - q == 0: F_0 = exp(1/(2m) * Σ_v ln|F²_v|) = exp(0.5 * mean(ln|F²_v|))

    Множитель 1/(2m) в идентичен усреднению ``np.mean`` по m элементам.
    """
    abs_cov = np.abs(covs)
    m = abs_cov.size
    out = np.full(q.size, np.nan, dtype=np.float64)
    if m == 0:
        return out
    abs_cov = np.where(abs_cov > 0, abs_cov, np.finfo(float).tiny)
    for qi, qv in enumerate(q):
        if qv == 0.0:
            out[qi] = np.exp(0.5 * np.mean(np.log(abs_cov)))
        else:
            out[qi] = float(np.mean(abs_cov ** (qv / 2.0)) ** (1.0 / qv))
    return out


def _fit_h_q(
    fq: np.ndarray, q: np.ndarray, s_arr: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Наклон log F_q vs log s и R² для каждого q.

    Возвращает ``(h_q, r_squared)``; NaN, если конечных точек < 3.
    """
    h_q = np.full(q.size, np.nan, dtype=np.float64)
    r_squared = np.full(q.size, np.nan, dtype=np.float64)
    log_s = np.log(s_arr)
    for qi in range(q.size):
        yv = np.log(fq[qi])
        good = np.isfinite(yv)
        if good.sum() >= _MIN_FIT_SCALES:
            slope, intercept = np.polyfit(log_s[good], yv[good], 1)
            h_q[qi] = float(slope)
            ss_res = float(
                np.sum((yv[good] - (slope * log_s[good] + intercept)) ** 2)
            )
            ss_tot = float(np.sum((yv[good] - yv[good].mean()) ** 2))
            if ss_tot > 0.0:
                r_squared[qi] = float(1.0 - ss_res / ss_tot)
    return h_q, r_squared


def cross_mfdfa(
    x: np.ndarray,
    y: np.ndarray,
    q_values: Sequence[float] = DEFAULT_Q,
    scales: Sequence[int] | None = None,
    *,
    signed: Literal["abs", "split"] = "abs",
) -> dict:
    """Cross-MFDFA: generalized cross-Hurst exponent h_xy(q).

    Parameters
    ----------
    x, y : array-like
        Одномерные ряды равной длины.
    q_values : sequence of float
        Порядки q (default -5..5).
    scales : sequence of int, optional
        Масштабы s; по умолчанию — лог-сетка от 10 до n//4.
    signed : {"abs", "split"}, default="abs"
        Convention for negative cross-fluctuations:
        - "abs": magnitude-only, |F²_v|^(q/2). Follows most
          published implementations. Loses sign information.
        - "split": separate spectra for F²_v > 0 and F²_v < 0.
          More informative but each spectrum has fewer segments.
          Experimental.

    Returns
    -------
    dict
        For ``signed="abs"``: ``scales``, ``q``, ``F_q`` (shape
        (len(q), len(scales))), ``h_q``, ``tau_q`` = q*h_q - 1,
        ``r_squared`` (R² of the log F vs log scale fit for each q,
        NaN if the fit is impossible), ``n_scales`` (how many scales
        were actually used).

        For ``signed="split"``, additionally: ``h_plus_q``,
        ``h_minus_q`` (per-sign spectra), ``r_squared_plus``,
        ``r_squared_minus``, ``n_plus``, ``n_minus`` (number of
        segments in each group). Fields ``h_q``, ``tau_q`` and
        ``r_squared`` mirror the positive group. If a group has fewer
        than 3 segments, its spectrum is all-NaN and a warning is
        emitted.

    Notes
    -----
    The treatment of negative F²_v(s) in MF-DXA is an OPEN
    PROBLEM in the literature:

    - Zhou (2008) PR E 77, 066211 does not specify a convention.
    - Most published implementations use magnitude-only
      (|F²_v|^(q/2)) — see Oświęcimka et al. (2014),
      Kristoufek (2014).

    The default "abs" convention follows that practice.
    The "split" option is experimental; it separates segments
    by the sign of their cross-covariance.

    References
    ----------
    Zhou (2008), Phys. Rev. E 77, 066211.
    Podobnik & Stanley (2008), Phys. Rev. Lett. 100, 084102.

    Examples
    --------
    >>> h = cross_mfdfa(x, y, q_values=[2, 3, 4])
    >>> # Для анализа знака:
    >>> result = cross_mfdfa(x, y, q_values=[2, 3], signed="split")
    >>> print(result["n_plus"], result["n_minus"])

    TODO(XM-1, XM-2): final convention requires reference validation.
    See audit/AUDIT_v5.md and audit/external_reviews/QWEN_v5_consultation.md.
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

    if signed not in ("abs", "split"):
        raise ValueError(
            f"signed должен быть 'abs' или 'split', получено {signed!r}"
        )

    px = _profile(xa)
    py = _profile(ya)

    # F_xy^2(s) -> F_xy(q)
    fq = np.full((q.size, s_arr.size), np.nan, dtype=np.float64)
    fq_plus = np.full((q.size, s_arr.size), np.nan, dtype=np.float64)
    fq_minus = np.full((q.size, s_arr.size), np.nan, dtype=np.float64)
    n_plus = 0
    n_minus = 0
    for si, s in enumerate(s_arr):
        covs = _detrended_cov(px, py, int(s))
        if covs.size == 0:
            continue
        fq[:, si] = _q_curve(covs, q)
        if signed == "split":
            pos = covs[covs > 0]
            neg = covs[covs < 0]
            n_plus += int(pos.size)
            n_minus += int(neg.size)
            fq_plus[:, si] = _q_curve(pos, q)
            fq_minus[:, si] = _q_curve(neg, q)
        else:
            fq[:, si] = np.abs(fq[:, si])

    if signed == "abs":
        h_q, r_squared = _fit_h_q(fq, q, s_arr)
        n_scales = int(np.any(np.isfinite(fq), axis=0).sum())
        bad = np.isfinite(r_squared) & (r_squared < 0.95)
        if bad.any():
            warnings.warn(
                f"Cross-MFDFA: R² < 0.95 для q={q[bad].tolist()}; линейная "
                "зависимость log F vs log scale ненадёжна",
                UserWarning,
                stacklevel=2,
            )
        return {
            "scales": s_arr,
            "q": q,
            "F_q": fq,
            "h_q": h_q,
            "tau_q": q * h_q - 1.0,
            "r_squared": r_squared,
            "n_scales": n_scales,
        }

    if n_minus < _MIN_FIT_SCALES:
        h_minus = np.full(q.size, np.nan, dtype=np.float64)
        r_minus = np.full(q.size, np.nan, dtype=np.float64)
        warnings.warn(
            "Cross-MFDFA (signed='split'): меньше 3 сегментов F²_v < 0; "
            "h_minus_q = NaN",
            UserWarning,
            stacklevel=2,
        )
    else:
        h_minus, r_minus = _fit_h_q(fq_minus, q, s_arr)
    if n_plus < _MIN_FIT_SCALES:
        h_plus = np.full(q.size, np.nan, dtype=np.float64)
        r_plus = np.full(q.size, np.nan, dtype=np.float64)
        warnings.warn(
            "Cross-MFDFA (signed='split'): меньше 3 сегментов F²_v > 0; "
            "h_plus_q = NaN",
            UserWarning,
            stacklevel=2,
        )
    else:
        h_plus, r_plus = _fit_h_q(fq_plus, q, s_arr)

    return {
        "scales": s_arr,
        "q": q,
        "F_q": fq,
        "h_q": h_plus,
        "tau_q": q * h_plus - 1.0,
        "r_squared": r_plus,
        "h_plus_q": h_plus,
        "h_minus_q": h_minus,
        "r_squared_plus": r_plus,
        "r_squared_minus": r_minus,
        "n_plus": n_plus,
        "n_minus": n_minus,
        "F_q_plus": fq_plus,
        "F_q_minus": fq_minus,
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
