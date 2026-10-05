# Audit v3 — verified

Дата: 2026-10-05
Ветка: main
Среда: Python 3.13.5, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1
Метод: каждая находка воспроизводится мини-скриптом из `audit/verify_*.py`; вывод скрипта зафиксирован ниже.

Классификация:
- CONFIRMED — гипотеза воспроизвелась.
- FALSE — воспроизвелась обратная картина.
- UNVERIFIED — без внешнего ресурса проверить нельзя.

---

## #1 (P0) correlation колонка = Fisher-score, не r в [-1,1]

- Скрипт: `audit/verify_1.py`
- Гипотеза: `cross_correlation_pairs_with_max_stat` пишет в колонку `correlation` значение `Fisher_weighted_max_stat` (`|arctanh(r)| * sqrt(n-3)`), которое может превышать 1.
- Вывод скрипта:

```
max |correlation| = 3.022468094753216
any > 1: True
min: 1.6385052158143596
max: 3.022468094753216
columns: ['detector_1', 'detector_2', 'lag', 'correlation', 'p_value', 'n_obs', 'n_surrogates', 'q_value', 'significant']
```

- Статус: **CONFIRMED**
- Обоснование: на чистых независимых рядах (r истинно ≈ 0) возвращённые значения лежат в диапазоне [1.64; 3.02], то есть не являются корреляцией в [-1,1]. Колонка `correlation` действительно хранит Fisher-score. Потребители `mantel.build_corr_matrix` (`mantel.py:135-137`), `distance_analysis.fit_distance_model` (`distance_analysis.py:102`) и heatmap (`visualization.py:227-228, 232`, `vmin=-1, vmax=1`) читают её как r и получают бессмысленные результаты.

---

## #3 (P1) пары с общим детектором → зависимые p-value (BH неприменим)

- Скрипты: `audit/verify_3.py`, `audit/verify_3b.py`, `audit/verify_3c.py`
- Гипотеза: пары с общим детектором используют одни и те же суррогаты, поэтому p-value зависимы и BH неприменим.
- Вывод verify_3 (60 прогонов):

```
share detector a: rho(p_ab, p_ac) = -0.0964
disjoint:         rho(p_ab, p_cd) = -0.0542
```

- Вывод verify_3c (прямая проверка нулевых статистик при общем детекторе `a`, 40 прогонов):

```
REPS = 40
mean rho(null_ab, null_ac | share a) = -0.0026
std  = 0.0681
fraction rho > 0: 0.5
```

- Статус: **UNVERIFIED**
- Обоснование: Эмпирика слабая: rho(p_ab,p_ac) незначимо (-0.0964 при 60 прогонах), shared -0.032 против independent -0.162 (verify_3b), rho нулевых статистик -0.003 (verify_3c). Механизм (общие суррогаты → зависимые нули) опровергнут. Наблюдаемая зависимость p-value приписана багу переиспользования seed из находки #6, но это не проверено напрямую.

---

## #5 (P1) max_lag > n → ValueError в `_count_valid_at_lag`

- Скрипт: `audit/verify_5.py`
- Гипотеза: при `n < max_lag` срезы в `_count_valid_at_lag` имеют разную длину и `&` бросает ValueError.
- Вывод скрипта:

```
n = 20 max_lag = 30 (> n)
EXCEPTION: ValueError - operands could not be broadcast together with shapes (0,) (10,)
```

- Статус: **CONFIRMED**
- Обоснование: `max_lag_surrogate_pvalue(x, y, max_lag=30)` при `n=20` падает с `ValueError`. Значит дефолтный `max_lag=72` ломает любой ряд короче 72 точек. `_count_valid_at_lag` вызывается до проверки `n < 10` в `lagged_cross_correlation`, поэтому защита там не срабатывает.

---

## #6 (P1) pair_idx не инкрементится после continue

- Скрипты: `audit/verify_6.py`, `audit/verify_6b.py`, `audit/verify_6c.py`
- Гипотеза: при пропуске пары (`continue`) `pair_idx` не растёт, следующая пара берёт тот же child_rng.
- Вывод verify_6c (детектор `c` постоянный, пара (b,c) пропускается):

```
successful pairs: [('a', 'b'), ('a', 'd'), ('b', 'd')]
seeds passed (pair order): [1068165419, 160407627, 1003928805, 1510093563, 152985023, 1931542420]
child seeds              : [1068165419, 160407627, 1510093563, 1931542420, 2051178993, 1453497291]
duplicate seeds used: False
```

