"""
Тесты stationarity.py (docs/roadmap.md, шаг 3).

Happy-path adf_test/check_stationarity_wide уже покрыт в
tests/test_E_stationarity.py. Здесь — недостающие ветки: исключение из
adfuller, verbose-вывод, CLI main() и guard ``__main__`` (модуль был 48%).
"""

import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import crosscorr_lib.analysis.stationarity as stationarity_module
from crosscorr_lib.analysis.stationarity import (
    adf_test,
    check_stationarity_wide,
)

MODULE_PATH = Path(__file__).resolve().parents[1] / "crosscorr_lib" / "analysis" / "stationarity.py"


def test_adf_test_constant_series_hits_exception_branch():
    """Константный ряд -> adfuller бросает ValueError -> ветка except."""
    result = adf_test(np.ones(50))

    assert "error" in result
    assert "constant" in result["error"].lower()
    assert np.isnan(result["statistic"])
    assert result["p_value"] == 1.0
    assert result["is_stationary"] is False
    assert result["n_obs"] == 50
    assert result["critical_values"] == {}


def test_adf_test_all_nan_returns_degenerate():
    """После удаления NaN не осталось наблюдений -> ранний выход, без падения."""
    result = adf_test(np.full(30, np.nan))

    assert result["n_obs"] == 0
    assert result["p_value"] == 1.0
    assert result["is_stationary"] is False
    assert np.isnan(result["statistic"])


def test_adf_test_counts_only_non_nan():
    """n_obs считается по не-NaN отсчётам, а не по длине входа."""
    x = np.concatenate([np.arange(15, dtype=float), np.full(25, np.nan)])

    result = adf_test(x)

    assert result["n_obs"] == 15  # 15 < 20 -> дегенеративный выход
    assert result["p_value"] == 1.0


def test_check_stationarity_wide_verbose_all_stationary(capsys, rng):
    """verbose=True, все ряды стационарны -> без блока НЕстационарных."""
    wide = pd.DataFrame({"white": rng.normal(size=400)})

    result = check_stationarity_wide(wide, verbose=True)

    out = capsys.readouterr().out
    assert "[ADF] Стационарных: 1/1" in out
    assert "НЕстационарных" not in out
    assert "phase randomization" not in out
    assert len(result) == 1


def test_check_stationarity_wide_verbose_reports_nonstationary(capsys):
    """verbose=True и есть нестационарный -> список + WARN (рекомендация)."""
    wide = pd.DataFrame(
        {
            "white": np.random.default_rng(0).normal(size=400),
            "short": np.concatenate(
                [np.random.default_rng(1).normal(size=10), np.full(390, np.nan)]
            ),  # 10 наблюдений < 20 -> всегда нестационарный
        }
    )

    check_stationarity_wide(wide, verbose=True)

    out = capsys.readouterr().out
    assert "[ADF] Стационарных: 1/2" in out
    assert "[ADF] НЕстационарных: 1" in out
    assert "short" in out
    assert "[WARN] Нестационарные ряды" in out


def test_check_stationarity_wide_verbose_false_prints_nothing(capsys, rng):
    check_stationarity_wide(pd.DataFrame({"white": rng.normal(size=60)}), verbose=False)
    assert capsys.readouterr().out == ""


def _make_parquet(tmp_path: Path) -> Path:
    n = 60
    df = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
            "detector_id": ["A", "B"] * (n // 2),
            "residual": np.random.default_rng(7).normal(size=n),
        }
    )
    path = tmp_path / "unified.parquet"
    df.to_parquet(path, index=False)
    return path


def test_main_cli_end_to_end(tmp_path, monkeypatch, capsys):
    """CLI читает parquet, строит wide и печатает сводку по 2 рядам."""
    parquet = _make_parquet(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["stationarity", "--input", str(parquet), "--freq", "1h", "--alpha", "0.05"],
    )

    stationarity_module.main()

    out = capsys.readouterr().out
    assert "[OK] Проверено 2 рядов" in out
    assert "[ADF] Стационарных" in out


def test_script_entry_point_runs(tmp_path, monkeypatch, capsys):
    """Запуск модуля как скрипта (guard ``__main__``) доходит до main()."""
    parquet = _make_parquet(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["stationarity.py", "--input", str(parquet), "--freq", "1h"],
    )

    runpy.run_path(str(MODULE_PATH), run_name="__main__")

    assert "[OK] Проверено 2 рядов" in capsys.readouterr().out


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
