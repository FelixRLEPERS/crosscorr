#!/usr/bin/env python
"""Stage the Zenodo v11 data package (unified.parquet with GOES X-ray).

Two-phase (AGENTS.md house pattern):

  Phase 1 (default)  print a report + unified diff of README/checksums edits
  Phase 2 --apply    copy data/processed/unified.parquet -> zenodo_data/,
                     write checksums.txt and the edited README.md

What v11 changes versus the staged (v10) package:

  * rows: the GOES-R XRS flare series (detector_type ``goes_xray``,
    hourly max of the 1-min 1-8A mean, unit ``W/m2``);
  * the ``detector_type`` / ``unit`` vocabularies in the column docs;
  * file size and SHA-256 (checksums.txt + README table row);
  * ETL steps (GOES download from NOAA NCEI) and package version note.

The script is dual-state: it also REFRESHES an already-staged v11
(after an ETL change such as the ``n_unique_tx`` re-pull: new hash/size,
meta vocabulary note, inventory drift) via state-independent regexes
plus conditional one-time updates - applied one-time literals are
skipped, ambiguous patterns (2+ matches) fail loudly.

Upload to Zenodo stays a manual maintainer step; this script only
prepares the staging directory.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "unified.parquet"
STAGE = ROOT / "zenodo_data"
DST = STAGE / "unified.parquet"
README = STAGE / "README.md"
CHECKSUMS = STAGE / "checksums.txt"

GOES_META = (
    "| `goes_xray` | {rows} | `goes_xray_hourly` "
    "(GOES-R XRS L2 1-min mean, hourly max) | {t0} \u2192 {t1} | W/m2 |"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fmt_n(n: int) -> str:
    """84402 -> '84 402' with a regular space (README style)."""
    return f"{n:,}".replace(",", " ")


def collect_stats() -> dict:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    df = pd.read_parquet(SRC)
    inv = {}
    for dtype, grp in df.groupby("detector_type", sort=True):
        ids = sorted(grp["detector_id"].astype(str).unique())
        ts = pd.to_datetime(grp["timestamp_utc"])
        inv[dtype] = {
            "rows": int(len(grp)),
            "n_ids": len(ids),
            "t0": str(ts.min())[:10],
            "t1": str(ts.max())[:16],
            "unit": sorted(grp["unit"].astype(str).unique()),
        }
    return {
        "rows": int(len(df)),
        "cols": list(df.columns),
        "sha": sha256(SRC),
        "size": SRC.stat().st_size,
        "inv": inv,
        "columns": df,
    }


def readme_edits(stats: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (replacements, insertions) for README.md.

    Dual-state by design (fail-loud in every state):

    * fresh v10 -> v11 staging: one-time literals jump straight to the
      final header/meta text;
    * v11 refresh after an ETL change (re-pull / rebuild): state-independent
      regexes (files row, rows sentence, inventory) plus conditional
      one-time updates.

    ``add()`` skips a literal that is absent (already applied) and fails
    on 2+ occurrences; required patterns raise when not found.
    """
    inv = stats["inv"]
    goes = inv.get("goes_xray")
    if goes is None:
        raise SystemExit("goes_xray detector_type absent from unified.parquet")

    text = README.read_text(encoding="utf-8")
    replaces: list[tuple[str, str]] = []
    inserts: list[tuple[str, str]] = []

    def add(old: str, new: str) -> None:
        n = text.count(old)
        if n == 1:
            replaces.append((old, new))
        elif n > 1:
            raise SystemExit(f"ambiguous pattern ({n}x): {old[:70]!r}")

    # -- package header --------------------------------------------------
    v10_header = (
        '**Package prepared:** 2026-10-28 (audit round v1.5.0, task "publish\n'
        'unified.parquet on Zenodo"). Upload to Zenodo is a manual step\n'
        "(performed by the maintainer); this directory is the staging area."
    )
    v11_base = (
        "**Package version:** v11 (2026-10-30) — schema adds `detector_type`\n"
        "`goes_xray` (unit `W/m2`; GOES-R XRS L2 1-min means, aggregated to\n"
        "hourly max) for the Q1 solar-flare control. Previous package (v10,\n"
        "2026-10-28) stays available under the same concept DOI.\n"
        "Upload to Zenodo is a manual step (performed by the maintainer);\n"
        "this directory is the staging area."
    )
    v11_meta = (
        "**Package version:** v11 (2026-10-30) — schema adds `detector_type`\n"
        "`goes_xray` (unit `W/m2`; GOES-R XRS L2 1-min means, aggregated to\n"
        "hourly max) for the Q1 solar-flare control, and `wspr_hourly` meta now\n"
        "stores the per-row unique transmitter count `n_unique_tx`\n"
        "(Selection-Bias control). Previous package (v10,\n"
        "2026-10-28) stays available under the same concept DOI.\n"
        "Upload to Zenodo is a manual step (performed by the maintainer);\n"
        "this directory is the staging area."
    )
    add(v10_header, v11_meta)  # fresh staging jumps to the final text
    add(v11_base, v11_meta)  # refresh of the already-staged v11 header

    # -- files table row: size + sha256 (state-independent) --------------
    m = re.search(r"\| `unified\.parquet` \| [\d\u00a0 ]+ bytes \| `[0-9a-f]{64}` \|", text)
    if not m:
        raise SystemExit("files-table row not found in README")
    new_row = f"| `unified.parquet` | {fmt_n(stats['size'])} bytes | `{stats['sha']}` |"
    if m.group(0) != new_row:
        replaces.append((m.group(0), new_row))

    # -- row/column count sentence (state-independent) -------------------
    m = re.search(r"\*\*[\d\u00a0 ]+ rows ×\s*\n9 columns\*\*", text)
    if not m:
        raise SystemExit("rows/columns sentence not found in README")
    new_sentence = f"**{fmt_n(stats['rows'])} rows ×\n9 columns**"
    if m.group(0) != new_sentence:
        replaces.append((m.group(0), new_sentence))

    # -- inventory lines whose content changed (dynamic) -----------------
    def inv_line(dtype: str) -> str:
        m = re.search(rf"^\| `{re.escape(dtype)}` \|.*\|$", text, flags=re.MULTILINE)
        if not m:
            raise SystemExit(f"inventory line for {dtype} not found in README")
        return m.group(0)

    for dtype, info in inv.items():
        if dtype == "goes_xray":
            continue  # handled as an insertion below
        old_line = inv_line(dtype)
        cells = [c.strip() for c in old_line.split("|")[1:-1]]
        listed_rows = int(cells[1].replace(" ", "").replace("\u00a0", ""))
        if listed_rows != info["rows"]:
            cells[1] = fmt_n(info["rows"])
        if dtype == "wspr_hourly":
            cells[3] = f"{info['t0']} → {info['t1']}"
        if dtype == "wspr":
            cells[2] = re.sub(r"^\d+ receiver", f"{fmt_n(info['n_ids'])} receiver", cells[2])
        new_line = "| " + " | ".join(cells) + " |"
        if new_line != old_line:
            replaces.append((old_line, new_line))

    # -- one-time prose/vocabulary updates (skip when already applied) ---
    add("`wspr` detector, 985 callsigns", "`wspr` detector, 1 206 callsigns")
    add(
        "`wspr_hourly`, `wspr`, `kp`, `dst`, `f107`, `ephemeris` |",
        "`wspr_hourly`, `wspr`, `kp`, `dst`, `f107`, `ephemeris`, `goes_xray` |",
    )
    add(
        "| `unit` | string | `count` (WSPR hourly spot counts), `dB` (spot SNR), "
        "`AU` (ephemeris distances), `unknown` (Kp/Dst/F10.7 as delivered by "
        "upstream services) |",
        "| `unit` | string | `count` (WSPR hourly spot counts), `dB` (spot SNR), "
        "`AU` (ephemeris distances), `W/m2` (GOES X-ray 1–8 Å flux), `unknown` "
        "(Kp/Dst/F10.7 as delivered by upstream services) |",
    )
    add(
        "| `meta` | string (JSON) | Per-row metadata: band/band_index/"
        "mean_snr/max_distance for `wspr_hourly`; granularity for indices; "
        "source URLs/objects elsewhere |",
        "| `meta` | string (JSON) | Per-row metadata: band/band_index/"
        "mean_snr/max_distance/n_unique_tx for `wspr_hourly`; granularity for "
        "indices; source URLs/objects elsewhere |",
    )
    add(
        "4. **Unification** — `unify_schema.py` merges all raw sources into the",
        "5. **Unification** — `unify_schema.py` merges all raw sources into the",
    )

    # -- insertions (guarded: only when the block is absent) -------------
    goest0 = goes["t0"]
    goest1 = goes["t1"][:10]
    unification_anchor = "5. **Unification** — `unify_schema.py` merges all raw sources into the"
    if "**GOES X-ray flare series**" not in text:
        inserts.append(
            (
                unification_anchor,
                "4. **GOES X-ray flare series** — `download_space_weather.py`: NOAA NCEI\n"
                "   GOES-R (`goes18`/`goes16`/`goes19`) XRS L2 1-min means\n"
                "   (`xrsf-l2-avg1m` NetCDF), aggregated to hourly **max**\n"
                "   (`detector_type = goes_xray`, unit `W/m2`;\n"
                f"   {fmt_n(goes['rows'])} rows, {goest0} → {goest1}).\n" + unification_anchor,
            )
        )
    if "| `goes_xray` |" not in text:
        f107_line = (
            "| `f107` | 18 | `f107_index` (NOAA SWPC, monthly sample) | "
            "2024-04-15 → 2026-09-15 | sfu (stored as `unknown`) |"
        )
        inserts.append(
            (
                f107_line,
                f107_line + "\n" + GOES_META.format(rows=fmt_n(goes["rows"]), t0=goest0, t1=goest1),
            )
        )
    return replaces, inserts


