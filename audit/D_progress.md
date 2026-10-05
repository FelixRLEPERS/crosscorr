# Группа D — прогресс ночной сессии

HEAD на старте: `4232b49`.
Среда: Python 3.13.5.

## Текущее состояние публичного API

- `crosscorr_lib.__all__`: 18 имён.
- Все имена из `__all__` импортируемы:
  `[getattr(crosscorr_lib,n) for n in __all__]` — OK.
- `from crosscorr_lib import pairs` — OK, `pairs.cross_correlation_pairs_with_max_stat` доступна.
- `from crosscorr_lib.safe_exec import run_code_safe` — OK.
- `from crosscorr_lib.analysis.preprocessing import preprocess` — OK.
- `crosscorr_lib.analysis.__all__` отсутствует; модуль реэкспортирует
  только `fdr_bh`, `max_lag_surrogate_pvalue`.
- `fdr_bh(pvals, alpha=0.05, method="by") -> np.ndarray`;
  `fdr_bh_q(pvals, alpha=0.05, method="by") -> (reject, q)`.
- git-тегов нет (`git tag` пуст).

## Факты по находкам

- D11 CONFIRMED: `True`/`False`/`None` в Python — ключевые слова
  (AST `Constant`), а не имена; в `SAFE_BUILTINS` они недостижимы.
- D4 CONFIRMED: `analysis/__init__.py` реэкспортирует 2 из 14 модулей,
  `__all__` нет.
- D5 CONFIRMED: git-тегов нет.
- D9/D10/D12/D13/D14 — код в файлах вне границ задачи.
- D6/D7 — игровой код (`narrator.py`, `ai_narrator.py`, `quest.py`, `game/`)
  вне границ.
- D8 — `pyproject.toml` вне границ.

## Классификация

D-CONTRACT: D1, D3, D4
D-TYPES: D3 (docstrings), D4
D-QUALITY: D5, D11
D-POLISH: D6, D7, D8, D9, D10, D12, D13, D14

## Статус
Начало: 2026-10-05 22:51

---

### D1 — две функции с именем cross_correlation_pairs_with_max_stat
- Classification: D-CONTRACT
- Start: 2026-10-05 22:51
- Verify: shell (`from crosscorr_lib import pairs`) + reading
- Verify result: CONFIRMED
- Action: fix (документирование, без смены API)
- Files changed: [`crosscorr_lib/__init__.py`]
- Backward compat: preserved
- Tests added: [`tests/test_D_api.py`]
- Notes: обе функции реально существуют: `analysis.cross_correlation` (Spearman per lag, колонки `detector_1/detector_2/correlation`) и `pairs` (FFT batch, колонки `detector_a/detector_b/C_obs`). Переименование — breaking. Добавлены комментарий в импортах и пояснение в docstring: в `__init__` экспортируется версия analysis, `pairs` доступен как модуль. `pairs` НЕ добавлен в `__all__` (правило 4g).

### D3 — fdr_bh рядом с fdr_bh_q
- Classification: D-CONTRACT
- Start: 2026-10-05 22:51
- Verify: shell (`inspect.signature`)
- Verify result: CONFIRMED
- Action: fix (документирование)
- Files changed: [`crosscorr_lib/__init__.py`]
- Backward compat: preserved
- Tests added: [`tests/test_D_api.py`]
- Notes: `fdr_bh(pvals, ...) -> np.ndarray` (только reject-массив, по умолчанию BY); `fdr_bh_q(pvals, ...) -> (reject, q)`. Оба не-deprecated, разные контракты. Добавлены комментарии в `__all__`. Сигнатуры не менялись.

### D4 — analysis/__init__.py экспортирует мало, нет __all__
- Classification: D-CONTRACT
- Start: 2026-10-05 22:51
- Verify: reading + shell (модули импортируются)
- Verify result: CONFIRMED
- Action: fix (аддитивно)
- Files changed: [`crosscorr_lib/analysis/__init__.py`]
- Backward compat: preserved (только добавления)
- Tests added: [`tests/test_D_api.py`]
- Notes: добавлены реэкспорты `preprocess` (из `preprocessing`) и `__all__` с двумя существующими именами плюс `preprocess`. Существующие `fdr_bh`, `max_lag_surrogate_pvalue` сохранены. Никакие символы не удалены.

