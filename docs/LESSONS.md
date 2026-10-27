# Операционные уроки и анти-паттерны CrossCorr

Этот файл содержит справочник грабель и анти-паттернов, собранных в ходе разработки проекта. Дополняет основной `AGENTS.md`.

---

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

- **PowerShell backtick.** В PS 5.1 обратная кавычка (`) является символом экранирования. При передаче inline-скриптов через `python -c "..."`, содержащих обратные кавычки (например, Markdown-код), PS съедает их, превращая в обратные слэши. Правило: сложные inline-скрипты со спецсимволами запускать только через сохранённый `.py` файл.

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

- **Никаких heredoc-инлайнов для LaTeX-правок (session 12).**
  `python - <<'PYEOF'` внутри Git Bash на Windows схлопнул
  `\\ref` → `\ref`, Python интерпретировал `\r` как CR — два
  `\ref` в main.tex молча превратились в битые макросы (поймано
  только при ревью diff следующего коммита). Правило: правки,
  затрагивающие обратные слэши, — только через записанный
  `tmp_fix_*.py` с Phase-1 verify. После любого автобайтового
  редактирования — dump `repr()` вокруг затронутых строк.

- **read_text/write_text vs CRLF (session 12).** `read_text()`
  делает universal-newline-нормализацию CR→LF; смешение
  `read_text`/`write_text` на CRLF-файле переписывает все 1256
  строк (diff от «однострочной» правки). Итог: `git add` хранит
  CRLF в blob при `* text=auto`. Правило: только
  `read_bytes`/`write_bytes` + явная проверка BOM и переводов
  строк. Если CRLF всё же попал в blob: `git reset --soft HEAD~1`,
  нормализовать файл в LF, `git add`, закоммитить заново
  (renormalize при этом бывает пустым — не доверять ему вслепую).
