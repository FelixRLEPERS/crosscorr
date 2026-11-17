# Release checklist v1.6.5 — Dst correction

**Created:** 2026-11-18 (post-verification round)
**Branch:** `fix/dst-parser` (HEAD `441d65c`, pushed)
**Corrected PDFs sent:** 2026-11-17 (main.pdf → editorial; Manuscript 2026SW005535)

## GATE — do not tag / do not touch Zenodo yet

Wait for the Space Weather editor to confirm that the corrected PDFs are in the
GEMS system (and whether a RU version is required). Reasoning: if the editor
asks for a re-upload through the portal or for the RU version, the work becomes
v1.6.6 — tagging/depositing now would force a re-tag and a new Zenodo version
for nothing. Zenodo deposits are immutable; do not spend a version id early.

## Verification results (2026-11-18, passed)

- **644-hour reconciliation is exact:** restored hours split 415 storm
  (Dst < −50) + 151 quiet (Dst > −20) + 78 excluded (−50…−20) = 644; totals
  886 + 8962 + 3304 = 13 152; old 471 + 8811 + 3226 = 12 508.
- **Independent data check of the restored hours:** mean −77.1 nT (arithmetic
  estimate from means −11.5 → −14.7: −76.8), min −406, max +66 — direction and
  magnitude plausible (storm main phases + tails).
- **Scope correct:** Kp arm, headline (−23.9/−22.5/−30.1), spatial, Table 4/6/11/12
  untouched; only Dst content changed; EN/RU Dst numbers in sync.
- **Comparative flip fixed** ("more storm hours … 886 versus 594"); Open Research
  URL `dst_realtime/` → `dst_provisional/` (EN + RU).
- **`checksums_v1.6.5.txt`:** 355 tracked + 3 local (gitignored) pins, sectioned
  this session. Verified with `sha256sum -c`: full file → 358 OK, exit 0;
  SECTION 1 only (`head -n 363 … | sha256sum -c -`) → 355 OK, exit 0 — the
  fresh-clone path works. The 3 local lines are kept on purpose: they pin the
  corrected PDFs/parquet, which are exactly the artifacts NOT in git.

## REQUIRED before tagging v1.6.5 (verification-round items 1–4)

- [ ] **1. Code Availability pin v1.6.4 → v1.6.5** (+ concept-DOI note).
      `paper/main.tex:2097–2099`, `paper/main_ru.tex:2226–2228`.
      Why: the corrected PDF currently cites v1.6.4, which still has the buggy
      parser (471 / −96 nT); corrected Table 5 does NOT reproduce from it.
- [ ] **2. New data-version DOI** for the corrected `unified.parquet`
      (13 152 rows / 886 storm). Current data DOI
      `10.5281/zenodo.23802881` contains the BUGGY parquet (12 508 / 471).
      Data Availability must point to the new version
      (`main.tex:2101`, `main_ru.tex:2230`) — otherwise the corrected paper
      cannot be reproduced from its own cited data.
- [ ] **3. Table 2 (tab:provenance), Dst row retrieval date.** Still
      "7--8 Oct 2026" (`main.tex:273–274`, RU `main_ru.tex:315`) — but the 886
      storm hours come from the 17 Nov 2026 re-fetch. Update: retrieval/re-parse
      date, parser version (v1.6.5), and checksum of the new frozen snapshot.
      (Decide whether the Kp/WSPR rows' 7–8 Oct dates stay — they were not refetched.)
- [ ] **4. (optional) Disclosure** of the parser correction in §2.2 / Table 2 or
      in the response letter, for the transparency of the published record.

## NOT REPRODUCED — verification-round item 5 (flag RETRACTED 2026-11-18)

- Claimed RU PLS error: «снижается на 22,5–30,1 **бури**» → «**процента**».
  **No such text exists** in `main_ru.tex`, `main_ru.pdf`, or anywhere else in
  the repo (searched 2026-11-18). Actual state: `main_ru.tex:167` reads
  «снижается на 22,5--30,1 **%**» — correct Russian; EN `main.tex:132` says
  "falls by 22.5--30.1 percent".
- **The verifier retracted the flag** (2026-11-18): their source was a stale /
  corrupted text extraction of `main_ru.pdf` from a KB copy (line 92 there read
  «…30,1 бури»), not the actual file. No fix needed; do not "fix" `%` →
  `процента` speculatively.
- **Residual control (non-blocking, done):** the sent PDFs == current repo PDFs
  — mtimes unchanged since the 2026-11-17 23:48 build/send, SHA-256 == the
  `checksums_v1.6.5.txt` pins, and both copies are archived in
  `audit/pdf_snapshot_2026-11-17_v1.6.5/`. Caveat: the email attachment itself
  cannot be re-hashed from here — the identity argument is "the files attached
  were the ones in `paper/` at send time, and those bytes are pinned + archived".

## After items 1–4 are approved (release sequence — ORDER FIXED 2026-11-18)

Supersedes the earlier order (build → checksums → AI_ASSISTANCE → merge → tag):
it produced PDFs from a NON-final source and could leave the tag pointing at
intermediate checksums. The reliable sequence:

1. **Finalize ALL source edits** — items 1–4 above (Code Availability pin,
   data DOI, Table 2 date, disclosure) **+ `docs/AI_ASSISTANCE.md`** (AGU rule).
2. **Build PDFs from the FINAL source** — `latexmk -pdf main.tex` /
   `main_ru.tex`; must be 0 errors / 0 undefined references.
3. **Regenerate `checksums_v1.6.5.txt`** — byte-pins of exactly the PDFs built
   in step 2 (PDF hashes are build-dependent: CreationDate/ID are not
   reproducible without `SOURCE_DATE_EPOCH`).
4. **Commit everything in one commit** (source + checksums + AI_ASSISTANCE),
   push `fix/dst-parser`.
5. **Merge to `main`** — only after human review.
6. **Tag `v1.6.5`** — the tag's tree then contains the final sources and the
   consistent checksums (PDF bytes themselves are gitignored; archive them as
   Release assets and/or a new `audit/pdf_snapshot_*` dir — see below).
7. **GitHub Release** (attach the final PDFs + `checksums_v1.6.5.txt` as
   assets — this is what a third party can actually download).
8. **Zenodo deposit** → verify by downloading the zip + checksums
   (LESSONS order: tag → push → release → Zenodo).

## Sent-PDF byte archive (closed 2026-11-18)

The bytes of the PDFs sent to the editorial office are archived in
`audit/pdf_snapshot_2026-11-17_v1.6.5/` (`main.pdf`, `main_ru.pdf`, README with
provenance). Verified: snapshot SHA-256 == `checksums_v1.6.5.txt` pins ==
`paper/*.pdf` on disk (mtimes unchanged since the 2026-11-17 23:48 send). This
closes the chain "what the editor received ↔ what the archive holds" —
`sha256sum -c` now has something to compare against even after `paper/` is
rebuilt. Do NOT overwrite this directory when PDFs are rebuilt for the release;
snapshot the new bytes separately.

## Conventions for this file

- `sha256sum -c checksums_v1.6.5.txt` prints a cosmetic
  "improperly formatted" WARNING for the '#' comment lines; the verdict and
  exit code are unaffected (verified with Git for Windows `sha256sum`).
- On a fresh clone check SECTION 1 only:
  `head -n 363 checksums_v1.6.5.txt | sha256sum -c -`
  (do NOT pipe through PowerShell without re-encoding — PS 5.1 pipes strings
  as ASCII and mangles the input; write to a temp file instead).
