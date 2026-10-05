"""
Приводит сырые файлы из data/raw/* к единому формату:
timestamp_utc, detector_id, detector_type, value, residual,
residual_method, unit, quality_flag, meta
Результат: data/processed/unified.parquet

Слои (P0-2)
-----------
Скрипт работает как **transform-слой над ETL-слойом загрузки**:

1. Загрузчики :func:`load_wspr`, :func:`load_intermagnet`,
   :func:`load_horizons` — тонкие читалки файлов. Они пишут сырое
   наблюдение в колонку ``value`` и его единицу в ``unit``. Остаток
   они **не** считают: остаток нужно оценивать по всем детекторам
   одного типа сразу, а не по одному файлу-фрагменту.
2. :func:`main` склеивает все файлы и передаёт результат в
   :func:`crosscorr_lib.analysis.residuals.fit_residual_model`, которая
   добавляет ``residual``, ``residual_method`` и ``quality_flag``.

Обратная совместимость
----------------------
``residual`` остаётся в :data:`UNIFIED_COLUMNS` и всегда заполнен, поэтому
потребители ``cross_correlation``, ``mfdfa``, ``stationarity`` и
``surrogate``, читающие ``residual`` из parquet, работают без изменений.
Если конфаундеры недоступны, базовая модель не оценивается:
``residual_method == "none"`` и ``residual == value``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

#: Файл конфаундеров (timestamp_utc, kp, dst, f107) для OLS-базовой модели.
DEFAULT_CONFOUNDERS = ROOT / "confounders.csv"

#: Колонки unified-таблицы в фиксированном порядке.
UNIFIED_COLUMNS = [
    "timestamp_utc",
    "detector_id",
    "detector_type",
    "value",
    "residual",
    "residual_method",
    "unit",
    "quality_flag",
    "meta",
]


def load_wspr(path: Path) -> pd.DataFrame:
    """Прочитать WSPR-выгрузку в unified-формат (сырое наблюдение = SNR)."""
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["timestamp"], utc=True),
        "detector_id": df["rx_call"].astype(str),
        "detector_type": "wspr",
        "value": df["snr"].astype(float),
    })
    out["meta"] = df.apply(
        lambda r: json.dumps({"tx": r.get("tx_call"), "band": r.get("band")}),
        axis=1,
    )
    return out


def load_intermagnet(path: Path) -> pd.DataFrame:
    """Прочитать CSV магнитометра в unified-формат (сырое наблюдение = X)."""
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["timestamp"], utc=True),
        "detector_id": path.stem,
        "detector_type": "magnetometer",
        "value": df["X"].astype(float),
    })
    out["meta"] = json.dumps({})
    return out


def load_horizons(path: Path) -> pd.DataFrame:
    """Прочитать выгрузку JPL Horizons (сырое наблюдение = расстояние r)."""
    df = pd.read_csv(path)
    # Horizons отдаёт колонку 'datetime_str' или 'Date__(UT)__HR:MN'
    ts_col = "datetime_str" if "datetime_str" in df.columns else df.columns[0]
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df[ts_col], utc=True, errors="coerce"),
        "detector_id": path.stem,
        "detector_type": "ephemeris",
        "value": pd.to_numeric(df.get("r"), errors="coerce"),  # расстояние от Солнца, а.е.
    }).dropna(subset=["timestamp_utc"])
    out["meta"] = json.dumps({})
    return out


LOADERS = {
    "wspr": load_wspr,
    "intermagnet": load_intermagnet,
    "horizons": load_horizons,
}


def load_confounders_if_present(path: Path) -> pd.DataFrame | None:
    """Загрузить конфаундеры, если файл существует, иначе вернуть None.

    Parameters
    ----------
    path : Path
        Путь к CSV с колонками ``timestamp_utc``, ``kp``, ``dst``, ``f107``.

    Returns
    -------
    pd.DataFrame | None
        Прочитанные конфаундеры либо ``None``, если файла нет.
    """
    if not path.exists():
        return None
    conf = pd.read_csv(path)
    if "timestamp_utc" not in conf.columns:
        return None
    conf["timestamp_utc"] = pd.to_datetime(conf["timestamp_utc"], utc=True, errors="coerce")
    return conf.dropna(subset=["timestamp_utc"])


def fit_residuals(
    unified: pd.DataFrame,
    confounders: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Добавить ``residual``, ``residual_method``, ``quality_flag``, ``unit``.

    Значения ``residual`` считаются **по группам ``detector_type``**, чтобы
    каждая базовая модель оценивалась на всех детекторах своего типа, а не
    на одном файле.

    Parameters
    ----------
    unified : pd.DataFrame
        Таблица с колонками ``timestamp_utc``, ``detector_id``,
        ``detector_type``, ``value``.
    confounders : pd.DataFrame | None, default None
        Конфаундеры для OLS-базовой модели. ``None`` — модель не
        оценивается, ``residual == value``.

    Returns
    -------
    pd.DataFrame
        Новая таблица с полным набором :data:`UNIFIED_COLUMNS`.
    """
    from crosscorr_lib.analysis.residuals import (
        detector_unit,
        fit_residual_model,
    )

    out = unified.copy()
    out["unit"] = [detector_unit(t) for t in out["detector_type"]]

    for detector_type, idx in out.groupby("detector_type").groups.items():
        part = out.loc[idx]
        fitted = fit_residual_model(
            part.drop(columns=["unit"]),
            detector_type=str(detector_type),
            confounders=confounders,
        )
        out.loc[idx, "residual"] = fitted["residual"].to_numpy()
        out.loc[idx, "residual_method"] = fitted["residual_method"].to_numpy()
        out.loc[idx, "quality_flag"] = fitted["quality_flag"].to_numpy()

    return out[UNIFIED_COLUMNS]


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

    unified = pd.concat(frames, ignore_index=True)

    confounders = load_confounders_if_present(DEFAULT_CONFOUNDERS)
    if confounders is None:
        print(
            f"[WARN] {DEFAULT_CONFOUNDERS} не найден: базовая модель не "
            "оценивается, residual_method = 'none', residual = value."
        )
    unified = fit_residuals(unified, confounders=confounders)

    unified = unified[UNIFIED_COLUMNS].sort_values("timestamp_utc").reset_index(drop=True)

    out = PROCESSED / "unified.parquet"
    unified.to_parquet(out, index=False)
    print(f"[DONE] {len(unified)} строк -> {out}")


if __name__ == "__main__":
    main()
