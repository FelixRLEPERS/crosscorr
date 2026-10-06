"""Benchmarks v5: реальная стоимость новых модулей на N=4000, 10 каналов.

Скрипт только измеряет (не оптимизирует): время через time.perf_counter
и пиковую память через tracemalloc. Каждый замер выполняется в отдельном
процессе с лимитом 60 сек — при превышении замер помечается
"> 60 сек (медленно)" и выполнение продолжается дальше.

Запуск: python -m bench.bench_new_modules
Результаты: bench/results_v5.txt
"""

from __future__ import annotations

import subprocess
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.cross_mfdfa import cross_mfdfa
from crosscorr_lib.analysis.mse import multiscale_entropy
from crosscorr_lib.analysis.mutual_info import mutual_information_matrix
from crosscorr_lib.analysis.transfer_entropy import transfer_entropy_matrix

N_POINTS = 4000
N_CHANNELS = 10
SEED = 42
TIMEOUT_SECONDS = 60.0
RESULTS_PATH = "bench/results_v5.txt"


def make_data() -> pd.DataFrame:
    """10 каналов: 9 случайных + 1 связанный с первым (0.7*x + шум)."""
    rng = np.random.default_rng(SEED)
    channels = {f"ch_{i}": rng.normal(size=N_POINTS) for i in range(1, N_CHANNELS)}
    channels[f"ch_{N_CHANNELS}"] = (
        0.7 * channels["ch_1"] + 0.3 * rng.normal(size=N_POINTS)
    )
    return pd.DataFrame(channels)


_MEASUREMENTS = {
    "mutual_information_matrix": lambda df: mutual_information_matrix(df),
    "transfer_entropy_matrix": lambda df: transfer_entropy_matrix(df),
    "mse": lambda df: multiscale_entropy(df["ch_1"], scales=range(1, 11)),
    "cross_mfdfa (ch1, ch2)": lambda df: cross_mfdfa(df["ch_1"], df["ch_2"]),
    "cross_mfdfa (ch1, ch3)": lambda df: cross_mfdfa(df["ch_1"], df["ch_3"]),
}


def _measure(label: str) -> tuple[float, float]:
    """Замер одного модуля: (время в сек, пиковая память в МБ)."""
    df = make_data()
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = _MEASUREMENTS[label](df)
    t1 = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return t1 - t0, peak / 1024**2


def _runner(label: str) -> None:
    """Входная точка для subprocess: RESULT <secs> <peak_mb>."""
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        secs, peak_mb = _measure(label)
    except Exception as exc:  # pragma: no cover
        print(f"ERROR {label!r}: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"RESULT {secs:.2f} {peak_mb:.1f}")


def _run_measurement(label: str) -> tuple[str, float | None, float | None]:
    """Замер в subprocess с лимитом TIMEOUT_SECONDS."""
    cmd = [sys.executable, "-m", "bench.bench_new_modules", "_runner", label]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        print(f"{label}: > {TIMEOUT_SECONDS:.0f} сек (медленно) — замер прерван")
        return label, None, None
    if proc.returncode != 0:
        print(f"{label}: ошибка: {proc.stderr.strip()}")
        return label, None, None
    tokens = proc.stdout.strip().split()
    if len(tokens) < 3:
        print(f"{label}: неожиданный выход subprocess: {proc.stdout!r}")
        return label, None, None
    secs_str, peak_str = tokens[1], tokens[2]
    return label, float(secs_str), float(peak_str)


def _format_time(secs: float | None) -> str:
    if secs is None:
        return f"> {TIMEOUT_SECONDS:.0f} сек (медленно)"
    return f"{secs:.2f} сек"


def _format_mem(mb: float | None) -> str:
    if mb is None:
        return "не измерено"
    return f"{mb:.1f} МБ"


def _build_report(rows: list[tuple[str, float | None, float | None]]) -> str:
    lines = [f"## Benchmarks v5 — N={N_POINTS}, {N_CHANNELS} каналов", ""]
    for label, secs, peak_mb in rows:
        lines.append(f"### {label}")
        lines.append(f"- Время: {_format_time(secs)}")
        lines.append(f"- Память: {_format_mem(peak_mb)}")
        lines.append("")
    measured = [(label, secs) for label, secs, _ in rows if secs is not None]
    slowest = max(measured, key=lambda p: p[1])
    fastest = min(measured, key=lambda p: p[1])
    lines.append("### Вывод")
    lines.append(f"- Самое медленное: {slowest[0]} ({slowest[1]:.2f} сек)")
    lines.append(f"- Самое быстрое: {fastest[0]} ({fastest[1]:.2f} сек)")
    lines.append(
        "- Память — пиковая, замерена tracemalloc (python-heap) "
        "в отдельном процессе для каждого модуля."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [
        _run_measurement(label)
        for label in _MEASUREMENTS
    ]

    print("| Модуль | Время (сек) | Память (МБ) |")
    print("|---|---:|---:|")
    for label, secs, peak_mb in rows:
        t = ">60 (стоп)" if secs is None else f"{secs:.2f}"
        m = "—" if peak_mb is None else f"{peak_mb:.1f}"
        print(f"| {label} | {t} | {m} |")
    print(f"\nОтчёт: {RESULTS_PATH}")

    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        fh.write(_build_report(rows))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "_runner":
        _runner(sys.argv[2])
        sys.exit(0)
    main()
