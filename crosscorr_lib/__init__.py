"""
CrossCorr: кросс-корреляционный анализ гетерогенных сенсорных данных.

Публичный API:

    from crosscorr_lib import (
        load_unified, build_wide_by_detector,
        lagged_cross_correlation, cross_correlation_pairs,
    )
"""

__version__ = "0.1.0"

# Основной пайплайн
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

__all__ = [
    # Пайплайн
    "load_unified",
    "build_wide_by_detector",
    "lagged_cross_correlation",
    "cross_correlation_pairs",
    "cross_correlation_pairs_with_max_stat",
    # FDR и суррогаты
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
