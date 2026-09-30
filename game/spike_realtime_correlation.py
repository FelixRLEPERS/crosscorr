"""Спайк v2: три метрики кросс-корреляции в реальном времени.

Что нового по сравнению с v1:
- BUFFER 40 → 200 (короткое окно давало ложные пики ~0.8 даже без связи)
- сигналы — случайные блуждания, а не детерминированные синусоиды
  (синусоиды на коротком окне «сами коррелируют» — это артефакт, не сигнал)
- три метрики: corr@lag0, max|corr|, sharpness

Запуск:
    python -m game.spike_realtime_correlation
"""
from __future__ import annotations

import time

import numpy as np

from crosscorr_lib.analysis.cross_correlation import lagged_cross_correlation

BUFFER = 200       # 10 сек при 20 Гц — окно достаточно длинное
MAX_LAG = 20
TICK_HZ = 20
DURATION_S = 20
SMOOTH = 0.7       # AR(1)-коэффициент для «датчиков»


class SensorState:
    """Состояние двух «датчиков» со связанным и раздельными компонентами."""

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.common = 0.0      # общий сигнал (виден обоим при coupling=1)
        self.ind_a = 0.0       # независимый шум датчика A
        self.ind_b = 0.0       # независимый шум датчика B

    def step(self, coupling: float) -> tuple[float, float]:
        r = self.rng.normal(0.0, 1.0)
        self.common = SMOOTH * self.common + (1.0 - SMOOTH) * r
        self.ind_a = SMOOTH * self.ind_a + (1.0 - SMOOTH) * self.rng.normal(0.0, 1.0)
        self.ind_b = SMOOTH * self.ind_b + (1.0 - SMOOTH) * self.rng.normal(0.0, 1.0)

        a = coupling * self.common + (1.0 - coupling) * self.ind_a
        b = coupling * self.common + (1.0 - coupling) * self.ind_b
        return float(a), float(b)


def coupling_schedule(t: float) -> float:
    """0 → 1 → 0 за 20 секунд."""
    if t < 5.0:
        return 0.0
    if t < 10.0:
        return (t - 5.0) / 5.0
    if t < 15.0:
        return 1.0
    return max(0.0, 1.0 - (t - 15.0) / 5.0)


def main() -> None:
    rng = np.random.default_rng(42)
    sensor = SensorState(rng)
    buf_a: list[float] = []
    buf_b: list[float] = []

    ticks = int(TICK_HZ * DURATION_S)
    for tick in range(ticks):
        t = tick / TICK_HZ
        c = coupling_schedule(t)

        a, b = sensor.step(c)
        buf_a.append(a)
        buf_b.append(b)

        if len(buf_a) >= BUFFER and tick % 5 == 0:
            arr_a = np.array(buf_a[-BUFFER:])
            arr_b = np.array(buf_b[-BUFFER:])
            lags, corrs, _p = lagged_cross_correlation(arr_a, arr_b, max_lag=MAX_LAG)

            # lag=0 живёт на индексе max_lag (lags идут от -MAX_LAG до +MAX_LAG)
            idx0 = MAX_LAG
            corr0 = float(corrs[idx0])

            abs_corrs = np.abs(corrs)
            imax = int(np.argmax(abs_corrs))
            max_corr = float(abs_corrs[imax])
            peak_lag = int(lags[imax])
            sharpness = max_corr - float(np.median(abs_corrs))

            bar0 = "#" * int(abs(corr0) * 20)
            barS = "=" * int(sharpness * 20)

            print(
                f"t={t:5.1f}s  c={c:.2f}  "
                f"|r0|={abs(corr0):.3f} {bar0:<20}  "
                f"|max|={max_corr:.3f}@lag{peak_lag:+d}  "
                f"sharp={sharpness:.3f} {barS}"
            )

        time.sleep(1.0 / TICK_HZ)


if __name__ == "__main__":
    main()