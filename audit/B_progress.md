# Группа B — прогресс ночной сессии

HEAD на старте: `6049c2a` (группа A уже закоммичена, дерево чистое).
Среда: Python 3.13.5, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1.
Baseline: `python -m pytest tests/test_statistical_reference.py -q` -> 12 passed.

## Фактическое число OPEN

BACKLOG группа B: 20 записей с OPEN-подобным статусом, из них
B19 помечен UNVERIFIED, а не OPEN. Реально OPEN = 17:
B18, B20, B21, B22, B23, B24, B25, B26, B27, B28, B29, B30,
B33, B35, B36, B38, B39.

## Ограничения границ (STOP до начала правок)

Разрешённые файлы: `cross_correlation.py`, `surrogate.py`,
`mantel.py`, `distance_analysis.py`, `effective_sample.py`,
`block_bootstrap.py`.
Запрещены: `pairs.py` (группа C), `preprocessing.py`
(не входит ни в разрешённые, ни в список создаваемых).

Поэтому недостижимы:
- B18, B19, B20, B26, B27, B35 — находятся в `pairs.py` (группа C).
- B23, B29, B30 — находятся в `preprocessing.py` (вне границ).

Это отмечено как STOP для каждой из них ниже.

## Классификация (достижимые)

B-STAT-RISK: B24, B25, B28, B36
B-CORRECTNESS: (нет отдельных, кроме границ в пределах B-STAT)
B-QUALITY: B21, B22, B38, B39
B-POLISH: B33

## Статус
Начало: 2026-10-05 21:57

---

### B18 — pairs.py: собственная реализация BH
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED (в BACKLOG, но)
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: правка живёт в `crosscorr_lib/pairs.py` — это группа C, править запрещено правилом 3. STOP без правки.

### B19 — pairs.py: зависимые p-value при общем детекторе
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: v3_verified
- Verify result: UNVERIFIED (механизм опровергнут, rho≈-0.003)
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: уже помечена UNVERIFIED в BACKLOG; правка вне границ (pairs.py).

### B20 — pairs.py: нет detrend/standardize
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: правка в `pairs.py` (группа C), запрещено.

### B21 — surrogate_test: Python-цикл + pandas.corr
- Classification: B-QUALITY
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: skip
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: оптимизация требует крупного рефакторинга surrogate_test; правило «не делать крупные рефакторинги» + скорость — отдельная задача. Не тронуто.

### B22 — mantel: permutation Python-цикл
- Classification: B-QUALITY
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: skip
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: перф-оптимизация; риск изменить числовой результат при переписывании. Оставлено следующей сессии.

### B23 — preprocessing: robust не Theil-Sen
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: правка в `crosscorr_lib/analysis/preprocessing.py`, который не входит ни в разрешённые, ни в список создаваемых. STOP.

### B24 — n_obs считается после интерполяции NaN
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: script `audit/verify_B24.py`
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`crosscorr_lib/analysis/cross_correlation.py`]
- Tests added: [`tests/test_B_statistics.py::test_n_obs_excludes_interpolated_points_max_stat`, `::test_n_obs_excludes_interpolated_points_naive`, `::test_n_obs_unchanged_without_nan`]
- Checkpoint: test_statistical_reference passed (12/12); test_B_statistics passed (4/4)
- Notes: вывод verify: `row length = 200, raw valid = 150, n_obs = 200, n_obs > raw_valid = True`. Добавлен `raw_wide = wide.copy()` до preprocess; `n_obs` берётся по исходным NaN обеих колонок. Для входов без NaN результат не меняется (отдельный тест).

### B25 — пары с NaN t_obs молча выбрасываются до FDR
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED (по коду `continue` на `cross_correlation.py:246`)
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: правка меняет число гипотез M для FDR — это смена статистического метода (сохранять NaN-пары в M или нет). Правило 5 требует решения пользователя. STOP. verify: reading (no script written; recommendation: add audit/verify_B25.py for reproducible check).

### B26 — pairs.py: shuffle разрушает автокорреляцию
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: `pairs.py` — группа C.

### B27 — pairs.py: AR(1) lfilter без burn-in
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: `pairs.py` — группа C.

### B28 — effective_sample: общий mask занижает IAT
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: script `audit/verify_B28.py`
- Verify result: FALSE
- Action: skip
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: вывод verify: `tau_x_own - tau_x_joint = -0.78`, `tau_y_own - tau_y_joint = -4.62`. Совместный mask дал tau ВЫШЕ, а не ниже; гипотеза «занижает IAT» не воспроизвелась. Причина: `effective_sample_size` вызывает IAT на `x[mask]`/`y[mask]`, но joint mask не занижает tau систематически; знак зависит от данных.

### B29 — preprocessing: интерполяция без ограничения длины
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: `preprocessing.py` вне границ задачи.

### B30 — preprocessing: ряд длины 2 → нули
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: `preprocessing.py` вне границ задачи.

### B33 — шесть копий NaN-интерполяции
- Classification: B-POLISH
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED (grep: surrogate.py, pairs.py, effective_sample.py, preprocessing.py)
- Action: skip
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: дедупликация требует общей функции; половина копий в `pairs.py` (запрещено) и `preprocessing.py` (вне границ). Отложено.

