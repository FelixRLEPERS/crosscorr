"""
Block bootstrap для не-стационарных временных рядов.

Отличие от phase randomization:
- Phase randomization сохраняет спектр (стационарен).
- Block bootstrap сохраняет КОРОТКИЕ паттерны, но разрушает длинные.
- Работает и для не-стационарных рядов.

Идея: нарезаем ряд на блоки длины L, перемешиваем блоки,
сшиваем в новый суррогат.
"""

from __future__ import annotations

import numpy as np


def block_bootstrap_surrogate(
    x: np.ndarray,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Один блок-бутстрап суррогат.

    Args:
        x: 1D временной ряд (без NaN).
        block_size: длина блока L (например, 24 для часовых данных).
        rng: генератор случайных чисел.

    Returns:
        Суррогатный ряд той же длины, что x.
    """
    x = np.asarray(x, dtype=float)
    n = x.size

    if block_size >= n or block_size < 2:
        # Слишком большой блок — возвращаем перемешанный x
        return rng.permutation(x)

    # Число блоков, необходимое для покрытия n
    n_blocks = int(np.ceil(n / block_size))

    # Случайные стартовые позиции блоков
    max_start = n - block_size
    starts = rng.integers(0, max_start + 1, size=n_blocks)

    # Собираем блоки
    chunks = [x[s : s + block_size] for s in starts]
    surrogate = np.concatenate(chunks)[:n]

    return surrogate


def block_bootstrap_pvalue(
    x: np.ndarray,
    y: np.ndarray,
    block_size: int = 24,
    n_surrogates: int = 500,
    seed: int = 42,
) -> tuple[float, float]:
    """
    p-value корреляции через block bootstrap.

    Тест: значима ли корреляция между x и y.

    Args:
        x, y: 1D ряды.
        block_size: длина блока (обычно ≥ IAT).
        n_surrogates: число суррогатов.
        seed: seed для воспроизводимости.

    Returns:
        (r_observed, p_value).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    mask = ~(np.isnan(x) | np.isnan(y))
    x_v, y_v = x[mask], y[mask]
    n = x_v.size

    if n < block_size * 2:
        return np.nan, 1.0

    r_obs = float(np.corrcoef(x_v, y_v)[0, 1])
    if np.isnan(r_obs):
        return np.nan, 1.0

    rng = np.random.default_rng(seed)
    n_extreme = 0

    for _ in range(n_surrogates):
        y_surr = block_bootstrap_surrogate(y_v, block_size, rng)
        r_surr = np.corrcoef(x_v, y_surr)[0, 1]
        if np.isnan(r_surr):
            continue
        if abs(r_surr) >= abs(r_obs):
            n_extreme += 1

    p = (n_extreme + 1) / (n_surrogates + 1)
    return r_obs, float(p)


def main() -> None:
    """CLI: демонстрация block bootstrap."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--block", type=int, default=24)
    parser.add_argument("--n-surrogates", type=int, default=500)
    args = parser.parse_args()

    rng = np.random.default_rng(42)

    # Синтетика: y = 0.5 * x(t-6) + шум
    x = np.zeros(args.n)
    for i in range(1, args.n):
        x[i] = 0.7 * x[i - 1] + rng.normal(0, 1)

    y = np.zeros(args.n)
    y[6:] = 0.5 * x[:-6]
    y = y + 0.3 * rng.normal(size=args.n)

    r, p = block_bootstrap_pvalue(
        x, y, block_size=args.block, n_surrogates=args.n_surrogates
    )
    print(f"\n[OK] r = {r:.4f}, p = {p:.4f} "
          f"(block_size={args.block}, n_surr={args.n_surrogates})")
    print()


if __name__ == "__main__":
    main()
