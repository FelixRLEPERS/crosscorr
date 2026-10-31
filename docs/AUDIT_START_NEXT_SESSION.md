# Audit — Start of Next Session

Generated: 2026-10-15 (session 15), refreshed 2026-10-31 (v1.6.1, HOLD)
For: next chat session (MiMo or human)
Purpose: operational snapshot — read this first.

## 1. Where we are (state at generation)

- **Mode:** HOLD — submission-ready, ждём Гэри (HamSCI Science telecon
  2026-11-05); paper/ и crosscorr_lib/ заморожены, только docs-правки.
- **Branch:** main
- **HEAD:** `a174ad2` — docs: sync cover letter date and finalize
  v1.6.1 DOI references (pushed; origin/main synced 2026-10-31).
- **Project version:** 1.6.1 — CITATION.cff = 1.6.1; pyproject.toml
  бампнут до 1.6.1 этим же docs-коммитом.
- **Zenodo concept DOI:** `10.5281/zenodo.23285958` (**active**)
- **Zenodo code version DOI (v1.6.1):** `10.5281/zenodo.23838116`
  (README, CITATION.cff и Cover Letter указывают на него; DOI v1.6.0
  = 23835569 — исторический)
- **Zenodo dataset v11 (data only):** `10.5281/zenodo.23802881`
- **GitHub Release:** для v1.6.1 ещё НЕ создан (manual, user via UI)
- **Latest tag:** `v1.6.1` @`af56edb` (annotated `5eaddaf`);
  v1.6.0 @`81efbf3`
- **Title:** 'Scale-dependent WSPR response to geomagnetic
  storms: frequency dependence and network-size effects on absolute
  loss'
- **PDFs:** paper/main.pdf — 39 pages (EN); paper/main_ru.pdf —
  43 pages (RU); Cover_Letter_SpaceWeather.pdf — 2 pages. pdflatex
  чист на последней сборке (2026-10-31): 0 errors,
  0 undefined refs, 0 Overfull.
- **Tests:** 369 passed, 2 deselected (`pytest -m "not slow"`,
  2026-10-31); ruff + mypy clean; CI green.
- **CI:** ci.yml (only workflow); green on latest pushed HEAD
- **Untracked (ожидаемые):** `checksums_v1.6.0.txt`,
  `checksums_v1.6.1.txt`, `results/perm_test_18mo_3band_fdr.json`.

## 2. What was done in sessions 12–13 (2026-10-15, external audit round 4)

Session 12 closed ALL 3 blockers + all major + all minor items
from external audit round 4. Commits `f84a3b2..d32bf52` (batches
11-20 + 2 fixes). Every fix = its own two-phase tmp_fix_*.py
(verify -> apply) and its own commit, per AGENTS.md lessons.
Session 13 added the residual cleanups and v1.3.0 prep (see
"Session 13" block at the end of this section).

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

### Session 13 — 2026-10-15 (C1 residuals + v1.3.0 prep)

- `3f38bc2` — paper: C1 residual `N = 720 hours` -> `epochs` in
  sec 5.5 item 10 (held-out series is 3-hourly; unit leftover from
  the C1 fix). Two-phase tmp_fix_final.py.
- `5751740` — paper: same residual in sec 4.6 ('sample for 40m'),
  separate script + commit per stop-condition (file-wide sweep
  found exactly this one other occurrence; no '648 hours' left).
- `974c3b7` — chore: .gitignore `zenodo_v1.3.0/` (upload staging).
- Zenodo staging created (NOT uploaded — manual user step):
  `zenodo_v1.3.0/` = 3 held-out parquets + summary JSON +
  audit/FINDING_HELDOUT_LIVE copy + README.md (60 KB total).
- Table 2 provenance dates AUDITED against file mtimes — all six
  dates match (WSPR/Kp/Dst 7-8 Oct, archived 8 Oct, live 15 Oct);
  no changes needed, no stop-condition triggered.