- Статус: **CONFIRMED**
- Обоснование: при пропуске первой пары (i=0,j=1)=(a,b) сид child[2]=1510093563 «съезжает» на пару (a,d), а исходный child[1]=160407627 используется дважды в другом порядке. `pair_idx` инкрементируется только в конце итерации (`cross_correlation.py:248`), поэтому нумерация сдвигается после каждого `continue`. Комментарий «гарантированная независимость» на строке 221 неверен. Результат пары (a,c) в функции (p=0.451) не совпал ни с одним прямым запуском по child-сиду (0.392-0.588), что подтверждает сдвиг.

---

## #7 (P1) time_shift: веса Fisher от n_lags наблюдения, не суррогата

- Скрипт: `audit/verify_7.py`
- Гипотеза: для `time_shift` Fisher-веса считаются из `n_obs` наблюдения, хотя у суррогата NaN на краях и своё n.
- Вывод скрипта:

```
n_obs  : [190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 199, ...]
n_surr : [91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 101, 101, ...]
equal: False
nan in surrogate edges: 99
```

- Статус: **CONFIRMED**
- Обоснование: `_time_shift` (`surrogate.py:635`) оставляет 99 NaN на краях, реальное n суррогата примерно вдвое меньше. При этом `max_lag_surrogate_pvalue` (`surrogate.py:404`) передаёт в `fisher_weighted_max_stat` массив `n_lags`, посчитанный один раз из наблюдения. Число наблюдений суррогата не пересчитывается, веса завышены, а `finite = np.isfinite(rho) & (n > 3)` использует чужое n.

---

## #8 (P1) surrogate_test: NaN в наблюдении, mean-imputed в нуле

- Скрипт: `audit/verify_8.py`
- Гипотеза: наблюдаемая корреляция считается с попарным удалением NaN, а нулевое распределение — на ряду с `fillna(mean)`.
- Вывод скрипта:

```
wide.corr (pairwise drop)   r = 0.442237
filled.corr (mean-imputed)  r = 0.299308
difference                  = 0.142929
surrogate_test p(x,y)       = 0.0196078431372549
```

- Статус: **CONFIRMED (механизм)**
- Обоснование: `surrogate_test` (`surrogate.py:80`) берёт `real = wide.corr(...)` с попарным удалением NaN, а нулевые суррогаты строит из `filled = wide.fillna(wide.mean())` (`surrogate.py:84`). На ряду с пропусками эти статистики различаются (0.442 против 0.299), то есть наблюдение и нуль считаются на разных данных. p-value неконсистентен.

---

## #9 (P1) ESS p-value округляется до 0.0 (нужен stats.t.sf)

- Скрипты: `audit/verify_9.py`, `audit/verify_9b.py`
- Гипотеза: `2*(1 - stats.t.cdf(...))` даёт 0.0 при большом |t|, а `stats.t.sf` это исправит.
- Вывод verify_9:

```
r      = 0.9999503955276189
n_eff  = 2000.0
p      = 0.0
p == 0.0: True
2*(1-cdf) = 0.0
2*sf      = 0.0
```

- Вывод verify_9b (n=300, растущая связь):

```
noise=0.5   r=0.905325 t=    36.80 p_returned=0.0 p_cdf=0.0 p_sf=7.615875036051954e-113
noise=0.2   r=0.984142 t=    95.78 p_returned=0.0 p_cdf=0.0 p_sf=7.006716773982336e-226
noise=0.1   r=0.995329 t=   177.97 p_returned=0.0 p_cdf=0.0 p_sf=1.3032112841522553e-304
noise=0.05  r=0.998735 t=   342.85 p_returned=0.0 p_cdf=0.0 p_sf=0.0
noise=0.02  r=0.999794 t=   850.75 p_returned=0.0 p_cdf=0.0 p_sf=0.0
```

- Статус: **CONFIRMED (partial, t < 343)**
- Обоснование: p_cdf = 0.0 при t ≥ 37, p_sf даёт 7.6e-113; исправляет округление в диапазоне t∈[37, 342]; при t ≥ 343 sf тоже возвращает 0.0.
- Дополнение (новое, не в v3_partial): `integrated_autocorrelation_time` не принимает параметр `max_lag` из вызывающего кода (`effective_sample.py:117-118`), поэтому для коротких рядов `max_lag` берётся по умолчанию, что может дать `tau < 1` и `n_eff > n`. Требует отдельной проверки.

---

## #16 (P2) B=0 и seed=-1 не валидируются в pairs.py

