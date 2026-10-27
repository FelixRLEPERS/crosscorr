# Дорожная карта CrossCorr

Стратегия **Г**: наука + обучение + портфолио детей.

Роли: Алексей (51) — архитектор/CI; Макар (13) — исследования/визуализация/тесты;
Егор (11) — данные/QA/озвучка; мама — тексты и коммуникации.

Актуально на: 2026-10-06.

---

## Уже сделано

- [x] Базовый пайплайн анализа (кросс-корреляция, surrogate, FDR, Mantel)
- [x] Игра «Охота на призрака» (`crosscorr_lib/quest.py`) и `game/`
- [x] Голосовой наставник (`crosscorr_lib/narrator.py`, `ai_narrator.py`)
- [x] Безопасное выполнение кода (`crosscorr_lib/safe_exec.py`)
- [x] CI: fast (3.11/3.12) + slow + Windows (informational)
- [x] 237 тестов, покрытие ~53%

## Ближайший квартал (0–3 мес) — «Обучающий слой»

- [ ] Покрытие `safe_exec.py`: 17% → 50% (задачи для Макара)
- [ ] Покрытие `game/`: 0% → 40% (тесты на `state.py`, `mode_a.py`)
- [ ] Покрытие `narrator.py`: 0% → 40%
- [ ] Ветки `feature/*` и правило «1 задача = 1 PR»
- [ ] Актуализация README (команда, убрать преждевременный раздел Fund)

## Полгода (3–6 мес) — «Наука»

- [ ] Reference-валидация KSG/CMI для ties (MI-1)
- Примечание: Benchmarks passed. Further optimization deferred.
- [ ] Покрытие ядра: 53% → 70%, порог CI 45% → 60%
- [ ] Первый прогон на реальных данных WSPR + INTERMAGNET
- [ ] Zenodo-релиз с DOI (требует git-тега, STOP D5)
- [ ] Первая детская публикация в `docs/journal/`

## Год (6–12 мес) — «Портфолио»

- [ ] Препринт (arXiv)
- [ ] Портфолио: по одному публичному PR каждого ребёнка в месяц
- [ ] Демо-день для семьи раз в месяц

## Отложено: требует математика

- **XM-1/XM-2 reference validation for publication.** Convention выбран
  (abs default, split option). Для публикации нужна сверка с независимой
  реализацией MF-DXA или консультация специалиста по мультифрактальному
  анализу.

---

## Метрики успеха

| Технические | Семейные |
|---|---|
| Покрытие ≥ 70% | 1 PR ребёнка в неделю |
| CI зелёный на 3.11/3.12 | Демо-день раз в месяц |
| 0 STOP-P0 | Ребёнок объясняет 1 концепцию |
| Zenodo DOI | Портфолио заполнено |

---

# Дорожная карта: Покрытие тестов и экспериментальные модули

Фаза разведки и планирования, 2026-10-27. Код и тесты в этой сессии не менялись.

Прогон: `pytest --cov=crosscorr_lib --cov-report=term-missing` -> **290 passed**, 430 c,
`TOTAL = 58%` (2549 операторов, покрыто 1475, не покрыто 1074). Порог CI
(`--cov-fail-under` в pyproject) - 45%, цель проекта - 70%.

## 1. Анализ покрытия (Текущее: 58%, порог CI: 45%, цель: 70%)

- До 70% не хватает **~310 операторов** (70% * 2549 = 1784, покрыто 1475).
- Цифра "~53%" из пункта «Ближайший квартал» выше устарела: фактически 58%.

Самые непокрытые модули (покрытие < 50%):

