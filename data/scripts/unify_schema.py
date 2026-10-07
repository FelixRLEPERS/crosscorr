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
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"

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


def _join_unique(values: pd.Series) -> str:
    """Уникальные непустые значения серии, соединённые через запятую."""
    seen: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value)
        if text not in seen:
            seen.append(text)
    return ",".join(seen)


def _first_non_null(values: pd.Series):
    """Первое непустое значение серии либо ``None``."""
    for value in values:
        if not pd.isna(value):
            return value
    return None


def load_wspr(path: Path) -> pd.DataFrame:
    """Прочитать WSPR-выгрузку в unified-формат (сырое наблюдение = SNR).

    Один приёмник (``rx_call``) может принять несколько передатчиков
    (``tx_call``) в один момент времени. Ключ unified-таблицы —
    ``(timestamp_utc, detector_id)`` — должен быть уникален, поэтому SNR
    агрегируется по ``(timestamp, rx_call)`` средним, а список передатчиков
    сохраняется в ``meta`` (находка A5 / V2-17).
    """
    df = pd.read_csv(path)
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp"], utc=True)
    df["detector_id"] = df["rx_call"].astype(str)
    df["value"] = df["snr"].astype(float)

    grouped = df.groupby(["timestamp_utc", "detector_id"], as_index=False).agg(
        value=("value", "mean"),
        tx=("tx_call", _join_unique),
        band=("band", _first_non_null),
    )
    grouped["detector_type"] = "wspr"
    grouped["meta"] = [
        json.dumps({"tx": tx, "band": band})
        for tx, band in zip(grouped["tx"], grouped["band"], strict=True)
    ]
    return grouped[["timestamp_utc", "detector_id", "detector_type", "value", "meta"]]


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


#: Возможные имена колонки времени в выгрузке JPL Horizons.
HORIZONS_TIME_COLUMNS = ("datetime_str", "Date__(UT)__HR:MN", "date")

#: Колонка расстояния от Солнца (а.е.) в выгрузке JPL Horizons.
HORIZONS_RANGE_COLUMN = "r"


def load_horizons(path: Path) -> pd.DataFrame:
    """Прочитать выгрузку JPL Horizons (сырое наблюдение = расстояние r).

    Колонка времени ищется по известным именам (``HORIZONS_TIME_COLUMNS``),
    а не берётся как первая колонка файла: слепой fallback мог принять за
    время любую колонку (находка A15 / V2-19). Строки без времени или без
    расстояния отбрасываются явно.
    """
    df = pd.read_csv(path)
    ts_col = next((c for c in HORIZONS_TIME_COLUMNS if c in df.columns), None)
    if ts_col is None:
        raise ValueError(
            f"В выгрузке Horizons нет колонки времени; ожидались "
            f"{list(HORIZONS_TIME_COLUMNS)}, есть {list(df.columns)}"
        )
    if HORIZONS_RANGE_COLUMN not in df.columns:
        raise ValueError(
            f"В выгрузке Horizons нет колонки {HORIZONS_RANGE_COLUMN!r}; "
            f"есть {list(df.columns)}"
        )
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df[ts_col], utc=True, errors="coerce"),
        "detector_id": path.stem,
        "detector_type": "ephemeris",
        "value": pd.to_numeric(df[HORIZONS_RANGE_COLUMN], errors="coerce"),
    })
    dropped = int(out["timestamp_utc"].isna().sum() + out["value"].isna().sum())
    if dropped:
        logger.warning(
            "%s: отброшено %d строк без времени или расстояния", path.name, dropped
        )
    out = out.dropna(subset=["timestamp_utc", "value"])
    out["meta"] = json.dumps({})
    return out[["timestamp_utc", "detector_id", "detector_type", "value", "meta"]]


def load_kp(path: Path) -> pd.DataFrame:
    """Прочитать Kp CSV в unified-формат (сырое наблюдение = Kp)."""
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["timestamp"], utc=True),
        "detector_id": "kp_index",
        "detector_type": "kp",
        "value": df["kp"].astype(float),
    })
    out["meta"] = json.dumps({"granularity": "3h"})
    return out[["timestamp_utc", "detector_id", "detector_type", "value", "meta"]]


