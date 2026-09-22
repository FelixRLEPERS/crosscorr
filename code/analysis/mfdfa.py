"""MFDFA-анализ унифицированных рядов."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from MFDFA import MFDFA

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results"
DEFAULT_OUT.mkdir(parents=True, exist_ok=True)


def mfdfa_spectrum(x: np.ndarray, q: np.ndarray | None = None, lag: np.ndarray | None = None):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size < 100:
        raise ValueError("Слишком короткий ряд для MFDFA")
    if q is None:
        q = np.array([-4, -2, -1, 0, 1, 2, 4], dtype=float)
    if lag is None:
        lag = np.unique(np.logspace(0.7, np.log10(x.size // 4), 20).astype(int))
    lag, dq = MFDFA(x, lag=lag, q=q, order=1)
    return lag, dq


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--freq", default="1h")
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["bucket"] = df["timestamp_utc"].dt.floor(args.freq)
    wide = df.groupby(["detector_type", "bucket"])["residual"].mean().unstack("detector_type")

    results = {}
    for col in wide.columns:
        try:
            lag, dq = mfdfa_spectrum(wide[col].values)
            results[col] = dq
            print(f"[OK] {col}: {len(lag)} масштабов")
        except Exception as e:  # noqa: BLE001
            print(f"[SKIP] {col}: {e}")

    if results:
        out = DEFAULT_OUT / "mfdfa_spectra.csv"
        pd.DataFrame(results).to_csv(out, index=False)
        print(f"[DONE] -> {out}")


if __name__ == "__main__":
    main()