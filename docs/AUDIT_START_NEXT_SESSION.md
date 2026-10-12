# Audit — Start of Next Session

Generated: 2026-10-12 (end of session 2)
For: next chat session (MiMo or human)
Purpose: operational snapshot — read this first.

## 1. Where we are (state at generation)

- **Branch:** main
- **HEAD:** `3207345` — chore: add pre-commit hook (ruff + file hygiene)
- **origin/main:** `3207345` — same as HEAD (ahead by 0)
- **Project version:** `1.0.2`
- **Zenodo concept DOI:** `10.5281/zenodo.23283375`
- **Zenodo version DOI (v1.0.2):** `10.5281/zenodo.23310672`
- **GitHub Release:** v1.0.2-paper
- **Latest tag:** `v1.0.2-paper`
- **Worktrees:** 5 (main + 4 opencode: happy-knight, playful-lagoon,
  proud-wizard, tidy-pixel — 3 KEEP pending user decision, happy-knight
  stale at 574f648)
- **Test files:** 32 (do not confuse with test count; run
  pytest to get count)
- **CI workflows:** ci.yml
- **CI blocking jobs:** fast tests (Py 3.11, 3.12), slow tests (Py 3.12)
- **CI informational jobs:** shared memory cleanup (Windows, Py 3.10/3.11/3.12, continue-on-error: true)

Note: CITATION.cff still says version 1.0.1 while pyproject.toml says
1.0.2 — stale, fix in next version bump.

## 2. What was done in session 2 (2026-10-12)

Session 2 (23 commits, 0b82d78…3207345) closed the entire external
audit backlog: all 5 submission findings verified/fixed (N=23 wording,
KSG-ties limitation, requirements.lock regenerated, Windows CI verified,
PROJECT_STATE drift notice), plus governance tooling: DELTA Protocol,
BOOTSTRAP, DELTA_PROMPT_TEMPLATE, pre-commit hook. Full commit-by-commit
detail: docs/DELTA_2026-10-12.md.

Highlights:
- All 5 submission findings from external audit: CLOSED
- requirements.lock regenerated (core-only, Python 3.11)
- KSG-ties probe + §5.5 limitation
- PROJECT_STATE.md drift notice
- DELTA Protocol + BOOTSTRAP + pre-commit hook installed
- Worktree cleanup: 22 → 4

## 3. Open loops (what is NOT closed)

From audit/BACKLOG_2026-10-12.md:
  - Finding 4 (Windows CI job): VERIFIED informational,
    action deferred to post-arXiv.

From docs/HANDOFF_2026-10-11.md (ОТКРЫТЫЙ ТЕХДОЛГ):
  - October 2024 f107 missing from unified.parquet
    (ETL gap, tracked for v1.1.0)
  - 3 KEEP worktrees (playful-lagoon, proud-wizard,
    tidy-pixel): user decision pending

External / non-code:
  - **arXiv endorsement** — blocked on Frissell response
  - **Version bump v1.0.3 / v1.1.0** — optional, not urgent
  - **2FA on GitHub** — deadline 25 Nov 2026

## 4. Ready for next session

These artifacts exist and are up to date:
  - `docs/BOOTSTRAP.md` — 10-line block for new chat
  - `docs/HANDOFF_2026-10-11.md` — full structure
  - `docs/DELTA_2026-10-12.md` — session 2 detail
  - `audit/BACKLOG_2026-10-12.md` — findings status
  - `AGENTS.md` — pre-commit + model policy
  - `.pre-commit-config.yaml` — active

## 5. What NOT to do (anti-patterns from session 2)

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

## 6. First commands to run in next session

    cd g:\crosscorr
    git fetch origin
    git status -sb
    git log --oneline -5
    git worktree list

If `ahead > 0` → push before working.
If any worktree is dirty → decide keep/remove before touching.

## 7. Recommended first task

**Write the Frissell endorsement request.**

- Template: `docs/HANDOFF_2026-10-11.md`, section
  "ШАБЛОНЫ КОММУНИКАЦИИ" → "Черновик письма Dr. Frissell".
- 4 questions: references, endorsement, HamSCI mailing list,
  advice for young citizen scientists.
- This is a HUMAN task, not a MiMo task. Author writes,
  human sends.
- After sending: wait 2 weeks before follow-up.

## 8. Second task (if first is done or blocked)

**Version bump decision.** Two options:
  - v1.0.3 — bugfix level (lock fix + docs only)
  - v1.1.0 — feature level (5 findings + tooling)
  Recommended: v1.1.0, bundled with arXiv submission.

## 9. Quick reference — where things live

  docs/HANDOFF_2026-10-11.md         — full structure + policy
  docs/DELTA_2026-10-12.md           — last session detail
  docs/BOOTSTRAP.md                  — start-message block
  docs/DELTA_PROMPT_TEMPLATE.md      — end-of-session prompt
  docs/AUDIT_START_NEXT_SESSION.md   — this file
  audit/BACKLOG_2026-10-12.md        — findings tracker
  AGENTS.md                          — pre-commit + model rules
  paper/main.tex                     — manuscript
  crosscorr_lib/analysis/            — statistical core
  scripts/                           — reproducible scripts

## 10. Model policy (from HANDOFF)

  - MiMo: default. File edits, git ops, multi-step tasks.
  - Bonsai 2 27B (local): read-only analysis, new-file
    creation. Do NOT give file-edit tasks.
  - Qwen 2.5 Coder 7B: not used (hallucinations on review).

## Metadata

- Generated by: MiMo via OpenCode
- Generated at: 2026-10-12 16:10 +03:00
- Source HEAD: 3207345
- Sources read: HANDOFF, DELTA, BACKLOG, BOOTSTRAP, AGENTS,
  DELTA_PROMPT_TEMPLATE, README, pyproject.toml, ci.yml

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
- **audit/BACKLOG_2026-10-12.md**: Source; Verification;
  Findings (all CLOSED/VERIFIED); Session progress; Not yet
  reviewed; Related; Final status.
- **docs/BOOTSTRAP.md**: Bootstrap block; Notes.
- **AGENTS.md**: Что это за проект; Стек; Структура; Команды;
  Правила для агентов; Известные системные ограничения;
  Pre-commit hook.
- **docs/DELTA_PROMPT_TEMPLATE.md**: What this is; When to run;
  Placeholders; Prompt; Failure modes; Cross-repo use.
