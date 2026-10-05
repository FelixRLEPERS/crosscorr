# Группа G — прогресс ночной сессии

HEAD на старте: `3c12ebc`.
Источник истины: код `crosscorr_lib/**`.

## Факты по группе G

BACKLOG группа G: 25 записей. CLOSED: G1, G5, G15-G21 (G21 — по коммиту
`2280fc2`). OBSOLETE: нет.
OPEN: G2, G3, G4, G6, G7, G8, G9, G10, G11, G12, G13, G14, G22, G23,
G24, G25.

Проверка кода (источник истины):
- `fdr_bh_q(..., method="by")` — по умолчанию BY (surrogate.py:237).
- `cross_correlation_pairs_with_max_stat(..., n_surrogates=200,
  fdr_method="by")` (cross_correlation.py:170-173).
- `max_lag_surrogate_pvalue(..., max_lag=72, n_surrogates=500,
  fisher=True, surrogate_method="phase")` (surrogate.py:334-341).
- CLI `cross_correlation.py`: `--n-surrogates` default 200,
  `--fdr-method` default "by" (строки 367-383).
- CLI нет флага `--surrogate-method`: доступны только phase;
  iaaft/time_shift — через API.
- `distance_analysis.main`: `--method` default "mantel" (строка 160).
- `api_client.DataClient` НЕ использует `SourceRegistry` (файл: docstring
  «точка расширения», `SourceRegistry` не импортируется).
- `tests/test_source_registry.py` отсутствует и не в git.

## Классификация

G-CORRECTNESS: G2, G3, G4, G8, G9
G-CONSISTENCY: G7, G10
G-LINKS: G6, G13
G-POLISH: G11, G12, G14
STOP (вне границ / код): G11, G12, G13, G14, G22, G23, G24, G25

## Статус
Начало: 2026-10-05 22:43

---

### G2 — PIPELINE.md §6 документирует только BH, код по умолчанию BY
- Classification: G-CORRECTNESS
- Start: 2026-10-05 22:43
- Verify: reading code (`surrogate.py:237`, `cross_correlation.py:173`)
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`docs/PIPELINE.md`]
- Code reference: `crosscorr_lib/analysis/surrogate.py:237`
- Notes: §6 назван «FDR (Benjamini-Hochberg)» и описывает только BH. Код по умолчанию — BY. Обновлено: BY (default, c(m)=Σ1/k), BH опционально.

### G3 — PIPELINE.md §11 описывает OLS, основной метод — Mantel
- Classification: G-CORRECTNESS
- Start: 2026-10-05 22:43
- Verify: reading code (`distance_analysis.py:159-161`)
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`docs/PIPELINE.md`]
- Code reference: `crosscorr_lib/analysis/distance_analysis.py:160`
- Notes: `--method` default = "mantel". §11 переписан: Mantel как default, OLS — опция.

### G4 — methodology.md не описывает max-stat, BY, bootstrap, Mantel, IAAFT, MFDFA
- Classification: G-CORRECTNESS
- Start: 2026-10-05 22:43
- Verify: reading other docs + code
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`docs/methodology.md`]
- Code reference: `surrogate.py`, `block_bootstrap.py`, `mantel.py`, `mfdfa.py`
- Notes: добавлены краткие пункты; полные формулы уже есть в PIPELINE.md. ESS-раздел уже был (коммит `cee803d`).

### G8 — PIPELINE.md §4.2 формула max-stat без Fisher-весов
- Classification: G-CORRECTNESS
- Start: 2026-10-05 22:43
- Verify: reading code (`surrogate.py:397-398, 512`)
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`docs/PIPELINE.md`]
- Code reference: `crosscorr_lib/analysis/surrogate.py:512`
- Notes: `fisher=True` по умолчанию: `T = max_tau |arctanh(r)|·sqrt(n_tau-3)`. Добавлено примечание к §4.2.

### G9 — три разных значения B
- Classification: G-CORRECTNESS
- Start: 2026-10-05 22:43
- Verify: reading code
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`docs/PIPELINE.md`]
- Code reference: `surrogate.py:334-341`, `cross_correlation.py:367-370`
- Notes: уточнено: функция `max_lag_surrogate_pvalue` default B=500; CLI `--n-surrogates` default 200; рекомендация 1000+ для публикаций.

### G7 — PIPELINE.md §5 описывает только phase
- Classification: G-CONSISTENCY
- Start: 2026-10-05 22:43
- Verify: reading code (`surrogate.py:341,357-361`)
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`docs/PIPELINE.md`]
- Code reference: `crosscorr_lib/analysis/surrogate.py:341`
- Notes: добавлено: phase (default), iaaft, time_shift доступны через API-параметр `surrogate_method`; из CLI недостижимы (нет флага).

