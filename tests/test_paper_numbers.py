"""Golden test: ключевые числа статейных артефактов не регрессируют.

Фикстура ``tests/fixtures/paper_numbers.json`` содержит top-level ключи
(p/delta/drop_pct/N) трёх артефактов, на которых стоят числа статьи:

- ``results/perm_test_18mo_3band.json``  — headline permutation (Table 2)
- ``results/spatial_lat_groups_norm_tx.json`` — latitude groups (Table 7)
- ``results/round3_episode_robustness.json`` — ordinal trend (Appendix)

Тест НЕ запускает скрипты — только читает JSON и сверяет с эталоном.
Допуск 1e-6 по float; для p на floor (add-one минимум: 1/50001 и 1/20001)
следующее возможное значение отличается на >= 1e-5, т.е. 1e-6 ловит любой
сдвиг p строго (floor-строгость обеспечена автоматически).

Артефакты в ``results/`` — gitignored, в их отсутствие (CI) тест skip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "paper_numbers.json"
TOL = 1e-6

if not FIXTURE.exists():  # pragma: no cover
    pytest.skip("golden fixture is missing", allow_module_level=True)

_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

_ARTIFACTS = sorted(_fixture)


def _diff(expected, actual, path="") -> list[str]:
    """Рекурсивное сравнение эталонного поддерева с текущим значением."""
    diffs: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected dict, got {type(actual).__name__}"]
        for key, want in expected.items():
            if key not in actual:
                diffs.append(f"{path}.{key}: missing in artifact")
            else:
                diffs.extend(_diff(want, actual[key], f"{path}.{key}"))
    elif isinstance(expected, bool) or isinstance(actual, bool):
        if expected is not actual:
            diffs.append(f"{path}: {expected!r} != {actual!r}")
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if abs(float(expected) - float(actual)) > TOL:
            diffs.append(f"{path}: {expected!r} != {actual!r} (|d| > {TOL})")
    elif expected != actual:
        diffs.append(f"{path}: {expected!r} != {actual!r}")
    return diffs


@pytest.mark.parametrize(
    "artifact",
    _ARTIFACTS,
    ids=[Path(a).name for a in _ARTIFACTS],
)
def test_paper_numbers_unchanged(artifact: str) -> None:
    """Текущий артефакт совпадает с зафиксированными числами статьи."""
    artifact_path = ROOT / artifact
    if not artifact_path.exists():
        pytest.skip(f"{artifact} not present (results/ is gitignored)")

    current = json.loads(artifact_path.read_text(encoding="utf-8"))
    diffs = _diff(_fixture[artifact], current)
    assert not diffs, (
        f"{artifact} drifted from the golden fixture "
        f"({len(diffs)} value(s)):\n  " + "\n  ".join(diffs)
    )
