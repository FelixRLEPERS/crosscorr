# Audit — Start of Next Session

Generated: 2026-10-15 (end of session 12)
For: next chat session (MiMo or human)
Purpose: operational snapshot — read this first.

## 1. Where we are (state at generation)

- **Branch:** main
- **HEAD:** `d32bf52` — paper: fix corruption -- repair broken \ref
  macros in sec 2 intro. (Session 12: batches 11-20 + 2 fixes;
  ALL external-audit-round-4 blockers, majors and minors closed.)
- **origin/main:** in sync after session-12 push
- **Project version:** 1.2.0 (pyproject.toml = "1.2.0"; CITATION.cff
  = "1.2.0", date-released 2026-10-15)
- **Zenodo concept DOI:** `10.5281/zenodo.23285958` (**active**)
- **Zenodo version DOI (v1.2.0):** `10.5281/zenodo.23394340`
- **GitHub Release:** v1.2.0 (latest)
- **Latest tag:** `v1.2.0` @`df843b6` (annotated)
- **Title (v1.2.0):** 'Scale-dependent WSPR response to geomagnetic
  storms: frequency dependence and network-size effects on absolute
  loss'
- **PDF:** paper/main.pdf — 25 pages, pdflatex+bibtex clean,
  21 references, 7 tables + provenance table, 5 figures,
  \linenumbers active, Plain Language Summary present.
- **Test files:** 32 (288 passed, `pytest -m "not slow"`,
  session 12 re-run)
- **CI:** ci.yml (only workflow); green on latest pushed HEAD
- **ruff:** clean on project code (crosscorr_lib/scripts/tests);
  15 ruff errors live only in untracked tmp_*.py session scripts.

## 2. What was done in session 12 (2026-10-15, external audit round 4)

Closed ALL 3 blockers + all major + all minor items from external
audit round 4. Commits `f84a3b2..d32bf52` (batches 11-20 + 2 fixes).
Every fix = its own two-phase tmp_fix_*.py (verify -> apply) and
its own commit, per AGENTS.md lessons.

### Phase 0 — reconnaissance (read-only scripts, results below)

- **C5-новая RESOLVED (was B1 in audit):** Table 5 reproduces
  EXACTLY (9/9 rows, diff=0) from the month x hod x dow residual
  model (model A) — audit's B1 was misdiagnosed. Table 4 does NOT
  come from either residual model; it matches the RAW-value drop
  formula 100*(mean_bin - quiet)/quiet exactly (8/8 cells) — the
  same formula as fig 2/3/4, Table 2 Drop%, and Table 8. The audit
  multiplied Table 4 % by quiet_mean, which is invalid because
  Table 4 was never residual-based. Table 2 Delta (-20421/-18285/
  -5178) is also raw (quiet-minus-storm), NOT the sec 3.3 residual
  statistic (-19793/-14847/-4362, in results JSON only).
  Decision (user): fix DEFINITIONS/CAPTIONS, not numbers.
- **.bib:** was 26 keys / 16 cited / 10 unused (not 8).
- **Table 9 live values (verified vs results JSON, exact):**
  20m -22482 [-35044,-2938] ratio 1.10; 40m -26287 [-37144,-12472]
  ratio 1.44; 15m -3627 [-7172,+3738] ratio 0.70 (CI crosses zero).
- **BH-FDR on 9 pairwise:** 5/9 pass (exceptions p_FDR 0.058, 0.058,
  0.097, 0.855) — audit's M2 confirmed.
- **M4 sensitivity (read-only):** occupancy 4.3 epochs/cell
  (range 4-5, zero n<4 cells); self-inclusion shrinkage 23.4%;
  day_of_week residual-variance reduction 13.4/12.7/16.1% (20/40/15m)
  — matches paper claim 12-16%. Residual Delta is 0.97/0.81/0.84x
  raw Delta. LOO baseline flips sign (degenerate for clustered
  data) — deliberately NOT reported.
- **m7 recomputed:** held-out 15m Kp 5-6 anomaly = +4.9% (N=25),
  not +1.4% (N<5) from archived snapshot.

### Phase 1 — blockers (batches 11-13)

- `f84a3b2` batch 11 (B2+N1+N4): Table 9 20m/15m -> live values,
  CIs for all 3 bands, captions/footnote updated, dates unified to
  2026-10-15 (Fig5 caption, tab:baseline caption, sec 4.6, sec 5.5
  item 10; audit filename FINDING_HELDOUT_LIVE_2026-10-13.md kept),
  abstract N1 clause fixed, sec 4.6 ratio range 0.70-1.44, fig5
  band_abs 20m/15m -> 22482/1.10 and 3627/0.70, 15m annotation
  updated, figure regenerated (fig1-4 byte-identical).
