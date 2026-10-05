"""Тесты базовых моделей остатков (аудит v2, P0-2).

Модуль: crosscorr_lib/analysis/residuals.py

Проверяются три ветки ``fit_residual_model``:
* ``ballistic``  -> MixedLM ``value ~ charge_temp + mass + (1|range_id)``;
* прочие типы   -> МНК ``value ~ kp + dst + f107``;
* без конфаундеров -> модель не оценивается, ``residual == value``.

Реальных баллистических данных в проекте нет (``data/raw`` пуст, ни один
загрузчик не выдаёт ``detector_type == "ballistic"``), поэтому баллистическая
ветка проверяется только на синтетике, сгенерированной из самой формулы.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.residuals import (
    BALLISTIC_COLUMNS,
    BALLISTIC_FORMULA,
    CONFOUNDER_COLUMNS,
    METHOD_MIXEDLM,
    METHOD_NONE,
    METHOD_OLS,
    QUALITY_MISSING,
    QUALITY_OK,
    RESIDUAL_METHODS,
    detector_unit,
    fit_residual_model,
    quality_flags,
)


# ---------------------------------------------------------------------------
# Вспомогательные фикстуры
# ---------------------------------------------------------------------------
def _ballistic_frame(n_rows: int = 120, n_groups: int = 3, seed: int = 42):
    """Синтетика из формулы MixedLM: value = b0 + b1*temp + b2*mass + u_g + eps."""
    rng = np.random.default_rng(seed)
    per_group = n_rows // n_groups

    rows = []
    for g in range(n_groups):
        u_g = rng.normal(0.0, 5.0)  # случайный эффект полигона
        charge_temp = rng.normal(15.0, 3.0, per_group)
        mass = rng.uniform(0.5, 3.0, per_group)
        value = 20.0 + 2.0 * charge_temp + 4.0 * mass + u_g + rng.normal(0, 0.5, per_group)
        rows.append(pd.DataFrame({
            "timestamp_utc": pd.date_range(
                "2025-01-01", periods=per_group, freq="1h", tz="UTC"
            ),
            "detector_id": f"ball_{g}",
            "detector_type": "ballistic",
            "value": value,
            "charge_temp": charge_temp,
            "mass": mass,
            "range_id": g,
        }))

    return pd.concat(rows, ignore_index=True)


def _confounder_frame(n: int = 200, seed: int = 7):
    """Синтетические Kp/Dst/F10.7 на часовой сетке."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({
        "kp": rng.uniform(0, 9, n),
        "dst": rng.uniform(-200, 20, n),
        "f107": rng.uniform(70, 300, n),
    }, index=idx).reset_index().rename(columns={"index": "timestamp_utc"})


def _geomagnetic_frame(n: int = 200, seed: int = 11):
    """Ряд магнитометра, линейно зависящий от конфаундеров."""
    conf = _confounder_frame(n=n, seed=seed)
    rng = np.random.default_rng(seed + 1)
    value = 30000.0 + 120.0 * conf["kp"] + 0.5 * conf["dst"] + 0.01 * conf["f107"]
    value = value + rng.normal(0, 5.0, n)
    return conf, pd.DataFrame({
        "timestamp_utc": conf["timestamp_utc"],
        "detector_id": "ABBR",
        "detector_type": "magnetometer",
        "value": value,
    })


# ---------------------------------------------------------------------------
# D1a — ballistic MixedLM smoke
# ---------------------------------------------------------------------------
def test_fit_residual_model_ballistic_mixedlm_smoke():
    """MixedLM на синтетике: остаток конечен почти для всех строк."""
    df = _ballistic_frame(n_rows=120, n_groups=3)

    out = fit_residual_model(df, detector_type="ballistic")

    assert "residual" in out.columns
    assert "residual_method" in out.columns
    assert "quality_flag" in out.columns
    assert out["residual_method"].unique().tolist() == [METHOD_MIXEDLM]

    finite = out["residual"].notna()
    assert finite.mean() > 0.9, (
        f"Ожидали конечный остаток почти для всех строк, "
        f"получили {finite.mean():.3f}"
    )
    # Остаток — это шум, а не сигнал: дисперсия мала относительно value
    assert out.loc[finite, "residual"].std() < df["value"].std()
    assert (out["quality_flag"] == QUALITY_OK).mean() > 0.9

    # Исходная таблица не мутирована
    assert "residual" not in df.columns


def test_fit_residual_model_ballistic_keeps_value_column():
    """Колонка value не затирается: остаток считается из неё."""
    df = _ballistic_frame(n_rows=120, n_groups=3)
    original = df["value"].to_numpy(dtype=float).copy()

    out = fit_residual_model(df, detector_type="ballistic")

    np.testing.assert_array_equal(out["value"].to_numpy(dtype=float), original)
    assert out["value"].dtype == np.float64


def test_ballistic_formula_matches_readme():
    """Формула в модуле соответствует README (латиница вместо кириллицы)."""
    assert BALLISTIC_FORMULA == "value ~ charge_temp + mass + (1|range_id)"
    assert set(BALLISTIC_COLUMNS) == {"value", "charge_temp", "mass", "range_id"}


