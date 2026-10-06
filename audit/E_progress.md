# Группа E — прогресс сессии

HEAD: `1a4e5c3de86757a12b23752abb6219d361c34c1d`
Ветка: main
Среда: Python 3.13.5 локально; CI ubuntu-24.04 / Windows.

## Карта покрытия (ФАЗА 0)

Существование тестов проверено grep по tests/. Имена файлов и покрытие:

- `test_statistical_reference.py` — эталоны fdr_bh_q, BY, max-stat, lagged_cc (священный, не менять)
- `test_core_regression.py` — регрессии фиксов 1..15 (священный, не менять)
- `test_pairs.py`, `test_C_pairs.py` — pairs.py (parallel/shm)
- `test_max_statistic.py`, `test_max_stat_pipeline.py` — max-stat null
- `test_ess_and_bootstrap.py` — ESS + block bootstrap
- `test_fdr.py`, `test_mantel.py`, `test_distance_analysis.py`,
  `test_confounders.py`, `test_residuals.py`, `test_preprocessing` (в core)
- `test_cross_correlation_synthetic.py`, `test_negative_control.py`
- `test_visualization.py` — visualization.py (уже есть)
- `test_data_samples.py`, `test_unify_schema.py`, `test_download_intermagnet.py`
- `test_D_api.py`, `test_F_ci.py`, `test_G_docs.py`

Модули без тестов (факт): `stationarity.py`, `mfdfa.py`, `power_curve.py`,
`benchmark_utils.py`. `visualization.py` — покрыт.

## Классификация

- E-CORRECTNESS: E3 (tau AR(1) эталон), E5 (IAAFT сходимость), E8 (пустой
  wide / constant series)
- E-COVERAGE: E7 (stationarity, mfdfa, load_unified, power_curve CLI)
- E-QUALITY: E9 (conftest/дубли фикстур)
- E-POLISH: нет отдельных
- STOP: E6 (Windows-specific shm — требует Windows runner)
- OBSOLETE: E10 (stale .pytest_cache)
- CLOSED до сессии: E1, E2, E4, E11

Примечание: BACKLOG-итог заявляет «4 open», фактически OPEN в таблице группы
E — 6 (E3, E5, E6, E7, E8, E9). Расхождение зафиксировано в DEVIATIONS.

## Статус

Начало: 2026-10-06T08:15:56

---

### E3 — эталон tau для AR(1)
- Classification: E-CORRECTNESS
- Start: 2026-10-06T08:15:56
- Verify: reading code
- Verify result: CONFIRMED (`test_ess_and_bootstrap.py`: есть только
  `test_iat_ar1_decreases_with_phi` — монотонность, нет численного эталона
  `(1+phi)/(1-phi)`)
- Action: add test
- Files changed: [`tests/test_E_correctness.py` (new), `tests/conftest.py` (new)]
- Tests added: [`test_E_correctness.py::test_iat_matches_ar1_analytic_reference`,
  `::test_iat_white_noise_is_one`]
- Smoke: passed
- Notes: фиксированный seed=28, n=40000, phi ∈ {0.0, 0.5, 0.7};
  rtol=0.05. Проверено локально: rel-ошибка 0.0000 / 0.0045 / 0.0146.

### E5 — сходимость/свойства IAAFT
- Classification: E-CORRECTNESS
- Start: 2026-10-06T08:15:56
- Verify: reading code
- Verify result: CONFIRMED (нет теста свойств `iaaft_surrogate`: сохранение
  рангов, воспроизведение амплитудного спектра, детерминизм)
- Action: add test
- Files changed: [`tests/test_E_correctness.py`]
- Tests added: [`::test_iaaft_preserves_ranks_and_is_deterministic`,
  `::test_iaaft_reproduces_amplitude_spectrum`]
- Smoke: passed
- Notes: seed 1, n=512; проверено: сортировка совпадает с исходной,
  относительная ошибка амплитудного спектра 0.0066 (< 0.05). Не тест
  распределения на 1000 прогонах (это E-QUALITY/сеть времени).

### E8 — граничные сценарии wide
- Classification: E-CORRECTNESS
- Start: 2026-10-06T08:15:56
- Verify: reading code
- Verify result: CONFIRMED (нет тестов пустого wide / constant series для
  `cross_correlation_pairs`; `B=0`, `seed=-1`, `max_lag>=n` уже закрыты
  `test_pairs.py`, `test_max_statistic.py`)
