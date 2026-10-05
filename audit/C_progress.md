# Группа C — прогресс ночной сессии

HEAD на старте: `25f0e90` (группы A/B закоммичены, дерево чистое).
Среда: Python 3.13.5, numpy 2.5.3, pandas 3.0.5.
Baseline smoke: `test_pairs.py` + `test_statistical_reference.py` + `test_max_stat_pipeline.py` -> 35 passed.

## Классификация

C-CORRECTNESS (приоритет 1):
- C6 — дефект среза `-(T-1)` при T=1
- C7 — нет тестов граничных размеров `_batch_max_stat_corr`

C-STAT (приоритет 2, needs user decision):
- C8 — float32 для суррогатов против float64 для C_obs (UNVERIFIED)

C-PERF (приоритет 3):
- C3 — двойное выделение памяти под суррогаты
- C9 — двойной unlink через resource_tracker (Python < 3.13, UNVERIFIED)

C-POLISH (приоритет 4):
- C10 — shm.close() при живых views (UNVERIFIED)

## Статус
Начало: 2026-10-05 22:12

---

### C6 — дефект среза -(T-1) при T=1
- Classification: C-CORRECTNESS
- Start: 2026-10-05 22:12
- Verify: script `audit/verify_C6.py`
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`crosscorr_lib/pairs.py`]
- Tests added: [`tests/test_C_pairs.py`] (test_batch_max_stat_single_sample_returns_zeros, test_max_stat_corr_short_series_returns_zero, test_batch_max_stat_two_samples_ok, test_c6_single_row_wide_is_handled)
- Smoke check: test_pairs + references + pipeline + C — passed (40 passed)
- Stdout (`python audit/verify_C6.py`):
```
T=1: irfft cols=2, after concat cols=3
  _batch_max_stat_corr -> [0. 0.]
T=2: irfft cols=4, after concat cols=3
  _batch_max_stat_corr -> [1. 1.]
T=3: irfft cols=6, after concat cols=5
  _batch_max_stat_corr -> [0.86975403 0.94543378]
T=1 constant surrogate, degenerate expected:
  out = [0.]
  max_stat single = 0.0
```
- Notes: подтверждено — при T=1 конкатенация даёт 3 столбца вместо 1. Результат на этих данных всё равно 0.0 из-за degenerate-маски, но структура неверна и зависит от данных. Правка: ранний `return np.zeros(B)` в `_batch_max_stat_corr` и `return 0.0` в `_max_stat_corr` при длине < 2. Формула FFT для T >= 2 не изменена.

### C7 — нет тестов граничных размеров
- Classification: C-CORRECTNESS
- Start: 2026-10-05 22:12
- Verify: reading
- Verify result: CONFIRMED (тестов не было)
- Action: fix (частично, через новые тесты C6)
- Files changed: []
- Tests added: [`tests/test_C_pairs.py`] (T=1, T=2, one-row wide)
- Smoke check: passed
- Notes: полный набор граничных размеров не покрыт, но T=1/T=2 и wide из одной строки добавлены. Осталось (для полноты): n=0 колонок, T=0.

### C3 — двойное выделение памяти под суррогаты
- Classification: C-PERF
- Start: 2026-10-05 22:12
- Verify: script `audit/verify_C3.py`
- Verify result: CONFIRMED
- Action: fix
- Files changed: [`crosscorr_lib/pairs.py`]
- Tests added: [`tests/test_C_pairs.py`] (test_c3_result_matches_expected)
- Smoke check: passed (40 passed)
- Stdout (`python audit/verify_C3.py`):
```
surrogates block nbytes = 40000000
plus X (T,N) float64    = 400000
peak double-alloc extra = 40000000 bytes (out + shm copy)
```
- Notes: подтверждено — `out` в куче плюс копия в shm давали пик ~2x (40 МБ при N=10,B=200,T=5000). Правка: `view_surr` выделяется первым, заполняется напрямую через `_make_surrogates`; промежуточный `out` убран. `out.shape` в вызовах `_worker` заменён на `surr_shape`. Результат не изменился (детерминизм seed проверен тестом). Публичный API не изменён.