- `09f1f09` batch 12 (B3): affiliation -> 'Independent researchers,
  Russia' (user-approved); KP2/KP3 shortened to 138/139 chars of
  source (limit 140); \usepackage{lineno} + \linenumbers; Plain
  Language Summary (~130 words, user-approved draft) after abstract.
- `61be805` batch 13 (N2): sec 3.4 ESS 610/793/743 relabelled
  epochs (= 1830/2379/2229 h); 'each hour as independent' ->
  'each epoch as independent'.

### Phase 2 — major (batches 14-19)

- `dc5bc10` batch 14 (M2): Conclusion #2 '7/9' -> '5 of 9 survive
  BH'; Table 5 caption nominal+BH note; sec 4.2 nominal wording.
- `65e10b4` batch 15 (M5+m11): sec 4.5 inversion paragraph (training
  38.7/27.7/27.2 vs held-out 22.1/26.7/29.0 for 15/20/40m + power/
  season/sporadic-E factors); Conclusion #5 -> 'Dual mechanism
  (training period; seasonal replication pending)'.
- `85d6042` batch 16 (M8): 4 new citations (efron1993 sec 3.2,
  gonzalez1994+tsurutani2003 intro, mitra1974 sec 5.5 SIDs,
  whitehead1989 sec 5.5 sporadic-E); 5 entries deleted from .bib
  (wilcoxon1945, schunk2009, hargreaves1992, goodman1992,
  ratcliffe1972 — user-approved); labelle2023 pages->eid 1184171;
  cerwin2026 eid 1723511. Post-condition: cited == bib == 21 keys.
- `1842897` batch 17 (N3): sec 3.6 check 3 MUF-range citation
  frissell2016,themens2021 -> davies1990 (those two works do not
  contain the 30-60% range).
- `396bb3f` batch 18 (M3+C5+M4): Eq (eq:drop) in sec 3.2 — drops
  are raw-value differences / quiet mean; Table 2 caption discloses
  the raw-Delta + residual-p mix (C5-новая); Table 4/fig2 captions
  and sec 4.2 prose drop the word 'residual'; Table 5 caption defines
  its Delta as residual-based (separate quantity); sec 3.1 M4
  paragraph (occupancy 4.3/cell, 23% self-inclusion shrinkage,
  type-I error unaffected, residual Delta 0.97/0.81/0.84x raw).
  NOTE: M4 and M3 scripts were both applied before this commit, so
  the M4 paragraph rode along in the M3 commit message.
- `6a9fbc1` batch 19 (M1): provenance table (tab:provenance) after
  Table 1 — training/Kp/Dst retrieved 7-8 Oct 2026 frozen in
  unified.parquet; held-out: archived 8 Oct 2026, live re-download
  15 Oct 2026 (dates from fs/git evidence per user decision); intro
  sentence links the table.
- `98a22d0` batch 20 (minors m1,m3-m8,m12,m13): -48.2->-48.3;
  Table 3 caption 3226 excluded hours; Table 6 caption 158/198 +
  2254/3035 coverage; rho=-0.13 over all epochs; spots/tx/h units;
  anomaly +4.9% (N=25, live); KSG paragraph -> own Limitations item;
  Table 7 caption shared-Kp note; sec 2.1 storm-share 6.5% vs 4.6%.
- `5568b27` batch 20 fix-up: Limitations item ref 9 -> 10 (KSG item
  shifted the numbering).
- `d32bf52` corruption repair: heredoc double-escaping mangled
  \ref in sec 2 intro (CR before 'ef'); restored both Table refs.
  Lesson recorded in AGENTS.md candidates (see §5).

## 3. Open loops (what is NOT closed)

- **Zenodo live-cache upload** — held-out per-band parquet caches
  (results/heldout_3band_{20m,40m,15m}_2026-10-15.parquet +
  heldout_3band_2026-10-15.json) are gitignored; user was asked
  whether to archive them to Zenodo as a separate file (manual
  web step). NOT YET DONE.
- **v1.3.0 release** — not cut. Paper is submit-ready modulo
  endorsement; consider a release after user review of the PDF.
- **arXiv endorsement** — Frissell follow-up 2026-10-28; HamSCI
  mailing list as second channel.
- **2FA on GitHub** — deadline 25 Nov 2026.
- **Legacy Zenodo concept** `23283375` — still contains retracted
  claim; options: deprecate or annotate.
- **H-2** (style sweep outside code dirs), **D/E/J/K/L** — deferred
  to Space Weather.
- **LOO baseline** — sign-flipping leave-one-out residual baseline
  observed in M4 recon (degenerate with clustered storms in
  4-5-obs cells); not reported; revisit if a reviewer asks.

