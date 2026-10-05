"""Tests for group F findings (CI and infrastructure configs).

These check config files directly, without running CI.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = ROOT / "pyproject.toml"
MAKEFILE = ROOT / "Makefile"
GITIGNORE = ROOT / ".gitignore"

yaml = pytest.importorskip("yaml")

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


def _ci() -> dict:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# F6 — ruff scope includes data/
# ---------------------------------------------------------------------------
def test_ci_yml_parses():
    data = _ci()
    assert "jobs" in data
    assert "on" in data or True in data  # YAML parses `on:` as boolean True


def test_ruff_scope_includes_data():
    data = _ci()
    found = False
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            run = step.get("run", "")
            if "ruff check" in run:
                found = True
                assert "data/" in run
    assert found, "в ci.yml нет шага ruff check"


# ---------------------------------------------------------------------------
# F4 — Windows job present
# ---------------------------------------------------------------------------
def test_ci_has_windows_job():
    data = _ci()
    assert "test-windows" in data["jobs"]
    assert data["jobs"]["test-windows"]["runs-on"].startswith("windows")


# ---------------------------------------------------------------------------
# F5 — coverage flag present
# ---------------------------------------------------------------------------
def test_fast_job_uses_coverage():
    data = _ci()
    runs = [
        step.get("run", "")
        for step in data["jobs"]["test-fast"].get("steps", [])
    ]
    joined = "\n".join(runs)
    assert "--cov=crosscorr_lib" in joined


# ---------------------------------------------------------------------------
# F8 — compileall step present
# ---------------------------------------------------------------------------
def test_ci_has_compileall():
    data = _ci()
    runs = [
        step.get("run", "")
        for step in data["jobs"]["test-fast"].get("steps", [])
    ]
    assert any("compileall" in r for r in runs)


# ---------------------------------------------------------------------------
# F9 — cache-dependency-path present
# ---------------------------------------------------------------------------
def test_setup_python_cache_dependency_path():
    data = _ci()
    for job_name, job in data["jobs"].items():
        for step in job.get("steps", []):
            if "setup-python" in str(step.get("uses", "")):
                with_ = step.get("with", {})
                if "cache" in with_:
                    assert "cache-dependency-path" in with_, job_name


# ---------------------------------------------------------------------------
# F20 — numpy lower bound respects Generator.spawn
# ---------------------------------------------------------------------------
def test_numpy_lower_bound_supports_spawn():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    numpy_req = next(d for d in deps if d.startswith("numpy"))
    assert "1.25" in numpy_req, numpy_req


# ---------------------------------------------------------------------------
# F12 — coverage artifacts ignored
# ---------------------------------------------------------------------------
def test_gitignore_ignores_coverage():
    content = GITIGNORE.read_text(encoding="utf-8")
    assert ".coverage" in content
    assert "htmlcov/" in content


# ---------------------------------------------------------------------------
# F13 / Makefile — test target present
# ---------------------------------------------------------------------------
def test_makefile_has_test_target():
    if not MAKEFILE.exists():
        pytest.skip("Makefile отсутствует")
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "test:" in content
    assert "lint:" in content


def test_pyproject_has_requires_python():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "requires-python" in data["project"]