def test_fit_residual_model_ballistic_requires_covariates():
    """Нет колонок формулы -> ValueError, а не молчаливый NaN."""
    df = pd.DataFrame({
        "timestamp_utc": pd.date_range("2025-01-01", periods=10, freq="1h", tz="UTC"),
        "value": np.arange(10, dtype=float),
    })

    with pytest.raises(ValueError, match="charge_temp"):
        fit_residual_model(df, detector_type="ballistic")


# ---------------------------------------------------------------------------
# D1b — OLS geomagnetic
# ---------------------------------------------------------------------------
def test_fit_residual_model_ols_geomagnetic():
    """OLS по Kp/Dst/F10.7: остаток конечен и отличается от value."""
    conf, df = _geomagnetic_frame(n=200)

    out = fit_residual_model(df, detector_type="magnetometer", confounders=conf)

    assert out["residual_method"].unique().tolist() == [METHOD_OLS]
    assert out["residual"].notna().all()

    # Остаток не равен исходному значению
    assert not np.allclose(
        out["residual"].to_numpy(dtype=float),
        out["value"].to_numpy(dtype=float),
    )

    # У дизайна остаток должен быть около нуля
    assert abs(float(out["residual"].mean())) < 1.0

    # Связь с конфаундерами снята: |corr| падает почти до нуля
    before = abs(float(np.corrcoef(out["value"], conf["kp"])[0, 1]))
    after = abs(float(np.corrcoef(out["residual"], conf["kp"])[0, 1]))
    assert after < 0.1, f"После OLS corr(residual, kp)={after:.3f}"
    assert before > 0.5


def test_fit_residual_model_ols_uses_only_available_confounders():
    """Если доступен лишь kp, модель строится только на нём."""
    conf, df = _geomagnetic_frame(n=200)
    conf = conf[["timestamp_utc", "kp"]]

    out = fit_residual_model(df, detector_type="magnetometer", confounders=conf)

    assert out["residual_method"].unique().tolist() == [METHOD_OLS]
    assert out["residual"].notna().any()


def test_fit_residual_model_confounders_without_columns():
    """Конфаундеры без kp/dst/f107 -> ValueError."""
    conf, df = _geomagnetic_frame(n=200)
    broken = conf[["timestamp_utc"]].copy()

    with pytest.raises(ValueError, match="конфаундер"):
        fit_residual_model(df, detector_type="magnetometer", confounders=broken)


def test_fit_residual_model_confounders_without_timestamp():
    """Конфаундеры без timestamp_utc -> ValueError."""
    _, df = _geomagnetic_frame(n=200)
    broken = pd.DataFrame({"kp": [1.0, 2.0, 3.0]})

    with pytest.raises(ValueError, match="timestamp_utc"):
        fit_residual_model(df, detector_type="magnetometer", confounders=broken)


def test_fit_residual_model_confounders_aligned_by_time():
    """Конфаундеры ресемпляются по метке времени строки, а не по порядку."""
    conf, df = _geomagnetic_frame(n=200)
    # Перемешиваем порядок строк конфаундеров и разрываем сетку
    shuffled = conf.sample(frac=1.0, random_state=3).reset_index(drop=True)
    shuffled = shuffled.iloc[::3].reset_index(drop=True)

    out = fit_residual_model(df, detector_type="magnetometer", confounders=shuffled)

    assert out["residual"].notna().any()
    assert out["residual_method"].unique().tolist() == [METHOD_OLS]


# ---------------------------------------------------------------------------
# D1c — без конфаундеров
# ---------------------------------------------------------------------------
def test_fit_residual_model_no_confounders():
    """Без конфаундеров модель не оценивается: residual == value, method = none."""
    _, df = _geomagnetic_frame(n=200)

    out = fit_residual_model(df, detector_type="magnetometer", confounders=None)

    assert out["residual_method"].unique().tolist() == [METHOD_NONE]
    np.testing.assert_allclose(
        out["residual"].to_numpy(dtype=float),
        out["value"].to_numpy(dtype=float),
    )
    assert (out["quality_flag"] == QUALITY_OK).all()
    # Колонка конфаундеров не появилась и не требуется
    for column in CONFOUNDER_COLUMNS:
        assert column not in out.columns


# ---------------------------------------------------------------------------
# D1d — неполные данные
# ---------------------------------------------------------------------------
def test_fit_residual_model_missing_required_columns():
    """Нет колонок value/timestamp_utc -> ValueError."""
    with pytest.raises(ValueError, match="value"):
        fit_residual_model(
            pd.DataFrame({"timestamp_utc": pd.date_range("2025-01-01", periods=3)}),
            detector_type="magnetometer",
        )

    with pytest.raises(ValueError, match="timestamp_utc"):
        fit_residual_model(
            pd.DataFrame({"value": [1.0, 2.0, 3.0]}),
            detector_type="magnetometer",
        )


