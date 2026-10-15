# AGENTS.md — CrossCorr

## Что это за проект
CrossCorr — воспроизводимый научный артефакт для анализа ионосферных бурь
по данным WSPR (citizen science) + независимым индексам космической погоды.
Целевая площадка: AGU / Space Weather (Wiley).

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
- `docs/` — методология, pipeline, AI_ASSISTANCE.md
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

## Правила для агентов
- НЕ менять исходный код без явного подтверждения пользователя.
- НЕ логировать секреты, .env, API-токены. При находке — маскировать.
- НЕ коммитить `data/raw/`, `data/processed/unified.parquet`, артефакты LaTeX.
- НЕ удалять и не переписывать файлы в `audit/` — это доказательная база.
- НЕ трогать `paper/` без запроса (там завязана submission-версия).
- Все новые параметры анализа — через CLI-флаги или `config.yaml`,
  без hardcoded дат.
- Экспериментальные модули (`mutual_info.py`, `transfer_entropy.py`, `mse.py`,
  `cross_mfdfa.py`) не трогать как production — либо доводить, либо выносить
  в отдельную ветку.
- Перед пушем — ruff + mypy + pytest (not slow).
- Всё важное для будущих чатов писать в файлы репозитория, а не в память чата.

## Известные системные ограничения
- WSPR API (`wspr.live`) требует VPN из некоторых регионов.
- Windows: см. `tests/test_shared_memory_cleanup.py` (shared_memory cleanup).
- Held-out период (Jan–Mar 2026) содержит N_storm = 23 часа — статистическая
  мощность ограничена, это ожидаемо и признано в Limitations.

## Уроки (операционные анти-паттерны)

Из сессии 2026-10-12 (релиз v1.1.0). Дополняют HANDOFF-уроки 1–8;
там же — специфика session 2/3 (worktree, cherry-pick, force-push).

### Windows / PowerShell

- **credential.helper.** GCM установлен
  (`git-credential-manager.exe` в `C:\Program Files\Git\mingw64\bin`,
  verified), но git о нём не знает, пока не сконфигурирован:
  `git config --global credential.helper manager`. Без этого push
  из PowerShell падает (`could not read Username for
  'https://github.com'`), даже если GitHub Desktop пушит из UI.
- **UTF-8 без BOM.** `Set-Content -Encoding utf8` в PS 5.1
  добавляет BOM (U+FEFF) в начало файла. Для записи UTF-8-без-BOM:
  `[System.IO.File]::WriteAllText($path, $c, (New-Object
  System.Text.UTF8Encoding $false))`.
- **Чтение UTF-8.** `Get-Content -Raw` в PS 5.1 читает файл как
  cp1251 на русской локали → не-ASCII превращается в моджеику при
  обратной записи (UTF-8 → cp1251-байты → UTF-8). Для корректного
  чтения: `[System.IO.File]::ReadAllText($path,
  [System.Text.Encoding]::UTF8)`. Симметрично с записью.
- **.NET cwd ≠ PS `$PWD`.** `[System.IO.File]::*` использует .NET
  current directory (обычно `C:\Users\<user>`), а не `Get-Location`.
  Относительный путь пишется не туда. Правило: перед .NET-API
  строить абсолютный путь через `Join-Path (Get-Location).Path $rel`.

- **`[Environment]::NewLine` = CRLF, не LF.** При работе с LF-файлами (write-tool, here-string, markdown этого репо) использовать LF-escape (backtick + n), а не `[Environment]::NewLine`. Иначе получается mixed-ending файл (LF + один CRLF), который ломает последующие regex/replace и загрязняет diff.

- **LF→CRLF warnings при `git add`** — ожидаемо на Windows (`core.autocrlf=true`); файлы пишутся в LF, git конвертирует в CRLF при checkout. Не ошибка. Cross-platform fix (`.gitattributes` `* text=auto eol=lf`) — в backlog.

### Git

- **GitHub Desktop не пушит локальные теги автоматически** (опыт
  проекта, HANDOFF-урок 6). Push тега — только из CLI:
  `git push origin <tag>`. Дополняет урок 6: remote-тег может
  отличаться от локального (`v1.0.2-paper`: локально `00e692a`,
  remote `f97844e`); переписывать задним числом нельзя.
- **First commit of a new file.** write-инструмент не ставит final
  newline; pre-commit `end-of-file-fixer` допишет его и уронит
  коммит. Ожидаемо: re-add + повторный commit. Тот же класс, что
  W292 в `probe_ksg_ties.py` (CI #139).

### Python replace-скрипты (tmp_fix_*.py)

Урок сессии 2026-10-15 (batch 9-11). Применяется к скриптам в
стиле `tmp_fix_*.py`, которые делают серию `str.replace` /
`lines[i:i+n] = [...]` и один `write_bytes` в конце.

- **Двухфазный паттерн обязателен.** Phase 1 — verify: пройти по
  всем паттернам, собрать счётчики `text.count(old)`, **вывести
  все** несовпадения (не падать на первом). Phase 2 — apply:
  только если Phase 1 дала `all OK`, выполнять замены и
  `write_bytes`. Это спасает от частично применённого состояния.
  Пример корректной реализации — `tmp_fix_c1b.py` (session 11).

- **Диагностика перед повторным запуском.** Если `tmp_fix_*.py`
  **упал**, не факт, что файл не тронут: скрипт мог упасть
  **после** `write_bytes` предыдущего запуска, или быть запущен
  дважды подряд (как случилось с `tmp_fix_audit2.py`, session
  11 → дубль блока Session 10/11). Правило: перед любым
  повторным запуском — `git diff <target>` + dump окна вокруг
  ожидаемого anchor. Не запускать replace-скрипт «вслепую»
  второй раз.

- **Anchor с indent = риск.** Для многострочных паттернов с
  continuation-indent (`\t      `, `\t\t`) нельзя угадывать
  пробелы/табы. Надёжнее: либо **line-based** (`split(NL)` +
  поиск по `anchor_substr in line` + `lines[i:i+n] = [...]`),
  либо предварительный dump байтов: `python -c` с
  `repr(text[i:i+250])`. `tmp_fix_c4.py` (session 11) падал
  трижды именно на indent — пока не перешли на line-based.

- **Один скрипт = один логический пакет.** Не смешивать в одном
  файле замены из разных категорий (units, refs, таблицы). При
  провале одного паттерна откат бьёт по всем категориям. Если
  пакетов несколько — отдельные `tmp_fix_<topic>.py`,
  последовательные коммиты.
## Pre-commit hook (2026-10-12)

Repo runs ruff + file hygiene on every CLI `git commit`.

Setup after clone:
    python -m pip install pre-commit
    pre-commit install

Enforces: ruff --fix, ruff-format, end-of-file-fixer,
trailing-whitespace, check-yaml, check-added-large-files (2MB).

If blocked: hook modified files → `git add -u && git commit`.

Bypass (rare): `git commit --no-verify`. CI still runs ruff.

Note: GitDesktop uses libgit2 → hooks don't fire. CLI commits
(MiMo) → hooks fire.
