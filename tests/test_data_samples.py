"""Тесты группы A: фикстуры, схема, загрузчики, заглушки (ночная сессия).

Покрывает находки:
- A4  — detector_type синтетики входит в enum схемы
- A5  — уникальность ключа (timestamp_utc, detector_id) для WSPR
- A6  — сбалансированный по детекторам сэмпл
- A12 — фикстуры в data/samples/ читаются загрузчиками
- A15 — load_horizons не делает слепой fallback на первую колонку
- A20 — download_and_save_intermagnet не создаёт пустой файл
- A21 — --station обязателен в download_intermagnet
- A24 — registry.expected_fields использует timestamp_utc
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "samples"
SCHEMA = ROOT / "data" / "schema" / "unified_schema.json"


def _load_synthetic_module():
    """Загрузить scripts/make_synthetic_unified.py по пути (не пакет)."""
    path = ROOT / "scripts" / "make_synthetic_unified.py"
    spec = importlib.util.spec_from_file_location("_make_synthetic_unified", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# A12 — фикстуры существуют и читаются
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    [
        "wspr_sample.csv",
        "intermagnet_sample.csv",
        "horizons_sample.csv",
        "confounders_sample.csv",
    ],
)
def test_sample_fixture_exists(name: str):
    assert (SAMPLES / name).is_file(), f"нет фикстуры {name}"


def test_sample_fixtures_readable_by_loaders():
    from data.scripts.unify_schema import (
        load_confounders_if_present,
        load_horizons,
        load_intermagnet,
        load_wspr,
    )

    wspr = load_wspr(SAMPLES / "wspr_sample.csv")
    mag = load_intermagnet(SAMPLES / "intermagnet_sample.csv")
    eph = load_horizons(SAMPLES / "horizons_sample.csv")
    conf = load_confounders_if_present(SAMPLES / "confounders_sample.csv")

    assert len(wspr) > 0 and "value" in wspr.columns
    assert len(mag) > 0 and mag["detector_type"].iloc[0] == "magnetometer"
    assert len(eph) > 0 and eph["detector_type"].iloc[0] == "ephemeris"
    assert conf is not None and len(conf) > 0


# ---------------------------------------------------------------------------
# A5 — уникальность ключа для WSPR (несколько tx на один rx)
# ---------------------------------------------------------------------------
def test_wspr_key_is_unique_per_receiver_time(tmp_path: Path):
    from data.scripts.unify_schema import load_wspr

    path = tmp_path / "wspr.csv"
    pd.DataFrame({
        "timestamp": ["2025-01-01T00:00:00Z"] * 3,
        "rx_call": ["RX1"] * 3,
        "tx_call": ["TX1", "TX2", "TX3"],
        "snr": [-10.0, -12.0, -8.0],
        "band": ["20m"] * 3,
    }).to_csv(path, index=False)

    out = load_wspr(path)

    assert len(out) == 1, "три tx на один rx и время должны агрегироваться"
    assert not out.duplicated(subset=["timestamp_utc", "detector_id"]).any()
    # SNR усреднён
    assert out["value"].iloc[0] == pytest.approx(-10.0)
    # все передатчики сохранены в meta
    meta = json.loads(out["meta"].iloc[0])
    assert set(meta["tx"].split(",")) == {"TX1", "TX2", "TX3"}


# ---------------------------------------------------------------------------
# A4 — detector_type синтетики входит в enum схемы
# ---------------------------------------------------------------------------
def test_synthetic_detector_types_in_schema_enum():
    gen = _load_synthetic_module()

    enum = set(json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]["detector_type"]["enum"])
    used = {d[3] for d in gen.DETECTORS}

    assert used <= enum, f"типы вне enum схемы: {used - enum}"


def test_synthetic_detector_ids_uppercase():
    gen = _load_synthetic_module()

    for detector_id, *_ in gen.DETECTORS:
        assert detector_id == detector_id.upper(), detector_id


# ---------------------------------------------------------------------------
# A6 — сбалансированный сэмпл
# ---------------------------------------------------------------------------
def test_make_sample_is_balanced_across_detectors(tmp_path: Path):
    from data.scripts.make_sample import make_sample

    src = tmp_path / "unified.parquet"
    n = 1000
    df = pd.concat(
        [
            pd.DataFrame({
                "timestamp_utc": pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
                "detector_id": det,
                "detector_type": "wspr",
                "value": range(n),
            })
            for det in ("D_A", "D_B")
        ],
        ignore_index=True,
    )
    df.to_parquet(src, index=False)

    out = make_sample(src, tmp_path / "sample.csv", rows_per_detector=10)

    assert set(out["detector_id"].unique()) == {"D_A", "D_B"}
    counts = out["detector_id"].value_counts().to_dict()
    assert counts == {"D_A": 10, "D_B": 10}


# ---------------------------------------------------------------------------
# A15 — load_horizons без слепого fallback
# ---------------------------------------------------------------------------
def test_load_horizons_rejects_unknown_time_column(tmp_path: Path):
    from data.scripts.unify_schema import load_horizons

    path = tmp_path / "weird.csv"
    pd.DataFrame({"foo": [1, 2], "r": [1.4, 1.5]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="колонки времени"):
        load_horizons(path)


def test_load_horizons_requires_range_column(tmp_path: Path):
    from data.scripts.unify_schema import load_horizons

    path = tmp_path / "no_r.csv"
    pd.DataFrame({"datetime_str": ["2025-01-01T00:00:00Z"]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="'r'"):
        load_horizons(path)


# ---------------------------------------------------------------------------
# A20 / A21 — заглушка INTERMAGNET и обязательный --station
# ---------------------------------------------------------------------------
def test_download_intermagnet_stub_does_not_create_file(tmp_path, monkeypatch):
    from data.scripts import download_intermagnet as di

    monkeypatch.setattr(di, "RAW_DIR", tmp_path)
    out = di.download_and_save_intermagnet("ABBR", 2020, 1)

    assert out.parent == tmp_path
    assert not out.exists(), "заглушка не должна создавать пустой .min"


def test_download_intermagnet_main_has_no_unknown_default():
    import ast
    import inspect

    from data.scripts import download_intermagnet as di

    src = inspect.getsource(di.main)
    tree = ast.parse(src)
    station_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", "") == "add_argument"
        and node.args
        and getattr(node.args[0], "value", None) == "--station"
    ]
    assert station_calls, "нет add_argument('--station')"
    kwargs = {kw.arg: kw for kw in station_calls[0].keywords}
    assert "default" not in kwargs, "--station не должен иметь default UNKNOWN"
    assert any(
        kw.arg == "required" and getattr(kw.value, "value", False)
        for kw in station_calls[0].keywords
    ), "--station должен быть required=True"


# ---------------------------------------------------------------------------
# A24 — registry.expected_fields
# ---------------------------------------------------------------------------
def test_registry_base_url_is_not_placeholder():
    from data.scripts.registry import SourceRegistry

    for name, meta in SourceRegistry.get_all_sources().items():
        url = meta.get("base_url")
        assert url is None or "TODO" not in url, name


def test_registry_ngl_download_script_is_none():
    from data.scripts.registry import SourceRegistry

    ngl = SourceRegistry.get_all_sources()["NGL"]
    assert ngl["download_script"] is None, (
        "download_ngl.py отсутствует; реестр не должен ссылаться на него"
    )


# ---------------------------------------------------------------------------
# A8 — checksums
# ---------------------------------------------------------------------------
def test_write_checksum_file_created(tmp_path: Path):
    from data.scripts.download_wspr import _write_checksum

    f = tmp_path / "data.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    sidecar = _write_checksum(f)

    assert sidecar.exists()
    digest, _, name = sidecar.read_text(encoding="utf-8").strip().partition("  ")
    assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    assert name == "data.csv"


def test_download_intermagnet_stub_returned_path_under_raw_dir(tmp_path, monkeypatch):
    from data.scripts import download_intermagnet as di

    monkeypatch.setattr(di, "RAW_DIR", tmp_path)
    out = di.download_and_save_intermagnet("ABBR", 2020, 1)

    assert out.name == "ABBR_2020_01.min"
    assert out.parent == tmp_path


def test_make_sample_missing_source_raises(tmp_path: Path):
    from data.scripts.make_sample import make_sample

    with pytest.raises(FileNotFoundError):
        make_sample(tmp_path / "nope.parquet", tmp_path / "out.csv")


def test_load_wspr_does_not_mutate_input(tmp_path: Path):
    from data.scripts.unify_schema import load_wspr

    path = tmp_path / "wspr.csv"
    pd.DataFrame({
        "timestamp": ["2025-01-01T00:00:00Z"],
        "rx_call": ["RX1"],
        "tx_call": ["TX1"],
        "snr": [-10.0],
        "band": ["20m"],
    }).to_csv(path, index=False)

    out = load_wspr(path)
    assert "detector_type" in out.columns
    assert "meta" in out.columns


def test_registry_expected_fields_use_timestamp_utc():
    from data.scripts.registry import UNIFIED_FIELDS

    assert "timestamp_utc" in UNIFIED_FIELDS
    assert "timestamp" not in UNIFIED_FIELDS

    from data.scripts.registry import SourceRegistry

    for name, meta in SourceRegistry.get_all_sources().items():
        assert "timestamp_utc" in meta["expected_fields"], name
        assert "timestamp" not in meta["expected_fields"], name


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
