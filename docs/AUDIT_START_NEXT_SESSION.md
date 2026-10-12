# Audit — Start of Next Session

Generated: 2026-10-12 (end of session 3)
For: next chat session (MiMo or human)
Purpose: operational snapshot — read this first.

## 1. Where we are (state at generation)

- **Branch:** main
- **HEAD:** `fbaa109` — docs: mark C and H closed, add H-2 deferred
- **origin/main:** `fbaa109` — same as HEAD (ahead 0)
- **Project version:** 1.1.0-dev (code: pyproject.toml = "1.1.0");
  CITATION.cff synced to last real release v1.0.2
- **Zenodo concept DOI:** `10.5281/zenodo.23283375` (unchanged)
- **Zenodo version DOI:** `10.5281/zenodo.23310672` (v1.0.2)
- **GitHub Release:** v1.0.2-paper (unchanged)
- **Latest tag:** `v1.0.2-paper` (unchanged)
- **Worktrees:** 5 (main + 4 opencode: happy-knight @574f648,
  playful-lagoon @a114e86, proud-wizard @284cf30, tidy-pixel @a114e86)
- **Test files:** 32 (test count: 290 passed, pytest -q, session 3)
- **CI:** ci.yml (only workflow); green on fbaa109

## 2. What was done in session 3 (2026-10-12)

Session 3 (12 commits, b161ef4..fbaa109) closed 3 findings
from external audit v11 plus a repo-wide style sweep:

- Version bump to 1.1.0-dev in code, CITATION.cff synced
  to v1.0.2 (was stale at 1.0.1).
- Finding B (p-value precision): perm test raised to
  n_iter=50000 with add-one (Davison-Hinkley) correction;
  p = 1/50001 ~ 2.0e-5 for all bands. Paper synced (text,
  Tables 2/3, Table 5, Eq.(3), Methods paragraph).
  Commits: 4c485c1, 6929a0d, f47a538.
- Finding C (day/night CI+N): script serialises results_dn
  to results/fig4_day_night.json; tab:daynight restructured
  in long format, 15m column added, bootstrap CI + N per
  subgroup. Commits: 8cb5211, 39d9856.
- Finding H (style sweep): 78 files across scripts/,
  tests/, crosscorr_lib/, data/scripts/ ruff-formatted in
  3 commits. pytest 290 passed, PNG/JSON artifacts
  byte-identical. Commits: 3082bc6, 92b817f, a7724e4.
- Backlog v11 updated: B, C, H closed; H-2 deferred.
  Commits: 4761f00, fbaa109.

Full detail: audit/BACKLOG_2026-10-12_v11.md (canonical).

## 3. Open loops (what is NOT closed)