| Модуль | Покрытие | Операторов | Не покрыто |
|---|---:|---:|---:|
| `crosscorr_lib/quest.py` | 0% | 298 | 298 |
| `crosscorr_lib/narrator.py` | 0% | 111 | 111 |
| `crosscorr_lib/ai_narrator.py` | 0% | 44 | 44 |
| `crosscorr_lib/safe_exec.py` | 17% | 58 | 48 |
| `analysis/benchmark_utils.py` | 28% | 18 | 13 |
| `analysis/power_curve.py` | 35% | 172 | 111 |
| `analysis/mfdfa.py` | 46% | 48 | 26 |
| `analysis/stationarity.py` | 48% | 48 | 25 |
| `analysis/distance_analysis.py` | 49% | 118 | 60 |
| `analysis/mantel.py` | 49% | 80 | 41 |

**Приоритет 1 (самые критичные):**

- `analysis/power_curve.py` (35%, -111) - статистика мощности, самая большая
  "дыра" аналитического пакета.
- `analysis/distance_analysis.py` (49%, -60) + `analysis/mantel.py` (49%, -41) -
  взаимосвязанная пара (`haversine_km`, `fit_distance_model`), используется
  `visualization.py`.
- `crosscorr_lib/safe_exec.py` (17%, -48) - песочница исполнения кода
  (`run_code_safe`), уже стоит в плане «Ближайший квартал».

**Приоритет 2:**

- `analysis/stationarity.py` (48%, -25) - входит в публичный API `crosscorr_lib`
  (`adf_test`, `check_stationarity_wide`).
- `analysis/mfdfa.py` (46%, -26), `analysis/benchmark_utils.py` (28%, -13).
- Крупные хвосты выше 50%: `analysis/surrogate.py` (78%, -66),
  `analysis/cross_correlation.py` (65%, -58, ядро), `analysis/confounders.py`
  (65%, -25), `analysis/block_bootstrap.py` (65%, -23).

**Отдельно - игровые модули:** `quest.py`, `narrator.py`, `ai_narrator.py` =
453 оператора при 0% покрытия. В коде помечены как
"not part of the library API... standalone game component"
(audit/STOP_DECISIONS.md, D6).

- Вариант А: добавить их в `omit` секции `[tool.coverage]` в pyproject ->
  1475 / 2096 = **70.4%** сразу.
- Вариант Б: покрыть тестами (в этом же файле стоит цель "narrator.py 0% -> 40%").
- Рекомендация: согласовать с владельцем - вариант А меняет конфиг CI.

## 2. Экспериментальные модули

| Модуль | Импортируется в скриптах? | Упоминается в статье? | Рекомендация |
|---|---|---|---|
| `mutual_info.py` (88%) | Да - `scripts/probe_ksg_ties.py` (+ `analysis/transfer_entropy.py`, `bench/bench_new_modules.py`) | Да - `paper/main.tex:1346`, `paper/main_ru.tex:1439` (Limitations: "excluded from all reported results") | Оставить exploratory: статус закреплён в статье; НЕ выносить в ветку - на модуль ссылается `probe_ksg_ties.py`, процитированный в Limitations |
| `transfer_entropy.py` (95%) | Нет - только `bench/` и `tests/` | Да - там же, Limitations (вместе с MI) | Оставить exploratory вместе с `mutual_info.py` (явная зависимость), закрепить статус в README |
| `mse.py` (84%) | Нет - только `bench/` и `tests/` | Нет | Мёртвый код для пайплайна -> вынести в отдельную ветку |
| `cross_mfdfa.py` (91%) | Нет - только `bench/` и `tests/` | Нет (в `paper/` нет упоминаний MFDF, DCCA, MF-DXA) | Вынести в отдельную ветку до reference-валидации XM-1/XM-2 (пункт «Отложено: требует математика» выше) |

**Вывод: мёртвый код или нет?**

- `mutual_info.py`, `transfer_entropy.py` - **не мёртвые**: их используют
  диагностический скрипт, и они прямо упомянуты в Limitations обеих версий
  статьи. Проблема не в отсутствии вызовов, а в непригодности KSG-оценки для
  дискретных/квантованных данных - это уже документировано в статье.
