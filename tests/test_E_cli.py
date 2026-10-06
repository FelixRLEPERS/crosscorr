"""Группа E — покрытие CLI power_curve.py (E7)."""

import subprocess
import sys

import numpy as np

from crosscorr_lib.analysis.power_curve import make_couplings, parse_args


def test_power_curve_cli_help_exits_zero():
    """CLI power_curve --help завершается с кодом 0."""
    result = subprocess.run(
        [sys.executable, "-m", "crosscorr_lib.analysis.power_curve", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_make_couplings_default_grid():
    """make_couplings(None) → 15 точек от 0.02 до 0.30."""
    couplings = make_couplings(None)
    assert len(couplings) == 15
    np.testing.assert_allclose(couplings[0], 0.02)
    np.testing.assert_allclose(couplings[-1], 0.30)


def test_make_couplings_triple_spec():
    """make_couplings([lo, hi, count]) → linspace с заданным числом точек."""
    couplings = make_couplings([0.1, 0.5, 5])
    assert len(couplings) == 5
    np.testing.assert_allclose(couplings[0], 0.1)
    np.testing.assert_allclose(couplings[-1], 0.5)


def test_parse_args_defaults():
    """parse_args по умолчанию: max_lag=24, null=time_shift, n=4000."""
    args = parse_args([])
    assert args.max_lag == 24
    assert args.null_model == "time_shift"
    assert args.n == 4000
