# CrossCorr — Backlog

## Мета

- Дата реестра: 2026-10-05
- HEAD: `cee803d` "fix: P1-11 — deprecate ESS path for lagged analysis"
- Рабочее дерево: чистое (`git status --short` пуст)
- Источники: `AUDIT_2026-10-05.md` (v1), `AUDIT_2026-10-05_v2.md` (v2), `AUDIT_2026-10-05_v3_partial.md` (v3), `AUDIT_2026-10-05_v3_verified.md` (v3v)
- Находок в v1: 60 (по мете v2)
- Находок в v2: 94 (V2-01..V2-94)
- Находок в v3: 39
- Всего исходных упоминаний: 193
- Дедуплицировано до: 158 уникальных записей
- CLOSED: 50
- OBSOLETE: 2
- UNVERIFIED: 5
- OPEN: 101

Коммиты-фиксы после v1: `4a1fcd3`, `f26f92d`, `bbe978b`, `0fafbaa`, `3093dd5`, `2280fc2` (v2), далее `ed9f9e1`, `dfa9999`, `d711569`, `2ee09c4`, `ce8b40e`, `4b1ee15`, `8c5edc9`, `4802988`, `6813e22`, `8888dcd`, `cee803d` (v3).

Статусы: OPEN, CLOSED `<hash>`, OBSOLETE, UNVERIFIED.
Верификация (v3v): CONFIRMED, FALSE, UNVERIFIED, NEEDS_RUN.

---

