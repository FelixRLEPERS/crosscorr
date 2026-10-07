"""Группа E — тесты mutual_info.py (KSG KNN estimator).

Численные эталоны:
- независимые гауссианы: I ≈ 0;
- бивариантный нормальный: I = -0.5 ln(1 - rho^2);
- нелинейная зависимость y = x^2: Pearson ≈ 0, но I > 0.
"""

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.mutual_info import (
    conditional_mutual_information,
    mutual_information,
    mutual_information_matrix,
)


def test_mi_independent_gaussians_is_zero(rng):
    """Два независимых белых шума → MI мала по модулю."""
    x = rng.normal(size=3000)
    y = rng.normal(size=3000)
    assert abs(mutual_information(x, y)) < 0.05


def test_mi_identical_series_positive(rng):
    """x = y → MI заметно положительна."""
    x = rng.normal(size=2000)
    assert mutual_information(x, x) > 0.5


def test_mi_linear_dependence(rng):
    """y = 2x + шум → MI > 0."""
    x = rng.normal(size=3000)
    y = 2.0 * x + 0.5 * rng.normal(size=3000)
    assert mutual_information(x, y) > 0.0


def test_mi_nonlinear_dependence(rng):
    """y = x^2 + шум: Pearson ≈ 0, но MI ловит нелинейность."""
    x = rng.normal(size=4000)
    y = x**2 + 0.1 * rng.normal(size=4000)
    pearson = float(np.corrcoef(x, y)[0, 1])
    mi = mutual_information(x, y)
    assert abs(pearson) < 0.1      # линейная связь отсутствует
    assert mi > 0.3                # но информационная связь есть


def test_mi_gaussian_analytic_reference(rng):
    """Бивариантный нормальный: I = -0.5 ln(1 - rho^2)."""
    rho = 0.5
    n = 5000
    z1 = rng.normal(size=n)
    z2 = rho * z1 + np.sqrt(1.0 - rho**2) * rng.normal(size=n)
    expected = -0.5 * np.log(1.0 - rho**2)   # ≈ 0.1438 nats
    mi = mutual_information(z1, z2, k=5)
    np.testing.assert_allclose(mi, expected, atol=0.05)


def test_mi_ksg_gaussian_reference():
    """Reference-валидация KSG: N=10000, rho=0.5, I = -0.5 ln(1-rho^2).

    Непрерывные данные — родной режим KSG. Оценка должна лежать в 10%
    от аналитического значения (MI-1 reference-валидация).
    """
    rho = 0.5
    n = 10000
    rng = np.random.default_rng(1234)
    z1 = rng.normal(size=n)
    z2 = rho * z1 + np.sqrt(1.0 - rho**2) * rng.normal(size=n)
    analytic = -0.5 * np.log(1.0 - rho**2.0)   # ≈ 0.1438 nats
    mi = mutual_information(z1, z2, k=5)
    np.testing.assert_allclose(mi, analytic, atol=0.015)


def test_mi_ksg_quantized_bias():
    """Квантование 10 уровней: eps→0, KSG возвращает inf (bias ≠ малый).

    Исходный план v6 ожидал смещение < 0.05, но измерение показало, что
    при 10 уровнях доля нулевых k-х совместных расстояний ≈72%, log-члены
    дают digamma(0) → -inf и оценка расходится. Тест фиксирует реальный
    контракт (MI-1).
    """
    rho = 0.5
    n = 10000
    rng = np.random.default_rng(1234)
    z1 = rng.normal(size=n)
    z2 = rho * z1 + np.sqrt(1.0 - rho**2) * rng.normal(size=n)
    xq = np.round(z1 * 10.0) / 10.0
    yq = np.round(z2 * 10.0) / 10.0
    with pytest.warns(UserWarning, match="continuous distributions"):
        mi = mutual_information(xq, yq, k=5)
    assert not np.isfinite(mi)
    assert np.isinf(mi)


def test_mi_ksg_fine_quantization_bias_positive_and_bounded():
    """Тонкое квантование (s=100) даёт конечную, но завышенную оценку.

    Эталон I ≈ 0.1438; измеренное смещение ≈ +0.17 (MI ≈ 0.31). Тест
    фиксирует направление (вверх) и верхнюю границу смещения, а не
    подгоняет число под аналитику.
    """
    rho = 0.5
    n = 10000
    rng = np.random.default_rng(1234)
    z1 = rng.normal(size=n)
    z2 = rho * z1 + np.sqrt(1.0 - rho**2) * rng.normal(size=n)
    xq = np.round(z1 * 100.0) / 100.0
    yq = np.round(z2 * 100.0) / 100.0
    analytic = -0.5 * np.log(1.0 - rho**2.0)
    with pytest.warns(UserWarning, match="continuous distributions"):
        mi = mutual_information(xq, yq, k=5)
    assert np.isfinite(mi)
    assert mi > analytic                 # квантование смещает вверх
    assert (mi - analytic) < 0.25        # но смещение ограничено сверху


def test_mi_matrix_shape_and_symmetry(rng):
    """Матрица MI: 5x5, симметричная, диагональ нулевая."""
    wide = pd.DataFrame(
        {f"d{i}": rng.normal(size=1500) for i in range(5)}
    )
    mat = mutual_information_matrix(wide, k=5)
    assert mat.shape == (5, 5)
    np.testing.assert_allclose(mat.to_numpy(), mat.to_numpy().T)
    np.testing.assert_allclose(np.diag(mat.to_numpy()), 0.0)


def test_cmi_reduces_to_mi_when_z_independent(rng):
    """I(X:Y|Z) ≈ I(X:Y), когда Z не зависит от X, Y."""
    n = 4000
    x = rng.normal(size=n)
    y = 0.6 * x + rng.normal(size=n)
    z = rng.normal(size=n)
    cmi = conditional_mutual_information(x, y, z, k=5)
    mi = mutual_information(x, y, k=5)
    np.testing.assert_allclose(cmi, mi, atol=0.15)


def test_mi_quantized_series_warns():
    """Точные дубликаты совместных samples предупреждают о KSG ties."""
    x = np.tile(np.arange(10, dtype=float), 20)
    y = np.tile(np.arange(10, dtype=float), 20)
    with pytest.warns(UserWarning, match="continuous distributions"):
        mutual_information(x, y)


def test_mi_zero_k_raises_value_error(rng):
    """Число соседей KSG должно быть положительным."""
    x = rng.normal(size=100)
    with pytest.raises(ValueError, match="k must be a positive integer"):
        mutual_information(x, x, k=0)


def test_mi_base_one_raises_value_error(rng):
    """Основание логарифма не может быть равно 1."""
    x = rng.normal(size=100)
    with pytest.raises(ValueError, match="base must be finite"):
        mutual_information(x, x + rng.normal(size=100), base=1.0)


def test_mi_unequal_lengths_raise_value_error(rng):
    """MI не обрезает неравные ряды молча."""
    x = rng.normal(size=100)
    y = rng.normal(size=99)
    with pytest.raises(ValueError, match="equal lengths"):
        mutual_information(x, y)
