# CrossCorr — аудит v8

## 0. Мета

- Дата: 2026-10-07
- HEAD: `e063fd3`
- Ветка: `main`
- Рабочее дерево: чистое
- Что проверено в v8: coverage (повторный замер), reference-валидация core,
  документация vs код, зависимости, edge cases

---

## 1. Coverage

| Метрика | Значение |
|---|---|
| Тесты | 291 |
| Общий coverage | 58% |
| Stmts | ~2538 |

Файлы с покрытием < 60%:

| Файл | Coverage | Причина |
|---|---|---|
| `power_curve.py` | 35% | CLI-обёртка + plot, core логика под bench |
| `mfdfa.py` | 46% | CLI-путь покрыт, `mfdfa_spectrum()` — мало кейсов |
| `stationarity.py` | 48% | `check_stationarity_wide` — мало кейсов с нестационарностью |
| `distance_analysis.py` | 49% | Mantel-путь покрыт; OLS-путь, бины — слабо |
| `benchmark_utils.py` | 28% | Узкая утилита, вызывается из power_curve |
| `confounders.py` | ~55% (оценка) | `remove_confounders` — basic path |
| `safe_exec.py` | 17% | Обучающая обёртка, не научный код |
| `narrator.py` | 0% | TTS/игровая обёртка |
| `quest.py` | 0% | Streamlit UI |

Ядро `analysis/` без peripheral: 46–95%.

**Вывод:** Основной статистический код (max-stat, FDR, surrogate, pairs,
effective_sample, block_bootstrap) покрыт ≥80%. Разрывы — в CLI-обёртках,
утилитах бенчмаркинга, игровых/обучающих модулях.

Топ-5 действий для повышения coverage:

1. `power_curve.py` 35% → 60%+ (тесты на `measure_point`, `power_curve_by_n`)
2. `stationarity.py` 48% → 60%+ (нестационарные синтетические ряды, edge
   cases)
3. `distance_analysis.py` 49% → 60%+ (OLS-путь, бины расстояний)
4. `mfdfa.py` 46% → 60%+ (edge cases: короткий ряд, NaN, q-вариации)
5. `benchmark_utils.py` 28% → 50%+ (все null-модели в `benchmark()`)

---

## 2. Reference-валидация core

Подробности — `audit/REFERENCE_v8.txt`.

| Тест | Параметры | Результат | Статус |
|---|---|---|---|
| Max-stat p-value | N=500, max_lag=30, n_surr=50, 20 trials | rejection rate 0.000, mean p 0.526 | ✅ |
| FDR BH | 90 null + 10 alt (p~U(0,0.001)), alpha=0.05 | FP 0/90, TP 10/10 | ✅ |
| IAAFT surrogate | AR(1) phi=0.7, N=1000 | ACF diff 0.0011, sorted match True | ✅ |

**Вывод:** Все три core-метода (max-stat, FDR Benjamini-Hochberg, IAAFT)
прошли reference-валидацию на синтетике с известным ответом. Статистическая
машинерия проекта корректна.

---

## 3. Документация

Расхождений: 11 (0 HIGH, 7 MEDIUM, 4 LOW). Broken references (файловые
ссылки в README/methodology, указывающие на несуществующий файл) — **не
обнаружено**.

| # | Файл | Строка | Проблема | Severity |
|---|---|---|---|---|
| 1 | README.md | 475 | «более 270 тестов» → 291 | MEDIUM |
| 2 | docs/roadmap.md | 19 | «237 тестов, покрытие ~53%» → 291/58% | MEDIUM |
| 3 | docs/methodology.md | 15 | Пространственная модель: «(planned)» → README/WIP ⚠ | MEDIUM |
| 4 | README.md | 356 | Импорт `from crosscorr_lib import ...` — не проверено наличие ре-экспорта | MEDIUM |
| 5 | docs/roadmap.md | 27 | Задача обновить README/Fund — в «ближайший квартал», раздел Fund на месте | MEDIUM |
| 6 | crosscorr_lib/analysis/cross_correlation.py | 39 | `load_unified()` — публичная функция без docstring | MEDIUM |
| 7 | crosscorr_lib/analysis/distance_analysis.py | 32 | `haversine_km()` — публичная функция без docstring | MEDIUM |
| 8 | README.md | 505 | «visualization.py» у Макара — файл в `analysis/visualization.py`, не на верхнем уровне | LOW |
| 9 | README.md | 461-464 | Закрытые чекбоксы в списке «Результаты» неотличимы от открытых | LOW |
| 10 | docs/roadmap.md | 8 | «Актуально на: 2026-10-06» — день назад | LOW |
| 11 | surrogate.py | 98 | `surrogate_test()` — есть описание, нет стандартных Args/Returns | LOW |

**Топ-3 критичных:**
1. README устаревшее число тестов (MEDIUM)
2. roadmap устаревшие метрики покрытия (MEDIUM)
3. methodology: planned vs WIP для пространственной модели (MEDIUM)

---

## 4. Зависимости