- `e3f3272` — docs(releases): v1.3.0 release notes
  (docs/releases/v1.3.0.md).
- `3ff87d1` — this AUDIT_START sync.
- `1add3b9` — paper: provenance-table Overfull (69pt unbreakable
  \texttt path) fixed; Overfull count 9 -> 8 (rest pre-existing).
- PDF rebuilt (pdflatex x2): clean, 25 pages, 0 errors,
  0 undefined refs, 8 cosmetic Overfull (<=18pt).

### Session 14 — 2026-10-15 (external audit round 5, Phase A — 3 blockers)

External audit #5 (MiMo-as-Reviewer-2, full text in chat) found 3 blockers
+ 6 serious + 14 minor. User decisions after Phase 0 diagnostics:
**B2 = (ii) narrow windows, B3 = (ii) residual recompute, ntx checks = (i)
delete; strategy = all three subphases in one run.**

Phase 0 (read-only, decision gate — scripts kept in scripts/):
- `diag_heldout_pval.py`: Table 8 p-values reproduce EXACTLY only under
  RAW-value block permutation (6.8e-4 / 6.8e-4 / 0.258 = JSON); under the
  §3.3 residual method: **2e-5 / 2e-4 / 8e-5 — 15m SIGNIFICANT**
  (3/50 000 exceedances). Audit-B3 hypothesis confirmed.
- `diag_daynight_windows.py`: `between(12,18)`/`between(0,6)` select
  epochs {12,15,18}/{0,3,6} = 12–21 / 0–9 UTC; caption remainder 25% vs
  the ~50% implied by literal 6-h windows proves the mismatch.
- `diag_ntx_presence.py`: NO ntx field/code ever existed in git history
  (`git log -S spots_per_tx -- "*.py"` empty); only 71 sampled
  timestamps carry meta.tx; -31.8/+4.0/rho=-0.21 exist only as prose
  (docs/first_result.md:210,217).

Commits:
- `73ac6a4` **A1 (B3)**: `scripts/recompute_heldout_residual.py` ->
  `results/heldout_resid_2026-10-15.json` (verify gate: p match Phase 0
  exactly). Table 8: all three p-values -> 2e-5 / 2e-4 / 8e-5, caption
  adds 'Drop% raw (Eq. 3); p from residual block permutation (§3.3)'.
  Narrative rewritten: Abstract ('all three bands, including 15m
  (p<1e-3)'), KP2 ('all three bands held-out'), Intro #3, §4.5 (exact
  p's + raw-CI-vs-residual-p clarification: 15m Table-10 CI still
  crosses zero — DISCLOSED, not hidden), ordering paragraph, §5.5 item 2,
  Conclusion #3. Removed: 'p=0.26', 'does not reach significance',
  'reduced storm-hour count', 'for this band' (m10), 'negative sign'.
- `867af34` **A2 (B2)**: `make_paper_figures.py` fig4 ->
  `isin([12,15])`/`isin([0,3])`, legend 'epochs 12/15 / 0/3'; fig4
  drop_pct switched to POINT estimate + local seed-42 per cell
  (deterministic — first regen produced RNG-dependent bootstrap means
  deviating up to 0.9pp from expected); RNG **burn block** (old sizes
  82/1107, 76/1147) preserves global stream -> **fig1/2/3/5 verified
  byte-identical, only fig4 changed**. Table 7 = -28.7/-24.8 (20m),
  -20.7/-30.2 (40m), -48.9/-18.7 (15m) with CI, N 53/732 & 58/734;
  caption 111/1466 (arithmetic now consistent: ~50% outside windows);
  9/10 -> **8/8** (Abstract, Fig4 caption, §4.4, >=3-epoch criterion);
  §4.3 daytime 15m -48.9; 'narrowly excludes' -> 'excludes'.