def load_dst(path: Path) -> pd.DataFrame:
    """Прочитать Dst CSV в unified-формат (сырое наблюдение = Dst, нТ)."""
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["timestamp"], utc=True),
        "detector_id": "dst_index",
        "detector_type": "dst",
        "value": df["dst_nt"].astype(float),
    })
    out["meta"] = json.dumps({"granularity": "1h"})
    return out[["timestamp_utc", "detector_id", "detector_type", "value", "meta"]]


def load_f107(path: Path) -> pd.DataFrame:
    """Прочитать F10.7 CSV в unified-формат (сырое наблюдение = F10.7)."""
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["date"], utc=True),
        "detector_id": "f107_index",
        "detector_type": "f107",
        "value": df["f107"].astype(float),
    })
    out["meta"] = json.dumps({"granularity": "monthly"})
    return out[["timestamp_utc", "detector_id", "detector_type", "value", "meta"]]


def _route_wspr(path: Path) -> pd.DataFrame:
    """Направить WSPR-файл в raw или hourly loader по префиксу имени."""
    if path.stem.startswith("wspr_hourly"):
        return load_wspr_hourly(path)
    return load_wspr(path)


def load_wspr_hourly(path: Path) -> pd.DataFrame:
    """Прочитать почасовую агрегацию WSPR в unified-формат (value = spots_count)."""
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(df["timestamp"], utc=True),
        "detector_id": f"_wspr_hourly_20m",
        "detector_type": "wspr_hourly",
        "value": df["spots_count"].astype(float),
    })
    out["meta"] = json.dumps({
        "mean_snr": float(df["mean_snr"].iloc[0]) if "mean_snr" in df.columns else None,
    })
    return out[["timestamp_utc", "detector_id", "detector_type", "value", "meta"]]


LOADERS = {
    "wspr": _route_wspr,
    "intermagnet": load_intermagnet,
    "horizons": load_horizons,
    "space_weather": lambda p: _route_sw(p),
}


def _route_sw(path: Path) -> pd.DataFrame:
    """Направить файл space_weather в правильный загрузчик по имени."""
    name = path.stem.lower()
    if name.startswith("kp"):
        return load_kp(path)
    if name.startswith("dst"):
        return load_dst(path)
    if name.startswith("f107"):
        return load_f107(path)
    raise ValueError(
        f"Неизвестный префикс файла space_weather: {path.name}. "
        f"Ожидается kp_*, dst_* или f107_*."
    )


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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    PROCESSED.mkdir(parents=True, exist_ok=True)

    frames = []
    skipped = 0
    for folder, loader in LOADERS.items():
        d = RAW / folder
        if not d.exists():
            continue
        for f in d.glob("*.csv"):
            try:
                frames.append(loader(f))
                logger.info("[OK] %s", f.name)
            except Exception as e:  # noqa: BLE001
                skipped += 1
                logger.warning("[SKIP] %s: %s", f.name, e)

    if not frames:
        raise SystemExit("Не найдено ни одного файла в data/raw/*")

    unified = pd.concat(frames, ignore_index=True)

    confounders = load_confounders_if_present(DEFAULT_CONFOUNDERS)
    if confounders is None:
        logger.warning(
            "%s не найден: базовая модель не оценивается, "
            "residual_method = 'none', residual = value.",
            DEFAULT_CONFOUNDERS,
        )
    unified = fit_residuals(unified, confounders=confounders)

    n_nan_residual = int(unified["residual"].isna().sum())
    if n_nan_residual:
        logger.warning(
            "residual содержит %d NaN строк из %d; они не удаляются, "
            "quality_flag помечает их как missing.",
            n_nan_residual, len(unified),
        )

    unified = unified[UNIFIED_COLUMNS].sort_values("timestamp_utc").reset_index(drop=True)

    out = PROCESSED / "unified.parquet"
    unified.to_parquet(out, index=False)
    logger.info(
        "[DONE] %d строк -> %s (пропущено файлов: %d)",
        len(unified), out, skipped,
    )


if __name__ == "__main__":
    main()
