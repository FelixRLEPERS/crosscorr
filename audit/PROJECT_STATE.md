# CrossCorr — состояние проекта

Дата сборки: 2026-10-06 (v5, sync до HEAD 65dbdbd)
HEAD: `65dbdbdac26aa9b161625294642053dea118ca81` "docs: sync methodology, roadmap, README, git checklist [DOC-1..5]"
Ветка: main
Рабочее дерево до v5-синхронизации: чистое (`git status --short` пуст);
после sync изменены `audit/BACKLOG.md`, `audit/PROJECT_STATE.md`,
`audit/STOP_DECISIONS.md`.
Удалённый репозиторий: `origin/main` (в синхроне, ahead/behind 0)

---

## 1. Резюме

За последние сутки (серия из ~30 часов) закрыты все 7 групп бэклога A–G
(плюс верификация группы H): закрыто 55 находок, все 9 P0 закрыты, тестов
стало 237 (collected) против 215 на начало сессии. Проект переведён на
новые аналитические и инфраструктурные рельсы: два пайплайна (`analysis` и
`pairs`) задокументированы, CI расширен matrix 3.11/3.12, добавлены
coverage-порог, compileall, ruff scope `data/`, Windows job (informational),
slow-тесты по paths-filter на PR. Численные эталоны статистики
(`fdr_bh_q`, BY, max-stat, lagged CC, IAAFT, AR(1)) зафиксированы тестами.
Единственный статистический гейт, который пока не пройден, — реальные
данные: `data/raw/` пуст, все результаты получены на синтетике (A9–A11).
Осталось 15 STOP-находок (было 34): в v5 закрыты очереди 1/2 (18 находок;
D8 — DEFERRED, вариант C), добавлено 13 находок по новым модулям
MI/TE/MSE/XM и производительности (12 closed, 1 deferred), установлен git-тег
`v0.1.0`. Закрыты XM-1/XM-2 (convention abs-default + split-option; XM-2 было
в статусе DEFERRED).
Итог: 171 находка, 135 closed, 15 STOP, 2 deferred. Следующий крупный
шаг — научная валидация на реальных WSPR + INTERMAGNET.

---

## 2. Метрики

| Метрика | Значение |
|---|---|
| Тесты | 237 collected (235 fast + 2 slow, сборка 08:51); v5: +~150 строк тестов в 4 модулях — точный collected-count переизмерить |
| Ruff | clean (`crosscorr_lib/ tests/ scripts/ data/`); порог CI 45% |
| CI | matrix 3.11 + 3.12 (fast), 3.12 (slow), 3.12 (windows, informational) |
| P0 open | 0 |
| P1 open | 0 |
| P2/P3 open | 4 (B21, B22, B33, H3) |
| CLOSED | 135 |
| STOP-находок | 15 |
| DEFERRED (v5) | 2 (D8, XM-5) |
| PARTIAL | 3 (A30, F17, F20) |
| FALSE (не подтверждены) | 6 (B28, B36, F11, F15, F16, G6) |
| UNVERIFIED | 4 (B19, C8, C9, C10) |
| Групп бэклога закрыто | 7 из 7 (A, B, C, D, E, F, G) |

---

## 3. Что сделано за последние 30 часов

### Группа A — ETL и данные (`6049c2a`)
- Закрыто 26 находок; переклассифицирована A30 (PARTIAL).
- Добавлены фикстуры `data/samples/` (wspr, intermagnet, horizons, confounders).
- Исправлены: парсер IAGA-2002 (`d711569`), схема `detector_type`, уникальность
  ключа `rx_call` + агрегация по `tx_call`, `.head(500)` в `make_sample`,
  абсолютные пути, sha256-сайдкары, `base_url`/`expected_fields` реестра.
- `tests/test_data_samples.py` (17 тестов).
- STOP: A9/A10/A11 — нужны реальные данные из сети.

