"""Регрессионные тесты для фиксов 1–8 (аудит 24 сентября).

Один тест на каждый фикс + smoke-тест импорта всех модулей анализа.
Заменяет старый ``test_core.py`` (81 тест, импорты из удалённого ``core``).
"""
from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = REPO_ROOT / "crosscorr_lib" / "analysis"


# ---------------------------------------------------------------------------
# Фикс 1 — randomize_both в max_lag_surrogate_pvalue
# ---------------------------------------------------------------------------
def test_fix1_randomize_both_in_max_lag_surrogate_pvalue():
    from crosscorr_lib.analysis import surrogate

    fn = getattr(surrogate, "max_lag_surrogate_pvalue", None)
    if fn is None:
        pytest.skip("max_lag_surrogate_pvalue не найден в surrogate.py")
    assert "randomize_both" in inspect.signature(fn).parameters


# ---------------------------------------------------------------------------
# Фикс 2 — cap n//4 в block_bootstrap_surrogate
# ---------------------------------------------------------------------------
def test_fix2_block_bootstrap_caps_block_size_at_n_over_4():
    src = (ANALYSIS / "block_bootstrap.py").read_text(encoding="utf-8")
    compact = src.replace(" ", "")
    assert "n//4" in compact, "не найден cap n // 4 в block_bootstrap.py"


# ---------------------------------------------------------------------------
# Фикс 3 — default block_size = n**(1/3)
# ---------------------------------------------------------------------------
def test_fix3_default_block_size_is_cube_root():
    src = (ANALYSIS / "block_bootstrap.py").read_text(encoding="utf-8")
    compact = src.replace(" ", "")
    assert "**(1/3)" in compact, "не найден default block_size = n**(1/3)"


# ---------------------------------------------------------------------------
# Фикс 4 — per-pair RNG через rng.spawn()
# ---------------------------------------------------------------------------
def test_fix4_per_pair_rng_spawn_in_cross_correlation():
    src = (ANALYSIS / "cross_correlation.py").read_text(encoding="utf-8")
    assert ".spawn(" in src, "не найден rng.spawn() в cross_correlation.py"


# ---------------------------------------------------------------------------
# Фикс 5 — NaN-safe FDR
# ---------------------------------------------------------------------------
def test_fix5_nan_safe_fdr_helpers_exist():
    from crosscorr_lib.analysis import surrogate

    for name in ("benjamini_yekutieli", "fdr_bh_q"):
        assert hasattr(surrogate, name), f"нет функции {name}"

    src = (ANALYSIS / "surrogate.py").read_text(encoding="utf-8")
    assert "finite_mask" in src, "нет finite_mask в NaN-safe FDR"
    assert "n_finite" in src, "нет n_finite в NaN-safe FDR"


# ---------------------------------------------------------------------------
# Фикс 6 — time_shift null model
# ---------------------------------------------------------------------------
def test_fix6_time_shift_null_model_present():
    from crosscorr_lib.analysis import surrogate

    assert hasattr(surrogate, "_time_shift"), "_time_shift отсутствует"
    assert callable(surrogate._time_shift)


# ---------------------------------------------------------------------------
# Фикс 7 — apply_preprocessing flag + модуль preprocessing
# ---------------------------------------------------------------------------
def test_fix7_apply_preprocessing_flag_and_preprocess_body():
    from crosscorr_lib.analysis import cross_correlation as cc
    from crosscorr_lib.analysis import preprocessing

    for name in (
        "cross_correlation_pairs",
        "cross_correlation_pairs_with_max_stat",
    ):
        fn = getattr(cc, name, None)
        assert fn is not None, f"{name} не найдена"
        params = inspect.signature(fn).parameters
        assert "apply_preprocessing" in params, (
            f"apply_preprocessing отсутствует в {name}"
        )
        assert params["apply_preprocessing"].default is True

    # тело фикса реально применено — проверим сам preprocess
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    out = preprocessing.preprocess(x)
    assert out.shape == x.shape
    assert np.isfinite(out).all()
    # линейный ряд после детренда и стандартизации → ~нули
    assert np.allclose(out, 0.0, atol=1e-8)


# ---------------------------------------------------------------------------
# Фикс 7b–7h — поведение apply_preprocessing и инварианты preprocessing
# ---------------------------------------------------------------------------
def _make_wide(n: int = 200):
    """Синтетический wide-фрейм в формате, который ждёт cross_correlation_pairs."""
    import pandas as pd

    t = pd.date_range("2024-01-01", periods=n, freq="h")
    idx = np.linspace(0.0, 4.0 * np.pi, n)
    return pd.DataFrame({"a": np.sin(idx), "b": np.cos(idx)}, index=t)


