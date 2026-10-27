"""Тесты mfdfa.py (docs/roadmap.md, шаг 3): CLI main() и edge-случаи.

Happy-path mfdfa_spectrum уже покрыт в tests/test_E_mfdfa.py. Здесь —
недостающие ветки main() (61-102, 106) и обработка NaN/константных рядов.

MFDFA — опциональная зависимость; тест пропускается, если не установлена.
"""

import runpy
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("MFDFA")

import crosscorr_lib.analysis.mfdfa as mfdfa_module  # noqa: E402
from crosscorr_lib.analysis.mfdfa import mfdfa_spectrum  # noqa: E402

MODULE_PATH = Path(__file__).resolve().parents[1] / "crosscorr_lib" / "analysis" / "mfdfa.py"


def test_mfdfa_spectrum_drops_nan_then_validates_length():
    """NaN удаляются до проверки min_obs=100: 150 валидных — проходит, 50 — ValueError."""
    good = np.concatenate([np.random.default_rng(1).normal(size=150), np.full(100, np.nan)])
    lag, q, dq = mfdfa_spectrum(good)
    assert dq.shape[0] == len(lag)
    assert np.all(np.isfinite(dq))

    bad = np.concatenate([np.random.default_rng(2).normal(size=50), np.full(100, np.nan)])
    with pytest.raises(ValueError, match="(?i)слишком короткий ряд"):
        mfdfa_spectrum(bad)


def test_mfdfa_spectrum_constant_series_returns_finite():
    """Константный ряд не роняет MFDFA (divide-by-zero уходит в RuntimeWarning)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        lag, q, dq = mfdfa_spectrum(np.ones(200))

    assert dq.shape == (len(lag), len(q))
    assert np.all(np.isfinite(dq))


def _make_parquet(path: Path, rows_per_detector: dict[str, int]) -> Path:
    frames = []
    for i, (det, n) in enumerate(rows_per_detector.items()):
        frames.append(
            pd.DataFrame(
                {
                    "timestamp_utc": pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
                    "detector_id": det,
                    "residual": np.random.default_rng(100 + i).normal(size=n),
                }
            )
        )
    pd.concat(frames).to_parquet(path, index=False)
    return path


def test_main_end_to_end_writes_long_csv(tmp_path, monkeypatch, capsys):
    """main() пишет long-format CSV; короткий детектор уходит в [SKIP]."""
    parquet = _make_parquet(
        tmp_path / "unified.parquet",
        {"good": 150, "short": 30},
    )
    monkeypatch.setattr(mfdfa_module, "DEFAULT_OUT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["mfdfa", "--input", str(parquet)],
    )

    mfdfa_module.main()

    out = capsys.readouterr().out
    assert "[OK] good" in out
    assert "[SKIP] short" in out

    csv = tmp_path / "mfdfa_spectra.csv"
    assert csv.exists()

    rows = pd.read_csv(csv)
    assert list(rows.columns) == ["detector", "lag", "q_index", "dq"]
    assert set(rows["detector"]) == {"good"}
    assert len(rows) == rows["lag"].nunique() * rows["q_index"].nunique()
    assert np.all(np.isfinite(rows["dq"]))


def test_main_all_skipped_writes_nothing(tmp_path, monkeypatch, capsys):
    """Если ни один детектор не прошёл min_obs -> rows пуст, CSV не создаётся."""
    parquet = _make_parquet(tmp_path / "unified.parquet", {"short": 30})
    monkeypatch.setattr(mfdfa_module, "DEFAULT_OUT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["mfdfa", "--input", str(parquet)])

    mfdfa_module.main()

    assert "[WARN] Нет результатов MFDFA." in capsys.readouterr().out
    assert not (tmp_path / "mfdfa_spectra.csv").exists()


def test_script_entry_point_runs_without_side_effects(tmp_path, monkeypatch, capsys):
    """Guard ``__main__`` доходит до main(); короткий вход -> WARN без записи CSV.

    Намеренно берём только короткий детектор: runpy исполняет собственную
    копию модуля с дефолтным DEFAULT_OUT (results/ в репозитории), поэтому
    файл в results/ создаваться не должен.
    """
    parquet = _make_parquet(tmp_path / "unified.parquet", {"short": 30})
    monkeypatch.setattr(
        sys,
        "argv",
        ["mfdfa.py", "--input", str(parquet)],
    )

    runpy.run_path(str(MODULE_PATH), run_name="__main__")

    assert "[WARN] Нет результатов MFDFA." in capsys.readouterr().out
    assert not (mfdfa_module.DEFAULT_OUT / "mfdfa_spectra.csv").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
