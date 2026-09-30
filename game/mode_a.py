"""Режим A: 'Симулятор'. Игрок ползунком управляет связью двух датчиков.

Управление:
    A / D  или  ←/→   — coupling вниз/вверх
    W / S             — размер окна детектора
    R                 — начать заново
    Q                 — выход

Запуск:
    python -m game.mode_a
"""
from __future__ import annotations

import os
import time

import numpy as np

from crosscorr_lib.analysis.cross_correlation import lagged_cross_correlation
from game.state import GameState, default_levels

TICK_HZ = 20
SMOOTH = 0.7
MAX_LAG = 20
DEFAULT_BUFFER = 120
MIN_BUFFER = 40
MAX_BUFFER = 240


class SensorState:
    """Состояние двух «датчиков» со связанным и раздельными компонентами."""

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.common = 0.0
        self.ind_a = 0.0
        self.ind_b = 0.0

    def step(self, coupling: float) -> tuple[float, float]:
        r = self.rng.normal(0.0, 1.0)
        self.common = SMOOTH * self.common + (1 - SMOOTH) * r
        self.ind_a = SMOOTH * self.ind_a + (1 - SMOOTH) * self.rng.normal()
        self.ind_b = SMOOTH * self.ind_b + (1 - SMOOTH) * self.rng.normal()
        a = coupling * self.common + (1 - coupling) * self.ind_a
        b = coupling * self.common + (1 - coupling) * self.ind_b
        return float(a), float(b)


def _try_input() -> tuple[float, float, bool, bool]:
    """Неблокирующее чтение клавиш через msvcrt (Windows).

    Возвращает (d_coupling, d_buffer, quit, restart).
    """
    try:
        import msvcrt
    except ImportError:
        return 0.0, 0.0, False, False

    d_c = 0.0
    d_buf = 0.0
    quit_ = False
    restart = False

    while msvcrt.kbhit():
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch().lower()
            if ch2 == "k":      # стрелка влево
                d_c = -0.02
            elif ch2 == "m":    # стрелка вправо
                d_c = +0.02
            continue

        ch = ch.lower()
        if ch == "a":
            d_c = -0.02
        elif ch == "d":
            d_c = +0.02
        elif ch == "w":
            d_buf = +10.0
        elif ch == "s":
            d_buf = -10.0
        elif ch == "q":
            quit_ = True
        elif ch == "r":
            restart = True

    return d_c, d_buf, quit_, restart


def _event_tag(event: str) -> str:
    return {
        "hold":     "держим",
        "miss":     "тает",
        "level_up": "УРОВЕНЬ ПРОЙДЕН!",
        "win":      "ПОБЕДА!",
        "done":     "партия окончена",
    }.get(event, "")


def _render(
    t: float,
    coupling: float,
    buffer_size: int,
    corr0: float,
    sharpness: float,
    state: GameState,
    event: str,
) -> None:
    os.system("cls" if os.name == "nt" else "clear")

    lvl = state.active_level
    print("=" * 62)
    print(f"  Режим A — Симулятор   |   Уровень {state.current + 1}/{len(state.levels)}: {lvl.name}")
    print("=" * 62)
    print(f"  {lvl.description}")
    print(f"  Цель: |r| >= {lvl.target_corr:.2f}  удержать {lvl.hold_seconds:.1f} с")
    print()
    print(f"  t = {t:5.1f}s    очки = {state.score}")
    print()
    print(f"  coupling  = {coupling:5.2f}   (A/D)")
    print(f"  окно      = {buffer_size:4d}   (W/S) — как долго помнит детектор")
    print()

    bar_len = 40
    filled = int(min(abs(corr0), 1.0) * bar_len)
    hit = abs(corr0) >= lvl.target_corr
    marker = "#" if hit else "-"
    print(f"  |r@lag0|  = {abs(corr0):.3f}  [{marker * filled}{' ' * (bar_len - filled)}]")
    print(f"  sharpness = {sharpness:.3f}")
    print()

    prog_len = 30
    prog = int(min(state.hold_progress / lvl.hold_seconds, 1.0) * prog_len)
    print(f"  удержание [{('=' * prog)}{' ' * (prog_len - prog)}] "
          f"{state.hold_progress:.1f}/{lvl.hold_seconds:.1f}с   {_event_tag(event)}")
    print()

    if state.finished:
        print("  " + "*" * 58)
        print(f"  *** ПОБЕДА! Финальный счёт: {state.score} ***".center(60))
        print("  " + "*" * 58)
        print()

    print("  Управление: A/D coupling, W/S окно, R заново, Q выход")


def main() -> None:
    rng = np.random.default_rng(42)
    sensor = SensorState(rng)
    state = GameState(levels=default_levels())

    coupling = 0.0
    buffer_size = DEFAULT_BUFFER
    buf_a: list[float] = []
    buf_b: list[float] = []

    tick = 0
    last_t = time.perf_counter()

    while True:
        now = time.perf_counter()
        dt = now - last_t
        last_t = now

        d_c, d_buf, quit_, restart = _try_input()

        if quit_:
            print("\nВыход.")
            return

        if restart:
            state = GameState(levels=default_levels())
            coupling = 0.0
            buffer_size = DEFAULT_BUFFER
            buf_a.clear()
            buf_b.clear()

        # после победы игра «замирает» — ждём только R или Q
        if state.finished:
            if tick % 3 == 0:
                # рисуем замороженный кадр (corr0/sharpness не пересчитываем)
                _render(tick / TICK_HZ, coupling, buffer_size, 0.0, 0.0, state, "done")
            time.sleep(1.0 / TICK_HZ)
            tick += 1
            last_t = time.perf_counter()
            continue

        coupling = float(np.clip(coupling + d_c, 0.0, 1.0))
        buffer_size = int(np.clip(buffer_size + d_buf, MIN_BUFFER, MAX_BUFFER))

        a, b = sensor.step(coupling)
        buf_a.append(a)
        buf_b.append(b)
        if len(buf_a) > MAX_BUFFER * 2:
            buf_a = buf_a[-MAX_BUFFER * 2:]
            buf_b = buf_b[-MAX_BUFFER * 2:]

        corr0 = 0.0
        sharpness = 0.0
        if len(buf_a) >= buffer_size:
            arr_a = np.array(buf_a[-buffer_size:])
            arr_b = np.array(buf_b[-buffer_size:])
            _lags, corrs, _p = lagged_cross_correlation(arr_a, arr_b, max_lag=MAX_LAG)
            corr0 = float(corrs[MAX_LAG])
            abs_corrs = np.abs(corrs)
            sharpness = float(abs_corrs.max() - np.median(abs_corrs))

        event = state.update(corr0, dt)

        if tick % 3 == 0:
            _render(tick / TICK_HZ, coupling, buffer_size, corr0, sharpness, state, event)

        time.sleep(max(0.0, 1.0 / TICK_HZ - (time.perf_counter() - now)))
        tick += 1


if __name__ == "__main__":
    main()