# Audit — Start of Next Session

Generated: 2026-10-15 (end of session 11)
For: next chat session (MiMo or human)
Purpose: operational snapshot — read this first.

## 1. Where we are (state at generation)

- **Branch:** main
- **HEAD:** `c53e3e3` — release: v1.2.0 -- version DOI 23394340
  in CITATION.cff and Code Availability. (Session 11: batches
  9-10 + v1.2.0 release; 7 of 9 blockers from external audit
  closed.)
- **origin/main:** `c53e3e3` (fully synced; ahead 0, behind 0)
- **Project version:** 1.2.0 (pyproject.toml = "1.2.0";
  CITATION.cff = "1.2.0", date-released 2026-10-15)
- **Zenodo concept DOI:** `10.5281/zenodo.23285958` (**active**;
  previously mis-recorded as `23283375`)
- **Zenodo version DOI (v1.2.0):** `10.5281/zenodo.23394340`
  (v1.1.0 version DOI was `23325197`; retired but still resolves)
- **Legacy Zenodo concept:** `10.5281/zenodo.23283375` (manual
  uploads only; see Open loops §3)
- **GitHub Release:** v1.2.0 (latest)
- **Latest tag:** `v1.2.0` @`df843b6` (annotated)
- **Title (v1.2.0):** 'Scale-dependent WSPR response to geomagnetic
  storms: frequency dependence and network-size effects on absolute
  loss' (baseline-invariance retracted; see §3)
- **Worktrees:** 5 (main + 4 opencode: happy-knight @574f648
  clean, playful-lagoon @a114e86 dirty-untracked,
  proud-wizard @284cf30 dirty-untracked, tidy-pixel @a114e86
  dirty-modified `crosscorr_lib/analysis/cross_mfdfa.py`) —
  **not touched**; outside release scope (Lesson 8).
- **Test files:** 32 (290 passed, pytest -q, session 5 re-run)
- **CI:** ci.yml (only workflow); green on latest HEAD

## 2. What was done in session 5 (2026-10-12 continuation)

Session 5 shipped **release v1.1.0** end-to-end (4 commits,
`997d171..2dd71b5`) plus 1 DOI-fix correction:

- `3a06f1a` — bump CITATION.cff to 1.1.0 / date 2026-10-12
  (with BOM-avoidance workaround).
- `a0141dd` — release notes at `docs/releases/v1.1.0.md`
  (95 lines); tagged v1.1.0.
- Tag `v1.1.0` pushed; GitHub Release created; Zenodo minted
  version DOI `10.5281/zenodo.23325197` (webhook delivery OK,
  release.published event confirmed in Recent Deliveries).
- `4c4e332` — concept DOI fix in live files: `23283375` →
  `23285958` in paper/main.tex (×2), README.md (×4),
  CITATION.cff (×1), docs/AUDIT_START_NEXT_SESSION.md (×1 +
  version DOI update). HANDOFF untouched (history).
- `2dd71b5` — paper Code Availability: `264cc93` → tag `v1.1.0`
  (`a0141dd`) + concept `23285958` → version `23325197`
  (exact-version citation).

Also verified:
- Table 1 overflow fix (commit `47de960`, tabularx) — verified
  in session 4 in rebuilt PDF.
- `ruff check .` green; `ruff format --check .` fails only on
  H-2 scope + 5 `.md` code-fences (deferred).
- Full 6-antipattern set for AGENTS.md recorded (see §5).

Full detail: audit/BACKLOG_2026-10-12_v11.md (canonical).

### Session 6 — 2026-10-13

Letter to Dr. Nathaniel Frissell sent (arXiv endorsement inquiry).
Two commits:

- `a06caa3` — docs(letters): draft for Dr. Frissell (arXiv endorsement inquiry)
- `debd96e` — docs(letters): mark Frissell draft as sent (2026-10-13)

Full letter: docs/letters/2026-10-13_frissell.md.
Attached paper/main.pdf (834 KB). Frissell silent 4 days after
CC reply (2026-10-09). Follow-up planned: 2026-10-27 if no reply.

