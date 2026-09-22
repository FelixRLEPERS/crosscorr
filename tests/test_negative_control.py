"""
Negative control: FDR на чистом шуме не должен давать ложных срабатываний.

Генерируем N детекторов с независимым AR(1) шумом.
Запускаем полный пайплайн: lagged CC + max-stat + FDR.
Ожидаем 0 значимых пар при alpha=0.05.
"""

import numpy as np
import pandas as pd
import pytest

from crosscorr_lib.analysis.cross_correlation import (
    build_wide_by_detector,
    lagged_cross_correlation,
)
from crosscorr_lib.analysis.surrogate import (
    fdr_bh,
    max_lag_surrogate_pvalue,
)


def _make_noise_wide(n_detectors=10, n_time=500, seed=42):
    """
    Широкая таблица с независимыми AR(1) шумовыми рядами.

    Никакой связи между детекторами не должно быть.
    """
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n_time, freq="1h", tz="UTC")

    data = {}
    for k in range(n_detectors):
        x = np.zeros(n_time)
        for i in range(1, n_time):
            x[i] = 0.5 * x[i - 1] + rng.normal(0, 1)
        data[f"D{k:02d}"] = x

    return pd.DataFrame(data, index=idx)


def test_negative_control_no_false_positives():
    """
    На чистом шуме алгоритм не должен находить значимых пар.

    При alpha=0.05 ожидаем 0 пар (или очень мало).
    """
    wide = _make_noise_wide(n_detectors=10, n_time=500, seed=42)

    # Все пары: max-stat p-value
    cols = wide.columns.tolist()
    rows = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            x = wide[cols[i]].values
            y = wide[cols[j]].values
            t_obs, p, best_lag = max_lag_surrogate_pvalue(
                x, y, max_lag=24, n_surrogates=200, seed=42
            )
            rows.append({
                "detector_1": cols[i],
                "detector_2": cols[j],
                "lag": best_lag,
                "correlation": t_obs,
                "p_value": p,
            })

    df = pd.DataFrame(rows)
    n_pairs = len(df)

    # FDR на всех парах (1D массив p-values)
    sig_mask = fdr_bh(df["p_value"].values, alpha=0.05)
    df["significant"] = sig_mask

    n_significant = int(sig_mask.sum())

    print(f"\nВсего пар: {n_pairs}")
    print(f"Значимых (alpha=0.05): {n_significant}")
    print(f"Минимальный p-value: {df['p_value'].min():.4f}")

    # Главная проверка: на чистом шуме не должно быть
    # систематических ложных срабатываний
    assert n_significant <= 1, (
        f"На чистом шуме найдено {n_significant} значимых пар. "
        f"Ожидали ≤ 1. Это ложные срабатывания."
    )


def test_negative_control_min_p_value_distribution():
    """
    Распределение p-values на шуме должно быть близко к uniform.

    Если алгоритм корректен, ~5% пар имеют p < 0.05.
    Если p-values сдвинуты влево — есть проблема.
    """
    wide = _make_noise_wide(n_detectors=8, n_time=400, seed=123)

    cols = wide.columns.tolist()
    p_values = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            x = wide[cols[i]].values
            y = wide[cols[j]].values
            _, p, _ = max_lag_surrogate_pvalue(
                x, y, max_lag=24, n_surrogates=200, seed=42
            )
            p_values.append(p)

    p_values = np.array(p_values)
    frac_small = np.mean(p_values < 0.05)

    print(f"\nПар: {len(p_values)}")
    print(f"Доля p < 0.05: {frac_small:.3f} (ожидали ~0.05)")

    # Проверка: доля p < 0.05 не должна быть катастрофически большой
    # (для чистого шума ожидаем ~5%, допустим до 20%)
    assert frac_small < 0.20, (
        f"Слишком много p < 0.05: {frac_small:.2%}. "
        f"Похоже на завышение значимости."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])