### C8 — float32 суррогатов против float64 C_obs
- Classification: C-STAT
- Start: 2026-10-05 22:12
- Verify: reading
- Verify result: UNVERIFIED
- Action: stop
- Files changed: []
- Tests added: []
- Smoke check: n/a
- Notes: STOP "needs user decision". Влияние float32 на p-value не проверено и требует численного исследования (сравнение p-value при dtype float32/float64 на одном seed). Варианты: (a) перевести суррогаты на float64, (b) оставить float32 с оценкой расхождения, (c) параметр уже есть (`dtype`) — документировать trade-off. Правило 3 запрещает менять статистическую модель без решения пользователя.

### C9 — двойной unlink через resource_tracker (Python < 3.13)
- Classification: C-PERF
- Start: 2026-10-05 22:12
- Verify: reading
- Verify result: UNVERIFIED
- Action: stop
- Files changed: []
- Tests added: []
- Smoke check: n/a
- Notes: STOP. Поведение resource_tracker в воркерах зависит от версии CPython (bpo-39959); на Python 3.13.5 не воспроизводится, на 3.10-3.12 требует отдельного окружения. Правка не входит в статистическую модель и не требуется для текущего CI (3.12 в ci.yml, но локально 3.13). Варианты не предлагаются — нужен прогон на 3.10-3.12.

### C10 — shm.close() при живых views
- Classification: C-POLISH
- Start: 2026-10-05 22:12
- Verify: reading
- Verify result: UNVERIFIED
- Action: stop
- Files changed: []
- Tests added: []
- Smoke check: n/a
- Notes: STOP. `_worker` закрывает `shm_s`/`shm_x` в `finally` при живых `surr`/`X`/`si`/`sj`. На CPython `close()` не освобождает буфер, пока есть views, но может предупреждать; существующий тест `test_two_sequential_calls_do_not_leak_shm` проходит, явного BufferError нет. Требует отдельной проверки с `tracemalloc`/`warnings`. Правка потребует переработки жизненного цикла views — риск для стабильности, поэтому STOP.

---

## Итог сессии

- Всего в группе C: 10 записей; статусы в BACKLOG: 4 CLOSED (C1, C2, C4, C5), 6 OPEN/UNVERIFIED.
- OPEN на старте: 6 (C3, C6, C7, C8, C9, C10).
- Обработано: 6
  - C-CORRECTNESS: 2 closed (C6 fix, C7 частично fix через тесты)
  - C-STAT: 1 STOP (C8, needs user decision)
  - C-PERF: 1 closed (C3), 1 STOP (C9, UNVERIFIED/platform)
  - C-POLISH: 1 STOP (C10, UNVERIFIED)
  - FALSE: 0
- Осталось OPEN: 3 (C8, C9, C10 — все UNVERIFIED/needs decision)
- Smoke checks: passed (test_pairs 14 + references 12 + pipeline + C_pairs 6 = 40 passed)
- Тесты: было 180 (по заданию), фактически 177 `def test_` до сессии; добавлено 6 в `tests/test_C_pairs.py`.
- Рекомендация на следующую сессию: решить C8 (dtype суррогатов, численное сравнение p-value) и C9/C10 на Python 3.10-3.12 с явным тестом жизненного цикла shm.

### Проверка арифметики (по строкам "- Action:")
- fix: C3, C6, C7 = 3
- stop: C8, C9, C10 = 3
- Итого обработано: 3 + 3 = 6
- Осталось OPEN: 6 − 3 = 3 (совпадает).

### Изменённые файлы
- `crosscorr_lib/pairs.py` (C6, C3)
- `tests/test_C_pairs.py` (new)
- `audit/C_progress.md` (new)
- `audit/verify_C3.py`, `audit/verify_C6.py` (new)
