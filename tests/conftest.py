"""Общие фикстуры pytest для набора тестов CrossCorr.

Здесь только новые, повторно используемые фикстуры. Существующие
тесты сохраняют свои локальные фикстуры без изменений.
"""

import numpy as np
import pytest


@pytest.fixture
def rng():
    """Детерминированный генератор с фиксированным seed."""
    return np.random.default_rng(1234)
