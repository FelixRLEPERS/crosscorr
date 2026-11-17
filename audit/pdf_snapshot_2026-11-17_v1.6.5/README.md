# PDF snapshot — Dst correction v1.6.5 (bytes sent to editorial, 2026-11-17)

This directory archives the **exact bytes** of the corrected PDFs handed to the
Space Weather editorial office (Manuscript 2026SW005535, correction round).

Purpose: close the byte-pin chain started in `checksums_v1.6.5.txt`. That file
pins `paper/main.pdf` / `paper/main_ru.pdf` by SHA-256, but both paths are
gitignored — without this snapshot a fresh clone would have nothing to compare
against, and `sha256sum -c` would fail on regenerated PDFs (expected: the
build is not deterministic, see below).

## Files

| File | Bytes | SHA-256 | Source path at send time |
|---|---|---|---|
| `main.pdf` | 1 048 274 | `5ca543f89b494e01…` (full hash in `checksums_v1.6.5.txt`, line `paper/main.pdf`) | `G:\crosscorr\paper\main.pdf` |
| `main_ru.pdf` | 1 255 901 | `550df6ae5d023675…` (full hash in `checksums_v1.6.5.txt`, line `paper/main_ru.pdf`) | `G:\crosscorr\paper\main_ru.pdf` |

Build: latexmk (MiKTeX), 2026-11-17 23:48 local, branch `fix/dst-parser`
(commit `74ed959`); 0 errors / 0 undefined references in both logs.

## Verification (done 2026-11-18)

- snapshot bytes == `paper/*.pdf` bytes at the time of the editorial send
  (mtime unchanged since 2026-11-17 23:48; SHA-256 re-hashed == pin) — MATCH
  for both files;
- `sha256sum -c checksums_v1.6.5.txt` (full) → 358 OK, exit 0.

To re-verify later:

```bash
sha256sum audit/pdf_snapshot_2026-11-17_v1.6.5/main.pdf audit/pdf_snapshot_2026-11-17_v1.6.5/main_ru.pdf
# compare with the paper/main.pdf and paper/main_ru.pdf lines in checksums_v1.6.5.txt
```

## Notes

- PDF SHA-256 pins are **byte pins of these specific PDFs**, not
  reproducible-build targets: pdfTeX writes CreationDate/ID, so a fresh LaTeX
  build produces different bytes (determinism would require
  `SOURCE_DATE_EPOCH` at build time).
- When PDFs are rebuilt for the v1.6.5 release (after items 1–4 of
  `docs/RELEASE_CHECKLIST_v1.6.5.md`), re-snapshot the new bytes and regenerate
  `checksums_v1.6.5.txt` — do not overwrite this directory: it records what the
  editor actually received in this round.
