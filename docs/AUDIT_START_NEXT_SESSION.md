# Audit — Start of Next Session

Generated: 2026-10-14 (end of session 9)
For: next chat session (MiMo or human)
Purpose: operational snapshot — read this first.

## 1. Where we are (state at generation)

- **Branch:** main
- **HEAD:** `8e4477e` — paper: Code Availability — pin exact
  version to v1.1.0 (tag + version DOI)
- **origin/main:** `8e4477e` (fully synced; ahead 0, behind 0)
- **Project version:** 1.1.0 (pyproject.toml = "1.1.0";
  CITATION.cff = "1.1.0", date-released 2026-10-12)
- **Zenodo concept DOI:** `10.5281/zenodo.23285958` (**active**;
  previously mis-recorded as `23283375`)
- **Zenodo version DOI (v1.1.0):** `10.5281/zenodo.23325197`
- **Legacy Zenodo concept:** `10.5281/zenodo.23283375` (manual
  uploads only; see Open loops §3)
- **GitHub Release:** v1.1.0 (latest)
- **Latest tag:** `v1.1.0` @`a0141dd` (annotated)
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

## 3. Open loops (what is NOT closed)

arXiv-minimum audit findings: **all closed** (or false positive).
Release v1.1.0: **shipped**.

Remaining:

- **HELDOUT-LIVE-REVISION documented** — see
  ``audit/FINDING_HELDOUT_LIVE_2026-10-13.md`` and paper §5.5 item 9.
- **arXiv submission** — reply sent 2026-10-14; awaiting endorsement. Follow-up 2026-10-28 if no reply.
  Prerequisites done: paper references `v1.1.0` tag, concept DOI
  is `23285958`, PDF builds.
- **Legacy Zenodo concept** `23283375` — parallel; manual
  uploads only. Options: leave, deprecate, or merge. Not a
  blocker.
- **H-2** — style sweep outside code dirs (23 `.py` +
  5 `.md` with python-fences: `AUDIT_REPORT.md`,
  `EXPORT_FOR_AUDIT.md`, `EXPORT_FOR_AUDIT_v2.md`,
  `EXPORT_FOR_AUDIT_v3.md`, `audit/AUDIT_2026-10-05_v2.md`).
  Deferred to v1.2.0 / Space Weather prep.
- **D, E, J, K, L** — deferred to Space Weather.

External / non-code:
- arXiv endorsement — blocked on Frissell response.
- 2FA on GitHub — deadline 25 Nov 2026.
- (Optional) Zenodo support contact re: legacy concept.

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
  2. Verify author list, affiliations, acknowledgments.
  3. Confirm `paper/main.tex` references v1.1.0 (done in
     `2dd71b5`).
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
- Generated at: 2026-10-14 (end of session 9)
- Source HEAD: 8e4477e
- Sources read: git log, git status, AGENTS.md,
  BACKLOG_2026-10-12_v11.md, HANDOFF_2026-10-11.md,
  docs/releases/v1.1.0.md.

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
