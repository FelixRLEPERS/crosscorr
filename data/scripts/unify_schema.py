"""
Приводит сырые файлы из data/raw/* к единому формату:
timestamp_utc, detector_id, detector_type, residual, meta
Результат: data/processed/unified.parquet
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

UNIFIED_COLUMNS = ["timestamp_utc", "detector_id", "detector_type", "residual", "meta"]


def load_wspr(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["timestamp"], utc=True),
        "detector_id": df["rx_call"].astype(str),
        "detector_type": "wspr",
        "residual": df["snr"].astype(float),  # SNR как первичный "residual"
    })
    out["meta"] = df.apply(lambda r: json.dumps({"tx": r.get("tx_call"), "band": r.get("band")}), axis=1)
    return out


def load_intermagnet(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["timestamp"], utc=True),
        "detector_id": path.stem,
        "detector_type": "magnetometer",
        "residual": df["X"].astype(float),
    })
    out["meta"] = "{}"
    return out


def load_horizons(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Horizons отдаёт колонку 'datetime_str' или 'Date__(UT)__HR:MN'
    ts_col = "datetime_str" if "datetime_str" in df.columns else df.columns[0]
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df[ts_col], utc=True, errors="coerce"),
        "detector_id": path.stem,
        "detector_type": "ephemeris",
        "residual": pd.to_numeric(df.get("r"), errors="coerce"),  # расстояние от Солнца
    }).dropna(subset=["timestamp_utc"])
    out["meta"] = "{}"
    return out


LOADERS = {
    "wspr": load_wspr,
    "intermagnet": load_intermagnet,
    "horizons": load_horizons,
}


def main() -> None:
    frames = []
    for folder, loader in LOADERS.items():
        d = RAW / folder
        if not d.exists():
            continue
        for f in d.glob("*.csv"):
            try:
                frames.append(loader(f))
                print(f"[OK] {f.name}")
            except Exception as e:  # noqa: BLE001
                print(f"[SKIP] {f.name}: {e}")

    if not frames:
        raise SystemExit("Не найдено ни одного файла в data/raw/*")

    unified = pd.concat(frames, ignore_index=True)[UNIFIED_COLUMNS]
    unified = unified.sort_values("timestamp_utc").reset_index(drop=True)

    out = PROCESSED / "unified.parquet"
    unified.to_parquet(out, index=False)
    print(f"[DONE] {len(unified)} строк -> {out}")


if __name__ == "__main__":
    main()