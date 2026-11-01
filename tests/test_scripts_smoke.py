"""Smoke-тест скриптов: perm_test_18mo_3band.py отрабатывает и пишет JSON.

Проверяет только СТРУКТУРУ выхода (ключи, n_iter-флаг, add-one:
p > 0), не числа — числа охраняет ``tests/test_paper_numbers.py``.
Полный 50k-прогон здесь не выполняется: --n-iter 100.

Пропускается, если ``data/processed/unified.parquet`` отсутствует
(gitignored — в CI данных нет).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "perm_test_18mo_3band.py"
PARQUET = ROOT / "data" / "processed" / "unified.parquet"

pytestmark = pytest.mark.skipif(
    not PARQUET.exists(),
    reason="data/processed/unified.parquet (gitignored) is required",
)


def test_perm_18mo_smoke_json_structure(tmp_path: Path) -> None:
    """--n-iter 100: exit 0, JSON создан, ожидаемые ключи на месте."""
    out = tmp_path / "smoke.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--n-iter",
            "100",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, (
        f"script failed with exit {proc.returncode}\n"
        f"stdout tail: {proc.stdout[-2000:]}\n"
        f"stderr tail: {proc.stderr[-2000:]}"
    )
    assert out.exists(), "output JSON was not written"

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["config"]["n_iter"] == 100, "--n-iter flag did not reach config"
    assert data["config"]["block_size"] == 24
    assert set(data["results"]) == {"20m", "40m", "15m"}

    for band, row in data["results"].items():
        expected_keys = {"N", "N_storm", "N_quiet", "delta", "drop_pct", "p_value"}
        assert expected_keys <= set(row), f"{band}: missing keys {expected_keys - set(row)}"
        # add-one (Davison-Hinkley): Monte-Carlo p is never exactly 0.
        assert 0.0 < row["p_value"] <= 1.0, f"{band}: p={row['p_value']} violates add-one"
        assert row["N"] > 0 and row["N_storm"] > 0