### D5 — __version__ без git-тегов
- Classification: D-QUALITY
- Start: 2026-10-05 22:51
- Verify: shell (`git tag` пуст)
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Backward compat: n/a
- Tests added: []
- Notes: STOP. Создание git-тегов — git write, запрещено. Правка версии в `__init__.py` не решает исходную находку (нет управления релизами). Требует решения пользователя.

### D6 — narrator/ai_narrator/quest не в __all__
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Backward compat: n/a
- Notes: STOP. Файлы вне границ (игровой код). Добавление их в `__all__` не требуется: они не библиотечные функции.

### D7 — game/ мёртвый код
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading + `git ls-files`
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. `game/` вне границ задачи.

### D8 — mypy не настроен
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. `pyproject.toml` вне границ.

### D9 — download_horizons.py аннотация -> "object"
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. `data/scripts/` вне границ.

### D10 — surrogate.py _lagged_cc без аннотаций
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. `crosscorr_lib/analysis/*.py` вне границ (кроме `__init__.py`).

### D11 — True/False/None в SAFE_BUILTINS недостижимы
- Classification: D-QUALITY
- Start: 2026-10-05 22:51
- Verify: shell (AST: True -> Constant, не Name)
- Verify result: CONFIRMED
- Action: fix (комментарий; записи оставлены ради совместимости)
- Files changed: [`crosscorr_lib/safe_exec.py`]
- Backward compat: preserved
- Tests added: [`tests/test_D_api.py`]
- Notes: `True/False/None` — ключевые слова, в `exec` не ищутся в `__builtins__`; как ключи `SAFE_BUILTINS` они недостижимы. Не удалял (правило 1: не удалять публичные данные), добавил комментарий-пометку. `SAFE_BUILTINS`/`FORBIDDEN_NAMES`/`run_code_safe` не менялись функционально.

### D12 — mantel.py избыточный import pandas
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. `mantel.py` вне границ.

### D13 — циклические импорты
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. Требует правки `crosscorr_lib/analysis/*.py` — вне границ.

### D14 — build_wide дубликат build_wide_by_detector
- Classification: D-POLISH
- Start: 2026-10-05 22:51
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. `surrogate.py` вне границ.

---

## Итог сессии

- Всего в группе D: 14 записей
- CLOSED (до сессии): 1 (D2)
- OPEN на старте: 13 (D1, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13, D14)
- Обработано: 13
  - D-CONTRACT: 3 closed (D1, D3, D4)
  - D-TYPES: 0 (входит в D3/D4)
  - D-QUALITY: 1 closed (D11), 1 STOP (D5)
  - D-POLISH: 8 STOP (D6, D7, D8, D9, D10, D12, D13, D14)
- Осталось OPEN: 9 (D5, D6, D7, D8, D9, D10, D12, D13, D14)
- Backward compatibility: preserved
- Тесты: было 205, стало 215 (добавлено 10 в `tests/test_D_api.py`)
- `__all__` count: было 18, стало 18 (в верхнем уровне не менялся)
- Рекомендация: D5 требует решения о релиз-тегировании; D9/D10/D12/D13/D14 — перенести в группы соответствующих файлов (A/B/C); D6/D7/D8 — решение о мёртвом коде/инфраструктуре.

### Проверка арифметики
- fix: D1, D3, D4, D11 = 4
- stop: D5, D6, D7, D8, D9, D10, D12, D13, D14 = 9
- Итого: 4 + 9 = 13 = OPEN на старте. Осталось 9.

### Изменённые файлы
- `crosscorr_lib/__init__.py` (D1, D3)
- `crosscorr_lib/analysis/__init__.py` (D4)
- `crosscorr_lib/safe_exec.py` (D11)
- `tests/test_D_api.py` (new)
- `audit/D_progress.md` (new)
