"""Tests for crosscorr_lib.pairs — parallel shared-memory pipeline."""
import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat


@pytest.fixture
def noisy_wide():
    rng = np.random.default_rng(1234)
    X = rng.standard_normal((400, 4))
    return pd.DataFrame(X, columns=["a", "b", "c", "d"])


@pytest.fixture
def signal_wide():
    rng = np.random.default_rng(1234)
    T = 400
    common = rng.standard_normal(T) * 0.7
    X = rng.standard_normal((T, 4))
    X[:, 0] += common
    X[:, 3] += common
    return pd.DataFrame(X, columns=["a", "b", "c", "d"])


def test_reproducible_with_same_seed(noisy_wide):
    df1 = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=42, n_jobs=1,
    )
    df2 = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=42, n_jobs=1,
    )
    pd.testing.assert_frame_equal(df1, df2)


def test_different_seeds_give_different_p_values(noisy_wide):
    df1 = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=42, n_jobs=1,
    )
    df2 = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=43, n_jobs=1,
    )
    assert not np.array_equal(df1["p_value"].values, df2["p_value"].values)


def test_parallel_equals_serial(noisy_wide):
    df_serial = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=42, n_jobs=1,
    )
    df_par = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=42, n_jobs=2,
    )
    pd.testing.assert_frame_equal(df_serial, df_par)


def test_shared_signal_gets_low_q_value(signal_wide):
    df = cross_correlation_pairs_with_max_stat(
        signal_wide, B=200, seed=42, n_jobs=1,
    )
    row = df[
        ((df.detector_a == "a") & (df.detector_b == "d"))
        | ((df.detector_a == "d") & (df.detector_b == "a"))
    ].iloc[0]
    assert row["verdict"] in ("INVARIANT", "CANDIDATE"), (
        f"shared signal not detected: q={row['q_value']}"
    )


def test_pure_noise_all_noise(noisy_wide):
    df = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=100, seed=42, n_jobs=1,
    )
    assert (df["verdict"] == "NOISE").all(), df


def test_pair_filter_ab_only(noisy_wide):
    def only_ab(a: str, b: str) -> bool:
        return {a, b} == {"a", "b"}

    df = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=42, n_jobs=1, pair_filter=only_ab,
    )
    assert len(df) == 1
    assert df.iloc[0]["detector_a"] == "a"
    assert df.iloc[0]["detector_b"] == "b"


def test_pair_filter_reject_all_returns_empty(noisy_wide):
    df = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=30, seed=42, n_jobs=1,
        pair_filter=lambda a, b: False,
    )
    assert len(df) == 0
    assert list(df.columns) == [
        "detector_a", "detector_b", "C_obs", "p_value",
        "q_value", "verdict",
    ]


@pytest.mark.parametrize("method", ["shuffle", "phase", "ar"])
def test_all_methods_run(noisy_wide, method):
    df = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=20, seed=42, n_jobs=1, method=method,
    )
    assert not df.empty
    assert set(df.columns) >= {
        "detector_a", "detector_b", "C_obs", "p_value",
        "q_value", "verdict",
    }
    assert (df["p_value"] > 0).all()
    assert (df["p_value"] <= 1).all()


def test_unknown_method_raises(noisy_wide):
    with pytest.raises(ValueError, match="Unknown method"):
        cross_correlation_pairs_with_max_stat(
            noisy_wide, B=10, seed=42, n_jobs=1, method="bogus",
        )


def test_two_sequential_calls_do_not_leak_shm(noisy_wide):
    df1 = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=20, seed=42, n_jobs=2,
    )
    df2 = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=20, seed=42, n_jobs=2,
    )
    pd.testing.assert_frame_equal(df1, df2)


def test_output_columns(noisy_wide):
    df = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=20, seed=42, n_jobs=1,
    )
    assert list(df.columns) == [
        "detector_a", "detector_b", "C_obs", "p_value",
        "q_value", "verdict",
    ]


def test_output_number_of_pairs(noisy_wide):
    """4 detectors -> C(4,2) = 6 pairs."""
    df = cross_correlation_pairs_with_max_stat(
        noisy_wide, B=20, seed=42, n_jobs=1,
    )
    assert len(df) == 6
