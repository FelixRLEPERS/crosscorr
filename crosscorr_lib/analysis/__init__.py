"""Публичный реэкспорт модулей analysis.

Реэкспортируются только те символы, что нужны потребителям верхнего
уровня. Полный набор модулей доступен как
``crosscorr_lib.analysis.<module>``.
"""

from .preprocessing import preprocess
from .surrogate import fdr_bh, max_lag_surrogate_pvalue

__all__ = [
    "fdr_bh",
    "max_lag_surrogate_pvalue",
    "preprocess",
]