### G10 — PIPELINE.md «Результаты: results/*.csv» без пометки об устаревании
- Classification: G-CONSISTENCY
- Start: 2026-10-05 22:43
- Verify: reading other docs
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`docs/PIPELINE.md`]
- Code reference: n/a
- Notes: добавлена пометка о перегенерации (согласовано с README:318).

### G6 — README ссылки на results/cross_correlation.png, results/mfdfa.png
- Classification: G-LINKS
- Start: 2026-10-05 22:43
- Verify: reading README
- Verify result: FALSE
- Action: skip
- Files changed: []
- Code reference: n/a
- Notes: обе ссылки находятся внутри HTML-комментария `<!-- ... -->` (README.md:574-580) и не рендерятся. Активных битых ссылок нет. Правка не требуется.

### G11 — README_ARCHITECTURE_UPDATE.md: api_client использует SourceRegistry
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: reading code (`data/scripts/api_client.py`)
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Code reference: `data/scripts/api_client.py:4-5`
- Notes: STOP. Файл `README_ARCHITECTURE_UPDATE.md` не входит в список разрешённых к правке (задание: README.md, docs/*, analysis/README.md, data/README.md). Утверждение ложно: `DataClient` не валидирует через реестр. Правка невозможна в границах сессии.

### G12 — README_ARCHITECTURE_UPDATE.md: «Надежность: Высокая»
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. Тот же файл вне границ.

### G13 — README_ARCHITECTURE_UPDATE.md: ссылка на test_source_registry.py
- Classification: G-LINKS
- Start: 2026-10-05 22:43
- Verify: `git ls-files`, `ls tests/`
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. Файл `tests/test_source_registry.py` отсутствует, но правка — в `README_ARCHITECTURE_UPDATE.md` вне границ.

### G-analysis-readme — analysis/README.md не перечислял модули
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: чтение каталога `crosscorr_lib/analysis/*.py` (тест выявил 9 модулей)
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`crosscorr_lib/analysis/README.md`]
- Code reference: n/a
- Notes: добавлена таблица модулей (cross_correlation, surrogate, effective_sample, block_bootstrap, preprocessing, confounders, stationarity, mantel, distance_analysis, mfdfa, residuals, power_curve, benchmark_utils, visualization). Не отдельная запись BACKLOG, обнаружено тестом.

### G14 — README_ARCHITECTURE_UPDATE.md: эмодзи
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: reading
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Notes: STOP. Файл вне границ.

### G22 — surrogate.py: константы без имени
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: reading code
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Code reference: `crosscorr_lib/analysis/surrogate.py:55,86,95,127`
- Notes: STOP. Это находка к коду (группа B), не к документации. Правило 5: правка требует изменения кода.

### G23 — cross_correlation.py: магическое n < 10
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: reading code
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Code reference: `crosscorr_lib/analysis/cross_correlation.py:88`
- Notes: STOP. Находка к коду (группа B).

### G24 — surrogate.py E302
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: reading code
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Code reference: `crosscorr_lib/analysis/surrogate.py:127,257,292,436,485`
- Notes: STOP. Код (группа B).

### G25 — surrogate.py 2D fdr_bh без проверки симметричности
- Classification: G-POLISH
- Start: 2026-10-05 22:43
- Verify: reading code
- Verify result: CONFIRMED
- Action: stop
- Files changed: []
- Code reference: `crosscorr_lib/analysis/surrogate.py:114-124`
- Notes: STOP. Код (группа B).

---

## Итог сессии

- Всего в группе G: 25 записей
- CLOSED (до сессии): 9 (G1, G5, G15-G21)
- OPEN на старте: 16
- Обработано: 16
  - G-CORRECTNESS: 5 closed (G2, G3, G4, G8, G9)
  - G-CONSISTENCY: 2 closed (G7, G10)
  - G-LINKS: 1 FALSE (G6)
  - G-POLISH: 1 closed (analysis/README.md — не BACKLOG-ID, выявлено тестом)
  - STOP: 8 (G11, G12, G13, G14 — вне границ; G22, G23, G24, G25 — код/группа B)
- Осталось OPEN: 8 (G11, G12, G13, G14, G22, G23, G24, G25)
- Тесты docs: добавлено `tests/test_G_docs.py`
- Рекомендация: перенести G11-G14 в правку `README_ARCHITECTURE_UPDATE.md` (файл вне границ текущей сессии) и G22-G25 — в группу B.

### Проверка арифметики
- fix: G2, G3, G4, G7, G8, G9, G10 = 7
- skip (FALSE): G6 = 1
- stop: G11, G12, G13, G14, G22, G23, G24, G25 = 8
- Итого: 7 + 1 + 8 = 16 = OPEN на старте. Осталось 8.

### Изменённые файлы
- `docs/PIPELINE.md` (G2, G3, G7, G8, G9, G10)
- `docs/methodology.md` (G4)
- `tests/test_G_docs.py` (new)
- `audit/G_progress.md` (new)
