"""
Surrogate-тесты для оценки значимости наблюдаемых кросс-корреляций.

Используются фазовые суррогаты (phase randomization), которые сохраняют
амплитудный спектр, но разрушают нелинейные связи.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results"
DEFAULT_OUT.mkdir(parents=True, exist_ok=True)


def phase_surrogate(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Возвращает фазовый суррогат для одномерного ряда."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size < 4:
        return x
    fft = np.fft.rfft(x)
    phases = np.angle(fft)
    magnitudes = np.abs(fft)
    random_phases = rng.uniform(-np.pi, np.pi, size=phases.shape)
    fft_surrogate = magnitudes * np.exp(1j * random_phases)
    surrogate = np.fft.irfft(fft_surrogate, n=x.size)
    return surrogate


def build_wide(df: pd.DataFrame, freq: str = "1h") -> pd.DataFrame:
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["bucket"] = df["timestamp_utc"].dt.floor(freq)
    wide = (
        df.groupby(["detector_type", "bucket"])["residual"]
        .mean()
        .unstack("detector_type")
        .sort_index()
    )
    return wide


def surrogate_test(wide: pd.DataFrame, n_surrogates: int = 1000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = wide.columns.tolist()
    real = wide.corr(method="spearman").values

    # накапливаем распределение корреляций по суррогатам
    surrogate_corrs = np.zeros((n_surrogates, len(cols), len(cols)))
    filled = wide.fillna(wide.mean())

    for i in range(n_surrogates):
        surro = np.column_stack([
            phase_surrogate(filled[c].values, rng) for c in cols
        ])
        surro_df = pd.DataFrame(surro, columns=cols)
        surrogate_corrs[i] = surro_df.corr(method="spearman").values

    # p-value: доля суррогатов, где |corr| >= |real|
    pvals = np.zeros_like(real)
    for r in range(len(cols)):
        for c in range(len(cols)):
            if r == c:
                pvals[r, c] = 0.0
                continue
            pvals[r, c] = np.mean(np.abs(surrogate_corrs[:, r, c]) >= abs(real[r, c]))

    result = pd.DataFrame(pvals, index=cols, columns=cols)
    return result


def fdr_bh(pvals: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg FDR. Возвращает булеву маску значимости."""
    flat = pvals.flatten()
    n = flat.size
    order = np.argsort(flat)
    ranked = flat[order]
    thresholds = alpha * (np.arange(1, n + 1) / n)
    passed = ranked <= thresholds
    if not passed.any():
        mask = np.zeros_like(flat, dtype=bool)
    else:
        k = np.max(np.where(passed)[0])
        mask = np.zeros_like(flat, dtype=bool)
        mask[order[: k + 1]] = True
    return mask.reshape(pvals.shape)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--freq", default="1h")
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    wide = build_wide(df, freq=args.freq)

    pvals = surrogate_test(wide, n_surrogates=args.n)
    significant = fdr_bh(pvals.values, alpha=args.alpha)
    sig_df = pd.DataFrame(significant, index=pvals.index, columns=pvals.columns)

    pvals.to_csv(DEFAULT_OUT / "surrogate_pvalues.csv")
    sig_df.to_csv(DEFAULT_OUT / "surrogate_significant.csv")
    print(f"[OK] p-values -> {DEFAULT_OUT / 'surrogate_pvalues.csv'}")
    print(f"[OK] significant pairs: {int(significant.sum())}")


if __name__ == "__main__":
    main()