"""
Кросс-корреляционный анализ унифицированной таблицы.

Идея:
1. Загрузить data/processed/unified.parquet
2. Сгруппировать по detector_type и привести к общему временному индексу.
3. Посчитать матрицу корреляций Пирсона/Спирмена.
4. Сохранить матрицу и heatmap.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results"
DEFAULT_OUT.mkdir(parents=True, exist_ok=True)


def load_unified(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df


def pivot_by_type(df: pd.DataFrame, freq: str = "1h") -> pd.DataFrame:
    """Усредняем residual по (type, time) и разворачиваем в wide-формат."""
    df = df.copy()
    df["bucket"] = df["timestamp_utc"].dt.floor(freq)
    wide = (
        df.groupby(["detector_type", "bucket"])["residual"]
        .mean()
        .unstack("detector_type")
    )
    wide = wide.sort_index()
    return wide


def cross_correlation(wide: pd.DataFrame, method: str = "spearman") -> pd.DataFrame:
    return wide.corr(method=method, min_periods=10)


def plot_heatmap(corr: pd.DataFrame, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.index)
    fig.colorbar(im, ax=ax, label="correlation")
    ax.set_title(f"Cross-correlation ({len(corr)} detectors)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--freq", default="1h")
    parser.add_argument("--method", default="spearman", choices=["pearson", "spearman", "kendall"])
    args = parser.parse_args()

    df = load_unified(args.input)
    wide = pivot_by_type(df, freq=args.freq)
    corr = cross_correlation(wide, method=args.method)

    csv_out = DEFAULT_OUT / "cross_correlation.csv"
    png_out = DEFAULT_OUT / "cross_correlation.png"
    corr.to_csv(csv_out)
    plot_heatmap(corr, png_out)
    print(f"[OK] {csv_out}")
    print(f"[OK] {png_out}")


if __name__ == "__main__":
    main()