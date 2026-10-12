# DELTA Protocol — Prompt Template
> Git-Derived Delta, a.k.a. Reincarnation

## What this is
A reusable prompt to generate a session DELTA at the end of
any work session. Derived from git log, not from memory.

## When to run
At end of every working session with an AI assistant.
One DELTA per calendar day; re-runs append.

## Placeholders
- <REPO_PATH>   — absolute path to repo (e.g. g:\crosscorr)
- <DATE>        — YYYY-MM-DD
- <START_TIME>  — HH:MM local, start of session
- <MODEL>       — model used (e.g. MiMo)

## Prompt

You are closing a work session in <REPO_PATH>.
Create docs/DELTA_<DATE>.md using ONLY data from git.

DO NOT invent commits. DO NOT paraphrase commit subjects.
Use them verbatim.

1. Get commits:
   git log --since="<DATE> <START_TIME>" --format="%h %s" --reverse

2. Group into five sections (in this order):
   - Что сделано (categorized: paper / tooling / docs / diagnostics / infra)
   - Решения (ADR-style: `<decision> — <reason>.`)
   - Открытые петли
   - Следующий шаг (ONE task only)
   - Метаданные (branch, HEAD, ahead/behind, model, duration)

3. If docs/DELTA_<DATE>.md already exists, append, do not overwrite.

4. Verify: git status shows exactly two changes (HANDOFF optional, DELTA new).

5. Commit: `git commit -m "delta: <DATE> session summary"`

## Failure modes
- git log empty → check timezone, do not proceed
- any file beyond DELTA (and optional HANDOFF) modified → STOP

## Cross-repo use
Template works in any git repo with a docs/ folder.
Replace <REPO_PATH>, <DATE>, <START_TIME>, <MODEL>.