- `332ef5b` **A3 (B1 + ntx)**: §4.1 Dst claim corrected (larger on 20m
  -22081 vs -20421; smaller on 40m -15038 vs -18285; comparable 15m
  -5143 vs -5178 + selection caveat); §3.6 checks 1&4 deleted,
  'Six' -> 'Four' (intro + Conclusion #1); zero ntx remnants.
- Disclosed plan deviation: `scripts/replication_2026.py` day/night
  windows -> isin (same bug class in the planned 6-month replication
  tool) — found by the final grep gate.

Builds: pdflatex x2 after each subphase — 0 errors, 0 undefined refs,
25 pages, warnings = 4x 'h' float (baseline only). Tests: 288 passed.

Session-14 gotchas (record for future fixers):
- Two-phase pre-check counters must match reality: 'transmitter' x5
  (incl. Per-transmitter + hyphens), '9 out of' split across a
  newline — pre-check FAILED **before** write (correct behaviour).
- In tmp_fix_A1_narrative a POST-assert ran before write_bytes ->
  no partial write; fix the assert, rerun, all clean. Assert-before-
  write is a feature, not a bug — do not 'fix' by reordering.
- Never assume a figure's byte-identity after an upstream RNG change:
  verify md5; if it fails, prefer deterministic point-estimate labels +
  explicit stream burn over accepting silent drift.

### Session 15 — 2026-10-15 (audit-5 wrap-up + v1.3.1 release)

Closed the remaining audit-5 items and cut the patch release:

- `4ccf68b` **m4**: Figure 4 cited in §4.4 first sentence
  (`The day/night decomposition (Figure~\ref{fig:daynight})`), Figure 5
  in §4.6 (`point estimate for 40 m (Figure~\ref{fig:baseline}; ...)`)
  — **all 5 figures now have in-text refs**.
- `a59a09c` **v1.3.1 prep**: pyproject/CITATION -> 1.3.1, CITATION doi
  temporarily -> concept 23285958, paper tag pin -> v1.3.1.
  (Gotcha: pyproject/CITATION are **CRLF** — first fixer run failed
  Phase-1 guard before any write; guard relaxed to main.tex-only +
  substring replacements that preserve native endings; diff stayed
  1/1 + 2/2 + 1/1, no EOL churn.)
- **Manual (user):** annotated tag `v1.3.1` @`a59a09c` (`d1f721a`),
  GitHub Release v1.3.1, Zenodo auto-version -> **version DOI
  10.5281/zenodo.23402384**.
- `3b891a0` **DOI patch**: CITATION doi -> 23402384; Code Availability
  rewritten (tag v1.3.1 archived at ...23402384, concept 23285958 as
  resolver, v1.3.0 DOI kept as history, v1.2.0 DOI dropped; Data
  Availability concept-DOI line untouched).

**Audit round 5 FULLY CLOSED** — 3 blockers + maketitle + 5 serious +
14 minor:
- **Blockers:** B1 §4.1 Dst per-band claim (`332ef5b`); B2 day/night
  windows -> literal narrow 12-18/0-6 UTC (`867af34`); B3 held-out ->
  residual permutation of §3.3, **15m now significant (p = 8e-5)**
  (`73ac6a4` — Abstract/KP/§4.5/§5.5/Conclusion #3 rewritten).
- **maketitle** (`976ffa6`): title block had been missing from EVERY
  PDF build in project history (class defines `\maketitle`, main.tex
  never called it — caught only by session-14 final page-1 check);
  same commit removed the cls `\correspondingauthor` bug (dangling
  superscript, lost footnote) — email moved to Acknowledgments.
- **Serious (Phase B):** B-1 baselines -> live 84 096/90 653/16 393
  (+14/+35/+22 %, Abstract & §4.6 38 % -> 35 %; `d9a824d`); B-2
  themens2021 = D-region model, not foF2/MUF (`f682358`); B-3 Davies
  30–60 % category error softened (`1ea0567`); B-4 diurnal 8× ->
  ~2–6× + Fig 1 cited (`4faf50c`); B-5 Table 1 Kp 5 069 (`ee4563f`).
- **Minor:** Phase C batch `2f3a230` (m1 Table 5 header 'residual
  drop'->'drop'; m2 Table 3 caption storm-minus-quiet; m3 Table 4
  delta-scale disclosure; m6 'adjacent'->'all 9 combinations'; m7 Kp
  max 9.0; m9 duration ~9 h; m11 Fig 2 storm-bins caption; m13 scoped
  \sloppy, Overfull 8->6; m14 Table 10 CI provenance) + m4 `4ccf68b`
  (Fig 4/5 cited) + m10 (closed in A1).
- **Skipped as stale/informal (do not re-litigate):**
  - **m5** stale FDR JSON (`results/perm_test_18mo_3band_fdr.json`:
    n_iter=5000, p_raw=0.0 without add-one, no-dow Kp deltas —
    substance re-verified at 50k: all six p = 2e-5);
  - **m8** Dst "42 storm events" unreproducible (gap>12h = 48,
    gap>24h = 41, runs = 96, days = 61 — no rule yields 42);
  - **m12** informal month threshold (">=3 storm epochs per window"
    now stated in the Fig 4 caption after A2).
- PDF: 26 pages (Phase C captions pushed ~4 lines of the reference
  tail onto page 26). Tests: 288 passed (session 14).

## 3. Open loops (what is NOT closed)

All audit-round-5 technical items are CLOSED (sessions 14–15 — full
fix log in the Session 14 / Session 15 blocks of §2, including the
skipped-as-stale m5/m8/m12 decisions).

Remaining external items:

- **arXiv submission** — endorsement: Frissell follow-up 2026-10-28;
  HamSCI telecon 2026-11-05 (Gary Mikitin invited). On acceptance:
  rebuild PDF, verify authors/affiliation, record arXiv ID.
- **2FA on GitHub** — deadline 25 Nov 2026.
- **Legacy Zenodo concept** `23283375` — still contains the retracted
  claim; options: deprecate or annotate.
- **Deferred to Space Weather revision** (unchanged backlog): H-2
  style sweep, D (SEA), E (recovery phase), J (more bands), K (foF2),
  L.

## 4. Ready for next session

- audit/BACKLOG_2026-10-12_v11.md (canonical findings)
- docs/HANDOFF_2026-10-11.md (structure + policy)
- docs/AUDIT_START_NEXT_SESSION.md (this file)
- docs/releases/v1.3.0.md (release notes, prepared)
- AGENTS.md (model rules, pre-commit, lessons §)
- paper/main.tex (manuscript; Code Availability = tag v1.6.0 for the
  core analysis; code DOI 23838116; API-repro notes + Limitations
  item 23; audit-5 + Q1 passes applied)
- docs/submission/Cover_Letter_SpaceWeather.tex/.pdf (date fixed
  2026-10-31, code DOI 23838116)
- checksums_v1.6.1.txt (8 файлов, только tracked-пути)
- scripts/perm_test_18mo_3band.py
- scripts/make_paper_figures.py (fig4 narrow windows + point
  estimates + RNG burn; fig5 band_abs = live values)
- scripts/recompute_heldout_residual.py (Table 8 p-value source)
- scripts/diag_heldout_pval.py / diag_daynight_windows.py /
  diag_ntx_presence.py (audit-5 Phase 0 diagnostics)
- results/heldout_3band_2026-10-15.json (live held-out cache)
- results/heldout_resid_2026-10-15.json (residual p-values, gitignored)
- zenodo_v1.3.0/ (upload staging, gitignored)
- paper/main.pdf (39 pages EN / 43 pages RU, rebuilt clean 2026-10-31)

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

1. **HamSCI Science teleconference — 5 November 2026, 16:00 ET.**
   Материалы готовы: `docs/presentations/hamsci_2026-11-05/`.
2. **Space Weather submission** — всё синхронизировано (cover letter,
   README, CITATION, DOI 23838116); отправка через Wiley UI.
3. **GitHub Release v1.6.1 + Zenodo autozip — manual (user, UI):**
   приложить 2 PDF + `checksums_v1.6.1.txt`.
4. **arXiv submission** — когда придёт endorsement (Frissell/HamSCI).
5. **2FA on GitHub** — deadline 25 Nov 2026.

## 9. Quick reference — where things live

    audit/BACKLOG_2026-10-12_v11.md    — findings tracker
    docs/HANDOFF_2026-10-11.md         — structure + policy
    docs/AUDIT_START_NEXT_SESSION.md   — this file
    docs/releases/v1.3.0.md            — release notes (prepared)
    docs/DELTA_2026-10-14.md           — session 7-11 journal
    zenodo_v1.3.0/                     — upload staging (gitignored)
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
- Generated at: 2026-10-15 (session 15); refreshed 2026-10-31 (v1.6.1)
- Source HEAD: `a174ad2` (v1.6.1 DOI sync; pushed to origin/main)
- Sources read: git log/tags, paper/main.tex, CITATION.cff,
  pyproject.toml, docs/AI_ASSISTANCE.md, results JSONs.

## Session 17 — 2026-10-19 (audit-2026-10-19 closure)

Full audit from third-party model (AUDIT_2026-10-19_scientific.md) verified by MiMo and closed:
- 🔴 B1 (§5.3 contradiction) — fixed in `7b1ad48`
- 🔴 B10 (Fig 2/4 CI inversion) — fixed in `7b1ad48`
- 🔴 B5 (Dst 50k p-value) — artifact generated `results/perm_test_dst_50k.json`, text unchanged
- 🔴 B7 ("42 events") — removed in `7b1ad48`
- 🟡 B6 (Dst block size) — clarified in `fe2adac`
- 🟡 B2-B4 (Keypoints/Abstract 15m caveat) — softened in `fe2adac`
- 🟡 B9 (Makefile) — removed in `fe2adac`
- M4/M5 (`speaker_notes.md`) — fixed in `fe2adac`
- All presentation materials synced.
- Remaining open: only deferred Space Weather backlog items (SEA, foF2, etc.).

## Release v1.4.0
Подготовлен релиз v1.4.0. Включает: Round 3 & 4 audit fixes, adjusted drops, ratio CIs, parquet publication, UT-window terminology.
Status: RELEASED. Version DOI: 10.5281/zenodo.23495246.

## Session 18 — 2026-10-27 (extended held-out Jan–Jun 2026)
- Downloaded missing WSPR hourly data for Apr–Jun 2026 (199 files, 0 errors).
- Created new extract `results/heldout_3band_*_2026h1.parquet` (1441 epochs).
- Recalculated p-values and ratio CIs.
- **Decision:** Keep Jan–Mar as primary held-out; add Jan–Jun as sensitivity check in Limitations/Appendix.
- Frozen v1.4.0 artifacts untouched.
- Implemented 2026-10-28: Limitations bullet + Appendix table `tab:heldout_sensitivity` added to `paper/main.tex` and `paper/main_ru.tex` (EN+RU); detailed numbers remain in `docs/AI_ASSISTANCE.md`.

## Session 2026-10-31 — submission freeze (v1.6.1)

- v1.6.0 (`81efbf3`): Q1 submission revision — flare control, tx-norm,
  extended held-out, provenance audit F1–F9 fixes.
- v1.6.1 (`af56edb`, annotated `5eaddaf`): API-repro notes (Data
  Availability + Limitations #23, EN+RU) + README version mapping;
  follow-up `a174ad2`: cover letter date/code DOI sync, README +
  CITATION → DOI 23838116.
- Code Availability намеренно пинит тег v1.6.0 (ядро анализа);
  v1.6.1 — только текст.
- Mode: HOLD до ответа Гэри / сабмита в Space Weather.
