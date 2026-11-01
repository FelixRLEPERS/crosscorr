"""
Block-permutation test (paper Section 3.3) — единая реализация.

Раньше эта логика была продублирована в ~10 местах в ``scripts/``;
дублирование породило obs/null-баг (2026-11-01), жил в 10 местах / 9 файлах.
Теперь все production-скрипты вызывают эти функции.

Ключевые инварианты (Q0-audit, Section 3.3):
- obs считается на ТОЙ ЖЕ обрезанной серии ``nb * block_size``, что и
  нулевое распределение (обрезка хвоста, не кратного блоку, до перестановок);
- блоки значений перестановываются, маски состояний (storm/quiet) фиксированы;
- add-one поправка Дэвисона–Хинкли: p = (1 + count) / (1 + n_valid).

RNG: если передан ``rng`` — используется он (важно: скрипты держат один
модульный генератор и исчерпывают его в том же порядке вызовов, что даёт
бит-в-бит воспроизводимость старых чисел). Свежий генератор создаётся из
``seed`` только когда ``rng is None``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

Alternative = Literal["two-sided", "greater", "less"]

__all__ = ["block_permutation_stat", "block_permutation_test"]


def block_permutation_stat(
    values: np.ndarray,
    stat_fn: Callable[[np.ndarray], float],
    block_size: int = 24,
    n_iter: int = 50_000,
    alternative: Alternative = "two-sided",
    add_one: bool = True,
    seed: int = 42,
    rng: np.random.Generator | None = None,
) -> dict[str, float | int | bool] | None:
    """Блочная перестановочная тестовая статистика произвольного вида.

    Ряд ``values`` разбивается на ``n_blocks = len // block_size`` блоков
    длины ``block_size``; блоки перестановываются, статистика ``stat_fn``
    вычисляется на каждом перестановленном ряду. Наблюдаемая статистика
    ``obs = stat_fn(values_trim)`` считается на обрезанной серии — том же
    срезе, что и нулевое распределение (Q0-audit правило).

    Args:
        values: 1D ряд (остатки), без NaN.
        stat_fn: статистика от 1D ряда той же длины, что обрезанный вход.
            Вызывается как ``stat_fn(obs_series)`` и ``stat_fn(permuted)``.
            Нефинитные значения считаются пропуском (как в старом коде).
        block_size: длина блока (24 = 72 ч для 3-часовых эпох).
        n_iter: число перестановок.
        alternative: "two-sided" (по умолчанию, |stat| >= |obs|),
            "greater" (stat >= obs) или "less" (stat <= obs).
        add_one: поправка Дэвисона–Хинкли (True) или голое count/n.
        seed: seed для генератора, если ``rng`` не передан.
        rng: внешний генератор (предпочтительно — модульный RNG скрипта).

    Returns:
        ``{p, obs, n_valid, n_blocks, n_iter, add_one, seed}`` или ``None``,
        если ряд слишком короткий (< 2 блоков) или obs нефинитна.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 1:
        raise ValueError(f"values must be 1D, got shape {values.shape}")
    if block_size < 1:
        raise ValueError(f"block_size must be >= 1, got {block_size}")

    n = values.size
    n_blocks = n // block_size
    if n_blocks < 2:
        return None

    blocks = values[: n_blocks * block_size].reshape(n_blocks, block_size)
    values_trim = values[: n_blocks * block_size]

    obs = float(stat_fn(values_trim))
    if not np.isfinite(obs):
        return None

    if rng is None:
        rng = np.random.default_rng(seed)

    stats: list[float] = []
    for _ in range(n_iter):
        order = rng.permutation(n_blocks)
        rp = blocks[order].ravel()
        stat = float(stat_fn(rp))
        if not np.isfinite(stat):
            continue
        stats.append(stat)

    stat_arr = np.asarray(stats, dtype=float)
    if alternative == "two-sided":
        count = int((np.abs(stat_arr) >= np.abs(obs)).sum())
    elif alternative == "greater":
        int_ok = stat_arr >= obs
        count = int(int_ok.sum())
    else:  # "less"
        count = int((stat_arr <= obs).sum())

    n_valid = int(stat_arr.size)
    if n_valid == 0:
        p = float("nan")
    elif add_one:
        # Add-one (Davison-Hinkley): Monte-Carlo p cannot be exactly 0.
        p = (1 + count) / (1 + n_valid)
    else:
        p = count / n_valid

    return {
        "p": float(p),
        "obs": obs,
        "n_valid": n_valid,
        "n_blocks": int(n_blocks),
        "n_iter": int(n_iter),
        "add_one": bool(add_one),
        "seed": int(seed),
    }


def block_permutation_test(
    values: np.ndarray,
    mask_a: np.ndarray,
    mask_b: np.ndarray,
    block_size: int = 24,
    n_iter: int = 50_000,
    alternative: Alternative = "two-sided",
    add_one: bool = True,
    seed: int = 42,
    rng: np.random.Generator | None = None,
) -> dict[str, float | int | bool] | None:
    """Блочный перестановочный тест разности средних двух групп (sec 3.3).

    ``obs = mean(values[mask_a]) - mean(values[mask_b])`` на обрезанной
    серии; при перестановке блоков значений маски фиксированы.

    Args:
        values: 1D ряд (остатки), без NaN.
        mask_a: булева маска группы-вычитаемого (storm: ``kp >= 5``).
        mask_b: булева маска группы-вычитаемого (quiet: ``kp < 3``).
            Средние группы (kp 3..5) в тест не входят.
        block_size, n_iter, alternative, add_one, seed, rng:
            см. :func:`block_permutation_stat`.

    Returns:
        Словарь :func:`block_permutation_stat` или ``None`` (короткий ряд /
        нефинитный obs / одна из групп пуста на обрезанной серии).
    """
    values = np.asarray(values, dtype=float)
    mask_a_arr = np.asarray(mask_a, dtype=bool)
    mask_b_arr = np.asarray(mask_b, dtype=bool)
    if mask_a_arr.shape != values.shape or mask_b_arr.shape != values.shape:
        raise ValueError(
            f"mask shapes must match values: {values.shape}, {mask_a_arr.shape}, {mask_b_arr.shape}"
        )

    # Обрезка масок тем же срезом, что применит block_permutation_stat.
    n_trim = (values.size // block_size) * block_size
    a_t = mask_a_arr[:n_trim]
    b_t = mask_b_arr[:n_trim]
    if not a_t.any() or not b_t.any():
        return None

    def stat_fn(rp: np.ndarray) -> float:
        return float(rp[a_t].mean() - rp[b_t].mean())

    return block_permutation_stat(
        values,
        stat_fn,
        block_size=block_size,
        n_iter=n_iter,
        alternative=alternative,
        add_one=add_one,
        seed=seed,
        rng=rng,
    )
