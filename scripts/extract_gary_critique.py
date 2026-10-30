"""Extract text from docs/reviews/gary_critique_v1.1.0.pdf.

Phase-1 step of the Gary critique review (session 2026-10-30).
Tries pdfplumber first, falls back to PyPDF2, writes UTF-8 (no BOM)
with explicit LF newlines per AGENTS.md rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "reviews" / "gary_critique_v1.1.0.pdf"
DST = ROOT / "docs" / "reviews" / "gary_critique_extracted.txt"


def extract_pdfplumber(path: Path) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            parts.append(f"--- page {i} ---\n{text}")
    return "\n".join(parts)


def extract_pypdf(path: Path, module: str = "pypdf") -> str:
    if module == "PyPDF2":
        from PyPDF2 import PdfReader
    else:
        from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        parts.append(f"--- page {i} ---\n{text}")
    return "\n".join(parts)


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: source PDF not found: {SRC}")
        return 1

    text = ""
    backend = ""
    chain = (
        ("pdfplumber", extract_pdfplumber),
        ("pypdf", extract_pypdf),
        ("PyPDF2", lambda p: extract_pypdf(p, module="PyPDF2")),
    )
    for name, fn in chain:
        try:
            text = fn(SRC)
            backend = name
            break
        except ImportError:
            print(f"{name}: not installed, trying next")
        except Exception as exc:  # noqa: BLE001 - report and try next backend
            print(f"{name}: failed ({exc!r}), trying next")

    if not text.strip():
        print("ERROR: no backend could extract text")
        return 2

    # UTF-8 no BOM, explicit LF, final newline (AGENTS.md).
    DST.write_bytes(
        text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n").encode("utf-8") + b"\n"
    )
    print(f"backend={backend}")
    print(f"chars={len(text)}")
    print(f"written={DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
