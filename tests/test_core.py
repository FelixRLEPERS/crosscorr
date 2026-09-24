"""
pytest suite for CrossCorr 2.0 core.py.

Explicitly covers:
- P0-1: block bootstrap does not degenerate (bs >= n)
- P0-2: randomize_both inflates null variance
- P1-1: block_size default is applied
- P1-2: NaN-safe FDR
- P1-3: RNG spawn produces independent streams
- P1-4: apply_preprocessing flag
Plus sanity tests for lagged_cc, null models, benchmark, robustness.
"""
import numpy as np
import pytest
from numpy.testing import assert_allclose

from core import (
    # public
    preprocess, lagged_cc, empirical_pvalue, fdr_bh,
    Detector, PairResult, analyze_pair, analyze_all_pairs,
    make_null, null_max_distribution, NULL_MODELS,
    windowed_stability, distance_dependence,
    synthetic_ar1_pair, benchmark,
    NullModelError, InsufficientDataError, PreprocessingError,
    DEFAULT_MIN_OVERLAP,
    # private (tested directly for P0/P1 regressions)
    _block_bootstrap, _phase_randomize, _iaaft, _time_shift, _spawn,
)


# ================================================================== #
#                        preprocessing                               #
# ================================================================== #

class TestPreprocess:
    def test_linear_detrend(self):
        t = np.arange(100)
        x = 3.0 + 0.5 * t
        y = preprocess(x, standardize=False)
        assert abs(np.mean(y)) < 1e-9

    def test_standardize(self):
        rng = np.random.default_rng(0)
        x = rng.normal(5, 2, 1000)
        y = preprocess(x, detrend=False, standardize=True)
        assert abs(np.mean(y)) < 1e-9
        assert abs(np.std(y, ddof=1) - 1.0) < 1e-9

    def test_nan_passthrough(self):
        x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        y = preprocess(x, detrend=False, standardize=False)
        assert np.isnan(y[2])
        assert_allclose(y[[0, 1, 3, 4]], x[[0, 1, 3, 4]])

    def test_constant_series(self):
        y = preprocess(np.ones(50))
        assert np.all(np.isfinite(y))

    def test_empty_raises(self):
        with pytest.raises(PreprocessingError):
            preprocess(np.array([]))

    def test_robust_detrend(self):
        """Theil-Sen slope should be closer to the true slope than OLS
        when a single large outlier is present at the edge."""
        from scipy import stats as _st

        rng = np.random.default_rng(0)
        t = np.arange(200)
        true_slope = 0.5
        x = true_slope * t + rng.normal(0, 1, 200)

        # Outlier must be at the EDGE to bias the OLS slope.
        # An outlier in the middle only shifts the intercept.
        x[-1] += 1000

        good = np.isfinite(x)
        ols_slope, _ = np.polyfit(t[good], x[good], 1)
        ts_slope, _, _, _ = _st.theilslopes(x[good], t[good])

        # Theil-Sen stays near truth
        assert abs(ts_slope - true_slope) < 0.05
        # OLS is badly biased by the outlier
        assert abs(ols_slope - true_slope) > 0.05
        # And Theil-Sen is much closer
        assert abs(ts_slope - true_slope) < abs(ols_slope - true_slope) / 5


# ================================================================== #
#                        lagged_cc                                   #
# ================================================================== #

class TestLaggedCC:
    def test_lag_recovery_no_noise(self):
        n = 500
        x = np.random.default_rng(0).normal(size=n)
        y = np.roll(x, 6)
        y[:6] = 0
        c = lagged_cc(x, y, max_lag=20)
        assert c.lag_max == 6
        assert c.rho_max > 0.9

    def test_zero_lag_symmetric(self):
        rng = np.random.default_rng(1)
        x = rng.normal(size=1000)
        y = 0.5 * x + 0.5 * rng.normal(size=1000)
        assert abs(lagged_cc(x, y, 0).rho_max -
                   lagged_cc(y, x, 0).rho_max) < 1e-9

    def test_negative_lag(self):
        n = 500
        x = np.random.default_rng(2).normal(size=n)
        y = np.roll(x, -8)
        y[-8:] = 0
        assert lagged_cc(x, y, max_lag=20).lag_max == -8

    def test_insufficient_data_raises(self):
        x = np.arange(10, dtype=float)
        with pytest.raises(InsufficientDataError):
            lagged_cc(x, x, max_lag=5)  # 5 == n//2

    def test_max_lag_negative_raises(self):
        x = np.arange(100, dtype=float)
        with pytest.raises(ValueError):
            lagged_cc(x, x, max_lag=-1)

    def test_all_nan_inputs(self):
        x = np.full(100, np.nan)
        y = np.arange(100, dtype=float)
        c = lagged_cc(x, y, max_lag=10)
        assert c.max_stat == 0.0

    def test_min_overlap_filters(self):
        n = 100
        x = np.random.default_rng(3).normal(size=n)
        # min_overlap large enough to kill extreme lags
        c = lagged_cc(x, x, max_lag=40, min_overlap=80)
        # only lags with at least 80 overlap survive
        assert np.isfinite(c.rho).sum() > 0
        # near max_lag the overlap is n - 40 = 60 < 80 => NaN
        assert np.isnan(c.rho[0])  # lag = -40
        assert np.isnan(c.rho[-1])  # lag = +40

    def test_fisher_and_plain_agree_on_lag(self):
        rng = np.random.default_rng(4)
        n = 500
        x = rng.normal(size=n)
        y = 0.3 * np.roll(x, 5) + 0.7 * rng.normal(size=n)
        c_f = lagged_cc(x, y, max_lag=15, fisher=True)
        c_p = lagged_cc(x, y, max_lag=15, fisher=False)
        assert c_f.lag_max == c_p.lag_max == 5


