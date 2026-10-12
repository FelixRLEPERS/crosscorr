# Audit — Start of Next Session

Generated: 2026-10-12 (end of session 4)
For: next chat session (MiMo or human)
Purpose: operational snapshot — read this first.

## 1. Where we are (state at generation)

- **Branch:** main
- **HEAD:** `306d5e7` — paper: clarify ESS scope (F) +
  justify 18-month window (M)
- **origin/main:** `306d5e7` (после пуша; синхронизировать
  через GitHub Desktop если ещё ahead)
- **Project version:** 1.1.0-dev (code: pyproject.toml = "1.1.0");
  CITATION.cff synced to last real release v1.0.2
- **Zenodo concept DOI:** `10.5281/zenodo.23283375` (unchanged)
- **Zenodo version DOI:** `10.5281/zenodo.23310672` (v1.0.2)
- **GitHub Release:** v1.0.2-paper (unchanged)
- **Latest tag:** `v1.0.2-paper` (unchanged)
- **Worktrees:** 5 (main + 4 opencode: happy-knight @574f648,
  playful-lagoon @a114e86, proud-wizard @284cf30, tidy-pixel @a114e86)
- **Test files:** 32 (test count: 290 passed, pytest -q, session 3)
- **CI:** ci.yml (only workflow); green on latest HEAD

## 2. What was done in session 4 (2026-10-12 continuation)

Session 4 (3 commits, 8e68d05..306d5e7) closed Finding A, F, M
plus two cosmetic fixes:

- Finding A (47de960): new script scripts/storm_episodes.py.
  Groups the 198 Kp >= 5 3-hourly slots in window
  2024-04-01..2025-10-01 into 58 episodes (gap > 12 h); also
  computed 76 distinct UTC days. Paper synced: §2.2 (198/76/58 +
  script reference), §3.6 item 2 (robustness check), §5.5 new
  item 8 (Storm-slot independence). Fixed pre-existing double-count
  bug in §2.2 (paper had "226 raw intervals across 67 storm days" —
  artifact of overlapping CSV files in data/raw/space_weather/).
  Also fixed Table 1 overflow: tabular -> tabularx (added
  \usepackage{tabularx} to preamble).

- Finding F (306d5e7): §3.4 ESS scope clarified — applies to full
  matched series (20 m, N = 482), not the storm subsample.

- Finding M (306d5e7): §2 training window justification — boundaries
  determined by wspr.live data availability, not selected a priori.

- Finding I: FALSE POSITIVE. grep "additive|additivity" in
  paper/main.tex: 0 matches. No change needed.

- Fix Figure 5 (2890603): annotation "40m: identical (ratio 1.00)"
  repositioned so it no longer overflows axes.

Full detail: audit/BACKLOG_2026-10-12_v11.md (canonical).

## 3. Open loops (what is NOT closed)

From external audit v11 (audit/BACKLOG_2026-10-12_v11.md):
  - D. Superposed epoch analysis — DEFERRED to Space Weather
    (v1.1.0 or later submission).
  - E. Recovery-phase exclusion from quiet group — DEFERRED.
  - H-2. Style sweep outside code dirs — DEFERRED to v1.1.0.
    23 files: audit/verify_*.py (19), bench/bench_new_modules.py (1),
    game/*.py (4).
  - J, K, L — deferred to Space Weather.

Closed in session 3: B, C, H. Closed in session 4: A, F, M.
False positive: I.

External / non-code:
  - arXiv endorsement — blocked on Frissell response.
  - 2FA on GitHub — deadline 25 Nov 2026.
  - Release v1.1.0 (tag + Zenodo DOI) — bundle with arXiv submission.

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

**Prepare v1.1.0 release:**
  - All arXiv-minimum audit findings closed.
  - Steps:
    1. Bump version in pyproject.toml and CITATION.cff to 1.1.0.
    2. Generate release notes from git log v1.0.2-paper..HEAD.
    3. Create tag v1.1.0.
    4. Push tag, create GitHub Release, mint Zenodo DOI.
    5. Update DOIs in paper/main.tex Code Availability section.
  - Estimated: ~1 hour + Zenodo propagation time.

## 8. Second task

**Prepare arXiv submission (once endorsement arrives):**
  - Rebuild PDF, verify page count and Table 1 / Figure 5 fixes.
  - Verify author list, affiliations, acknowledgments.
  - Confirm paper/main.tex references v1.1.0 tag (not 264cc93).
  - Upload to arXiv, choose categories.

## 9. Quick reference — where things live

  audit/BACKLOG_2026-10-12_v11.md       — findings tracker
  docs/HANDOFF_2026-10-11.md            — structure + policy
  docs/DELTA_2026-10-12.md              — session 2 detail
  docs/AUDIT_START_NEXT_SESSION.md      — this file
  AGENTS.md                             — model rules
  paper/main.tex                        — manuscript
  scripts/perm_test_18mo_3band.py       — perm test
  scripts/storm_episodes.py             — Finding A (episodes)
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
- Generated at: 2026-10-12 (end of session 4)
- Source HEAD: 306d5e7
- Sources read: BACKLOG_2026-10-12_v11, AUDIT_START_NEXT_SESSION
  (session 3 version), git log, git worktree list.

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
  arXiv (A closed, B closed); Already addressed (C, H closed;
  H-2 deferred; G, sporadic-E already); Text-only (F, I, M —
  F/M closed, I false positive); Deferred; False positives;
  Session log (session 3 + session 4); Next actions.
- **docs/BOOTSTRAP.md**: Bootstrap block; Notes.
- **AGENTS.md**: Что это за проект; Стек; Структура; Команды;
  Правила для агентов; Известные системные ограничения;
  Pre-commit hook.
- **docs/DELTA_PROMPT_TEMPLATE.md**: What this is; When to run;
  Placeholders; Prompt; Failure modes; Cross-repo use.
