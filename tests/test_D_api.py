"""Tests for group D: public API contract.

Checks imports and __all__ consistency. No heavy computation.
"""

import pytest


def test_public_api_imports():
    """Все имена из __all__ импортируются."""
    import crosscorr_lib

    for name in crosscorr_lib.__all__:
        assert hasattr(crosscorr_lib, name), (
            f"{name} in __all__ but not in module"
        )


def test_no_private_in_all():
    """В __all__ нет приватных имён."""
    import crosscorr_lib

    for name in crosscorr_lib.__all__:
        assert not name.startswith("_"), f"private {name} in __all__"


def test_analysis_init_all_matches():
    """analysis.__all__ — все имена существуют."""
    import crosscorr_lib.analysis as a

    if not hasattr(a, "__all__"):
        return
    for name in a.__all__:
        assert hasattr(a, name), (
            f"{name} in analysis.__all__ but not in module"
        )


def test_analysis_all_has_preprocess():
    import crosscorr_lib.analysis as a

    assert "preprocess" in a.__all__
    assert callable(a.preprocess)


def test_safe_exec_public():
    """safe_exec.run_code_safe импортируется."""
    from crosscorr_lib import safe_exec

    assert hasattr(safe_exec, "run_code_safe")


def test_pairs_module_accessible():
    """crosscorr_lib.pairs доступен."""
    from crosscorr_lib import pairs

    assert hasattr(pairs, "cross_correlation_pairs_with_max_stat")


def test_two_pipelines_are_distinct():
    """Две функции с одним именем различаются контрактом."""
    import crosscorr_lib
    from crosscorr_lib import pairs

    assert (
        crosscorr_lib.cross_correlation_pairs_with_max_stat
        is not pairs.cross_correlation_pairs_with_max_stat
    )


def test_fdr_functions_exported():
    """fdr_bh и fdr_bh_q экспортируются."""
    from crosscorr_lib import fdr_bh, fdr_bh_q

    assert callable(fdr_bh)
    assert callable(fdr_bh_q)


def test_core_pipeline_functions_exported():
    """Основные pipeline функции экспортируются."""
    from crosscorr_lib import (
        cross_correlation_pairs_with_max_stat,
        lagged_cross_correlation,
    )

    assert callable(cross_correlation_pairs_with_max_stat)
    assert callable(lagged_cross_correlation)


def test_preprocess_accessible():
    """preprocess доступен."""
    try:
        from crosscorr_lib.analysis.preprocessing import preprocess
    except ImportError:
        pytest.fail("preprocess module not importable")
    assert callable(preprocess)
