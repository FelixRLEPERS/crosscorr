"""MFDFA-анализ унифицированных рядов.

Сохраняет результаты в long-format CSV:
    detector, lag, q_index, dq

Особенности:
- MFDFA() исключает q=0 из выходного массива dq
  (формула MFDFA делит на q, q=0 — предельный случай).
- Поэтому dq.shape[1] может быть меньше len(q).
- Используем dq.shape[1] как фактическое число q-колонок.
- Long-format позволяет разным детекторам иметь разное число масштабов.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from MFDFA import MFDFA

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "unified.parquet"
DEFAULT_OUT = ROOT / "results"


def mfdfa_spectrum(
    x: np.ndarray,
    q: np.ndarray | None = None,
    lag: np.ndarray | None = None,
):
    """
    Возвращает (lag, q, dq) для одного ряда.

    lag : 1D массив масштабов
    q   : 1D массив параметров q (используется для передачи в MFDFA)
    dq  : 2D массив формы (len(lag), n_q_cols),
          где n_q_cols = dq.shape[1] — фактическое число q-колонок
          (может быть меньше len(q), если MFDFA исключила q=0).
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]

    if x.size < 100:
        raise ValueError("Слишком короткий ряд для MFDFA")

    if q is None:
        # q=0 исключён: формула MFDFA делит на q,
        # большинство реализаций обрабатывают q=0 отдельно.
        q = np.array([-4, -2, -1, 1, 2, 4], dtype=float)

    if lag is None:
        lag = np.unique(
            np.logspace(0.7, np.log10(x.size // 4), 20).astype(int)
        )

    lag, dq = MFDFA(x, lag=lag, q=q, order=1)
    return lag, q, dq


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--freq", default="1h")
    args = parser.parse_args()

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.input)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["bucket"] = df["timestamp_utc"].dt.floor(args.freq)
    wide = (
        df.groupby(["detector_id", "bucket"])["residual"]
        .mean()
        .unstack("detector_id")
    )
    rows = []
    for col in wide.columns:
        try:
            lag, q, dq = mfdfa_spectrum(wide[col].values)

            # dq может иметь меньше колонок, чем len(q),
            # если библиотека исключила q=0.
            n_q_cols = dq.shape[1]

            for i, lag_val in enumerate(lag):
                for j in range(n_q_cols):
                    rows.append({
                        "detector": col,
                        "lag": int(lag_val),
                        "q_index": int(j),
                        "dq": float(dq[i, j]),
                    })

            print(
                f"[OK] {col}: {len(lag)} масштабов × {n_q_cols} q "
                f"= {len(lag) * n_q_cols} точек"
            )

        except Exception as e:  # noqa: BLE001
            print(f"[SKIP] {col}: {e}")

    if rows:
        out = DEFAULT_OUT / "mfdfa_spectra.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"[DONE] -> {out}  ({len(rows)} строк)")
    else:
        print("[WARN] Нет результатов MFDFA.")


if __name__ == "__main__":
    main()