def inventory_report(stats: dict) -> str:
    """Actual vs README inventory, informational."""
    lines = ["Detector inventory — actual (unified.parquet) vs README:"]
    readme = README.read_text(encoding="utf-8")
    for dtype, info in stats["inv"].items():
        m = re.search(rf"^\| `{re.escape(dtype)}` \| ([\d  ]+) \|", readme, flags=re.MULTILINE)
        listed = m.group(1).replace(" ", "") if m else "ABSENT"
        actual = str(info["rows"])
        flag = "OK" if listed == actual else "DIFF"
        lines.append(
            f"  [{flag}] {dtype:12s} actual={actual:>7s} readme={listed:>7s} "
            f"ids={info['n_ids']} period={info['t0']}..{info['t1'][:10]}"
        )
    return "\n".join(lines)


def apply_edits(
    text: str,
    replaces: list[tuple[str, str]],
    inserts: list[tuple[str, str]],
    label: str,
) -> str:
    problems: list[str] = []
    for old, new in replaces:
        n = text.count(old)
        if n != 1:
            problems.append(f"  replace ({n}x): {old[:70]!r}")
        else:
            text = text.replace(old, new)
    for anchor, addition in inserts:
        n = text.count(anchor)
        if n != 1:
            problems.append(f"  insert  ({n}x): {anchor[:70]!r}")
        else:
            text = text.replace(anchor, addition)
    if problems:
        print(f"[FAIL] {label}: pattern verification failed, nothing written:")
        print("\n".join(problems))
        raise SystemExit(2)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="stage v11 (default: report + diff)")
    parser.add_argument(
        "--diff-out",
        metavar="PATH",
        default=None,
        help="also write the README diff to PATH as UTF-8 (console-safe)",
    )
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

    stats = collect_stats()
    print(f"source   : {SRC}")
    print(f"sha256   : {stats['sha']}")
    print(f"size     : {stats['size']:,} bytes".replace(",", " "))
    print(f"shape    : {stats['rows']:,} rows x {len(stats['cols'])} columns".replace(",", " "))
    print(inventory_report(stats))

    staged_sha = sha256(DST) if DST.exists() else None
    print(f"staged   : {staged_sha or '(no file)'}")
    if staged_sha == stats["sha"] and stats["sha"] in README.read_text(encoding="utf-8"):
        print("[SKIP] v11 already staged: parquet, README and checksums agree")
        return 0

    replaces, inserts = readme_edits(stats)
    old_readme = README.read_text(encoding="utf-8")
    new_readme = apply_edits(old_readme, replaces, inserts, "README.md")
    diff = "".join(
        difflib.unified_diff(
            old_readme.splitlines(keepends=True),
            new_readme.splitlines(keepends=True),
            fromfile="a/zenodo_data/README.md",
            tofile="b/zenodo_data/README.md",
        )
    )
    print(diff)
    if args.diff_out:
        with open(args.diff_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(diff)
        print(f"[OK] README diff written to {args.diff_out}")

    new_checksum = f"{stats['sha']}  unified.parquet\n"
    old_checksum = CHECKSUMS.read_text(encoding="utf-8")
    print("--- a/zenodo_data/checksums.txt")
    print("+++ b/zenodo_data/checksums.txt")
    print(f"-{old_checksum.rstrip()}")
    print(f"+{new_checksum.rstrip()}")

    if not args.apply:
        print("[CHECK] dry run only; re-run with --apply to stage v11")
        return 0

    shutil.copyfile(SRC, DST)
    assert sha256(DST) == stats["sha"], "post-copy hash mismatch"
    with README.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(new_readme)
    with CHECKSUMS.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(new_checksum)
    print(f"[OK] staged {DST.relative_to(ROOT)} ({stats['size']:,} bytes)".replace(",", " "))
    print("[OK] README.md + checksums.txt updated (LF, no BOM)")
    print(
        "payload="
        + json.dumps(
            {
                "version": "v11",
                "sha256": stats["sha"],
                "bytes": stats["size"],
                "rows": stats["rows"],
                "goes_rows": stats["inv"].get("goes_xray", {}).get("rows"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