### Sessions 7–9 — 2026-10-13/14

- Session 7 (night): found HELDOUT-LIVE-REVISION — training
  reproducible byte-for-byte, held-out shifted 18304 → 26287
  (data revision on wspr.live). Commit `11dc5e0`.
- Session 8 (night): paper fix — invariance wording softened,
  block-CI in Table 9 (40m training [12930, 23807], 40m held-out
  [12472, 37144]), §5.5 archive note. Commit `dd52ef1`.
- Session 9 (morning): reply to Dr. Frissell sent — declined live
  telecon (time-zone + family constraints), offered written
  alternatives, re-asked arXiv endorsement. Commit `7e0ee64`.
  Follow-up 2026-10-28 if no reply.
- Session 9 (afternoon): audit round 2 — §3.3 wording, Table 2 Δ (spots/h),
  §5.5 F10.7 held-out note. Commit `b4fc568`.

### Session 10 — 2026-10-15 (external audit round 3, batches 1-8)

Eight paper fixes + fig5 regen + docs sync. Closed numeric audit
findings: 198 raw -> 66 raw -> 198 epochs; 2.3% -> 0.87%; -37% ->
own drops; 89-95% -> 0.89-1.05 (then 1.01-1.12); Table 3 caption;
Table 9 caption; N_quiet 3359 -> 3035; N_unsettled 792 -> 1116;
baseline-invariance reframed; ESS 482/0.83/82 -> 4349/0.69-0.75/
610-793; Table 7 -> live wspr.live 2026-10-15 (720/47, drops
-26.7/-29.0/-22.1%, 15m p=0.26); Table 8 ratios 1.11/1.01/1.12.

Commits `688ceab..66b919b` (see DELTA_2026-10-14.md for full log).

### Session 11 — 2026-10-15 (external audit round 3, batches 9-10 + v1.2.0)

Second, deeper external audit identified 9 blockers + 9 major items.
Verified with read-only scripts (tmp_verify_*.py):
- **C1 verified**: analysis series is 3-hourly (inner join on
  native Kp timestamps, no forward-fill). hours-of-day ∈
  {0,3,6,9,12,15,18,21}; gap = 3h (4344/4348).
- **C4 verified**: `BLOCK = 24` rows = 72 h (three diurnal cycles).
- **C5 mostly rejected**: Table 5 reproduces exactly from current
  parquet. But new finding: Table 2 Δ (raw value diff) differs
  from §3.3 definition (residual diff). Left for future work.
- **C6 verified**: retracted claim still in README (6 places),
  CITATION.cff, and Zenodo concept record.
- **M8 verified**: 26 .bib keys, 16 rendered in .bbl.

**Batches 9-10 (paper):**
- `8b2058b` — batch 9: block size = 24 epochs = 72 h throughout;
  M6 (null statement corrected: residual blocks permuted, Kp
  labels fixed; not 'equivalent to shuffling Kp labels');
  M7 (p = 2×10⁻⁵ add-one floor, not p <).
- `5984d9a` — batch 10: C1 (3-hourly epoch units throughout
  methods); C2 (39,456 WSPR hours -> 13,152 per band + 39,456
  across three); C3 (66 raw 3-hourly intervals -> 198 epochs,
  = 594 storm hours); M2 (Dst 2.4× more storm samples + 2.9×
  larger total sample).

**v1.2.0 release:**
- `df843b6` — CITATION.cff title 'baseline-invariant absolute loss'
  -> 'network-size effects on absolute loss'; version 1.2.0;
  README 5 places updated (key findings #3 rewritten as
  database-mutability cautionary); pyproject 1.2.0; paper Code
  Availability tag v1.2.0 + concept DOI 23285958.
- Tag `v1.2.0` @`df843b6` (annotated); GitHub Release published;
  Zenodo minted version DOI `10.5281/zenodo.23394340` (webhook OK).
- `c53e3e3` — version DOI in CITATION.cff and paper Code
  Availability; concept DOI kept for Data Availability.