# ================================================================== #
#                        null models                                 #
# ================================================================== #

class TestBlockBootstrap:
    """P0-1, P1-1: block bootstrap must not degenerate."""

    def test_huge_block_size_does_not_copy_input(self):
        rng = np.random.default_rng(0)
        y = rng.normal(size=200)
        y_s = _block_bootstrap(y, rng, block_size=200)
        assert not np.array_equal(y, y_s), \
            "block bootstrap returned a copy of the original"

    def test_huge_block_size_repeatedly_differs(self):
        """Even with bs >= n, every draw must differ (probabilistically)."""
        rng = np.random.default_rng(1)
        y = rng.normal(size=100)
        diffs = sum(
            not np.array_equal(y, _block_bootstrap(y, rng, block_size=100))
            for _ in range(20)
        )
        assert diffs >= 19

    def test_default_block_size_applied(self):
        """P1-1: block_size=None uses n**(1/3) internally."""
        rng = np.random.default_rng(2)
        y = rng.normal(size=1000)
        y_s = _block_bootstrap(y, rng, block_size=None)
        assert y_s.shape == y.shape
        assert not np.array_equal(y, y_s)

    def test_cap_at_n_over_4(self):
        """Block size is capped so at least 4 blocks are used."""
        rng = np.random.default_rng(3)
        y = rng.normal(size=8)  # n//4 = 2
        y_s = _block_bootstrap(y, rng, block_size=8)
        assert len(y_s) == 8

    def test_tiny_input(self):
        rng = np.random.default_rng(4)
        y = np.array([1.0, 2.0])
        y_s = _block_bootstrap(y, rng, block_size=2)
        assert np.array_equal(y, y_s)  # n<4 -> return copy


class TestOtherNullModels:
    def test_phase_preserves_spectrum(self):
        rng = np.random.default_rng(0)
        y = rng.normal(size=512)
        y_s = _phase_randomize(y, rng)
        sp_o = np.abs(np.fft.rfft(y - y.mean()))
        sp_n = np.abs(np.fft.rfft(y_s - y_s.mean()))
        assert_allclose(sp_o, sp_n, atol=1e-8)

    def test_phase_preserves_length(self):
        rng = np.random.default_rng(1)
        y = rng.normal(size=333)
        assert len(_phase_randomize(y, rng)) == 333

    def test_iaaft_preserves_distribution(self):
        rng = np.random.default_rng(2)
        y = rng.exponential(size=500)
        y_s = _iaaft(y, rng, n_iter=30)
        assert_allclose(np.sort(y), np.sort(y_s), atol=1e-9)

    def test_time_shift_differs(self):
        rng = np.random.default_rng(3)
        y = np.arange(100, dtype=float)
        y_s = _time_shift(y, rng)
        assert not np.array_equal(y, y_s)
        assert np.array_equal(np.sort(y), np.sort(y_s))

    def test_time_shift_min_shift_respected(self):
        """P2: small shifts should be excluded."""
        rng = np.random.default_rng(4)
        y = np.arange(100, dtype=float)
        y_s = _time_shift(y, rng, min_shift=10)
        # circular shift by >= 10 => first element moved by at least 10
        # so y_s[0] != y[0] with high probability
        assert y_s[0] != y[0]