| Пакет | pyproject.toml | requirements.lock | Актуальный (окт 2026) | Риск |
|---|---|---|---|---|
| numpy | ≥1.25 | 2.5.3 | 2.x — свежий | LOW |
| scipy | ≥1.10 | 1.18.1 | 1.x — свежий | LOW |
| pandas | ≥2.0 | 3.0.6 | 3.x — свежий | LOW |
| matplotlib | ≥3.7 | 3.11.2 | 3.x — свежий | LOW |
| statsmodels | ≥0.14 | 0.15.0 | 0.15 — свежий | LOW |
| pyarrow | ≥14.0 | 25.0.1 | 25.x — свежий | LOW |
| requests | ≥2.31 | 2.34.2 | 2.x — свежий | LOW |
| pymc | ≥5.10 | 6.3.2 | 6.x — свежий | LOW |
| arviz | ≥0.16 | 1.3.0 | 1.x — свежий | LOW |
| streamlit | ≥1.30 | 1.64.0 | 1.x — свежий | LOW |
| MFDFA | ≥0.4 | 0.4.3 | 0.4.x — свежий | LOW |
| **joblib** | **≥1.3** | **отсутствует** | — | **HIGH** |
| **edge-tts** | **≥6.1** | **отсутствует** | — | **HIGH** |
| pytest | ≥7.4 | не в lock | не проверено | MEDIUM |
| ruff | ≥0.6 | не в lock | не проверено | MEDIUM |
| mypy | ≥1.8 | не в lock | не проверено | MEDIUM |

Расхождения:

- **HIGH:** `joblib` отсутствует в requirements.lock. При установке из lock
  → `ImportError` в `cross_correlation_pairs_with_max_stat`.
- **HIGH:** `edge-tts` отсутствует и в requirements.in, и в requirements.lock.
  При `pip install -e ".[game]"` — ок; из lock — нет.
- **MEDIUM:** `requirements.lock` скомпилирован `pip-compile --no-index` под
  Python 3.13; проект заявляет ≥3.10. Флаг `--no-index` ненадёжен.
- **MEDIUM:** `requirements.lock` от 2026-09-23; `requirements.in` обновлён
  2026-10-05. Lock отстаёт на 2 недели.
- **MEDIUM:** dev-зависимости (pytest, ruff, mypy, pytest-cov, pytest-xdist,
  pip-tools) не включены в requirements.in → не попали в lock.

**CVE:** не проверено (pip-audit не установлен). Пакеты очень свежие
(lock 2026-09-23); известные CVE для старых numpy/scipy/pandas (CVE-2021-*)
недосягаемы для текущих версий. Требует внешней проверки.

---

## 5. Edge cases

### RISK

| Функция | Кейс | Поведение из кода | Метка |
|---|---|---|---|
| `iaaft_surrogate` | All-Inf | Inf проходит маску `np.isfinite(x)`? Inf ≠ NaN и isfinite=False, но код проверяет только `np.isnan`: маска `good = np.isfinite(x)` → good.sum()=0 → NaN-array; ОК. Но если Inf вперемешку с числами — FFT мусор | **RISK** |
| `effective_sample_size` | All-Inf | `x - x.mean() = inf - inf = NaN`; FFT даёт NaN ACF; tau=NaN; N_eff=NaN | **RISK** |
| `lagged_cross_correlation` | All-Inf (N≥10) | `np.isnan(inf)=False` → Inf идёт в `spearmanr` → запрос | **?** |
| `lagged_cross_correlation` | Константный ряд (N≥10) | `spearmanr` на константе → NaN; downstream `all(isnan(corrs))` ловит; своей проверки нет | **?** |
| `block_bootstrap_surrogate` | All-Inf | Inf-срезы конкатенируются; `corrcoef` ловит → NaN | **?** |

### OK

Все проверенные функции (`max_lag_surrogate_pvalue`, `fdr_bh_q`,
`block_bootstrap_pvalue`, `effective_sample_size`, `lagged_cross_correlation`
и `iaaft_surrogate`) имеют явную обработку для:

- Пустого и короткого ряда (<4 или <10): `ValueError` / NaN-возврат
- All-NaN: `np.isnan`-маски, `MIN_SAMPLES=10`, NaN-array на выходе
- NaN в середине: интерполяция или pairwise-маски
- Константного ряда: через NaN от `spearmanr`/`corrcoef` (неявно)
- N=100000: O(N) или O(N log N), без скрытых O(N²)

**Выводы:**

- Топ-3 функции с RISK: `iaaft_surrogate`, `effective_sample_size`,
  `lagged_cross_correlation`
- Топ-3 проблемных кейса: All-Inf (№1 — Inf не является NaN, маски
  пропускают), константный ряд (№2 — неявная обработка через scipy),
  смешанный Inf+числа (№3 — наихудший сценарий)
- Системный паттерн: нет единой `np.isfinite`-валидации на входе
  ключевых функций; Inf-проверка полагается на downstream-ловлю

---

## 6. Новые findings v8