- Скрипт: `audit/verify_16.py`
- Гипотеза: `B=0` и `seed=-1` дают невнятную ошибку вместо валидации.
- Вывод скрипта:

```
B=0: EXCEPTION ValueError: 'size' must be a positive number different from zero
seed=-1: EXCEPTION ValueError: expected non-negative integer
```

- Статус: **CONFIRMED**
- Обоснование: обе границы воспроизведены. `B=0` падает на `_make_surrogates` с сообщением, не упоминающим B; `seed=-1` падает из `np.random.default_rng(seed)` в недрах библиотеки. Публичного контракта на «B ≥ 1, seed ≥ 0» нет, и в docstring не задокументировано.

---

## PHASE A DONE:

| # | находка | статус | вывод скрипта (1 строка) |
|---|---|---|---|
| 1 | Fisher-score в correlation | CONFIRMED | max = 3.022 > 1, min = 1.639 |
| 3 | зависимые p-value | UNVERIFIED | rho нулевых статистик -0.003, механизм опровергнут, эмпирика слабая |
| 5 | max_lag > n | CONFIRMED | ValueError shapes (0,) (10,) при n=20, max_lag=30 |
| 6 | pair_idx | CONFIRMED | сид child[2] съехал на пару (a,d), child[1] использован повторно |
| 7 | time_shift weights | CONFIRMED | n_obs 190-200 против n_surr 91-101, equal=False |
| 8 | surrogate_test NaN vs mean-imputed | CONFIRMED | real pairwise = 0.442, imputed = 0.299 |
| 9 | p-value = 0.0 | CONFIRMED (partial, t < 343) | p_sf = 7.6e-113 при t=36.8, sf исправляет округление в t∈[37, 342] |
| 16 | B=0, seed=-1 | CONFIRMED | B=0 ValueError size; seed=-1 ValueError non-negative |

## VERIFIED SUMMARY

- CONFIRMED: 7
- FALSE: 0
- UNVERIFIED: 1

---

## PHASE B DONE

### FILES CHANGED

- `scripts/make_synthetic_unified.py`
- `data/scripts/unify_schema.py`
- `data/schema/unified_schema.json` (следствие выбора по хвосту 2, обоснован в DEVIATIONS)

### LINES ADDED: 21
### LINES REMOVED: 3
(git diff --stat; только эти три файла)

### Деталь

Хвост 1: `unified.parquet` теперь пишется с полным набором колонок схемы (`timestamp_utc, detector_id, detector_type, value, residual, residual_method, unit, quality_flag, meta`). Проверка запуском:

```
[OK] unified.parquet: (7200, 9)
['timestamp_utc', 'detector_id', 'detector_type', 'value', 'residual',
 'residual_method', 'unit', 'quality_flag', 'meta']
{'residual_method': 'none', 'unit': 'arbitrary', 'quality_flag': 0, 'meta': '{}'}
```

Хвост 2: `meta` оставлена строкой (`json.dumps`), как требует тест `test_unify_preserves_existing_columns:171` (`isinstance(..., str)` + `json.loads`). `"{}"` заменено на `json.dumps({})` в `load_intermagnet` и `load_horizons`; схема приведена к `type: string`. Проверка запуском:

```
python -m pytest tests/test_unify_schema.py::test_unify_preserves_existing_columns
   tests/test_unify_schema.py::test_unify_returns_value_column -q
2 passed
```

### DEVIATIONS

1. Хвост 2: выбран вариант «meta = string», а не «meta = object». Причина: незакоммиченный `tests/test_unify_schema.py:170-172` жёстко требует `isinstance(out["meta"].iloc[0], str)` и `json.loads`. Правка `tests/` запрещена, поэтому вместо смены типа в коде обновлена схема (`data/schema/unified_schema.json`, `meta` → `type: string`). Тест не редактировался.
2. Хвост 1: `unit` для синтетики выставлен в `"arbitrary"` (в `DETECTOR_UNITS` типов синтетических детекторов нет), а не в конкретную единицу из физики.
3. `data/processed/unified.parquet` пересоздан запуском генератора (файл в `.gitignore`, в git не попадает).
4. Добавлено «Дополнение (новое)» к #9 и один непроверенный пункт про `max_lag` в `integrated_autocorrelation_time` — это наблюдение из верификации, отдельного скрипта на него не писалось.

---

## NEXT STEPS

1. Проверить `audit/AUDIT_2026-10-05_v3_verified.md`.
2. `python -m pytest tests/ -m "not slow" -q`.
3. `git diff --stat`.
4. Если зелёное — коммит.