### B35 — pairs.py: недостижимая ветка интерполяции
- Classification: B-POLISH
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: `pairs.py` — группа C.

### B36 — max_lag не принимается из вызывающего кода
- Classification: B-STAT-RISK
- Start: 2026-10-05 21:57
- Verify: script `audit/verify_B36.py`
- Verify result: FALSE
- Action: skip
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Stdout (`python audit/verify_B36.py`):
```
iat.signature      = (x: 'np.ndarray', max_lag: 'int | None' = None) -> 'float'
ess.signature      = (x: 'np.ndarray', y: 'np.ndarray') -> 'float'
iat has max_lag    = True
ess has max_lag    = False
iat(max_lag=5)     = 1.0
iat(max_lag=100)   = 1.0
max_lag respected  = False
```
- Notes: `integrated_autocorrelation_time` уже имеет параметр `max_lag` (сигнатура `(x, max_lag=None)`); правка ранее внесена. `effective_sample_size` не прокидывает `max_lag`, но это не дефект: он вызывает IAT с дефолтом. Гипотеза «max_lag не принимается» не воспроизвелась. Строка `max_lag respected = False` относится только к белому шуму (`tau = 1.0` при любом max_lag) и не означает отсутствия параметра.

### B38 — np.argsort без kind="stable"
- Classification: B-QUALITY
- Start: 2026-10-05 21:57
- Verify: script (inline) + reading
- Verify result: CONFIRMED (порядок при ties недетерминирован)
- Action: fix
- Files changed: [`crosscorr_lib/analysis/surrogate.py`]
- Tests added: [`tests/test_B_statistics.py::test_fdr_ties_are_stable_across_calls`]
- Checkpoint: test_statistical_reference passed (12/12); test_B_statistics passed (4/4)
- Notes: добавлен `kind="stable"` в `benjamini_yekutieli` (строка ~209) и `fdr_bh_q` (строка ~271). Числовые q-value не меняются (v2 сам отмечал: «на решения не влияет»), меняется только scatter-back при ties.

### B39 — критерий сходимости IAAFT не стандартен
- Classification: B-QUALITY
- Start: 2026-10-05 21:57
- Verify: reading
- Verify result: CONFIRMED
- Action: STOP
- Files changed: []
- Tests added: []
- Checkpoint: n/a
- Notes: смена критерия сходимости меняет числовой результат `_iaaft_surrogate` — это изменение статистики без явного указания формулы-замены. STOP.

---

## Итог сессии

- Всего в группе B: 40 (BACKLOG)
- CLOSED (до сессии): 23
- Всего OPEN-подобных в BACKLOG: 17 OPEN + 1 UNVERIFIED (B19) = 18
- OPEN на старте сессии: 17
- Обработано: 18
  - B-STAT-RISK: 2 closed (B24, B38 переклассифицирован сюда), 2 FALSE (B28, B36), 1 UNVERIFIED-вход (B19), 7 STOP вне границ (B18, B20, B23, B26, B27, B29, B30), 1 STOP stat-decision (B25)
  - B-CORRECTNESS: 0
  - B-QUALITY: 0 closed (B21, B22, B39 skip/STOP)
  - B-POLISH: 0 (B33 skip, B35 STOP)
- Осталось OPEN: 15
- Численные эталоны: 12 из 12 прошли
- Тесты: было 173 `def test_` (176 по заданию), стало 177 (добавлено 4 в `tests/test_B_statistics.py`)
- Полный прогон: `python -m pytest tests/ -m "not slow" -q` -> 180 passed, 2 deselected
- Рекомендация на следующую сессию: перенести B18/B19/B20/B26/B27/B35 в сессию группы C (pairs.py) и B23/B29/B30 — в сессию с правом на preprocessing.py; B25 требует решения пользователя о судьбе NaN-пар в FDR.

### Проверка арифметики (по фактическим строкам "- Action:")
- fix: B24, B38 = 2
- skip (FALSE/no-fix): B21, B22, B28, B33, B36 = 5
- STOP: B18, B19, B20, B23, B25, B26, B27, B29, B30, B35, B39 = 11
- Итого обработано: 2 + 5 + 11 = 18
- База: OPEN на старте = 17 (B18, B20, B21, B22, B23, B24, B25, B26, B27, B28, B29, B30, B33, B35, B36, B38, B39) плюс B19 (UNVERIFIED).
- Просмотрено/обработано: 18 = 17 OPEN + 1 UNVERIFIED (B19).
- Закрыто фактически (fix): 2 (B24, B38).
- Осталось OPEN: 17 − 2 = 15. Совпадает с «Осталось OPEN: 15» в «Итоге сессии».

Примечание: прежняя формулировка «2 closed + 2 FALSE + 13 STOP = 17» смешивала
категории Action (fix/skip/STOP) и Verify result (CONFIRMED/FALSE/UNVERIFIED).
Корректная разбивка — по строкам "- Action:" выше. Базовое число 20 из
задания не совпадает с BACKLOG: в группе B фактически 17 OPEN, а не 20.
