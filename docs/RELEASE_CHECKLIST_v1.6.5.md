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

## NOT REPRODUCED — verification-round item 5

- Claimed RU PLS error: «снижается на 22,5–30,1 **бури**» → «**процента**».
  **No such text exists** in `main_ru.tex`, `main_ru.pdf`, or anywhere else in
  the repo (searched 2026-11-18). Actual state: `main_ru.tex:167` reads
  «снижается на 22,5--30,1 **%**» — correct Russian; EN `main.tex:132` says
  "falls by 22.5--30.1 percent". Action: ask the verifier for the exact
  location; fix only if a real instance is found. Do not "fix" `%` → `процента`
  speculatively.

## After items 1–4 are approved (release sequence, not now)

1. Apply edits → rebuild `paper/main.pdf` + `paper/main_ru.pdf`
   (latexmk; must be 0 errors / 0 undefined refs).
2. Regenerate `checksums_v1.6.5.txt` (or bump to the tag's version name) —
   PDF hashes are build-dependent byte-pins (CreationDate/ID are not
   reproducible without `SOURCE_DATE_EPOCH`).
3. Update `docs/AI_ASSISTANCE.md` in the same commit (AGU rule).
4. Commit to `fix/dst-parser`, push, merge to `main` **only after human review**.
5. Tag `v1.6.5` → push tag → GitHub Release → Zenodo deposit → verify by
   downloading the zip + checksums (LESSONS order: tag → push → release).

## Conventions for this file

- `sha256sum -c checksums_v1.6.5.txt` prints a cosmetic
  "improperly formatted" WARNING for the '#' comment lines; the verdict and
  exit code are unaffected (verified with Git for Windows `sha256sum`).
- On a fresh clone check SECTION 1 only:
  `head -n 363 checksums_v1.6.5.txt | sha256sum -c -`
  (do NOT pipe through PowerShell without re-encoding — PS 5.1 pipes strings
  as ASCII and mangles the input; write to a temp file instead).