- `mse.py`, `cross_mfdfa.py` - **де-факто мёртвые**: участвуют только в
  `bench/` и `tests/`, в ETL/analysis-пайплайне и в статье не задействованы.
- Ни один из четырёх не реэкспортируется из `crosscorr_lib/__init__.py` и
  `crosscorr_lib/analysis/__init__.py` (публичный API: `preprocess`,
  `fdr_bh`, `max_lag_surrogate_pvalue`).

## 3. План действий на следующие сессии

- [x] Шаг 1 (Done, 2026-10-27): тесты для `analysis/power_curve.py` - покрытие 35% -> 98%.
  Новый файл `tests/test_power_curve.py` (21 тест).
- [x] Шаг 2 (Done, 2026-10-27): тесты для `analysis/distance_analysis.py` и
  `analysis/mantel.py` - покрытие 49% -> 100% и 49% -> 100% соответственно.
  Дополнены `tests/test_distance_analysis.py` и `tests/test_mantel.py` (побочно `benchmark_utils.py` 28% -> 100%).
- Шаг 3: Тесты для `analysis/stationarity.py` (48% -> >= 80%) и
  `analysis/mfdfa.py` (46% -> >= 80%).
- Шаг 4: Тесты для `crosscorr_lib/safe_exec.py` (17% -> >= 50%, это +19
  операторов) - уже стоит в плане «Ближайший квартал».
- Шаг 5: Решение по игровым модулям (`quest.py`/`narrator.py`/`ai_narrator.py`):
  omit в покрытии против новых тестов.
- Шаг 6: Вынести `mse.py` и `cross_mfdfa.py` в отдельную ветку; закрепить статус
  exploratory для `mutual_info.py`/`transfer_entropy.py` в
  `crosscorr_lib/analysis/README.md` (порог
  `test_analysis_readme_lists_all_modules` - меньше 8 упоминаний).
- Шаг 7: Повторный `pytest --cov` и подъём `--cov-fail-under` 45 -> 60
  (пункт «Полгода (3-6 мес)» этого файла).

Шаги 1-2 дают +212 операторов -> ~66% без изменения игровых модулей.
Шаги 1-4 дают ~+324 оператора -> ~71%, цель 70% достижима без "omit".

---

## Прогресс (Дата: 2026-10-27)

Полный прогон `pytest --cov=crosscorr_lib --cov-report=term`:

- **Общее покрытие: 67%** (было 58%; CI-порог 45% превышен, до цели 70%
  осталось ~3 процентных пункта).
- Операторы: 1696 / 2549 покрыто (было 1475 / 2549, **+221 оператор**).
- Тесты: **333 passed** (было 290, **+43 новых теста**), 0 упавших.
- Целевые модули шагов 1-2:

  | Модуль | Было | Стало |
  |---|---:|---:|
  | `analysis/power_curve.py` | 35% | **98%** |
  | `analysis/distance_analysis.py` | 49% | **100%** |
  | `analysis/mantel.py` | 49% | **100%** |
  | `analysis/benchmark_utils.py` (побочно) | 28% | **100%** |

- Не покрыто в целевых модулях: только ветка ImportError matplotlib в
  `power_curve.py` (строки 273-276) - недостижима, пока matplotlib установлен.
- Инструментальная заметка: `--cov=crosscorr_lib.analysis.<module>` в этой
  среде падает на импорте numpy ("cannot load module more than once per
  process"); использовать `--cov=crosscorr_lib` и смотреть строки нужных
  модулей.
- Найденные, но НЕ исправленные (код не менялся по правилам сессии) огрехи
  смотрите в отчете сессии: неиспользуемые `null_model_name` и `ar` в
  `benchmark_utils.benchmark()`, NaN-диагональ в `mantel.build_dist_matrix`.

Следующий шаг по плану - Шаг 3 (`analysis/stationarity.py`, `analysis/mfdfa.py`).