From external audit v11 (audit/BACKLOG_2026-10-12_v11.md):
  - A. N_storm_episodes — OPEN, top priority.
    Group storm hours into episodes (gap > 12h), report
    N_episodes. New script scripts/storm_episodes.py.
  - F. ESS=82 scope — OPEN, low priority (10 min).
    One sentence in §3.4 clarifying that ESS applies to
    the full series, not storm subsample.
  - D. Superposed epoch analysis — DEFERRED to Space
    Weather submission.
  - H-2. Style sweep outside code dirs — DEFERRED to
    v1.1.0. 23 files: audit/verify_*.py (19),
    bench/bench_new_modules.py (1), game/*.py (4).

External / non-code:
  - arXiv endorsement — blocked on Frissell response.
  - 2FA on GitHub — deadline 25 Nov 2026.
  - Release v1.1.0 (tag + Zenodo DOI) — bundle with arXiv
    submission.

## 4. Ready for next session

- audit/BACKLOG_2026-10-12_v11.md (canonical findings)
- docs/HANDOFF_2026-10-11.md (structure + policy)
- docs/DELTA_2026-10-12.md (session 2 detail; session 3
  summary lives in backlog v11 Session log)
- docs/AUDIT_START_NEXT_SESSION.md (this file)
- AGENTS.md (model rules, pre-commit)
- docs/hypothesis.md
- paper/main.tex (manuscript)
- scripts/perm_test_18mo_3band.py
- scripts/make_paper_figures.py

## 5. What NOT to do (anti-patterns from session 2/3)

1. **Do not paste EXACT TEXT with unclosed markdown into
   prompts.** Session 2 lost ~30 min on 3 separate failures
   (Bonsai × 2, MiMo × 1).
2. **Do not mix PowerShell and bash in one command.**
   Bonsai hangs.
3. **Do not give multi-Part prompts (Part A + Part B) as
   one task.** MiMo executed Part A, skipped Part B.
4. **Do not put contradictions in prompts** (e.g. "don't run
   pytest" + "run pytest in step 1"). Both Bonsai and MiMo
   stall.
5. **Do not copy files from a worktree into main without
   checking `git merge-base --is-ancestor`.** Session 2
   reverted signed-implementation this way (Lesson 8).
6. **Do not commit untracked scripts without running
   `ruff check <file>` first.** W292 in probe_ksg_ties.py
   broke CI #139.
7. **Do not create a new file from an old file's content
   without checking the old file is gone or explicitly
   marked superseded** (session 3 backlog update drift).

## 6. First commands to run in next session

    cd g:\crosscorr
    git fetch origin
    git status -sb
    git log --oneline -10
    git worktree list
    Get-Content audit\BACKLOG_2026-10-12_v11.md

If `ahead > 0` → push before working.
If any worktree is dirty → decide keep/remove before touching.

## 7. Recommended first task

**Finding A — write scripts/storm_episodes.py (read-only
analysis first):**
  - Read unified.parquet
  - Filter kp >= 5 rows
  - Sort by hour, group consecutive hours into episodes
    with gap > 12h
  - Report N_episodes (vs N_storm_hours = 198)
  - Decide: one sentence in Limitations, or SEA foundation
Estimated: ~1 evening.

## 8. Second task

**Finding F — one sentence in paper §3.4 (10 min).**

## 9. Quick reference — where things live

  audit/BACKLOG_2026-10-12_v11.md       — findings tracker
  docs/HANDOFF_2026-10-11.md            — structure + policy
  docs/DELTA_2026-10-12.md              — session 2 detail
  docs/AUDIT_START_NEXT_SESSION.md      — this file
  AGENTS.md                             — model rules
  paper/main.tex                        — manuscript
  scripts/perm_test_18mo_3band.py       — perm test
  scripts/make_paper_figures.py         — figures + JSON out
  results/fig4_day_night.json           — Day/Night CI+N
                                          (gitignored,
                                          reproducible)

## 10. Model policy (from HANDOFF)

  - MiMo: default. File edits, git ops, multi-step tasks.
  - Bonsai 2 27B (local): read-only analysis, new-file
    creation. Do NOT give file-edit tasks.
  - Qwen 2.5 Coder 7B: not used (hallucinations on review).

## Metadata

- Generated by: MiMo via OpenCode
- Generated at: 2026-10-12 19:58 +03:00
- Source HEAD: fbaa109
- Sources read: BACKLOG_2026-10-12_v11, HANDOFF_2026-10-11,
  DELTA_2026-10-12, pyproject.toml, CITATION.cff, ci.yml,
  git worktree list, git log.

## Appendix — source inventory (sections found, STEP 1)

- **docs/HANDOFF_2026-10-11.md** (21 sections): КТО МЫ; PAPER I;
  PAPER II PILOT; PAPER II τ(d,f) model; КРИТИЧЕСКИЕ ТЕХНИЧЕСКИЕ
  НЮАНСЫ; СДЕЛАНО; ЧТО ОСТАЛОСЬ; ЧТО НЕ ДЕЛАТЬ; СТРАТЕГИЯ;
  ШАБЛОНЫ КОММУНИКАЦИЙ; КОНТЕКСТ ДЛЯ НОВОГО ЧАТА; ОТКРЫТЫЙ
  ТЕХДОЛГ; ПОЛНЫЙ СПИСОК АРТЕФАКТОВ; v1.0.2 ЗАВЕРШЕНО; Уроки
  сессии 2026-10-11 (1–8); Следующая сессия; OPENCODE MODEL
  POLICY; PRE-COMMIT HOOK; DELTA PROTOCOL; OPENCODE WORKTREE.
- **docs/DELTA_2026-10-12.md**: Что сделано (5 categories);
  Решения; Открытые петли; Следующий шаг; Метаданные.
- **audit/BACKLOG_2026-10-12_v11.md**: header; Critical for
  arXiv; Already addressed; Text-only; Deferred; False
  positives; Session log; Next actions.
- **docs/BOOTSTRAP.md**: Bootstrap block; Notes.
- **AGENTS.md**: Что это за проект; Стек; Структура; Команды;
  Правила для агентов; Известные системные ограничения;
  Pre-commit hook.
- **docs/DELTA_PROMPT_TEMPLATE.md**: What this is; When to run;
  Placeholders; Prompt; Failure modes; Cross-repo use.
