"""Тесты unified-слоя (аудит v2, P0-2).

Модуль: data/scripts/unify_schema.py

Загрузчики теперь пишут сырое наблюдение в ``value``, а ``residual``,
``residual_method`` и ``quality_flag`` проставляет transform-слой
``fit_residuals`` поверх ``crosscorr_lib.analysis.residuals``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.residuals import METHOD_NONE, METHOD_OLS
from data.scripts.unify_schema import (
    UNIFIED_COLUMNS,
    fit_residuals,
    load_confounders_if_present,
    load_horizons,
    load_intermagnet,
    load_wspr,
)


def _wspr_csv(tmp_path: Path, n: int = 50) -> Path:
    path = tmp_path / "wspr.csv"
    pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
        "rx_call": [f"RX{i % 3}" for i in range(n)],
        "tx_call": [f"TX{i % 2}" for i in range(n)],
        "snr": np.linspace(-10.0, 10.0, n),
        "band": ["20m"] * n,
    }).to_csv(path, index=False)
    return path


def _intermagnet_csv(tmp_path: Path, n: int = 50) -> Path:
    path = tmp_path / "ABBR.csv"
    pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
        "X": np.linspace(30000.0, 30100.0, n),
        "Y": np.zeros(n),
        "Z": np.zeros(n),
    }).to_csv(path, index=False)
    return path


def _horizons_csv(tmp_path: Path, n: int = 50) -> Path:
    path = tmp_path / "mars.csv"
    pd.DataFrame({
        "datetime_str": pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
        "r": np.linspace(1.4, 1.6, n),
    }).to_csv(path, index=False)
    return path


def _confounders_csv(tmp_path: Path, n: int = 50) -> Path:
    path = tmp_path / "confounders.csv"
    idx = pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC")
    pd.DataFrame({
        "timestamp_utc": idx,
        "kp": np.linspace(1.0, 5.0, n),
        "dst": np.linspace(-50.0, -10.0, n),
        "f107": np.linspace(100.0, 200.0, n),
    }).to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# D2a — колонка value
# ---------------------------------------------------------------------------
def test_unify_returns_value_column(tmp_path: Path):
    """Загрузчики отдают сырое наблюдение в value."""
    df = load_wspr(_wspr_csv(tmp_path))

    assert "value" in df.columns
    assert df["value"].dtype == np.float64
    assert df["value"].notna().all()
    # value совпадает с исходным SNR
    assert df["value"].iloc[0] == -10.0

    # Магнитометр и эфемериды — тоже в value
    mag = load_intermagnet(_intermagnet_csv(tmp_path))
    assert mag["value"].iloc[0] == 30000.0
    assert mag["detector_type"].unique().tolist() == ["magnetometer"]

    eph = load_horizons(_horizons_csv(tmp_path))
    assert eph["value"].iloc[0] == 1.4
    assert eph["detector_type"].unique().tolist() == ["ephemeris"]


def test_unify_loaders_do_not_set_residual(tmp_path: Path):
    """Загрузчики — тонкие читалки: остаток считает transform-слой."""
    for frame in (
        load_wspr(_wspr_csv(tmp_path)),
        load_intermagnet(_intermagnet_csv(tmp_path)),
        load_horizons(_horizons_csv(tmp_path)),
    ):
        assert "residual" not in frame.columns
        assert "residual_method" not in frame.columns


def test_unify_returns_residual_method(tmp_path: Path):
    """После fit_residuals появляются residual_method и quality_flag."""
    raw = pd.concat(
        [load_wspr(_wspr_csv(tmp_path)), load_intermagnet(_intermagnet_csv(tmp_path))],
        ignore_index=True,
    )

    out = fit_residuals(raw, confounders=None)

    assert "residual_method" in out.columns
    assert out["residual_method"].unique().tolist() == [METHOD_NONE]
    assert "quality_flag" in out.columns
    assert set(out["quality_flag"].unique()) <= {0, 1}


def test_unify_residual_method_ols_with_confounders(tmp_path: Path):
    """С конфаундерами метод становится ols_geomagnetic."""
    raw = load_intermagnet(_intermagnet_csv(tmp_path))
    conf = load_confounders_if_present(_confounders_csv(tmp_path))
    assert conf is not None

    out = fit_residuals(raw, confounders=conf)

    assert out["residual_method"].unique().tolist() == [METHOD_OLS]
    assert out["residual"].notna().all()
    assert not np.allclose(out["residual"].to_numpy(float), out["value"].to_numpy(float))


def test_unify_sets_unit_per_detector_type(tmp_path: Path):
    """unit проставляется по типу детектора."""
    raw = pd.concat(
        [
            load_wspr(_wspr_csv(tmp_path)),
            load_intermagnet(_intermagnet_csv(tmp_path)),
            load_horizons(_horizons_csv(tmp_path)),
        ],
        ignore_index=True,
    )

    out = fit_residuals(raw, confounders=None)

    units = out.groupby("detector_type")["unit"].unique().to_dict()
    assert units["wspr"] == ["dB"]
    assert units["magnetometer"] == ["nT"]
    assert units["ephemeris"] == ["AU"]


# ---------------------------------------------------------------------------
# D2c — существующие колонки сохранены
# ---------------------------------------------------------------------------
def test_unify_preserves_existing_columns(tmp_path: Path):
    """Все поля из UNIFIED_COLUMNS присутствуют и в правильном порядке."""
    raw = pd.concat(
        [load_wspr(_wspr_csv(tmp_path)), load_intermagnet(_intermagnet_csv(tmp_path))],
        ignore_index=True,
    )

    out = fit_residuals(raw, confounders=None)

    assert list(out.columns) == UNIFIED_COLUMNS
    # Ни одно старое поле не потеряно
    for name in ("timestamp_utc", "detector_id", "detector_type", "meta"):
        assert name in out.columns
        assert out[name].notna().all()
    # meta остался json-строкой, как и раньше (находка V2-15, не в этой задаче)
    assert isinstance(out["meta"].iloc[0], str)
    assert "tx" in json.loads(out["meta"].iloc[0])


def test_unify_columns_order_starts_with_timestamp():
    """timestamp_utc первый — потребители полагаются на этот порядок."""
    assert UNIFIED_COLUMNS[0] == "timestamp_utc"
    assert UNIFIED_COLUMNS[1] == "detector_id"
    assert UNIFIED_COLUMNS[2] == "detector_type"
    # Новые поля идут после существующих идентификаторов
    for name in ("value", "residual", "residual_method", "unit", "quality_flag"):
        assert name in UNIFIED_COLUMNS


# ---------------------------------------------------------------------------
# D2d — обратная совместимость
# ---------------------------------------------------------------------------
def test_unify_backward_compat(tmp_path: Path):
    """Потребитель, читающий только timestamp_utc и residual, работает."""
    raw = pd.concat(
        [load_wspr(_wspr_csv(tmp_path)), load_intermagnet(_intermagnet_csv(tmp_path))],
        ignore_index=True,
    )

    out = fit_residuals(raw, confounders=None)

    # Ровно тот контракт, который использует cross_correlation.build_wide_by_detector
    df = out.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["bucket"] = df["timestamp_utc"].dt.floor("1h")
    wide = (
        df.groupby(["detector_id", "bucket"])["residual"]
        .mean()
        .unstack("detector_id")
        .sort_index()
    )
    assert wide.shape[0] > 0
    assert wide.shape[1] == 4  # 3 RX + 1 магнитометр
    assert wide.notna().any().any()


def test_unify_residual_equals_value_without_confounders(tmp_path: Path):
    """Без конфаундеров residual тождественно равен value."""
    raw = load_wspr(_wspr_csv(tmp_path))

    out = fit_residuals(raw, confounders=None)

    np.testing.assert_allclose(
        out["residual"].to_numpy(dtype=float),
        out["value"].to_numpy(dtype=float),
    )


def test_unify_does_not_mutate_input(tmp_path: Path):
    """fit_residuals возвращает новую таблицу, вход не меняется."""
    raw = load_wspr(_wspr_csv(tmp_path))
    before = list(raw.columns)

    fit_residuals(raw, confounders=None)

    assert list(raw.columns) == before
    assert "residual" not in raw.columns


# ---------------------------------------------------------------------------
# Загрузка конфаундеров
# ---------------------------------------------------------------------------
def test_load_confounders_if_present_missing(tmp_path: Path):
    """Отсутствующий файл конфаундеров -> None, а не исключение."""
    assert load_confounders_if_present(tmp_path / "нет_такого.csv") is None


def test_load_confounders_if_present_without_timestamp(tmp_path: Path):
    """Файл без timestamp_utc -> None."""
    path = tmp_path / "broken.csv"
    pd.DataFrame({"kp": [1.0, 2.0]}).to_csv(path, index=False)

    assert load_confounders_if_present(path) is None


def test_load_confounders_if_present_reads(tmp_path: Path):
    """Нормальный файл читается, время приводится к UTC."""
    conf = load_confounders_if_present(_confounders_csv(tmp_path))

    assert conf is not None
    assert len(conf) == 50
    assert pd.api.types.is_datetime64_any_dtype(conf["timestamp_utc"])
    for name in ("kp", "dst", "f107"):
        assert name in conf.columns


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "-s"])