def test_fit_residual_model_rejects_non_dataframe():
    """Не DataFrame -> ValueError."""
    with pytest.raises(ValueError, match="DataFrame"):
        fit_residual_model([1.0, 2.0, 3.0], detector_type="magnetometer")


def test_fit_residual_model_too_few_obs_falls_back_to_none():
    """Мало строк для МНК -> модель не оценивается, method = none."""
    _, df = _geomagnetic_frame(n=3)
    conf = _confounder_frame(n=3)

    out = fit_residual_model(df, detector_type="magnetometer", confounders=conf)

    assert out["residual_method"].unique().tolist() == [METHOD_NONE]
    np.testing.assert_allclose(
        out["residual"].to_numpy(dtype=float),
        out["value"].to_numpy(dtype=float),
    )


def test_fit_residual_model_nan_values_flagged():
    """NaN в value -> quality_flag = 1, остаток NaN."""
    _, df = _geomagnetic_frame(n=200)
    df.loc[5, "value"] = np.nan

    out = fit_residual_model(df, detector_type="magnetometer")

    assert out["quality_flag"].iloc[5] == QUALITY_MISSING
    assert np.isnan(out["residual"].iloc[5])


# ---------------------------------------------------------------------------
# D1e — quality_flag при неудачном фите
# ---------------------------------------------------------------------------
def test_quality_flag_on_failed_fit():
    """Если MixedLM не сошёлся: residual = NaN, quality_flag = 1."""
    df = _ballistic_frame(n_rows=120, n_groups=3)
    # Колонка группировки становится константой: смешанная модель вырождена
    df["range_id"] = "single_range"

    with pytest.warns(UserWarning, match="mixedlm_ballistic"):
        out = fit_residual_model(df, detector_type="ballistic")

    assert out["residual"].isna().all()
    assert (out["quality_flag"] == QUALITY_MISSING).all()
    assert out["residual_method"].unique().tolist() == [METHOD_MIXEDLM]


def test_quality_flag_on_too_few_ballistic_rows():
    """Слишком мало полных строк для MixedLM -> quality_flag = 1."""
    df = _ballistic_frame(n_rows=6, n_groups=3)  # 6 строк < порога 2*5

    with pytest.warns(UserWarning, match="mixedlm_ballistic"):
        out = fit_residual_model(df, detector_type="ballistic")

    assert out["residual"].isna().all()
    assert (out["quality_flag"] == QUALITY_MISSING).all()


# ---------------------------------------------------------------------------
# Константы схемы
# ---------------------------------------------------------------------------
def test_detector_unit_mapping():
    """Единицы измерения по типу детектора."""
    assert detector_unit("wspr") == "dB"
    assert detector_unit("magnetometer") == "nT"
    assert detector_unit("ephemeris") == "AU"
    assert detector_unit("неизвестный") == "unknown"


def test_residual_methods_match_schema_enum():
    """Значения residual_method совпадают с enum unified_schema.json."""
    assert RESIDUAL_METHODS == ("mixedlm_ballistic", "ols_geomagnetic", "none")


def test_quality_flags_helper():
    """quality_flags: 1 на месте NaN, 0 на конечных значениях."""
    flags = quality_flags(pd.Series([1.0, np.nan, 3.0, None]))
    assert flags.tolist() == [QUALITY_OK, QUALITY_MISSING, QUALITY_OK, QUALITY_MISSING]
    assert flags.dtype == np.int64


def test_detector_units_cover_schema_enum():
    """DETECTOR_UNITS покрывает все 8 типов детектора из enum схемы."""
    import json
    from pathlib import Path

    schema_path = (
        Path(__file__).resolve().parents[1] / "data" / "schema" / "unified_schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    enum = schema["properties"]["detector_type"]["enum"]

    from crosscorr_lib.analysis.residuals import DETECTOR_UNITS

    assert set(enum) == set(DETECTOR_UNITS), (
        f"enum схемы {sorted(enum)} не совпадает с DETECTOR_UNITS {sorted(DETECTOR_UNITS)}"
    )


def test_schema_declares_new_columns():
    """Схема объявляет value, residual, residual_method, unit, quality_flag."""
    import json
    from pathlib import Path

    schema_path = (
        Path(__file__).resolve().parents[1] / "data" / "schema" / "unified_schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    properties = schema["properties"]

    for name in ("timestamp_utc", "detector_id", "detector_type", "meta"):
        assert name in properties, name

    assert properties["value"]["type"] == "number"
    assert properties["residual"]["type"] == "number"
    assert "description" in properties["residual"]
    assert set(properties["residual_method"]["enum"]) == set(RESIDUAL_METHODS)
    assert properties["unit"]["type"] == "string"
    assert properties["quality_flag"]["type"] == "integer"

    # Обратная совместимость: старые потребители читают timestamp_utc/residual
    assert list(schema["properties"])[0] == "timestamp_utc"
    assert set(schema["required"]) == {
        "timestamp_utc", "detector_id", "detector_type", "residual",
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
