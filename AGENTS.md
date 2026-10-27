# AGENTS.md — CrossCorr

**Last updated:** 2026-10-27
**Applies to:** v1.1.x

## Содержание
1. [Что это за проект](#что-это-за-проект)
2. [Стек](#стек)
3. [Структура](#структура-ключевое)
4. [Команды](#команды)
5. [Приоритеты](#приоритеты)
6. [Правила для агентов](#правила-для-агентов)
7. [Definition of Done](#definition-of-done)
8. [Краткая памятка (полная версия в docs/LESSONS.md)](#краткая-памятка)
9. [Известные системные ограничения](#известные-системные-ограничения)
10. [Pre-commit hook](#pre-commit-hook)

## Что это за проект
CrossCorr — воспроизводимый научный артефакт для анализа ионосферных бурь по данным WSPR (citizen science) + независимым индексам космической погоды. Целевая площадка: AGU / Space Weather (Wiley).

## Стек
- Python 3.10+ (CI: 3.11, 3.12)
- pyproject.toml (PEP 621), pip-tools, requirements.lock
- ruff, mypy, pytest, pytest-cov
- pandas / numpy / statsmodels / scipy
- LaTeX (AGU template) в `paper/`
- Parquet для unified-схемы

## Структура (ключевое)
- `crosscorr_lib/analysis/` — 20 модулей статистического ядра
- `data/scripts/` — 13 ETL-скриптов; `data/processed/unified.parquet` — gitignored
- `scripts/` — 15 скриптов анализа
- `tests/` — 291 тест
- `paper/` — статья (AGU)
- `docs/` — методология, pipeline, AI_ASSISTANCE.md, LESSONS.md
- `audit/` — версионированные аудиты (не удалять, это часть прозрачности)

## Команды
- Установка: `pip install -e ".[dev,all]"`
- Линт: `ruff check .`
- Типы: `mypy crosscorr_lib`
- Быстрые тесты: `pytest -m "not slow"`
- Все тесты: `pytest`
- Покрытие: `pytest --cov=crosscorr_lib --cov-fail-under=45` (план: поднять до 70)
- ETL: `python data/scripts/fetch_all.py`
- Главный результат: `python scripts/perm_test_18mo_3band.py`

## Приоритеты
1. Явная инструкция пользователя в текущей сессии.
2. Правила из этого файла (`AGENTS.md`).
3. Дефолтные настройки модели.

## Правила для агентов
- НЕ менять исходный код без явного подтверждения пользователя.
- НЕ логировать секреты, .env, API-токены. При находке — маскировать.
- НЕ коммитить `data/raw/`, `data/processed/unified.parquet`, артефакты LaTeX.
- НЕ удалять и не переписывать файлы в `audit/` — это доказательная база.
- НЕ трогать `paper/` без запроса (там завязана submission-версия).
- При правках `paper/` или любых текстов, связанных со статьей, ОБЯЗАТЕЛЬНО обновлять `docs/AI_ASSISTANCE.md` в соответствии с требованиями AGU.
- Все новые параметры анализа — через CLI-флаги или `config.yaml`, без hardcoded дат.
- Экспериментальные модули (`mutual_info.py`, `transfer_entropy.py`) не трогать как production — либо доводить, либо выносить в отдельную ветку. `mse.py` и `cross_mfdfa.py` **вынесены в ветку `experimental`** (2026-10-27) и в `main` отсутствуют — не восстанавливать без reference-валидации XM-1/XM-2.
- Всё важное для будущих чатов писать в файлы репозитория, а не в память чата.

## Definition of Done
Перед завершением любой задачи агент ОБЯЗАН:
1. Запустить `ruff check .` и `mypy crosscorr_lib`.
2. Запустить `pytest -m "not slow"`.
3. Проверить `git diff` глазами на наличие мусора и артефактов.
4. Сделать коммит через CLI.

## Краткая памятка
(Полная версия — в `docs/LESSONS.md`)
- **Windows PS 5.1:** использовать `[System.IO.File]::ReadAllText(..., UTF8)` для чтения, избегать `Set-Content` (добавляет BOM).
- **Git:** пушить теги только через CLI (`git push origin <tag>`). GitHub Desktop не пушит теги.
- **Скрипты `tmp_fix_*.py`:** всегда использовать двухфазный паттерн (verify -> apply).
- **LaTeX:** никогда не использовать heredoc для правок с обратными слэшами.
- **Текстовые файлы:** Все текстовые файлы пишутся в LF. Использовать `write_bytes` с явным `\n`.

## Известные системные ограничения
- WSPR API (`wspr.live`) требует VPN из некоторых регионов.
- Windows: см. `tests/test_shared_memory_cleanup.py` (shared_memory cleanup).
- Held-out период (Jan–Mar 2026) содержит N_storm = 23 часа — статистическая мощность ограничена, это ожидаемо и признано в Limitations.

## Pre-commit hook (2026-10-12)
Repo runs ruff + file hygiene on every CLI `git commit`.
Setup after clone:
    python -m pip install pre-commit
    pre-commit install

Enforces: ruff --fix, ruff-format, end-of-file-fixer, trailing-whitespace, check-yaml, check-added-large-files (2MB).
If blocked: hook modified files -> `git add -u && git commit`.
Bypass (rare): `git commit --no-verify`. CI still runs ruff.
Note: GitDesktop uses libgit2 -> hooks don't fire. CLI commits (MiMo) -> hooks fire.