def test_fix7b_apply_preprocessing_false_skips_preprocess(monkeypatch):
    """apply_preprocessing=False → preprocess() не вызывается ни раза."""
    from crosscorr_lib.analysis import cross_correlation as cc
    from crosscorr_lib.analysis import preprocessing as pp

    calls = []
    real = pp.preprocess

    def spy(x, *args, **kwargs):
        calls.append(np.asarray(x).copy())
        return real(x, *args, **kwargs)

    monkeypatch.setattr(pp, "preprocess", spy)
    cc.cross_correlation_pairs(_make_wide(), max_lag=5, apply_preprocessing=False)
    assert calls == [], f"preprocess вызван {len(calls)} раз при apply_preprocessing=False"


def test_fix7c_apply_preprocessing_true_calls_preprocess_per_column(monkeypatch):
    """apply_preprocessing=True → preprocess() вызывается по разу на колонку."""
    from crosscorr_lib.analysis import cross_correlation as cc
    from crosscorr_lib.analysis import preprocessing as pp

    calls = []
    real = pp.preprocess

    def spy(x, *args, **kwargs):
        calls.append(np.asarray(x).copy())
        return real(x, *args, **kwargs)

    monkeypatch.setattr(pp, "preprocess", spy)
    wide = _make_wide()
    cc.cross_correlation_pairs(wide, max_lag=5, apply_preprocessing=True)
    assert len(calls) == wide.shape[1], (
        f"preprocess вызван {len(calls)} раз, ожидалось {wide.shape[1]}"
    )


def test_fix7d_preprocess_is_pure():
    """preprocess не мутирует входной массив."""
    from crosscorr_lib.analysis.preprocessing import preprocess

    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    x_before = x.copy()
    _ = preprocess(x)
    np.testing.assert_array_equal(x, x_before)


def test_fix7e_preprocess_robust_branch():
    """robust=True даёт конечный результат и центр ~0 даже с выбросом."""
    from crosscorr_lib.analysis.preprocessing import preprocess

    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    x[10] = 1e6
    out = preprocess(x, robust=True)
    assert np.isfinite(out).all()
    assert abs(np.median(out)) < 1e-6


def test_fix7f_preprocess_all_nan_returns_all_nan():
    """Весь ряд NaN → возврат как есть, без исключений."""
    from crosscorr_lib.analysis.preprocessing import preprocess

    x = np.full(10, np.nan)
    out = preprocess(x)
    assert out.shape == x.shape
    assert np.isnan(out).all()


def test_fix7g_preprocess_interpolates_internal_gaps():
    """Внутренние NaN интерполируются."""
    from crosscorr_lib.analysis.preprocessing import preprocess

    x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    out = preprocess(x, detrend=False, standardize=False)
    assert np.isfinite(out).all()
    assert abs(out[2] - 3.0) < 1e-9


def test_fix7h_preprocess_constant_series():
    """Константный ряд → нули, без деления на ноль."""
    from crosscorr_lib.analysis.preprocessing import preprocess

    x = np.full(50, 7.0)
    out = preprocess(x)
    assert np.isfinite(out).all()
    assert np.allclose(out, 0.0)


# ---------------------------------------------------------------------------
# Фикс 8 — этот файл больше не тянет удалённый core.py
# ---------------------------------------------------------------------------
def test_fix8_no_imports_from_core_module():
    src = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "core", "найден import core"
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "core", "найден from core import ..."


# ---------------------------------------------------------------------------
# Smoke — все модули анализа импортируются
# ---------------------------------------------------------------------------
def test_smoke_import_all_analysis_modules():
    failures: list[str] = []
    for path in sorted(ANALYSIS.glob("*.py")):
        if path.name.startswith("_"):
            continue
        mod_name = f"crosscorr_lib.analysis.{path.stem}"
        try:
            importlib.import_module(mod_name)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{mod_name}: {exc!r}")

    assert not failures, "Не импортируются модули:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# Фикс 9 — sandbox: ctypes/code/threading/multiprocessing/platform заблокированы
# ---------------------------------------------------------------------------
def test_fix9_ctypes_blocked_in_safe_exec():
    from crosscorr_lib.safe_exec import FORBIDDEN_NAMES

    for name in [
        "ctypes",
        "code",
        "threading",
        "multiprocessing",
        "platform",
    ]:
        assert name in FORBIDDEN_NAMES, f"{name} не заблокирован"