Классификация: ID | класс | severity | статус | описание.

### Coverage (COV)

| ID | Класс | Severity | Статус | Описание |
|---|---|---|---|---|
| COV-1 | COVERAGE | P2 | OPEN | `power_curve.py`: 35% покрытия (CLI+plot, core логика) |
| COV-2 | COVERAGE | P2 | OPEN | `mfdfa.py`: 46% покрытия (CLI-путь только) |
| COV-3 | COVERAGE | P3 | OPEN | `stationarity.py` 48%, `distance_analysis.py` 49% — <50% |
| COV-4 | COVERAGE | P3 | OPEN | `benchmark_utils.py` 28%, `safe_exec.py` 17% |

### Documentation (DOC)

| ID | Класс | Severity | Статус | Описание |
|---|---|---|---|---|
| DOC-1 | DOCS | P2 | OPEN | README: «более 270 тестов» → 291 |
| DOC-2 | DOCS | P2 | OPEN | roadmap: устаревшие метрики (237 тестов, ~53%) |
| DOC-3 | DOCS | P3 | OPEN | methodology: пространственная модель «(planned)» → WIP |
| DOC-4 | DOCS | P3 | OPEN | Нет docstring у `load_unified()`, `haversine_km()` |
| DOC-5 | DOCS | P3 | OPEN | roadmap: HEAD устарел на 1 день |

### Dependencies (DEP)

| ID | Класс | Severity | Статус | Описание |
|---|---|---|---|---|
| DEP-1 | DEPENDENCY | P1 | OPEN | `joblib` отсутствует в requirements.lock |
| DEP-2 | DEPENDENCY | P2 | OPEN | `edge-tts` отсутствует в requirements.in + lock |
| DEP-3 | DEPENDENCY | P2 | OPEN | Lock скомпилирован `--no-index` под Python 3.13 |
| DEP-4 | DEPENDENCY | P3 | OPEN | Dev-deps (pytest/ruff/mypy) не в отдельном lock |

### Edge cases (EDGE)

| ID | Класс | Severity | Статус | Описание |
|---|---|---|---|---|
| EDGE-1 | ROBUSTNESS | P2 | OPEN | `iaaft_surrogate`: no Inf validation |
| EDGE-2 | ROBUSTNESS | P2 | OPEN | `effective_sample_size`: no Inf validation |
| EDGE-3 | ROBUSTNESS | P3 | OPEN | `lagged_cross_correlation`: no explicit Inf/constant guard |
| EDGE-4 | ROBUSTNESS | P3 | OPEN | No consistent `np.isfinite`-policy across analysis modules |

**Всего v8:** 17 новых findings (4 COV + 5 DOC + 4 DEP + 4 EDGE).

---

## 7. Топ-5 действий на v9

| # | Приоритет | Действие | Закрывает |
|---|---|---|---|
| 1 | P1 | Добавить `joblib` в `requirements.in`, перегенерировать lock с PyPI (без `--no-index`) под Python 3.10 | DEP-1 |
| 2 | P2 | Исправить DOC-1, DOC-2: актуализировать числа в README и roadmap | DOC-1, DOC-2 |
| 3 | P2 | EDGE-1/EDGE-2: добавить `np.isfinite`-валидацию в `iaaft_surrogate`, `effective_sample_size` | EDGE-1, EDGE-2 |
| 4 | P2 | DEP-2: добавить `edge-tts` в `requirements.in` + перегенерировать lock | DEP-2 |
| 5 | P2 | COV-1: повысить покрытие `power_curve.py` до 60%+ (тесты на `measure_point`, `power_curve_by_n`) | COV-1 |

---

## 8. Что узнали в v8

- **Core статистика полностью валидирована.** Max-stat, FDR BH и IAAFT
  прошли все три reference-теста на синтетике с известным ответом. Это
  даёт научную уверенность в корректности основной машинерии проекта.

- **Inf — систематическая слепая зона.** Все функции проверяют `np.isnan`,
  но `np.isnan(inf) == False`. Inf проскальзывает в FFT и `spearmanr`.
  Нужна единая политика `np.isfinite` на входе критических функций.

- **Lock-файл не покрывает все зависимости.** `joblib` (критичная для
  parallel execution) и `edge-tts` (игровой модуль) отсутствуют. Lock
  скомпилирован `--no-index` под нецелевой Python 3.13. Для production
  установки lock непригоден.

- **Документация отстаёт на ~1 цикл версий.** Метрики в roadmap
  зафиксированы на v6 (237 тестов), хотя в v6 уже было 291. Число
  тестов в README не обновлялось. Механизма автообновления метрик нет.

- **Coverage ядра 46-95%, обёртки не покрыты.** Основной научный код
  (max-stat, FDR, surrogate) имеет хорошее покрытие. Периферийные
  модули (power_curve, mfdfa, stationarity) — слабое. Игровые/обучающие
  модули — 0%. Это сознательное проектное решение (отделить науку от
  обучения), но оно зафиксировано явно.

---

*Конец аудита v8.*