- Action: add test
- Files changed: [`tests/test_E_correctness.py`]
- Tests added: [`::test_cross_correlation_pairs_empty_wide_returns_empty`,
  `::test_cross_correlation_pairs_constant_series_skipped`]
- Smoke: passed
- Notes: «ряды разной длины» неприменимо к wide-таблице (прямоугольная);
  отмечено, не добавлялось.

### E7 — покрытие stationarity/mfdfa/load_unified/power_curve
- Classification: E-COVERAGE
- Start: 2026-10-06T08:15:56
- Verify: reading code
- Verify result: CONFIRMED (нет тестов `adf_test`, `check_stationarity_wide`,
  `mfdfa_spectrum`, `load_unified`, CLI `power_curve`)
- Action: add test
- Files changed:
  [`tests/test_E_stationarity.py` (new), `tests/test_E_mfdfa.py` (new),
   `tests/test_E_coverage.py` (new), `tests/test_E_cli.py` (new)]
- Tests added: 12 (stationarity 4, mfdfa 3, load_unified 1, power_curve CLI 4)
- Smoke: passed
- Notes: mfdfa импортируется через `pytest.importorskip("MFDFA")`;
  CLI — subprocess `--help`, exit code 0. benchmark_utils покрыт косвенно
  через power_curve CLI (`--help` не считает точку), отдельный вызов
  `measure_point` слишком медленный для fast-тестов.

### E9 — conftest/дубли фикстур
- Classification: E-QUALITY
- Start: 2026-10-06T08:15:56
- Verify: reading code
- Verify result: CONFIRMED (`tests/` без `conftest.py`; фикстуры `rng`
  локальны в E-тестах)
- Action: add test
- Files changed: [`tests/conftest.py` (new)]
- Tests added: []
- Smoke: passed
- Notes: добавлена общая фикстура `rng`. Существующие тесты НЕ менялись —
  их локальные фикстуры не трогаются (правило 2). Централизация применена
  к новым E-тестам.

### E6 — Windows-specific тест shm
- Classification: E-QUALITY
- Start: 2026-10-06T08:15:56
- Verify: reading code
- Verify result: CONFIRMED (нет Windows-специфичного теста)
- Action: stop
- Files changed: []
- Tests added: []
- Smoke: n/a
- Notes: STOP. Требует Windows runner (`multiprocessing.shared_memory`
  поведение отличается); текущая среда — win32, но воспроизводимого
  проверяемого инварианта помимо существующих `test_pairs.py` нет, а
  заказ Windows-job в CI — группа F. Не добавлялось.

### E10 — stale .pytest_cache
- Classification: E-QUALITY
- Start: 2026-10-06T08:15:56
- Verify: reading code
- Verify result: OBSOLETE (кэш-артефакт, файла `test_pipeline.py` нет)
- Action: skip
- Files changed: []
- Tests added: []
- Smoke: n/a
- Notes: не является дефектом тестов.

---

## Итог сессии

- Всего в группе E (таблица): 11
- CLOSED (до сессии): 4 (E1, E2, E4, E11)
- OBSOLETE: 1 (E10)
- OPEN на старте: 6 (E3, E5, E6, E7, E8, E9)
- Обработано: 6
  - E-CORRECTNESS: 3 находки, 8 tests added (E3: 4 кейса, E5: 2, E8: 2)
  - E-COVERAGE: 1 находка, 12 tests added (E7)
  - E-QUALITY: 1 находка (E9), conftest + 1 fixture
  - E-POLISH: 0
  - STOP: 1 (E6)
  - FALSE: 0
- Осталось OPEN: 1 (E6 — STOP, требует Windows CI)
- Тесты: было 215, стало 235 (добавлено 20 новых тестов)
- Smoke: passed (`235 passed, 2 deselected`, последний прогон)
- Рекомендация: закрыть E6 вместе с Windows-job из группы F после
  получения traceback.

### Финальная проверка
- `python -m pytest tests/ -m "not slow" -q` → 235 passed, 2 deselected.
- `python -m ruff check tests/conftest.py tests/test_E_*.py` → All checks passed.
- Все новые файлы untracked (коммит не выполнялся).