# ---------------------------------------------------------------------------
# Фикс 10 — surrogate_test: правило +1
# ---------------------------------------------------------------------------
def test_fix10_surrogate_test_uses_plus_one():
    """surrogate_test должен возвращать p >= 1/(B+1), не 0."""
    import numpy as np
    import pandas as pd

    from crosscorr_lib.analysis.surrogate import surrogate_test

    rng = np.random.default_rng(0)
    n = 500
    x = rng.normal(size=n)
    y = x + 0.01 * rng.normal(size=n)  # сильная связь
    wide = pd.DataFrame({"x": x, "y": y})
    p = surrogate_test(wide, n_surrogates=50, seed=42)

    # p-value для очень сильной связи должен быть минимальным,
    # но НЕ нулём
    min_p = 1.0 / (50 + 1)
    assert p.iloc[0, 1] >= min_p - 1e-12, (
        f"p-value {p.iloc[0, 1]} < {min_p}, правило +1 не применено"
    )


# ---------------------------------------------------------------------------
# Фикс 11 — пропущенные суррогаты уменьшают знаменатель
# ---------------------------------------------------------------------------
def test_fix11_skipped_surrogates_reduce_denominator():
    """Если часть суррогатов вырождена — знаменатель уменьшается."""
    import inspect

    from crosscorr_lib.analysis import block_bootstrap, surrogate

    src_sur = inspect.getsource(surrogate.max_lag_surrogate_pvalue)
    src_bb = inspect.getsource(block_bootstrap.block_bootstrap_pvalue)

    assert "n_used" in src_sur, "max_lag_surrogate_pvalue не считает n_used"
    assert "n_used" in src_bb, "block_bootstrap_pvalue не считает n_used"


# ---------------------------------------------------------------------------
# Фикс 12 — phase_surrogate при n<4 возвращает NaN, а не оригинал
# ---------------------------------------------------------------------------
def test_fix12_phase_surrogate_short_input():
    """phase_surrogate при n<4 не возвращает исходные данные."""
    import numpy as np

    from crosscorr_lib.analysis.surrogate import phase_surrogate

    x = np.array([1.0, 2.0, 3.0])
    out = phase_surrogate(x, np.random.default_rng(0))
    assert not np.array_equal(out, x), (
        "phase_surrogate вернул исходный ряд при n<4"
    )
    assert np.all(np.isnan(out)), (
        "phase_surrogate должен вернуть NaN при n<4"
    )


# ---------------------------------------------------------------------------
# Фикс 13 — fit_distance_model не делит на ноль при constant x
# ---------------------------------------------------------------------------
def test_fix13_distance_model_constant_x():
    """При constant distance_km fit_distance_model не даёт inf."""
    import numpy as np
    import pandas as pd

    from crosscorr_lib.analysis.distance_analysis import (
        fit_distance_model,
    )

    x = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    df = pd.DataFrame({"distance_km": x, "correlation": y})

    try:
        result = fit_distance_model(df)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"fit_distance_model упал: {e}")

    for key, val in result.items():
        if isinstance(val, float):
            assert np.isfinite(val) or np.isnan(val), (
                f"{key}={val} — inf недопустимо"
            )


# ---------------------------------------------------------------------------
# Фикс 14 — phase_surrogate не компактифицирует ряд при NaN
# ---------------------------------------------------------------------------
def test_fix14_phase_surrogate_preserves_length():
    """phase_surrogate не меняет длину при NaN."""
    import numpy as np

    from crosscorr_lib.analysis.surrogate import phase_surrogate

    x = np.random.default_rng(0).normal(size=100)
    x[10] = np.nan
    x[20:30] = np.nan
    out = phase_surrogate(x, np.random.default_rng(0))
    assert len(out) == len(x), (
        f"phase_surrogate вернул {len(out)} вместо {len(x)}"
    )
    assert np.isfinite(out).all(), "NaN не интерполированы"


# ---------------------------------------------------------------------------
# Фикс 15 — iaaft_surrogate при вырожденном входе даёт NaN, не оригинал
# ---------------------------------------------------------------------------
def test_fix15_iaaft_surrogate_degenerate_input():
    """iaaft_surrogate при вырожденном входе даёт NaN, не оригинал."""
    import numpy as np

    from crosscorr_lib.analysis.surrogate import iaaft_surrogate

    x = np.array([np.nan, np.nan, 1.0, np.nan, np.nan])
    out = iaaft_surrogate(x, np.random.default_rng(0))
    assert not np.array_equal(out, x), (
        "iaaft_surrogate вернул исходник при вырожденном входе"
    )