class TestMakeNull:
    def test_defaults_filled_for_block(self):
        """P1-1: make_null fills block_size from n."""
        fn = make_null("block", n=1000)
        y = np.random.default_rng(0).normal(size=1000)   # ← size= добавлен
        out = fn(y, np.random.default_rng(1))
        assert len(out) == 1000
        assert not np.array_equal(out, y)

    def test_unknown_model_raises(self):
        with pytest.raises(NullModelError):
            make_null("nonsense", n=100)

    def test_bad_kwargs_raises(self):
        """P1-1: bad kwargs surface as NullModelError, not TypeError."""
        fn = make_null("block", n=100, wrong_kwarg=10)
        with pytest.raises(NullModelError):
            fn(np.ones(100), np.random.default_rng(0))

    def test_no_n_no_kwargs_returns_raw(self):
        fn = make_null("time_shift")
        assert fn is NULL_MODELS["time_shift"]


# ================================================================== #
#                        p-value                                     #
# ================================================================== #

class TestEmpiricalPvalue:
    def test_extreme_observed(self):
        null = np.random.default_rng(0).normal(size=1000)
        assert empirical_pvalue(1e9, null) == pytest.approx(1.0 / 1001)
        assert empirical_pvalue(-1e9, null) == 1.0

    def test_empty_null(self):
        assert empirical_pvalue(0.0, np.array([])) == 1.0


# ================================================================== #
#                        FDR — P1-2                                  #
# ================================================================== #

class TestFDR:
    def test_all_equal(self):
        p = np.array([0.001] * 10)
        q = fdr_bh(p)
        assert_allclose(q, p)

    def test_q_at_least_p(self):
        rng = np.random.default_rng(0)
        p = rng.uniform(0, 1, 100)
        q = fdr_bh(p)
        assert np.all(q >= p - 1e-12)

    def test_nan_propagates(self):
        """P1-2: NaN in p -> NaN in q, others untouched."""
        p = np.array([0.01, 0.02, np.nan, 0.03])
        q = fdr_bh(p)
        assert np.isnan(q[2])
        assert np.isfinite(q[0])
        assert np.isfinite(q[1])
        assert np.isfinite(q[3])

    def test_all_nan(self):
        q = fdr_bh(np.array([np.nan, np.nan]))
        assert np.all(np.isnan(q))

    def test_empty(self):
        assert len(fdr_bh([])) == 0

    def test_monotone_in_p_order(self):
        rng = np.random.default_rng(1)
        p = rng.uniform(0, 1, 100)
        q = fdr_bh(p)
        order = np.argsort(p)
        assert np.all(np.diff(q[order]) >= -1e-12)


# ================================================================== #
#                        RNG — P1-3                                  #
# ================================================================== #

class TestRNG:
    def test_spawn_independent_streams(self):
        rng = np.random.default_rng(0)
        children = _spawn(rng, 5)
        assert len(children) == 5
        samples = [c.normal(size=10) for c in children]
        for i in range(5):
            for j in range(i + 1, 5):
                assert not np.array_equal(samples[i], samples[j])

    def test_analyze_all_pairs_deterministic(self):
        rng = np.random.default_rng(0)
        dets = [Detector(f"D{i}", "t", rng.normal(size=300))
                for i in range(4)]
        r1 = analyze_all_pairs(dets, max_lag=10, n_surrogates=30, seed=7)
        r2 = analyze_all_pairs(dets, max_lag=10, n_surrogates=30, seed=7)
        for a, b in zip(r1, r2):
            assert a.detector_1 == b.detector_1
            assert a.detector_2 == b.detector_2
            assert a.p_value == b.p_value

    def test_analyze_pair_no_rng_isolated(self):
        """P1-3: analyze_pair without rng must not require external state."""
        rng = np.random.default_rng(0)
        d1 = Detector("A", "t", rng.normal(size=500))
        d2 = Detector("B", "t", rng.normal(size=500))
        r1 = analyze_pair(d1, d2, max_lag=10, n_surrogates=30)
        r2 = analyze_pair(d1, d2, max_lag=10, n_surrogates=30)
        assert isinstance(r1, PairResult)
        assert isinstance(r2, PairResult)


# ================================================================== #
#                        pair analysis — P1-4                        #
# ================================================================== #

class TestAnalyzePair:
    def test_detects_lag_with_preprocessing(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=500)
        y = np.roll(x, 6) + 0.1 * rng.normal(size=500)
        d1 = Detector("A", "t", x)
        d2 = Detector("B", "t", y)
        r = analyze_pair(d1, d2, max_lag=12, n_surrogates=50)
        assert r.lag_max == 6
        assert r.rho_max > 0.5

    def test_apply_preprocessing_flag(self):
        """P1-4: raw path skips preprocess; both should still find lag."""
        rng = np.random.default_rng(1)
        x = rng.normal(size=500)
        y = np.roll(x, 6) + 0.1 * rng.normal(size=500)
        d1 = Detector("A", "t", x)
        d2 = Detector("B", "t", y)
        rp = analyze_pair(d1, d2, max_lag=12, n_surrogates=50,
                          apply_preprocessing=True)
        rr = analyze_pair(d1, d2, max_lag=12, n_surrogates=50,
                          apply_preprocessing=False)
        assert rp.lag_max == 6
        assert rr.lag_max == 6


