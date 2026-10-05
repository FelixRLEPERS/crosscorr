"""Создаёт маленький сэмпл унифицированной таблицы для воспроизводимости.

Сэмпл берётся **по каждому детектору отдельно** (по ``rows_per_detector``
строк), а не срезом первых 500 строк глобально отсортированной таблицы.
Прежний ``df.head(500)`` после ``sort_values("timestamp_utc")`` возвращал
первые часы только одного-двух детекторов, поэтому кросс-корреляция на
таком сэмпле вырождена (находка A6 / V2-24).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "processed" / "unified.parquet"
DEFAULT_DST = ROOT / "samples" / "unified_sample.csv"

#: Сколько строк на каждый детектор попадает в сэмпл.
DEFAULT_ROWS_PER_DETECTOR = 200


def make_sample(
    src: Path,
    dst: Path,
    rows_per_detector: int = DEFAULT_ROWS_PER_DETECTOR,
) -> pd.DataFrame:
    """Сохранить сбалансированный по детекторам сэмпл unified-таблицы.

    Parameters
    ----------
    src : Path
        Путь к ``unified.parquet``.
    dst : Path
        Куда записать CSV-сэмпл.
    rows_per_detector : int
        Максимум строк на каждый ``detector_id``.

    Returns
    -------
    pd.DataFrame
        Записанный сэмпл.
    """
    if not src.exists():
        raise FileNotFoundError(
            f"Нет файла {src}. Сначала запустите data/scripts/unify_schema.py"
        )

    df = pd.read_parquet(src)
    if df.empty:
        raise ValueError(f"{src} пуст: сэмпл создать нельзя")
    if "detector_id" not in df.columns:
        raise ValueError(f"В {src} нет колонки detector_id")

    sample = (
        df.sort_values("timestamp_utc")
        .groupby("detector_id", group_keys=False)
        .head(rows_per_detector)
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(dst, index=False)
    return sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--dst", type=Path, default=DEFAULT_DST)
    parser.add_argument(
        "--rows-per-detector", type=int, default=DEFAULT_ROWS_PER_DETECTOR
    )
    args = parser.parse_args()

    sample = make_sample(args.src, args.dst, args.rows_per_detector)
    n_detectors = sample["detector_id"].nunique()
    print(
        f"[OK] {len(sample)} строк, {n_detectors} детекторов -> {args.dst}"
    )


if __name__ == "__main__":
    main()