### Группа B — Ядро анализа (`25f0e90`)
- Закрыто 2: B24 (`n_obs` до интерполяции NaN), B38 (`kind="stable"` в FDR ties).
- Подтверждены FALSE: B28 (общий mask не занижает IAT), B36 (`max_lag` уже есть).
- STOP (вне границ/решение): B18, B20, B23, B25, B26, B27, B29, B30, B35, B39.
- Отложено (перф): B21, B22, B33.
- `tests/test_B_statistics.py` (4 теста).

### Группа C — pairs.py (`0e75aab`)
- Закрыто 3: C3 (убрано двойное выделение памяти), C6 (дефект `-(T-1)` при T=1),
  C7 (тесты T=1/T=2/one-row wide).
- STOP/UNVERIFIED: C8 (dtype float32), C9 (resource_tracker < 3.13), C10 (shm views).
- `tests/test_C_pairs.py` (5 тестов).

### Группа D — API (`15c38ed`)
- Закрыто 4: D1 (две `cross_correlation_pairs_with_max_stat` задокументированы,
  API сохранён), D3 (`fdr_bh` vs `fdr_bh_q`), D4 (`analysis.__all__` + `preprocess`),
  D11 (комментарий про `True/False/None` в SAFE_BUILTINS).
- STOP: D5 (git-теги), D6–D14 (игровой код / pyproject / analysis/*.py вне границ).
- `tests/test_D_api.py` (10 тестов). Backward compatibility сохранена.

### Группа E — Тесты (`786c471`)
- Закрыто 5: E3 (эталон AR(1) `(1+φ)/(1-φ)`), E5 (свойства/сходимость IAAFT),
  E7 (`adf_test`, `check_stationarity_wide`, `mfdfa_spectrum`, `load_unified`,
  CLI `power_curve`), E8 (пустой wide, constant series), E9 (`conftest.py`,
  фикстура `rng`).
- STOP: E6 (Windows-специфичный тест shm — нужен Windows runner).
- Новые файлы: `tests/conftest.py`, `tests/test_E_correctness.py`,
  `test_E_stationarity.py`, `test_E_mfdfa.py`, `test_E_coverage.py`, `test_E_cli.py`.

### Группа F — CI (`49417c9`, `5194f36`, `3c12ebc`, `1a4e5c3`)
- Закрыто 8: F3 (matrix 3.11/3.12), F4 (Windows job), F5 (coverage),
  F6 (ruff `data/`), F7 (slow по paths-filter на PR), F8 (compileall),
  F9 (`cache-dependency-path`), F12 (ignore coverage-артефактов).
- PARTIAL: F17 (pytest-cov задействован, pip-tools нет), F20 (numpy>=1.25).
- STOP: F1 (lock, нужна сеть), F14 (две модели зависимостей), F18 (git-мусор).
- `1a4e5c3`: `test-windows` переведён в informational (`continue-on-error`).
- `tests/test_F_ci.py` (10 тестов).

### Группа G — Документация (`4232b49`)
- Закрыто 7: G2 (BY vs BH), G3 (Mantel default), G4 (methodology: max-stat, BY,
  bootstrap, Mantel, IAAFT, MFDFA), G7 (surrogate methods), G8 (Fisher-веса),
  G9 (значения B), G10 (results-пометка).
- FALSE: G6 (ссылки внутри HTML-комментария).
- STOP: G11–G14 (`README_ARCHITECTURE_UPDATE.md` вне границ), G22–G25 (код, группа B).
- `tests/test_G_docs.py` (10 тестов).

### Пост-сессионно
- `386c5c7`: `adfuller(..., result_object=False)` — снят FutureWarning statsmodels.

---

## 4. Текущий CI

Файл: `.github/workflows/ci.yml` (112 строк, YAML валиден).

| Job | Что проверяет | Blocking |
|---|---|---|
| check-changes | `dorny/paths-filter@v3`: `crosscorr_lib/analysis/**`, тесты анализа | нет (нужен для test-slow) |
| test-fast (3.11) | ruff + compileall + pytest `not slow` + coverage | да |
| test-fast (3.12) | ruff + compileall + pytest `not slow` + coverage | да |
| test-slow | pytest `-m slow` на push или PR с изменениями analysis | да (по условию) |
| test-windows | pytest `not slow` на windows-latest | нет (informational, `continue-on-error: true`) |

- Coverage threshold: `--cov-fail-under=45` (измерено ~49%).
- Matrix: `test-fast` = `["3.11", "3.12"]`; slow/windows = 3.12.
- Triggers: `push` (main) и `pull_request` (main).
- Ruff scope: `crosscorr_lib/ tests/ scripts/ data/`.
- Известная внешняя проблема: 2 job-а (3.11, slow) не получили hosted runner
  ("The job was not acquired by Runner of type hosted") — инфраструктура GitHub,
  не код. План: Re-run failed jobs после восстановления.

---

## 5. Публичный API

- `crosscorr_lib.__all__`: 18 символов (load_unified, build_wide_by_detector,
  lagged_cross_correlation, cross_correlation_pairs,
  cross_correlation_pairs_with_max_stat, pairs, fdr_bh, fdr_bh_q,
  max_lag_surrogate_pvalue, phase_surrogate, surrogate_test,
  effective_sample_size, correlation_pvalue_with_ess, block_bootstrap_pvalue,
  load_confounders, remove_confounders, adf_test, check_stationarity_wide;
  `__version__ = "0.1.0"` объявлен отдельно).
- `analysis.__all__`: `["fdr_bh", "max_lag_surrogate_pvalue", "preprocess"]`.
- Ключевые точки входа:
  - `analysis.cross_correlation.cross_correlation_pairs_with_max_stat` — ядро
    (Spearman per lag, колонки `detector_1/detector_2/lag/correlation`).
  - `pairs.cross_correlation_pairs_with_max_stat` — production (FFT-batch +
    shared memory, колонки `detector_a/detector_b/C_obs/verdict`).
  - `safe_exec.run_code_safe` — песочница (FORBIDDEN_NAMES: ctypes, code,
    threading, multiprocessing, platform).
- git-тегов: `v0.1.0` (D5 CLOSED `f730ddd`; `git tag --list` подтверждено).

---

## 6. Тестовое покрытие

- Всего тестов: 237 collected (235 fast + 2 `slow`).
- Численные эталоны: 12 (`test_statistical_reference.py`: BH, BY, max-stat,
  lagged CC, fisher_weighted_max_stat).
- Consensus/контрактные: `test_core_regression.py` (25), `test_D_api.py` (10),
  `test_F_ci.py` (10), `test_G_docs.py` (10).
- DOC-тесты: 10 (`test_G_docs.py`) + часть `test_F_ci.py`.
- Coverage: ~49% (порог CI 45%). Точное значение не переизмерялось в этой
  сборке (правило: без запуска pytest).

---

## 7. STOP-находки (требуют решений пользователя)

15 STOP открыто + 2 DEFERRED (v5: D8, XM-5).
Закрыто в v5: D5, D6, D7, D9, D10, D12, D13, D14, B35, F18, G11–G14, G22–G25
(`a7c8a0c`, `f730ddd`), MI-3, TE-3 и BENCH-1 (benchmark достаточен для целевого
масштаба K≤20, N≤10000). C8/C9/C10 — UNVERIFIED (не в счёт 15), B19 — фактически
FALSE; см. приложение `audit/STOP_DECISIONS.md`.

### Пары / предобработка (нужна сессия группы C)
- B18/B20/B26/B27: `pairs.py`.
- B23/B29/B30: `preprocessing.py` (robust != Theil-Sen, интерполяция без лимита,
  ряд длины 2 → нули) — вне границ прошлых сессий.
- B25: NaN-пары выбрасываются до FDR — меняет число гипотез M.
- B39: критерий сходимости IAAFT не стандартен — меняет числовой результат.

### Внешние данные / окружение
- A9/A10/A11: реальные данные (`data/raw` пуст, parquet синтетический).
- E6: Windows-специфичный тест shm — нужен Windows runner.
- F1: `requirements.lock` (нет joblib, собран на 3.13) — нужна сеть `pip-compile`.

### Архитектура
- F14: две модели зависимостей (`requirements.in` vs `pyproject.toml`) —
  архитектурное решение.

### CI
- F7 => перенесено в feature (paths-filter), STOP закрыт в `5194f36`.
- Codecov (F7 исходно в описании задания как «F7»): отдельный внешний сервис
  (`codecov.io` + `CODECOV_TOKEN`). В BACKLOG это не отдельный ID; текущий
  `--cov-report=term-missing` покрывает локальную потребность.

---

## 8. Научные решения

- **Cross-MFDFA convention:** принят abs-default + split-option.
  Обоснование — Qwen 3.8 Max Prime consultation,
  `audit/external_reviews/QWEN_v5_consultation.md`. Открытая проблема
  (знак F²_v) задокументирована в docstring; XM-1/XM-2 закрыты.

---

## 9. Стратегические цели (что дальше)

### Немедленные (можно сделать в ближайшие дни)
1. Re-run упавших CI-job (3.11, slow) после восстановления GitHub runners;
   получить traceback Windows job и закрыть E6.
2. Сессия группы C для оставшихся B-STOP (B18/B20/B23/B25/B26/B27/B29/B30/
   B39 — pairs.py / preprocessing.py) и F14 — это код и решения вне границ
   прошлых сессий.

### Научные (требуют данных)
1. Прогон на реальных WSPR + INTERMAGNET (A9/A10/A11), затем перегенерация
   `unified.parquet` документированным `unify_schema.py`.
2. Препринт (требует реальных данных + финального B/CI).

### Долгосрочные
1. Дедупликация NaN-интерполяции (B33) и перф-оптимизация surrogate/mantel
   (B21, B22).
2. Полный mypy-гейт (D8 — DEFERRED, вариант C, `f730ddd`).

---

## 10. Технический долг

- Windows traceback (`test-windows` падает, informational) — нужен лог.
- Re-run старых красных CI после восстановления GitHub-hosted runners.
- P2/P3 отложенные: B21, B22, B33, H3.
- PARTIAL: A30 (физика синтетики), F17 (pip-tools не используется),
  F20 (numpy>=1.25 без прогонного подтверждения).
- Оптимизация #1: `rho` из `max_lag_surrogate_pvalue` (избежать повторного
  `lagged_cross_correlation` в `cross_correlation_pairs_with_max_stat`).
- 15 STOP-находок + 2 DEFERRED (v5) ждут решений (см. секцию 7).

---

## 11. Рекомендуемый следующий шаг

Начать с разблокировки CI: дождаться восстановления GitHub-hosted runners,
сделать Re-run упавших job-ов и снять traceback `test-windows` — это снимет
инфраструктурный шум и закроет E6. Административные пункты очередей 1/2
закрыты в v5 (D5 — тег `v0.1.0`, F18, D6/D7, D13/D14, B35; `a7c8a0c`,
`f730ddd`); короткая сессия остаётся только по остаточным STOP-решениям
(F14, B18/B20/B23/B25/B26/B27/B29/B30/B39) — они не требуют данных и сети.
Затем перейти к главному научному гейту — получению реальных данных
(A9/A10/A11): именно он, а не какие-либо оставшиеся P2/P3, определяет, можно ли
переходить к препринту и Zenodo-релизу (git-тег `v0.1.0` уже установлен).
Сессии по B-остатку стоит ставить после появления реального датасета, чтобы
правки статистики проверялись на значимых данных, а не на синтетике.
