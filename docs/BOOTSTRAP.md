# Bootstrap — New Chat Session

Copy the block below into the first message of any new chat
to give the assistant full context in 10 lines.

---

Проект: CrossCorr (WSPR / geomagnetic storms / citizen science).
Репо: g:\crosscorr.
Структура контекста:
  1. docs/HANDOFF_2026-10-11.md — структура проекта, model policy,
     worktree rules, lessons, next steps.
  2. docs/DELTA_<latest-date>.md — состояние последней сессии
     (если существует).
  3. audit/BACKLOG_<latest>.md — открытые findings.
  4. git log --oneline -10 — свежие коммиты.
Текущий HEAD: <вставь из git rev-parse --short HEAD>.
Модель: MiMo (default). Bonsai — read-only. Qwen — не использовать.
Задача: <одна строка, что делаем сегодня>.

---

## Notes
- Keep the block short — 10 lines max.
- Update HEAD before sending.
- If task is large, add a "Constraints" line:
  e.g. "Не трогать paper/main.tex без запроса."
