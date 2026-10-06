"""
CrossCorr: кросс-корреляционный анализ гетерогенных сенсорных данных.

Публичный API:

    from crosscorr_lib import (
        load_unified, build_wide_by_detector,
        lagged_cross_correlation, cross_correlation_pairs,
        pairs,
    )

Две реализации парного анализа
==============================

В проекте есть две функции с одинаковым именем
``cross_correlation_pairs_with_max_stat``:

* ``crosscorr_lib.analysis.cross_correlation.cross_correlation_pairs_with_max_stat``
  — Spearman-корреляция на лагах, суррогаты генерируются на пару; колонки
  ``detector_1, detector_2, lag, correlation, ...``. Экспортируется здесь как
  ``crosscorr_lib.cross_correlation_pairs_with_max_stat``.
* ``crosscorr_lib.pairs.cross_correlation_pairs_with_max_stat``
  — FFT-batch корреляция с shared memory; колонки
  ``detector_a, detector_b, C_obs, ...`` и verdict
  ``INVARIANT / CANDIDATE / NOISE``. Доступна через модуль ``pairs``.

Функции не взаимозаменяемы: различаются статистикой, форматом вывода и FDR.
Переименование одной из них было бы breaking change и не выполнялось.
"""

# Sync with git tag vX.Y.Z (см. audit/STOP_DECISIONS.md, D5)
__version__ = "0.1.0"

# Основной пайплайн.
# ВНИМАНИЕ (D1): cross_correlation_pairs_with_max_stat импортируется из
# analysis.cross_correlation, а не из pairs; у pairs — собственная функция
# с тем же именем и другим контрактом (см. docstring модуля).
from crosscorr_lib.analysis.block_bootstrap import block_bootstrap_pvalue
from crosscorr_lib.analysis.confounders import (
    load_confounders,
    remove_confounders,
)
from crosscorr_lib.analysis.cross_correlation import (
    build_wide_by_detector,
    cross_correlation_pairs,
    cross_correlation_pairs_with_max_stat,
    lagged_cross_correlation,
    load_unified,
)

# Дополнительные методы
from crosscorr_lib.analysis.effective_sample import (
    correlation_pvalue_with_ess,
    effective_sample_size,
)
from crosscorr_lib.analysis.stationarity import adf_test, check_stationarity_wide

# Статистические утилиты
from crosscorr_lib.analysis.surrogate import (
    fdr_bh,
    fdr_bh_q,
    max_lag_surrogate_pvalue,
    phase_surrogate,
    surrogate_test,
)

from . import pairs

__all__ = [
    # Пайплайн
    "load_unified",
    "build_wide_by_detector",
    "lagged_cross_correlation",
    "cross_correlation_pairs",
    "cross_correlation_pairs_with_max_stat",
    # Параллельный shared-memory pipeline
    "pairs",
    # FDR и суррогаты.
    # fdr_bh -> только reject-массив; fdr_bh_q -> (reject, q). Оба используют
    # method="by" (Benjamini-Yekutieli) по умолчанию; "bh" доступен опцией.
    "fdr_bh",
    "fdr_bh_q",
    "max_lag_surrogate_pvalue",
    "phase_surrogate",
    "surrogate_test",
    # ESS, bootstrap, confounders, stationarity
    "effective_sample_size",
    "correlation_pvalue_with_ess",
    "block_bootstrap_pvalue",
    "load_confounders",
    "remove_confounders",
    "adf_test",
    "check_stationarity_wide",
]
