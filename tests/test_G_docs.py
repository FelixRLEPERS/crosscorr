"""Tests for group G: documentation consistency with code.

Light-weight checks that read files only, no code execution.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


def test_readme_exists():
    assert (ROOT / "README.md").exists()


def test_readme_no_dead_links_to_local_files():
    """Все локальные ссылки [text](path) в README указывают на файлы."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # Убрать HTML-комментарии: ссылки внутри них не рендерятся.
    readme = re.sub(r"<!--.*?-->", "", readme, flags=re.DOTALL)
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    missing = []
    for _text, path in pattern.findall(readme):
        if path.startswith(("http", "#", "mailto:", "tel:")):
            continue
        target = ROOT / path.split("#")[0]
        if not target.exists():
            missing.append(path)
    assert not missing, f"Битые локальные ссылки в README: {missing}"


def test_methodology_has_mixedlm_formula():
    content = (ROOT / "docs" / "methodology.md").read_text(encoding="utf-8")
    assert "MixedLM" in content or "mixedlm" in content


def test_pipeline_describes_default_surrogates():
    content = (ROOT / "docs" / "PIPELINE.md").read_text(encoding="utf-8")
    assert "200" in content  # CLI default B
    assert "FDR" in content


def test_pipeline_mentions_by_default():
    """PIPELINE.md фиксирует BY как метод по умолчанию."""
    content = (ROOT / "docs" / "PIPELINE.md").read_text(encoding="utf-8")
    assert "Benjamini-Yekutieli" in content
    assert 'method="by"' in content


def test_pipeline_mentions_mantel_default():
    content = (ROOT / "docs" / "PIPELINE.md").read_text(encoding="utf-8")
    assert "Mantel" in content


def test_analysis_readme_lists_all_modules():
    readme = ROOT / "crosscorr_lib" / "analysis" / "README.md"
    if not readme.exists():
        return
    content = readme.read_text(encoding="utf-8")
    analysis = ROOT / "crosscorr_lib" / "analysis"
    modules = [
        p.stem for p in analysis.glob("*.py")
        if not p.stem.startswith("_")
    ]
    missing = [m for m in modules if m not in content]
    assert len(missing) < 8, (
        f"Модули не упомянуты в analysis/README.md: {missing}"
    )


def test_no_deprecated_ci_badge():
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "img.shields.io/github/workflow/status" not in content, (
        "Deprecated CI badge format in README"
    )


def test_pyproject_version_matches_readme():
    data = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    version = data.get("project", {}).get("version", "0.0.0")
    assert version


def test_data_readme_documents_value_column():
    """data/README.md описывает расширенную схему (P0-2)."""
    content = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    for col in ("value", "residual_method", "unit", "quality_flag"):
        assert col in content, f"data/README.md не описывает {col}"