## 4. Ready for next session

- audit/BACKLOG_2026-10-12_v11.md (canonical findings)
- docs/HANDOFF_2026-10-11.md (structure + policy)
- docs/AUDIT_START_NEXT_SESSION.md (this file)
- AGENTS.md (model rules, pre-commit, lessons §)
- paper/main.tex (manuscript, references v1.2.0; 21 bib keys)
- scripts/perm_test_18mo_3band.py
- scripts/make_paper_figures.py (fig5 band_abs = live values)
- results/heldout_3band_2026-10-15.json (live held-out cache)
- paper/main.pdf (25 pages, rebuilt clean in session 12)

## 5. What NOT to do (anti-patterns)

Consolidated in **AGENTS.md → Уроки**. Session 12 additions:

- **Heredoc double-escaping on Windows:** a `python - <<'PYEOF'`
  heredoc inside Git Bash collapsed `\\ref` to `\ref`, which Python
  interpreted as a CR escape -> silently corrupted two \ref macros
  in main.tex (detected only at the next commit review). RULE: for
  LaTeX backslash edits use a written .py file (tmp_fix_*.py with
  Phase-1 verify), NEVER inline heredocs. Dump bytes with repr()
  after any automated edit that touches backslashes.
- **read_text/write_text newline trap:** read_text() universal-
  newline-normalizes CR -> LF; mixing read_text/write_text on a
  CRLF file rewrites every line (1256-line diff from a 1-line
  edit). Prefer read_bytes/write_bytes with explicit BOM handling.
- **git commit --amend + renormalize trap:** amending a commit that
  contains a worktree-written CRLF file with `* text=auto` can
  store CRLF in the blob (renormalize diff was empty). Fix: reset
  --soft, convert file to LF explicitly, re-add, re-commit.
- HANDOFF-уроки 1–8 (session 2/3) and session 5/11 lessons still
  apply (see AGENTS.md).

## 6. First commands to run in next session

    cd g:\crosscorr
    git fetch origin
    git status -sb
    git log --oneline -14
    python -m ruff check .
    python -m pytest -m "not slow" -q

If `ahead > 0` → push before working (CLI, credential.helper
configured).

## 7. Recommended next tasks (in order)

1. **User review of paper/main.pdf** (25 pages) — all audit-4
   blockers closed; look at Table 9, fig5, PLS, Key Points.
2. **Zenodo live-cache decision** (open loop §3) — upload the
   three held-out parquets + JSON as a versioned supplement,
   update Data Availability if done.
3. **arXiv submission** once endorsement arrives:
   rebuild PDF, verify author list/affiliations (now 'Russia',
   no placeholder), upload, choose categories, record arXiv ID.
4. **Space Weather prep** (D/E/J/K/L) if endorsement is slow.

## 9. Quick reference — where things live

    audit/BACKLOG_2026-10-12_v11.md    — findings tracker
    docs/HANDOFF_2026-10-11.md         — structure + policy
    docs/AUDIT_START_NEXT_SESSION.md   — this file
    docs/DELTA_2026-10-14.md           — session 7-11 journal
    audit/REVIEWER2_FULL_AUDIT.txt     — external audit round 4
    audit/FINDING_HELDOUT_LIVE_2026-10-13.md — HELDOUT-LIVE finding
    audit/NUMBERS_MAP_2026-10-15.md    — numbers map (session 10)
    AGENTS.md                          — model rules + lessons
    paper/main.tex                     — manuscript
    paper/references.bib               — 21 keys, all cited
    scripts/perm_test_18mo_3band.py    — perm test (model A)
    scripts/make_paper_figures.py      — figures + fig5 band_abs
    results/heldout_3band_2026-10-15.json — live held-out cache
    results/perm_test_18mo_3band.json  — pairwise p-values source

## 10. Model policy (from HANDOFF)

  - MiMo: default. File edits, git ops, multi-step tasks.
  - Bonsai 2 27B (local): read-only analysis, new-file
    creation. Do NOT give file-edit tasks.
  - Qwen 2.5 Coder 7B: not used (hallucinations on review).

## Metadata

- Generated by: MiMo via OpenCode
- Generated at: 2026-10-15 (session 12 tail)
- Source HEAD: d32bf52 (corruption repair)
- Sources read: git log, AGENTS.md, DELTA_2026-10-14.md,
  REVIEWER2_FULL_AUDIT.txt (round 4, via chat prompt),
  paper/main.tex, paper/references.bib, results JSONs,
  tmp_verify_T4_T5.py / tmp_verify_heldout_live.py /
  tmp_verify_M4_sensitivity.py outputs (session 12).