## Группа A — ETL и данные

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| A1 | P0 | `data/scripts/download_intermagnet.py:30-38` | Парсер IAGA-2002 структурно неверен (дата из позиций 0-1, значения из 3-5 вместо 7-9) | CLOSED `d711569` | v2 (V2-13) |
| A2 | P0 | `data/scripts/unify_schema.py:28` | SNR используется как `residual` | CLOSED `2ee09c4` | v2 (V2-14) |
| A3 | P1 | `unify_schema.py:30,42,56` vs `data/schema/unified_schema.json:13` | `meta` пишется строкой, схема требует object | CLOSED `ce8b40e` (схема приведена к string) | v2 (V2-15) |
| A4 | P1 | `scripts/make_synthetic_unified.py:44-50` vs `unified_schema.json:10` | `detector_type` intermagnet/ngl отсутствуют в enum схемы | OPEN | v2 (V2-16) |
| A5 | P1 | `unify_schema.py:26` | `detector_id = rx_call`, агрегации по `tx_call` нет → неуникальный ключ | OPEN | v2 (V2-17) |
| A6 | P1 | `make_sample.py:14` | `.head(500)` после глобальной сортировки даёт срез одного детектора | OPEN | v2 (V2-24) |
| A7 | P1 | `download_intermagnet.py:48` | Относительный путь вместо абсолютного `RAW_DIR` | OPEN | v2 (V2-25) |
| A8 | P1 | `download_wspr.py:85`, `download_horizons.py:44` | Нет кэша и checksums, воспроизвести прогон невозможно | OPEN | v2 (V2-35) |
| A9 | P1 | `data/raw/` | Каталог пуст, реальных данных нет | OPEN | v2 (V2-37), v1 |
| A10 | P1 | `data/processed/unified.parquet` | Создан `make_synthetic_unified.py`, а не документированным `unify_schema.py` | OPEN | v2 (V2-38) |
| A11 | P0 | весь датасет | Единственный датасет полностью синтетический; real-data прогонов нет | OPEN | v2 (V2-39) |
| A12 | P2 | `data/samples/` | Каталог пуст, примеры данных отсутствуют; README обещает примеры | OPEN | v2 (V2-40), v3 (#12) |
| A13 | P2 | `make_synthetic_unified.py:27` | `PROCESSED_DIR.mkdir` на уровне модуля | OPEN | v2 (V2-41) |
| A14 | P2 | `unify_schema.py:54-55` | `dropna` по timestamp, `residual` остаётся с NaN | OPEN | v2 (V2-18) |
| A15 | P2 | `unify_schema.py:49` | Слепой fallback на первую колонку | OPEN | v2 (V2-19) |
| A16 | P2 | `unify_schema.py:30` | `df.apply(..., axis=1)` построчно на всём файле | OPEN | v2 (V2-20) |
| A17 | P2 | `unify_schema.py:77-78` | `except Exception: print` молча уменьшает N | OPEN | v2 (V2-21) |
| A18 | P2 | `unify_schema.py:17` | `PROCESSED.mkdir` на импорте модуля | OPEN | v2 (V2-22) |
| A19 | P2 | `make_sample.py:11-16` | Код уровня модуля без `__main__` | OPEN | v2 (V2-23) |
| A20 | P2 | `download_intermagnet.py:52` | `out_path.touch()` создаёт пустой файл и возвращает успех | OPEN | v2 (V2-26) |
| A21 | P2 | `download_intermagnet.py:59` | `--station default="UNKNOWN"` | OPEN | v2 (V2-27) |
| A22 | P2 | `registry.py:77` | `download_ngl.py` отсутствует | OPEN | v2 (V2-28) |
| A23 | P2 | `registry.py:52,66,80` | `base_url` с placeholder `https://TODO...` | OPEN | v2 (V2-29) |
| A24 | P2 | `registry.py:48,62,76` | `expected_fields` использует `timestamp`, схема — `timestamp_utc` | OPEN | v2 (V2-30) |
| A25 | P3 | `registry.py:87` + `data/scripts/__init__.py:3` | `_initialize_registry()` печатает при каждом импорте | OPEN | v2 (V2-31) |
| A26 | P2 | `download_wspr.py:29,77` | `limit=5000` молча усекает конец дня | OPEN | v2 (V2-32) |
| A27 | P3 | `download_wspr.py:3` vs `:84` | Docstring обещает не тот путь файла | OPEN | v2 (V2-33) |
| A28 | P2 | `download_horizons.py:26-29` | Эфемериды не версионируются | OPEN | v2 (V2-36) |
| A29 | P3 | `make_synthetic_unified.py:47` | `D_Krasnoyarsk` в смешанном регистре | OPEN | v2 (V2-43) |
| A30 | P2 | `make_synthetic_unified.py:32-50` | Смешивает WSPR/магнитометр/GNSS в одном пуле | OPEN | v2 (V2-44) |
| A31 | P3 | `make_synthetic_unified.py:87-93` | Пространственная корреляция мгновенная, лаг всегда 0 | OPEN | v2 (V2-45) |
| A32 | P3 | `make_synthetic_unified.py` | Колонка `meta` отсутствовала у второго производителя | CLOSED `ce8b40e` | v2 (V2-42) |
| A33 | P2 | `data/scripts/api_client.py` | Класс без методов, импортируется 0 раз (requests уже импортирован) | OPEN | v2 (V2-70) |
| A34 | P3 | `download_intermagnet.py:41-54` | `download_and_save_intermagnet` не вызывается | OPEN | v2 (V2-72) |

---

## Группа B — Ядро анализа

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| B1 | P0 | `cross_correlation.py:157,242` | Колонка `correlation` хранила Fisher-score, потребители читали как r | CLOSED `8c5edc9` | v3 (#1), v3v CONFIRMED |
| B2 | P0 | `cross_correlation.py` | Дефолтный CLI-путь не корректирует поиск по лагам | CLOSED `f26f92d` | v1 (P0-3) |
| B3 | P0 | `cross_correlation.py` | ESS перезаписывала max-stat p-value | CLOSED `f26f92d`; усилено `cee803d` (deprecate) | v1 (P0-4) |
| B4 | P1 | `surrogate.py:384`, `block_bootstrap.py:120` | Пропущенные суррогаты не меняли знаменатель | CLOSED `f26f92d` | v1 (P1-2) |
| B5 | P1 | `surrogate.py:583-586` | Диапазон сдвигов `_time_shift` смещал нулевую модель | CLOSED `3093dd5` | v1 (P1-5) |
| B6 | P1 | `effective_sample.py:138-139` | `p_value = 0.0` при abs(r) >= 1 | CLOSED `3093dd5` | v1 (P1-6) |
| B7 | P1 | `effective_sample.py:69-75` | Окно IAT обрывалось на первом незначимом лаге | CLOSED `3093dd5` | v1 (P1-7) |
| B8 | P1 | `distance_analysis.py:103-111` | Деление на ноль в OLS | CLOSED `3093dd5` | v1 (P1-8) |
| B9 | P1 | `mantel.py:84-91` | Невалидный `alternative` давал минимальный p-value | CLOSED `4a1fcd3` | v1 (P1-9) |
| B10 | P1 | `mantel.py:157-168` | Пропущенные пары получали расстояние 0.0 | CLOSED `4a1fcd3` | v1 (P1-10) |
| B11 | P1 | `effective_sample.py` | ESS игнорировал кросс-корреляцию x и y | CLOSED `cee803d` (вариант A: deprecate, zero-lag only) | v1 (P1-11), v2 (§4.4) |
| B12 | P1 | `effective_sample.py:62-65` | Комментарий про FFT, код — `np.correlate` O(n²) | CLOSED `3093dd5` | v1 (P1-12) |
| B13 | P1 | `surrogate.py:29, 437-444, 538-546` | NaN компактировал ряд; возврат исходника вместо суррогата (в т.ч. `phase_surrogate` при коротком ряде) | CLOSED `ed9f9e1` | v2 (V2-02), v1 (P1-3) |
| B14 | P1 | `surrogate.py:404` | time_shift: Fisher-веса от `n_lags` наблюдения, не суррогата | CLOSED `4802988` | v3 (#7), v3v CONFIRMED |
| B15 | P1 | `surrogate.py:80,84` | `surrogate_test`: NaN в наблюдении, mean-imputed в нуле | CLOSED `4802988` | v3 (#8), v3v CONFIRMED |
| B16 | P1 | `effective_sample.py:175` | `1-cdf` округлялось до p=0.0 при большом t | CLOSED `4b1ee15` | v3 (#9), v3v CONFIRMED |
| B17 | P1 | `surrogate.py:421-431` | `max_lag > n` давал ValueError вместо понятной ошибки | CLOSED `4802988` | v3 (#5), v3v CONFIRMED |
| B18 | P1 | `pairs.py:301-310` | Собственная реализация BH (жёстко BH для зависимых пар, нужен BY / общий `fdr_bh_q`) | OPEN | v3 (#2), v3 (#36) |
| B19 | P1 | `pairs.py:240-241,366-367` | Пары с общим детектором используют одни суррогаты → зависимые p-value | UNVERIFIED (v3v: механизм опровергнут, rho≈-0.003) | v3 (#3) |
| B20 | P1 | `pairs.py` | Нет detrend/standardize, расхождение с max-stat пайплайном | OPEN | v3 (#4) |
| B21 | P2 | `surrogate.py:66-74` | Python-цикл + DataFrame + `pandas.corr` на каждый суррогат | OPEN | v1 (P2-2) |
| B22 | P2 | `mantel.py:71-89` | Permutation-тест — чистый Python-цикл (9999 итераций) | OPEN | v1 (P2-4) |
| B23 | P2 | `preprocessing.py` | `robust=True` — median/MAD, не Theil-Sen; detrend остаётся OLS | OPEN | v3 (#19), v1 (§3.4) |
| B24 | P2 | `cross_correlation.py:137,236` | `n_obs` считается после интерполяции NaN | OPEN | v3 (#17) |
| B25 | P2 | `cross_correlation.py:231-232` | Пары с NaN t_obs молча выбрасываются до FDR | OPEN | v3 (#18) |
| B26 | P2 | `pairs.py:71-76` | Метод `shuffle` разрушает автокорреляцию (нуль слишком узкий) | OPEN | v3 (#14) |
| B27 | P2 | `pairs.py:91-101` | AR(1) суррогат через `lfilter` без burn-in | OPEN | v3 (#15) |
| B28 | P2 | `effective_sample.py:111-118` | Общий mask занижает IAT обоих рядов | OPEN | v2 (V2-63) |
| B29 | P2 | `preprocessing.py:38-47` | NaN-интерполяция без ограничения длины пропуска | OPEN | v2 (V2-64) |
| B30 | P2 | `preprocessing.py:50` | Ряд длины 2 после детренда → нули | OPEN | v2 (V2-65) |
| B31 | P2 | `surrogate.py` | `DEFAULT_OUT.mkdir` при импорте пакета | CLOSED `8888dcd` | v1 (P3), v3 (#20) |
| B32 | P3 | `effective_sample.py` | Лаги ниже порога между значимыми не суммируются; не окно Sokal (правило и docstring) | CLOSED `ed9f9e1`/`8888dcd` | v3 (#33), v1 (P1-7) |
| B33 | P3 | `surrogate.py`, `pairs.py`, `effective_sample.py`, `preprocessing.py` | Шесть копий NaN-интерполяции с разными порогами (в т.ч. `pairs.py:65`) | OPEN | v3 (#35) |
| B34 | P3 | `cross_correlation.py` | `print()` внутри библиотечной функции | CLOSED `8888dcd` (logging) | v3 (#38) |
| B35 | P3 | `pairs.py:60-67` | Ветка интерполяции NaN недостижима | OPEN | v3 (#37) |
| B36 | P3 | `effective_sample.py:82-83` | `max_lag` не принимается из вызывающего кода | OPEN | v3v (дополнение к #9) |
| B37 | P1 | `surrogate.py:83` | `surrogate_test` не применял правило Davison-Hinkley | CLOSED `f26f92d` | v1 (P1-4) |
| B38 | P3 | `surrogate.py:245,183` | `np.argsort` без `kind="stable"` при ties | OPEN | v2 (V2-59) |
| B39 | P3 | `surrogate.py` | Критерий сходимости IAAFT не стандартен | OPEN | v2 (V2-54) |
| B40 | P1 | `block_bootstrap.py:9-10` | Docstring описывал перемешивание блоков, код — случайные старты | CLOSED `8888dcd` | v2 (V2-62), v3 (#32) |

---

## Группа C — pairs.py и параллелизм

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| C1 | P0 | `pairs.py:199,345,348` | NaN обращался в максимальную значимость | CLOSED `4a1fcd3` | v1 (P0-1) |
| C2 | P1 | `pairs.py:220-229` | Утечка shared memory при ошибке создания второго блока | CLOSED `f26f92d` (ExitStack) | v1 (P1-1) |
| C3 | P2 | `pairs.py:213,220-222` | Двойное выделение памяти под суррогаты | OPEN | v1 (P2-1) |
| C4 | P1 | `cross_correlation.py:222,248` | `pair_idx` не инкрементился после `continue` | CLOSED `4b1ee15` | v3 (#6), v3v CONFIRMED |
| C5 | P2 | `pairs.py:183,236-237,246` | Не было валидации `B < 1` и `seed < 0` | CLOSED `4b1ee15` | v3 (#16), v3v CONFIRMED |
| C6 | P2 | `pairs.py:129,155` | Дефект `-(T-1)` при `T=1` даёт 3 столбца вместо 1 | OPEN (v1 выведен чтением) | v1 (§4.4) |
| C7 | P2 | `pairs.py` (T=1, n=0/1) | Нет тестов граничных размеров `_batch_max_stat_corr` | OPEN | v1 (§4.4) |
| C8 | P2 | `pairs.py` | float32 для суррогатов против float64 для `C_obs` — влияние не проверено | UNVERIFIED (v3v) | v3 (Not verified) |
| C9 | P2 | `pairs.py:359-360` | Двойной unlink через resource_tracker на Python < 3.13 | UNVERIFIED (v3v) | v3 (Not verified) |
| C10 | P2 | `pairs.py:247,255,390-391` | `shm.close()` при живых views может бросить BufferError | UNVERIFIED (v3v) | v3 (Not verified) |

---

## Группа D — API и публичный интерфейс

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| D1 | P1 | `cross_correlation.py:157`, `pairs.py:178` | Две разные функции с именем `cross_correlation_pairs_with_max_stat` | OPEN | v1 (§1.3), v3 (#21) |
| D2 | P2 | `cross_correlation.py:28` | Alias `fdr_bh_q as _benjamini_hochberg` вводил в заблуждение | CLOSED `8888dcd` (`_fdr_correct`) | v2 (V2-04), v1 (P3) |
| D3 | P2 | `__init__.py:58-59` | `fdr_bh` рядом с `fdr_bh_q`, расхождение не документировано | OPEN | v2 (V2-66) |
| D4 | P2 | `analysis/__init__.py:1` | Реэкспортировано 2 из 14 модулей, нет `__all__` | OPEN | v2 (V2-67), v1 (§1.3) |
| D5 | P3 | `__init__.py:13` | `__version__` — единственное объявление, git-тегов нет | OPEN | v2 (V2-69) |
| D6 | P3 | `ai_narrator.py`, `narrator.py`, `quest.py` | Не в `__all__`, не импортируются | OPEN | v2 (V2-71) |
| D7 | P3 | `game/` (4 файла) | Мёртвый код, не упомянут в README/pyproject | OPEN | v2 (V2-74) |
| D8 | P2 | `pyproject.toml` | mypy не настроен, типы не проверяются | OPEN | v2 (V2-75) |
| D9 | P3 | `download_horizons.py:26` | Аннотация возврата `-> "object"` бессмысленна | OPEN | v2 (V2-76) |
| D10 | P3 | `surrogate.py:419` | `_lagged_cc` без аннотаций | OPEN | v2 (V2-77) |
| D11 | P3 | `safe_exec.py:45` | `True/False/None` в `SAFE_BUILTINS` недостижимы (ключевые слова) | OPEN | v1 (P3) |
| D12 | P3 | `mantel.py:115` | Избыточный `import pandas as pd # noqa: F401` | OPEN | v1 (P3) |
| D13 | P2 | `analysis/` циклические импорты | `surrogate`↔`cross_correlation`, `mantel`↔`distance_analysis` | OPEN | v1 (§1.2) |
| D14 | P2 | `surrogate.py:47` | `build_wide` — дубликат `build_wide_by_detector` | OPEN | v1 (§1.4) |

---

## Группа E — Тесты

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| E1 | P2 | `test_core_regression.py:23-75` | Тесты проверяли подстроки исходника, не поведение | CLOSED `6813e22` | v1 (§4.2), v3 (#22) |
| E2 | P1 | `test_fdr.py` | Нет численного эталона `fdr_bh_q`/`benjamini_yekutieli` | CLOSED `6813e22` (`test_statistical_reference.py`) | v2 (V2-50), v1 (§4.1) |
| E3 | P1 | `test_ess_and_bootstrap.py:28` | Нет эталона `tau` для AR(1) против `(1+φ)/(1-φ)` | OPEN | v2 (V2-51) |
| E4 | P3 | `test_cross_correlation_synthetic.py` | Нет точного численного эталона ρ | CLOSED `6813e22` (lagged_cc_recovers_known_lag) | v2 (V2-52) |
| E5 | P2 | `tests/` | Нет теста сходимости/распределения IAAFT | OPEN | v2 (V2-55) |
| E6 | P3 | `tests/` | Нет Windows-специфичного теста shm | OPEN | v2 (V2-58) |
| E7 | P2 | `tests/` | Нет тестов `adf_test`, `check_stationarity_wide`, `fisher_weighted_max_stat`, `mfdfa`, `load_unified`, `power_curve` | OPEN | v3 (#23), v1 (§4.1) |
| E8 | P2 | `tests/` | Нет сценариев пустой wide, constant series, ряды разной длины | OPEN (B=0, seed=-1, max_lag закрыты `4b1ee15`/`4802988`) | v3 (#24), v1 (§4.4) |
| E9 | P3 | `tests/`, корень | Нет `conftest.py`, фикстуры дублируются | OPEN | v1 (§4.3) |
| E10 | P2 | `.pytest_cache/v/cache/lastfailed` | Устаревшая запись `test_pipeline.py`, файла нет | OBSOLETE (stale cache) | v3 (#27) |
| E11 | P2 | `test_negative_control.py` | Тест допускает `<=1`, README заявлял 0 | CLOSED `8888dcd` | v3 (#28), v1 |

---

## Группа F — CI и инфраструктура

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| F1 | P1 | `requirements.lock` | Lock устарел: нет `joblib`, собран на Python 3.13 | OPEN | v1 (§5), v2 (V2-82,83), v3 (#10) |
| F2 | P1 | `pyproject.toml` | `pyarrow` отсутствовал в `[project] dependencies` | CLOSED `205daf9` | v2 (V2-87) |
| F3 | P2 | `.github/workflows/ci.yml:16,50` | CI только Python 3.12 при `requires-python>=3.10` | OPEN | v1 (§4.5), v2, v3 (#26) |
| F4 | P2 | `ci.yml` | Нет Windows job при использовании `SharedMemory` | OPEN | v1 (§4.5), v2 |
| F5 | P1 | `ci.yml` | Coverage не собирается (`pytest-cov` в dev не используется) | OPEN | v1 (P2-5), v2 (§6.1), v3 (#26) |
| F6 | P2 | `ci.yml:38` | ruff не покрывает `data/scripts/` и `game/` | OPEN | v1 (§4.5), v2 (V2-80) |
| F7 | P2 | `ci.yml:43` | Slow-тесты только на push в main | OPEN | v3 (#25) |
| F8 | P3 | `ci.yml` | Нет `compileall`/проверки импорта `registry.py` | OPEN | v2 (V2-81) |
| F9 | P3 | `ci.yml` | `cache: pip` без `cache-dependency-path` | OPEN | v2 |
| F10 | P2 | `.gitignore` | Дубли записей `__pycache__/`, `*.egg-info/`, `.venv/`, `venv/` (в т.ч. как отмечено в README) | CLOSED `8888dcd` | v1 (P3), v2 (V2-89), v3 (#39) |
| F11 | P2 | `.gitignore:46` | `audit/` в ignore, но файлы отслеживаются | OPEN | v2 (V2-90) |
| F12 | P3 | `.gitignore` | Нет игнора `.coverage`, `htmlcov/` | OPEN | v2 (V2-91) |
| F13 | P2 | `Makefile` | Не было целей `test`/`lint` | CLOSED `8888dcd` | v2 (V2-79), v3 (#39) |
| F14 | P2 | `requirements.in` vs `pyproject.toml` | Две конфликтующие модели зависимостей | OPEN | v1 (§5.1), v2 (V2-84) |
| F15 | P2 | `pyproject.toml` | `joblib` в `dependencies`, но не в `dev` | OPEN | v2 (V2-85) |
| F16 | P3 | `pyproject.toml:57` | `MFDFA` объявлен трижды | OPEN | v2 (V2-86) |
| F17 | P3 | `pyproject.toml` | `pytest-cov`/`pip-tools` не используются | OPEN | v2 (V2-88) |
| F18 | P3 | `bench.log`, `check_sprint4.py` | Файлы в git, не документированы | OPEN | v1 (§5.4), v3 (#39) |
| F19 | P1 | `results/` (git) | `results/` не игнорировался, противоречие README | CLOSED `2280fc2` | v1 (§5.3), v2 (V2-09) |
| F20 | P3 | `pyproject.toml:34` | numpy>=1.24 против `Generator.spawn` (нужен 1.25) | UNVERIFIED (v3v) | v3 (Not verified) |
| F21 | P2 | `data/processed/unified.parquet` | Файл пересоздан локально, в git не входит | OBSOLETE | v3v (PHASE B) |

---

## Группа G — Документация

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| G1 | P0 | `docs/PIPELINE.md:153` | Описание IAT противоречило коду после фикса P1-7 | CLOSED `ed9f9e1` | v2 (V2-01) |
| G2 | P1 | `docs/PIPELINE.md:117-133` | Документирован только BH, код по умолчанию BY | OPEN | v2 (V2-03), v1 |
| G3 | P1 | `docs/PIPELINE.md:256-278` | §11 описывает OLS, основной метод — Mantel | OPEN | v2 (V2-08) |
| G4 | P1 | `docs/methodology.md` | 9 строк: не описаны max-stat, BY, bootstrap, Mantel, IAAFT, MFDFA (ESS добавлен `cee803d`) | OPEN (partial) | v2 (V2-10), v1 |
| G5 | P3 | `README.md` | Битые ссылки `paper/work.tex`, `paper/references.bib`, `docs/quest.md`, `docs/fund.md` | CLOSED `8888dcd` | v2 (V2-11, V2-94), v1 (§5.4), v3 (#31) |
| G6 | P2 | `README.md` (Скриншоты) | Ссылки на `results/cross_correlation.png`, `results/mfdfa.png` | OPEN | v2 (V2-12) |
| G7 | P2 | `docs/PIPELINE.md:96-113` | §5 описывает только phase; IAAFT/time_shift недостижимы из CLI | OPEN | v2 (V2-05) |
| G8 | P2 | `docs/PIPELINE.md:69-77` | Формула max-stat без Fisher-весов | OPEN | v2 (V2-06) |
| G9 | P2 | `docs/PIPELINE.md:89-90` | Три разных значения B (функция/CLI/документ) | OPEN | v2 (V2-07) |
| G10 | P2 | `docs/PIPELINE.md:283` | «Результаты: results/*.csv» без пометки об устаревании | OPEN | v2 (V2-09) |
| G11 | P2 | `README_ARCHITECTURE_UPDATE.md:20-21` | Ложное утверждение о `api_client`/`SourceRegistry` | OPEN | v2 (V2-46) |
| G12 | P2 | `README_ARCHITECTURE_UPDATE.md:29` | Заявление «Надежность: Высокая» | OPEN | v2 (V2-47) |
| G13 | P1 | `README_ARCHITECTURE_UPDATE.md:32-34` | Ссылка на несуществующий `test_source_registry.py` | OPEN | v2 (V2-48) |
| G14 | P3 | `README_ARCHITECTURE_UPDATE.md:1,3,8,23,31` | Эмодзи | OPEN | v2 (V2-49) |
| G15 | P2 | `README.md:15` | Бейдж вёл на `ci.yaml`, файл `ci.yml` | CLOSED `8888dcd` | v3 (#29) |
| G16 | P2 | `README.md:194,216` | `requirements.txt` удалён, но указан в установке | CLOSED `8888dcd` | v3 (#29) |
| G17 | P3 | `README.md:498` | «11 тестов в 5 файлах» | CLOSED `8888dcd` | v3 (#29) |
| G18 | P3 | `README.md:109,113,124` | «1000+ суррогатов», «единая BH» | CLOSED `8888dcd` | v3 (#30) |
| G19 | P3 | `cross_correlation.py:174-175` | Docstring «5-10 минут для 45 пар» | CLOSED `8888dcd` | v3 (#34) |
| G20 | P3 | `docs/methodology.md:19` | «1000+ фазовых суррогатов» против дефолта 200 | CLOSED `8888dcd` | v2 (V2-10) |
| G21 | P3 | `README.md` | `results/ # gitignored` противоречит состоянию | CLOSED `2280fc2` (results удалён из git) | v1 (§5.3) |
| G22 | P3 | `surrogate.py:55,86,95,127` | Константы без имени/обоснования | OPEN | v1 (P3) |
| G23 | P3 | `cross_correlation.py:88` | Магическое `n < 10` без параметра | CLOSED `8888dcd` (MIN_SAMPLES в effective_sample; в cross_correlation.py — OPEN) | v1 (P3) |
| G24 | P3 | `surrogate.py:127,257,292,436,485` | E302: одна пустая строка перед `def` | OPEN | v1 (P3) |
| G25 | P3 | `surrogate.py:114-124` | Ветка 2D `fdr_bh` без проверки симметричности | OPEN | v1 (P3) |

---

## Группа H — Безопасность

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| H1 | P0 | `safe_exec.py:15-32` | `ctypes` и др. не в `FORBIDDEN_NAMES` — выход из песочницы | CLOSED `4a1fcd3` | v1 (P0-5) |
| H2 | P0 | `opencode.json` @ `bc58a3b` | API-ключ в истории git; untracking не удаляет секрет | OPEN (нужна ротация ключа) | v2 (V2-93), v3 (#13) |
| H3 | P2 | `opencode.json` в `.gitignore` | Ignore добавлен, но объект в истории остаётся | OPEN (тот же корень, что H2) | v1 (§5.3) |

---

## Итог по приоритетам

| Severity | Open | Closed | Obsolete | Unverified | Total |
|----------|------|--------|----------|------------|-------|
| P0 | 2 | 8 | 0 | 0 | 10 |
| P1 | 17 | 22 | 0 | 1 | 40 |
| P2 | 53 | 9 | 2 | 3 | 67 |
| P3 | 29 | 11 | 0 | 1 | 41 |
| Итого | 101 | 50 | 2 | 5 | 158 |

Разбивка по группам: A 34, B 40, C 10, D 14, E 11, F 21, G 25, H 3 (сумма 158).

Проверка сумм: Open + Closed + Obsolete + Unverified = 101 + 50 + 2 + 5 = 158 = Total.
Проверка по severity: 10 + 40 + 67 + 41 = 158 = Total.

Примечание: часть записей имеет класс `stat`/`infra`/`docs`, отнесённый к ближайшей группе по файлу. UNVERIFIED-записи (B19, C8, C9, C10, F20) посчитаны в своей группе и одновременно отражены в колонке Unverified.

---

## Замечания

- **Расхождения между отчётами.** v3_partial #3 (зависимые p-value при общем детекторе) v3_verified переклассифицировал в UNVERIFIED: механизм (общие суррогаты → зависимые нули) опровергнут, эмпирика слабая. В реестре оставлен один UNVERIFIED-статус.
- **v3 #9.** Изначально помечен FALSE, затем исправлен на CONFIRMED (partial, t<343); закрыт `4b1ee15` заменой `1-cdf` на `sf`. При t≥343 `sf` тоже даёт 0.0 — это ограничение float64, не дефект кода.
- **v2 V2-68, V2-56, V2-57, V2-60, V2-61, V2-34, V2-53** — не находки (подтверждения корректности), в реестр не включены.
- **v2 V2-73** (`_lagged_cc` вызывается ли) — UNVERIFIED, требует `git grep`.
- **v1 §1.4** `check_sprint4.py` — в v2 (§7) признан отсутствующим в `git ls-files`; v3 подтверждает наличие `check_sprint4.py` в git. Расхождение источников, оставлено в F18 по факту `git ls-files`.
- **Без данных нельзя проверить:** A9, A10, A11 (реальные прогоны), A4 (валидация схемы), F20 (numpy.spawn), C8-C10 (shm/BufferError/float32).
- **Противоречие docs-vs-code** по FDR (G2): `docs/PIPELINE.md` §6 описывает BH, код по умолчанию BY — см. также B18 (pairs жёстко BH).
- **v3 (#4)** (pairs без preprocess, B20) пересекается с D1 (две разные функции) — общий корень: расхождение двух пайплайнов.
- **v3 (#26)** CI: Python 3.12 only — пересекается с F3; coverage — с F5.
- **A12, F19, F21** связаны с одной темой: происхождение и доступность данных (`data/raw` пуст, `data/samples` пуст, `results` удалён).

### Объединённые дубликаты (эта ревизия)

- B34 (v3 #36, собственная реализация BH) → B18 (v3 #2, BH для зависимых пар): один файл:строка `pairs.py:301-310`.
- B39 (v1 P1-3, `phase_surrogate` короткий ряд) → B13 (v2 V2-02): та же функция `surrogate.py`.
- B32 (v3 #33) ← G21 (v1 P1-7 / v3 #33): оба про правило IAT/Sokal в `effective_sample.py`.
- B33 (v3 #35, копии NaN-интерполяции) ← C7 (v3 #35 `pairs.py:65`): `pairs.py:65` внутри перечня B33.
- G5 (v2 V2-11/V2-94, битые ссылки) ← G19 (v3 #31, битые ссылки `docs/quest.md`, `docs/fund.md`, `paper/*`).
- A12 (v2 V2-40 + v3 #12) ← G28 + G29 (v3 #12, `data/samples/` пуст): одна тема.
- F10 (v2 V2-89, дубли `.gitignore`) ← F21 (v1, дубли записей): одна тема.

---

## Рекомендуемый порядок работ

1. **Группа H (безопасность)** — 2 open, ~30 мин. Ротация ключа — единственная P0 за пределами кода, критична перед публикацией.
2. **Группа A (ETL и данные)** — 33 open, ~6-8 ч. Без воспроизводимого датасета ни один статистический результат не публикуем.
3. **Группа B (ядро анализа)** — 20 open, ~8-10 ч. Здесь B18/B19/B20/B28/B29/B30 — статистические риски; B33 — дедупликация.
4. **Группа C (pairs.py)** — 6 open, ~3-4 ч. C6 (дефект `T=1`) и C3 (память) — сначала, C8-C10 требуют запуска.
5. **Группа E (тесты)** — 4 open, ~4-6 ч. Наполнение эталонов (E3, E5, E7, E8) фиксирует корректность после правок B/A.
6. **Группа F (CI и инфра)** — 16 open, ~4-5 ч. F1/F3/F4/F5 — воспроизводимость CI; механические.
7. **Группа G (документация)** — 14 open, ~5-6 ч. G2/G3/G4/G11/G13 — научная честность; остальное косметика.
8. **Группа D (API)** — 10 open, ~4-5 ч. D1 — публичный контракт; остальное типизация/dead code.

Обоснование по группам:
- H: секрет в истории — риск утечки, дёшево закрыть.
- A: пустой `data/raw` и синтетический parquet блокируют любую научную валидность.
- B: методы, на которых строятся выводы; зависимы от A.
- C: отдельный публичный пайплайн, содержит собственные P2-дефекты.
- E: защита от регрессий, ставить после фиксов B/A/C.
- F: CI-воспроизводимость, влияет на доверие к прогонам.
- G: документация приводится в соответствие уже исправленному коду.
- D: API/типизация — низший риск для результата.
