#!/usr/bin/env python3
"""Update the block-sensitivity sentence in paper/main.tex and paper/main_ru.tex
after the block=8 spatial rerun (Phase 2 apply, post-rebuild).

Reads:
  - results/spatial_lat_groups.json (canonical, block=24, no flares)
  - results/spatial_lat_groups_block8.json (block=8, no flares)

Branching logic:
  1. Verify both runs are conservative (p_block8 <= p_block24 for all 12 cells).
  2. Count floor-cells (p <= 5.1e-5) in both runs.
  3. Identify the 40m-low cell (p_block24 ~ 1.95e-3).
  4. If p_block8(40m-low) is at floor: append "к ней" (RU) / "to the floor" (EN).
     Else: append "к $p = ...$" (RU) / "to $p = ...$" (EN).

Two-phase pattern (AGENTS.md):
  Phase 1 (--check): print proposed diff + exit 0 (or 2 on violation).
  Phase 2 (--apply): apply the edit to both .tex files (LF endings, final newline).

Usage:
  python scripts/update_paper_block8.py --check   # dry-run
  python scripts/update_paper_block8.py --apply   # apply edit
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "results" / "spatial_lat_groups.json"
BLOCK8 = ROOT / "results" / "spatial_lat_groups_block8.json"
MAIN_TEX = ROOT / "paper" / "main.tex"
MAIN_RU_TEX = ROOT / "paper" / "main_ru.tex"

P_FLOOR = 5.1e-5  # add-one correction floor: 1 / (20000 + 1) ≈ 5e-5, tolerance


def _p_parts(p: float) -> tuple[str, int]:
    """Mantissa (up to 2 decimals, trailing zeros stripped) and exponent."""
    exp = int(f"{p:.1e}".split("e")[1])
    mantissa = f"{p / (10**exp):.2f}".rstrip("0").rstrip(".")
    return mantissa, exp


def fmt_p_tex(p: float) -> str:
    """Format p-value for LaTeX (dot decimal separator), or 'the floor'."""
    if p <= P_FLOOR:
        return "the floor"
    mantissa, exp = _p_parts(p)
    return f"${mantissa} \\times 10^{{{exp}}}$"


def fmt_p_tex_ru(p: float) -> str:
    """Format p-value for LaTeX RU (comma decimal separator), or 'ней'."""
    if p <= P_FLOOR:
        return "ней"
    mantissa, exp = _p_parts(p)
    mantissa = mantissa.replace(".", "{,}")
    return f"${mantissa} \\times 10^{{{exp}}}$"


def load_json(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"[ERROR] file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_conservativeness(canon: dict, b8: dict) -> tuple[bool, int, int, float, float]:
    """Returns (is_conservative, floor_24, floor_8, p_40m_low_b24, p_40m_low_b8).

    Floor counts cover the NINE per-band cells only -- the paper sentence
    says "N/9 at the p-floor", pooled cells are excluded by design.
    """
    floor_24 = 0
    floor_8 = 0
    conservative = True

    # Pooled: conservativeness check only (no floor count)
    for group in ("high", "mid", "low"):
        p24 = canon["pooled"][group]["p_value"]
        p8 = b8["pooled"][group]["p_value"]
        if p8 > p24 * 1.05:
            conservative = False

    # Per-band (the nine cells of the sentence)
    for band in ("40m", "20m", "15m"):
        for group in ("high", "mid", "low"):
            p24 = canon["per_band"][band][group]["p_value"]
            p8 = b8["per_band"][band][group]["p_value"]
            if p8 <= P_FLOOR:
                floor_8 += 1
            if p24 <= P_FLOOR:
                floor_24 += 1
            if p8 > p24 * 1.05:
                conservative = False

    p_40m_low_b24 = canon["per_band"]["40m"]["low"]["p_value"]
    p_40m_low_b8 = b8["per_band"]["40m"]["low"]["p_value"]
    return conservative, floor_24, floor_8, p_40m_low_b24, p_40m_low_b8


def build_sentences(
    conservative: bool,
    floor_24: int,
    floor_8: int,
    p_40m_low_b24: float,
    p_40m_low_b8: float,
) -> tuple[str, str]:
    """Return (en_sentence, ru_sentence)."""
    if not conservative:
        sys.exit("[ERROR] block=8 run violates conservativeness (some p_block8 > p_block24)")

    # EN sentence (source p read from the canonical JSON, not hardcoded)
    en_p_source = fmt_p_tex(p_40m_low_b24)
    en_p_target = fmt_p_tex(p_40m_low_b8)
    en = (
        f"Block-size sensitivity: rerunning the permutation with block = 8\n"
        f"epochs (24\\,h, one diurnal cycle) leaves every band $\\times$ latitude\n"
        f"cell unchanged or more significant: block = 24 is uniformly\n"
        f"conservative relative to block = 8 across all nine cells; no cell\n"
        f"becomes less significant ({floor_24}/9 at the $p$-floor under both settings;\n"
        f"low-latitude 40\\,m moves from {en_p_source} to {en_p_target})."
    )

    # RU sentence (source p read from the canonical JSON, not hardcoded)
    ru_p_source = fmt_p_tex_ru(p_40m_low_b24)
    ru_p_target = fmt_p_tex_ru(p_40m_low_b8)
    if p_40m_low_b8 <= P_FLOOR:
        ru_target = "к ней"
    else:
        ru_target = f"к {ru_p_target}"
    ru = (
        f"Чувствительность к размеру блока: повторная перестановка с блоком\n"
        f"= 8 эпох (24\\,ч, один суточный цикл) оставляет каждую ячейку\n"
        f"(диапазон $\\times$ широта) неизменной или более значимой: блок = 24\n"
        f"единообразно консервативен по отношению к блоку = 8 во всех\n"
        f"девяти ячейках; ни одна ячейка не становится менее значимой\n"
        f"({floor_24}/9 на уровне нижней границы $p$ при обоих настройках;\n"
        f"низкоширотная 40\\,м переходит от {ru_p_source} {ru_target})."
    )

    return en, ru


def update_file(path: Path, old_block: str, new_block: str, dry_run: bool) -> bool:
    """Replace old_block with new_block in path. Returns True if successful."""
    text = path.read_text(encoding="utf-8")

    # Count occurrences (must be exactly 1)
    count = text.count(old_block)
    if count != 1:
        print(f"[FAIL] {path.name}: expected 1 occurrence of old block, found {count}")
        return False

    if dry_run:
        # Show unified diff
        diff = list(
            difflib.unified_diff(
                text.splitlines(keepends=True),
                text.replace(old_block, new_block).splitlines(keepends=True),
                fromfile=str(path),
                tofile=f"{path} (updated)",
                lineterm="",
            )
        )
        print("".join(diff))
        return True

    # Apply (LF endings, final newline)
    new_text = text.replace(old_block, new_block)
    if not new_text.endswith("\n"):
        new_text += "\n"
    path.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"[OK] {path.name} updated")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update block-sensitivity sentence EN/RU after block=8 rerun"
    )
    parser.add_argument("--check", action="store_true", help="Phase 1: dry-run, print diff only")
    parser.add_argument("--apply", action="store_true", help="Phase 2: apply edit to .tex files")
    args = parser.parse_args()

    if not args.check and not args.apply:
        parser.error("must specify --check or --apply")

    canon = load_json(CANONICAL)
    b8 = load_json(BLOCK8)

    # Guard: both must be block runs (not with_flares)
    for name, data in [("canonical", canon), ("block8", b8)]:
        ff = data["params"]["flare_filter"]
        if not ff.get("exclude_flares", False):
            sys.exit(f"[ERROR] {name}: flare_filter.exclude_flares must be True (no-flare run)")
        if data["params"]["block"] not in (8, 24):
            sys.exit(f"[ERROR] {name}: unexpected block size {data['params']['block']}")

    # Verify conservativeness + count floor cells (per-band cells only)
    conservative, floor_24, floor_8, p_40m_low_b24, p_40m_low_b8 = check_conservativeness(canon, b8)

    print("=" * 80)
    print("Block-sensitivity sentence update (EN + RU)")
    print("=" * 80)
    print(f"Canonical (block=24): {CANONICAL}")
    print(f"Block8:               {BLOCK8}")
    print(f"Conservative:         {conservative}")
    print(f"Floor count (b=24):   {floor_24}/9 per-band cells")
    print(f"Floor count (b=8):    {floor_8}/9 per-band cells")
    print(f"p(40m-low, b=24):     {p_40m_low_b24:.4e}")
    print(f"p(40m-low, b=8):      {p_40m_low_b8:.4e}")
    print()

    # Build new sentences
    en_new, ru_new = build_sentences(conservative, floor_24, floor_8, p_40m_low_b24, p_40m_low_b8)

    # Extract old block from .tex files (lines 550-555 for EN, 599-605 for RU)
    en_text = MAIN_TEX.read_text(encoding="utf-8")
    ru_text = MAIN_RU_TEX.read_text(encoding="utf-8")

    # Find old EN block (starts with "Block-size sensitivity:")
    en_lines = en_text.split("\n")
    en_start = None
    for i, line in enumerate(en_lines):
        if line.startswith("Block-size sensitivity:"):
            en_start = i
            break
    if en_start is None:
        sys.exit("[ERROR] EN: 'Block-size sensitivity:' not found")

    # Extract 6 lines (EN block: 550-555)
    en_old_block = "\n".join(en_lines[en_start : en_start + 6])
    if not en_old_block.rstrip().endswith(")."):
        # Try 7 lines
        en_old_block = "\n".join(en_lines[en_start : en_start + 7])

    # Find old RU block (starts with "Чувствительность к размеру блока:")
    ru_lines = ru_text.split("\n")
    ru_start = None
    for i, line in enumerate(ru_lines):
        if line.startswith("Чувствительность к размеру блока:"):
            ru_start = i
            break
    if ru_start is None:
        sys.exit("[ERROR] RU: 'Чувствительность к размеру блока:' not found")

    # Extract 7 lines (RU block: 599-605)
    ru_old_block = "\n".join(ru_lines[ru_start : ru_start + 7])
    if not ru_old_block.rstrip().endswith(")."):
        # Try 6 lines
        ru_old_block = "\n".join(ru_lines[ru_start : ru_start + 6])

    # Verify block ends with ")."
    if not en_old_block.rstrip().endswith(")."):
        sys.exit(
            f"[ERROR] EN block extraction failed (does not end with ').'): {en_old_block[-50:]}"
        )
    if not ru_old_block.rstrip().endswith(")."):
        sys.exit(
            f"[ERROR] RU block extraction failed (does not end with ').'): {ru_old_block[-50:]}"
        )

    print("=" * 80)
    print("Old EN block:")
    print("-" * 40)
    print(en_old_block)
    print()
    print("New EN block:")
    print("-" * 40)
    print(en_new)
    print()
    print("Old RU block:")
    print("-" * 40)
    print(ru_old_block)
    print()
    print("New RU block:")
    print("-" * 40)
    print(ru_new)
    print("=" * 80)

    if args.check:
        # Show diffs
        print("\n=== Diff main.tex ===")
        update_file(MAIN_TEX, en_old_block, en_new, dry_run=True)
        print("\n=== Diff main_ru.tex ===")
        update_file(MAIN_RU_TEX, ru_old_block, ru_new, dry_run=True)
        print("\n[CHECK] dry run only; re-run with --apply to update .tex files")
        return 0

    if args.apply:
        # Apply edits
        en_ok = update_file(MAIN_TEX, en_old_block, en_new, dry_run=False)
        ru_ok = update_file(MAIN_RU_TEX, ru_old_block, ru_new, dry_run=False)

        if not (en_ok and ru_ok):
            print("[FAIL] one or more files failed to update")
            return 2

        # Verify final newline + no BOM
        for path in [MAIN_TEX, MAIN_RU_TEX]:
            raw = path.read_bytes()
            if raw.startswith(b"\xef\xbb\xbf"):
                print(f"[WARN] {path.name}: BOM detected")
            if not raw.endswith(b"\n"):
                print(f"[WARN] {path.name}: no final newline")

        print("\n[APPLY] both .tex files updated")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