**Major items still open (not blockers):** C5-новая (Table 2 Δ
vs §3.3), C7 (Table 9 20m/15m), C8 (§5.5 item 9 first
sentence), C9 (date re-download 13 vs 15), M1 (provenance
table), M5 (frequency inversion in held-out), M8 (.bib 26 vs
16), M9 (affiliation placeholder / KeyPoints >140 / linenumbers).

## 3. Open loops (what is NOT closed)

Release v1.2.0: **shipped** (Zenodo version DOI `23394340`).
All **arXiv-minimum** blockers from external audit rounds 3 and 4:
**closed** (C1, C2, C3, C4, C6, M6, M7).

Remaining — **major, not blockers for arXiv submission**:

- **C5-новая** — Table 2 Δ (raw value diff) vs §3.3 definition
  (residual diff) are not the same quantity. Either rename Table
  2 column or redefine §3.3. Small fix, needs decision.
- **C7** — Table 9 rows 20m/15m still archived snapshot (ratios
  0.77 / 0.42). Recompute from live-cache parquet; update §4.6
  ratios + fig5.
- **C8** — §5.5 item 9 first sentence ('Held-out numbers ...
  reflect wspr.live snapshot at time of original analysis') still
  contradicts Tables 7-8 captions (live 2026-10-15).
- **C9** — re-download date inconsistent: Table 7/8 say
  2026-10-15; Table 9/Fig 5/§4.6 say 2026-10-13. Same pull,
  different dates.
- **M1** — Data provenance table (download dates, freeze status,
  storage location) missing; §4.6 relies on it. Also: commit
  live-cache held-out to Zenodo as separate file.
- **M5** — frequency ordering reverses in held-out (training
  15m > 20m ≈ 40m; held-out 40m > 20m > 15m). Needs explicit
  discussion (power / season / sporadic-E), soften Conclusion #5.
- **M8** — 26 .bib keys, 16 rendered. Cite 5 (whitehead1989,
  gonzalez1994, tsurutani2003, mitra1974, efron1993), delete
  wilcoxon1945, decide on 4 (schunk2009, hargreaves1992,
  goodman1992, ratcliffe1972).
- **M9** — affiliation placeholder `[City, Country]`; KeyPoints
  2 and 3 exceed 140 chars; no `linenumbers`; no Plain Language
  Summary.
- **H-2** — style sweep outside code dirs. Deferred.
- **D, E, J, K, L** — deferred to Space Weather.

External / non-code:
- arXiv endorsement — Frissell follow-up 2026-10-28; HamSCI
  mailing list as second channel.
- 2FA on GitHub — deadline 25 Nov 2026.
- Legacy Zenodo concept `23283375` (v1, v2, 1.0.2-paper) — still
  contains retracted claim. Options: deprecate or annotate with
  'Superseded by 23285958; baseline-invariance retracted in
  v1.2.0'.

## 4. Ready for next session

- audit/BACKLOG_2026-10-12_v11.md (canonical findings)
- docs/HANDOFF_2026-10-11.md (structure + policy)
- docs/AUDIT_START_NEXT_SESSION.md (this file)
- docs/releases/v1.1.0.md (shipped release notes)
- AGENTS.md (model rules, pre-commit, **lessons §**)
- paper/main.tex (manuscript, references v1.1.0)
- scripts/perm_test_18mo_3band.py
- scripts/storm_episodes.py
- scripts/make_paper_figures.py

## 5. What NOT to do (anti-patterns)

Consolidated in **AGENTS.md → Уроки (операционные
анти-паттерны)**. HANDOFF-уроки 1–8 (session 2/3) still apply:
no multi-Part prompts, no contradiction in prompts, no
worktree-cherry-pick without `merge-base --is-ancestor`, no
mixed PS/bash in one command.

Session 5 additions (now in AGENTS.md):
- `credential.helper manager` required for CLI push.
- `Set-Content -Encoding utf8` adds BOM (PS 5.1).
- `Get-Content -Raw` reads cp1251 (PS 5.1).
- `.NET File.*` uses .NET cwd, not PS `$PWD`.
- GitHub Desktop does not push tags.
- First commit of a new file → EOF-fixer fix-up.

## 6. First commands to run in next session

    cd g:\crosscorr
    git fetch origin
    git status -sb
    git log --oneline -10
    git worktree list
    Get-Content audit\BACKLOG_2026-10-12_v11.md

If `ahead > 0` → push before working (CLI, credential.helper
now configured).
If any worktree is dirty → decide keep/remove (Lesson 8).

## 7. Recommended first task

**arXiv submission** (once endorsement arrives):
  1. Rebuild PDF, verify page count + Table 1 + Figure 5.
  2. Verify author list, affiliations (placeholder
     `[City, Country]` in main.tex L21 needs to be filled in),
     acknowledgments.
  3. Confirm `paper/main.tex` references v1.2.0 (tag `df843b6`,
     version DOI `23394340`) — done in `c53e3e3`.
  4. Upload to arXiv, choose categories.
  5. Record arXiv ID in README + CITATION.cff (post-accept).

If endorsement not yet available: address H-2 (style sweep
extension) or start D (SEA) for Space Weather.

## 8. Second task

**Space Weather submission prep** (D/E/J/K/L):
- D — superposed epoch analysis.
- E — recovery-phase exclusion.
- J — additional bands 30 m / 17 m.
- K — foF2 comparison (GIRO / DIDBase).
- L — Zenodo DOI for data + code.

## 9. Quick reference — where things live

    audit/BACKLOG_2026-10-12_v11.md    — findings tracker
    docs/HANDOFF_2026-10-11.md         — structure + policy
    docs/AUDIT_START_NEXT_SESSION.md   — this file
    docs/releases/v1.1.0.md            — shipped release notes
    docs/letters/2026-10-14_frissell_reply.md — Frissell reply (sent)
    audit/FINDING_HELDOUT_LIVE_2026-10-13.md — HELDOUT-LIVE finding
    docs/letters/2026-10-13_frissell.md — Frissell letter (sent)
    AGENTS.md                          — model rules + lessons
    paper/main.tex                     — manuscript
    scripts/perm_test_18mo_3band.py    — perm test
    scripts/storm_episodes.py          — Finding A
    scripts/make_paper_figures.py      — figures + JSON out
    results/fig4_day_night.json        — Day/Night CI+N
                                         (gitignored,
                                         reproducible)

## 10. Model policy (from HANDOFF)

  - MiMo: default. File edits, git ops, multi-step tasks.
  - Bonsai 2 27B (local): read-only analysis, new-file
    creation. Do NOT give file-edit tasks.
  - Qwen 2.5 Coder 7B: not used (hallucinations on review).

## Metadata

- Generated by: MiMo via OpenCode
- Generated at: 2026-10-15 (session 11 tail, after c53e3e3)
- Source HEAD: c53e3e3
- Sources read: git log, git status, AGENTS.md,
  BACKLOG_2026-10-12_v11.md, HANDOFF_2026-10-11.md,
  docs/DELTA_2026-10-14.md, external audit round 4 (chat).

## Appendix — source inventory (sections found)

- **AGENTS.md** (9 sections incl. Уроки):
  Что это за проект; Стек; Структура; Команды; Правила для
  агентов; Известные системные ограничения; Уроки;
  Pre-commit hook.
- **audit/BACKLOG_2026-10-12_v11.md** (7 sections):
  Critical for arXiv; Already addressed; Text-only fixes;
  Deferred to Space Weather; False positives / notes;
  Session log; Next actions.
- **docs/HANDOFF_2026-10-11.md** (21 sections) — unchanged.
- **docs/releases/v1.1.0.md** (6 sections): Added; Changed;
  Fixed; Docs / Internal; Deferred; Notes.
- **docs/BOOTSTRAP.md** — unchanged.
- **docs/DELTA_PROMPT_TEMPLATE.md** — unchanged.
