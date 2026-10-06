# Queue 1 — закрытые STOP

Дата: 2026-10-06
HEAD до правок: `d9a09dacf09c0efc78cfdde630e5e05cb2d2ef26`
Ветка: main
Источник: `audit/STOP_DECISIONS.md`, раздел «Очередь 1»

| ID | Что сделано | Файл | Строк | Проверка |
|----|-------------|------|-------|----------|
| D9 | `-> object` заменён на строковую аннотацию `-> "astropy.table.Table"` (фактический возврат `Horizons.ephemerides()`) | `data/scripts/download_horizons.py:27-29` | +3/-1 | import data OK |
| D10 | добавлены аннотации параметров (`np.ndarray`, `int`) и возврата `tuple[np.ndarray, np.ndarray, np.ndarray]` по факту `lagged_cross_correlation` | `crosscorr_lib/analysis/surrogate.py:468-472` | +5/-1 | import modules OK |
| D12 | удалён локальный `import pandas as pd  # noqa: F401` в `build_corr_matrix` (pd не используется; `pd` берётся из шапки) | `crosscorr_lib/analysis/mantel.py:140` | -2 | import modules OK |
| G11 | удалён файл с ложью про `api_client`/`SourceRegistry` (вариант A) | `README_ARCHITECTURE_UPDATE.md` | -36 (удалён) | не упоминается в md |
| G12 | закрыт вместе с G11 (файл удалён) | (часть G11) | — | — |
| G13 | закрыт вместе с G11 (ссылка на отсутствующий тест удалена) | (часть G11) | — | — |
| G14 | закрыт вместе с G11 (эмодзи удалены с файлом) | (часть G11) | — | — |
| F18 | `bench.log` и `check_sprint4.py` удалены из дерева и индекса | `bench.log`, `check_sprint4.py` | -40 + binary (удалены) | git ls-files пуст |

## Итог
- Закрыто STOP: 8 из 8.
- Кода не сломано: `import crosscorr_lib` -> OK (`__all__` = 18).
- Импорты работают: `surrogate`, `mantel` -> OK; `data.scripts.download_horizons` -> OK.
- Что осталось из Queue 1: 0.

## Замечания
- G11-G14 закрыты одной операцией `git rm README_ARCHITECTURE_UPDATE.md`.
  Файл не упоминается в `README.md` и `docs/*.md` (git grep вернул только
  `audit/*` и `AGENTS_AUDIT.md`, которые не являются документацией проекта).
- D9: строковая аннотация `"astropy.table.Table"` выбрана, чтобы не тянуть
  импорт astropy на уровне модуля; `from __future__ import annotations` в
  файле уже есть, так что аннотация не вычисляется.
- F18: `bench.log` — бинарный дамп (нечитаем как текст), `check_sprint4.py` —
  одноразовый скрипт Sprint 4.2. Оба не документированы, удалены полностью
  по правилу 3. В `.gitignore` изменения не требовались.
- Правки застейджены только для удалённых файлов (`git rm`); текстовые
  правки D9/D10/D12 остаются unstaged, коммит не выполнялся.