# ================================================================== #
#                        P0-2: randomize_both                        #
# ================================================================== #

class TestRandomizeBoth:
    def test_randomize_both_changes_null(self):
        """P0-2: with autocorrelated series, the two nulls differ."""
        rng = np.random.default_rng(0)

        def ar1(n, phi=0.9, sigma=1.0):
            e = rng.normal(0, sigma, size=n)
            out = np.zeros(n)
            for t in range(1, n):
                out[t] = phi * out[t - 1] + e[t]
            return out

        x = preprocess(ar1(1000))
        y = preprocess(ar1(1000))
        fn = make_null("phase", n=1000)

        null_1 = null_max_distribution(
            x, y, max_lag=10, null_fn=fn, n_surrogates=100,
            rng=np.random.default_rng(1), randomize_both=False,
        )
        null_2 = null_max_distribution(
            x, y, max_lag=10, null_fn=fn, n_surrogates=100,
            rng=np.random.default_rng(1), randomize_both=True,
        )
        assert not np.allclose(null_1, null_2)

    def test_randomize_both_default_is_true(self):
        """The default should be conservative."""
        import inspect
        sig = inspect.signature(null_max_distribution)
        assert sig.parameters["randomize_both"].default is True


# ================================================================== #
#                        robustness                                  #
# ================================================================== #

class TestRobustness:
    def test_windowed_stability_short_series(self):
        rng = np.random.default_rng(0)
        res = windowed_stability(rng.normal(size=50),
                                 rng.normal(size=50),
                                 max_lag=5, n_windows=4)
        assert "n_windows_used" in res

    def test_windowed_stability_consistent(self):
        rng = np.random.default_rng(1)
        n = 3000
        x = rng.normal(size=n)
        y = np.roll(x, 6) + 0.1 * rng.normal(size=n)
        res = windowed_stability(x, y, max_lag=15, n_windows=6)
        assert res["n_windows_used"] >= 4
        assert abs(res["lag_median"] - 6) <= 2
        assert res["rho_sign_consistency"] == 1.0

    def test_distance_dependence_null(self):
        rng = np.random.default_rng(2)
        d = rng.uniform(0, 100, 50)
        rho = rng.normal(0, 0.1, 50)
        res = distance_dependence(d, rho, n_perm=500, rng=rng)
        assert res["p_value"] > 0.05

    def test_distance_dependence_signal(self):
        rng = np.random.default_rng(3)
        d = np.linspace(0, 100, 50)
        rho = 0.5 - 0.005 * d + rng.normal(0, 0.02, 50)
        res = distance_dependence(d, rho, n_perm=500, rng=rng)
        assert res["p_value"] < 0.05


# ================================================================== #
#                        synthetic & benchmark                       #
# ================================================================== #

class TestSynthetic:
    def test_shape(self):
        x, y = synthetic_ar1_pair(n=1000, true_lag=6, coupling=0.5, seed=0)
        assert len(x) == len(y) == 1000

    def test_deterministic(self):
        x1, y1 = synthetic_ar1_pair(n=100, seed=42)
        x2, y2 = synthetic_ar1_pair(n=100, seed=42)
        assert_allclose(x1, x2)
        assert_allclose(y1, y2)

    def test_benchmark_detects_strong_signal(self):
        r = benchmark(coupling=0.4, n=4000, n_surrogates=100, seed=0)
        assert r["hit"] is True
        assert r["detected_lag"] == 6


class TestBenchmarkRegression:
    def test_noise_not_detected(self):
        hits = [
            benchmark(coupling=0.0, n=2000, n_surrogates=100, seed=s)["hit"]
            for s in range(10)
        ]
        assert np.mean(hits) <= 0.3

    def test_power_increases_with_coupling(self):
        hits_low = [
            benchmark(coupling=0.01, n=3000, n_surrogates=100, seed=s)["hit"]
            for s in range(10)
        ]
        hits_high = [
            benchmark(coupling=0.35, n=3000, n_surrogates=100, seed=s)["hit"]
            for s in range(10)
        ]
        assert np.mean(hits_high) > np.mean(hits_low)
        assert np.mean(hits_high) >= 0.8