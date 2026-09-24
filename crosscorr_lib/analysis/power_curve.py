"""
power_curve.py — кривая мощности CrossCorr 2.0.

Измеряет вероятность обнаружения (power) лаговой кросс-корреляции
как функцию:
    - силы связи coupling
    - длины ряда n
    - истинного лага true_lag
    - уровня автокорреляции ar
    - нулевой модели null_model_name

Результат: CSV-таблица + опциональный PNG-график.

Запуск:
    python -u power_curve.py
    python -u power_curve.py --couplings 0.02 0.30 15 --seeds 30 --n 4000
    python -u power_curve.py --by-n --plot
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

from crosscorr_lib.analysis.benchmark_utils import benchmark  # локальный импорт из той же папки


# ------------------------------------------------------------------ #
#                         конфигурация                               #
# ------------------------------------------------------------------ #

@dataclass
class PowerPoint:
    coupling: float
    n_seeds: int
    n: int
    true_lag: int
    ar: float
    max_lag: int
    null_model: str
    n_surrogates: int
    power: float
    lag_median: float
    lag_iqr: float
    rho_median: float
    p_median: float
    p_10: float
    p_90: float
    n_hits: int
    elapsed_s: float


# ------------------------------------------------------------------ #
#                       одна точка кривой                            #
# ------------------------------------------------------------------ #

def measure_point(coupling: float,
                  n_seeds: int = 30,
                  n: int = 4000,
                  true_lag: int = 6,
                  ar: float = 0.85,
                  max_lag: int = 24,
                  null_model_name: str = "time_shift",
                  n_surrogates: int = 200,
                  base_seed: int = 0,
                  verbose: bool = True) -> PowerPoint:
    """
    Прогоняет benchmark() по n_seeds реализациям и возвращает сводку.

    Каждая реализация — свой seed, чтобы получить независимую оценку.
    """
    t0 = time.time()

    hits: list[bool] = []
    lags: list[int] = []
    rhos: list[float] = []
    ps: list[float] = []

    for s in range(n_seeds):
        seed = base_seed + s
        r = benchmark(
            true_lag=true_lag,
            coupling=coupling,
            n=n,
            max_lag=max_lag,
            n_surrogates=n_surrogates,
            null_model_name=null_model_name,
            seed=seed,
        )
        hits.append(bool(r["hit"]))
        lags.append(int(r["detected_lag"]))
        rhos.append(float(r["rho_max"]))
        ps.append(float(r["p_value"]))

    hits_arr = np.asarray(hits, dtype=float)
    lags_arr = np.asarray(lags, dtype=float)
    rhos_arr = np.asarray(rhos, dtype=float)
    ps_arr = np.asarray(ps, dtype=float)

    pt = PowerPoint(
        coupling=float(coupling),
        n_seeds=int(n_seeds),
        n=int(n),
        true_lag=int(true_lag),
        ar=float(ar),
        max_lag=int(max_lag),
        null_model=null_model_name,
        n_surrogates=int(n_surrogates),
        power=float(hits_arr.mean()),
        lag_median=float(np.median(lags_arr)),
        lag_iqr=float(np.percentile(lags_arr, 75) - np.percentile(lags_arr, 25)),
        rho_median=float(np.median(rhos_arr)),
        p_median=float(np.median(ps_arr)),
        p_10=float(np.percentile(ps_arr, 10)),
        p_90=float(np.percentile(ps_arr, 90)),
        n_hits=int(hits_arr.sum()),
        elapsed_s=float(time.time() - t0),
    )

    if verbose:
        print(
            f"  c={pt.coupling:>5.3f}  power={pt.power:>4.2f} "
            f"({pt.n_hits:>2}/{pt.n_seeds})  "
            f"lag_med={pt.lag_median:>5.1f}  "
            f"p_med={pt.p_median:>6.3f}  "
            f"[{pt.elapsed_s:>5.1f}s]",
            flush=True,
        )
    return pt


# ------------------------------------------------------------------ #
#                        основная кривая                             #
# ------------------------------------------------------------------ #

def power_curve(couplings: np.ndarray,
                n_seeds: int = 30,
                n: int = 4000,
                true_lag: int = 6,
                ar: float = 0.85,
                max_lag: int = 24,
                null_model_name: str = "time_shift",
                n_surrogates: int = 200,
                base_seed: int = 0,
                verbose: bool = True) -> list[PowerPoint]:
    """Прогон по всем coupling."""
    if verbose:
        print(f"\n=== Power curve: n={n}, true_lag={true_lag}, "
              f"ar={ar}, max_lag={max_lag}, "
              f"null={null_model_name}, "
              f"n_surrogates={n_surrogates} ===")
    return [
        measure_point(
            coupling=float(c),
            n_seeds=n_seeds,
            n=n,
            true_lag=true_lag,
            ar=ar,
            max_lag=max_lag,
            null_model_name=null_model_name,
            n_surrogates=n_surrogates,
            base_seed=base_seed,
            verbose=verbose,
        )
        for c in couplings
    ]


def power_curve_by_n(n_values: list[int],
                     couplings: np.ndarray,
                     n_seeds: int = 30,
                     true_lag: int = 6,
                     ar: float = 0.85,
                     max_lag: int = 24,
                     null_model_name: str = "time_shift",
                     n_surrogates: int = 200,
                     base_seed: int = 0,
                     verbose: bool = True) -> list[PowerPoint]:
    """Прогон по сетке (n, coupling)."""
    out: list[PowerPoint] = []
    for n in n_values:
        if verbose:
            print(f"\n--- n = {n} ---")
        out.extend(power_curve(
            couplings=couplings,
            n_seeds=n_seeds,
            n=n,
            true_lag=true_lag,
            ar=ar,
            max_lag=max_lag,
            null_model_name=null_model_name,
            n_surrogates=n_surrogates,
            base_seed=base_seed,
            verbose=verbose,
        ))
    return out


# ------------------------------------------------------------------ #
#                     сохранение и вывод                             #
# ------------------------------------------------------------------ #

def save_csv(points: list[PowerPoint], path: Path) -> None:
    if not points:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(points[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in points:
            w.writerow(asdict(p))
    print(f"\nCSV сохранён: {path}")


def save_json(points: list[PowerPoint], path: Path) -> None:
    if not points:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in points], f,
                  ensure_ascii=False, indent=2)
    print(f"JSON сохранён: {path}")


def print_table(points: list[PowerPoint]) -> None:
    print("\n" + "=" * 78)
    print(f"{'coupling':>9} {'n':>7} {'power':>7} {'hits':>7} "
          f"{'lag_med':>8} {'lag_iqr':>8} {'p_med':>7} {'p_10':>7}")
    print("-" * 78)
    for p in points:
        print(f"{p.coupling:>9.3f} {p.n:>7d} {p.power:>7.2f} "
              f"{p.n_hits:>3d}/{p.n_seeds:<3d} "
              f"{p.lag_median:>8.1f} {p.lag_iqr:>8.1f} "
              f"{p.p_median:>7.3f} {p.p_10:>7.3f}")
    print("=" * 78)


# ------------------------------------------------------------------ #
#                           график                                   #
# ------------------------------------------------------------------ #

def plot_curves(points: list[PowerPoint], path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nmatplotlib не установлен — график пропущен.")
        print("Установите: python -m pip install matplotlib")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # группируем по n
    ns = sorted({p.n for p in points})
    for n in ns:
        subset = [p for p in points if p.n == n]
        subset.sort(key=lambda p: p.coupling)
        c = [p.coupling for p in subset]
        pw = [p.power for p in subset]
        pm = [p.p_median for p in subset]
        ax1.plot(c, pw, marker="o", label=f"n={n}")
        ax2.plot(c, pm, marker="s", label=f"n={n}")

    ax1.axhline(0.8, color="grey", linestyle="--", linewidth=0.8)
    ax1.axhline(0.5, color="grey", linestyle=":",  linewidth=0.8)
    ax1.set_xlabel("coupling")
    ax1.set_ylabel("power")
    ax1.set_title("Power vs coupling")
    ax1.set_ylim(-0.02, 1.05)
    ax1.grid(alpha=0.3)
    ax1.legend()

    ax2.axhline(0.05, color="red", linestyle="--", linewidth=0.8,
                label="α=0.05")
    ax2.set_xlabel("coupling")
    ax2.set_ylabel("median p-value")
    ax2.set_title("Median p-value vs coupling")
    ax2.set_yscale("log")
    ax2.grid(alpha=0.3, which="both")
    ax2.legend()

    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f"График сохранён: {path}")


# ------------------------------------------------------------------ #
#                           CLI                                      #
# ------------------------------------------------------------------ #

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="CrossCorr 2.0: power curve benchmark",
    )
    p.add_argument("--couplings", nargs="+", type=float,
                   default=None,
                   help="список coupling или пара (min, max, count). "
                        "По умолчанию: 0.02..0.30, 15 точек")
    p.add_argument("--seeds", type=int, default=30,
                   help="число seeds на точку (default: 30)")
    p.add_argument("--n", type=int, default=4000,
                   help="длина ряда (default: 4000)")
    p.add_argument("--n-list", nargs="+", type=int, default=None,
                   help="сетка длин ряда для --by-n")
    p.add_argument("--by-n", action="store_true",
                   help="прогон по сетке n (использует --n-list)")
    p.add_argument("--true-lag", type=int, default=6)
    p.add_argument("--ar", type=float, default=0.85)
    p.add_argument("--max-lag", type=int, default=24)
    p.add_argument("--null", dest="null_model", default="time_shift",
                   choices=["time_shift", "phase", "iaaft", "block"])
    p.add_argument("--n-surrogates", type=int, default=200)
    p.add_argument("--base-seed", type=int, default=0)
    p.add_argument("--out-dir", type=str, default=".",
                   help="куда сохранить CSV/JSON/PNG")
    p.add_argument("--plot", action="store_true",
                   help="построить график (нужен matplotlib)")
    return p.parse_args(argv)


def make_couplings(arg) -> np.ndarray:
    if arg is None:
        return np.linspace(0.02, 0.30, 15)
    if len(arg) == 1:
        return np.linspace(0.02, arg[0], 10)
    if len(arg) == 3:
        lo, hi, cnt = arg
        return np.linspace(lo, hi, int(cnt))
    return np.asarray(arg, dtype=float)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    couplings = make_couplings(args.couplings)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("CrossCorr 2.0 — power curve")
    print(f"couplings: {len(couplings)} точек от "
          f"{couplings.min():.3f} до {couplings.max():.3f}")
    print(f"seeds/tочка: {args.seeds}  n_surrogates: {args.n_surrogates}")

    if args.by_n:
        n_values = args.n_list or [1000, 2000, 4000, 8000]
        points = power_curve_by_n(
            n_values=n_values,
            couplings=couplings,
            n_seeds=args.seeds,
            true_lag=args.true_lag,
            ar=args.ar,
            max_lag=args.max_lag,
            null_model_name=args.null_model,
            n_surrogates=args.n_surrogates,
            base_seed=args.base_seed,
        )
        tag = "by_n"
    else:
        points = power_curve(
            couplings=couplings,
            n_seeds=args.seeds,
            n=args.n,
            true_lag=args.true_lag,
            ar=args.ar,
            max_lag=args.max_lag,
            null_model_name=args.null_model,
            n_surrogates=args.n_surrogates,
            base_seed=args.base_seed,
        )
        tag = f"n{args.n}"

    print_table(points)

    save_csv(points, out_dir / f"power_curve_{tag}.csv")
    save_json(points, out_dir / f"power_curve_{tag}.json")

    if args.plot:
        plot_curves(points, out_dir / f"power_curve_{tag}.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())