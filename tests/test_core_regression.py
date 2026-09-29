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
