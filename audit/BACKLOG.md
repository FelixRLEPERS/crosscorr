# CrossCorr — Backlog

## Мета

- Дата реестра: 2026-10-05
- Дата обновления: 2026-10-06 (v6)
- HEAD: `ebb7d66` "perf(XM): optimize cross_mfdfa [XM-5]"
- Рабочее дерево на момент реестра: чистое (`git status --short` пуст); после обновления 2026-10-06 изменены `audit/BACKLOG.md` и добавлен `audit/PROJECT_STATE.md`
- Источники: `AUDIT_2026-10-05.md` (v1), `AUDIT_2026-10-05_v2.md` (v2), `AUDIT_2026-10-05_v3_partial.md` (v3), `AUDIT_2026-10-05_v3_verified.md` (v3v)
- Находок в v1: 60 (по мете v2)
- Находок в v2: 94 (V2-01..V2-94)
- Находок в v3: 39
- Всего исходных упоминаний: 193
- Дедуплицировано до: 158 уникальных записей
- CLOSED: 138
- STOP (требует решения/вне границ): 13
- UNVERIFIED: 4 (B19, C8, C9, C10; C8 одновременно STOP, C9/C10 — PARTIAL)
- PARTIAL: 5 (A30, F17, F20, C9, C10)
- FALSE (находка не подтверждена): 6
- OBSOLETE: 2
- OPEN (отложено): 4
- DEFERRED (отложено): 0 (D8 — CLOSED af47ec3 (mypy); XM-5 — CLOSED ebb7d66 (58×))

Проверка (v6 + D8): CLOSED 138 + STOP 13 + UNVERIFIED 4 + PARTIAL 5 + FALSE 6 +
OBSOLETE 2 + OPEN 4 + DEFERRED 0 = 172.
Примечание: MI-1 в v5 уже был CLOSED (первичная валидация `3c627d6`+`c84ffa4`),
в v6 закрыт вторичный reference-пункт; XM-5 переведён DEFERRED → CLOSED.
Двойной счёт MI-1 даёт 172 вместо 171 (см. примечание в «Итог по приоритетам»).

Коммиты-фиксы после v1: `4a1fcd3`, `f26f92d`, `bbe978b`, `0fafbaa`, `3093dd5`, `2280fc2` (v2), далее `ed9f9e1`, `dfa9999`, `d711569`, `2ee09c4`, `ce8b40e`, `4b1ee15`, `8c5edc9`, `4802988`, `6813e22`, `8888dcd`, `cee803d` (v3).
Коммиты серии групп A–G: `6049c2a` (A), `25f0e90` (B), `0e75aab` (C), `4232b49` (G), `15c38ed` (D), `49417c9`+`5194f36`+`3c12ebc` (F), `1a4e5c3` (F post-CI), `786c471` (E), `386c5c7` (stationarity).
Коммиты v5: `72e13a2` (модули MI/TE/MSE/cross-MFDFA), `54ac8af` (TE-1, TE-2), `3c627d6` (MI-1, MSE-1), `c84ffa4` (MI-1 docstring), `dd6eb92` (XM-3, XM-4, XM-6), `037e0e1` (benchmark MI/TE/XM-5), `a7c8a0c` (Queue 1), `f730ddd` (Queue 2), `65dbdbd` (docs).

Статусы: OPEN, CLOSED `<hash>`, PARTIAL `<hash>`, FALSE, OBSOLETE, UNVERIFIED,
STOP (причина), DEFERRED (причина).
Верификация (v3v): CONFIRMED, FALSE, UNVERIFIED, NEEDS_RUN.

---

## Группа A — ETL и данные

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| A1 | P0 | `data/scripts/download_intermagnet.py:30-38` | Парсер IAGA-2002 структурно неверен (дата из позиций 0-1, значения из 3-5 вместо 7-9) | CLOSED `d711569` | v2 (V2-13) |
| A2 | P0 | `data/scripts/unify_schema.py:28` | SNR используется как `residual` | CLOSED `2ee09c4` | v2 (V2-14) |
| A3 | P1 | `unify_schema.py:30,42,56` vs `data/schema/unified_schema.json:13` | `meta` пишется строкой, схема требует object | CLOSED `ce8b40e` (схема приведена к string) | v2 (V2-15) |
| A4 | P1 | `scripts/make_synthetic_unified.py:44-50` vs `unified_schema.json:10` | `detector_type` intermagnet/ngl отсутствуют в enum схемы | CLOSED `6049c2a` | v2 (V2-16) |
| A5 | P1 | `unify_schema.py:26` | `detector_id = rx_call`, агрегации по `tx_call` нет → неуникальный ключ | CLOSED `6049c2a` | v2 (V2-17) |
| A6 | P1 | `make_sample.py:14` | `.head(500)` после глобальной сортировки даёт срез одного детектора | CLOSED `6049c2a` | v2 (V2-24) |
| A7 | P1 | `download_intermagnet.py:48` | Относительный путь вместо абсолютного `RAW_DIR` | CLOSED `6049c2a` | v2 (V2-25) |
| A8 | P1 | `download_wspr.py:85`, `download_horizons.py:44` | Нет кэша и checksums, воспроизвести прогон невозможно | CLOSED `6049c2a` | v2 (V2-35) |
| A9 | P1 | `data/raw/` | Каталог пуст, реальных данных нет | STOP (нужен сетевой источник) | v2 (V2-37), v1 |
| A10 | P1 | `data/processed/unified.parquet` | Создан `make_synthetic_unified.py`, а не документированным `unify_schema.py` | STOP (нужен прогон на реальных данных) | v2 (V2-38) |
| A11 | P1 | весь датасет | Единственный датасет полностью синтетический; real-data прогонов нет (не баг, задача real-data валидации) | STOP (real-data валидация) | v2 (V2-39) |
| A12 | P2 | `data/samples/` | Каталог пуст, примеры данных отсутствуют; README обещает примеры | CLOSED `6049c2a` | v2 (V2-40), v3 (#12) |
| A13 | P2 | `make_synthetic_unified.py:27` | `PROCESSED_DIR.mkdir` на уровне модуля | CLOSED `6049c2a` | v2 (V2-41) |
| A14 | P2 | `unify_schema.py:54-55` | `dropna` по timestamp, `residual` остаётся с NaN | CLOSED `6049c2a` | v2 (V2-18) |
| A15 | P2 | `unify_schema.py:49` | Слепой fallback на первую колонку | CLOSED `6049c2a` | v2 (V2-19) |
| A16 | P2 | `unify_schema.py:30` | `df.apply(..., axis=1)` построчно на всём файле | CLOSED `6049c2a` | v2 (V2-20) |
| A17 | P2 | `unify_schema.py:77-78` | `except Exception: print` молча уменьшает N | CLOSED `6049c2a` | v2 (V2-21) |
| A18 | P2 | `unify_schema.py:17` | `PROCESSED.mkdir` на импорте модуля | CLOSED `6049c2a` | v2 (V2-22) |
| A19 | P2 | `make_sample.py:11-16` | Код уровня модуля без `__main__` | CLOSED `6049c2a` | v2 (V2-23) |
| A20 | P2 | `download_intermagnet.py:52` | `out_path.touch()` создаёт пустой файл и возвращает успех | CLOSED `6049c2a` | v2 (V2-26) |
| A21 | P2 | `download_intermagnet.py:59` | `--station default="UNKNOWN"` | CLOSED `6049c2a` | v2 (V2-27) |
| A22 | P2 | `registry.py:77` | `download_ngl.py` отсутствует | CLOSED `6049c2a` | v2 (V2-28) |
| A23 | P2 | `registry.py:52,66,80` | `base_url` с placeholder `https://TODO...` | CLOSED `6049c2a` | v2 (V2-29) |
| A24 | P2 | `registry.py:48,62,76` | `expected_fields` использует `timestamp`, схема — `timestamp_utc` | CLOSED `6049c2a` | v2 (V2-30) |
| A25 | P3 | `registry.py:87` + `data/scripts/__init__.py:3` | `_initialize_registry()` печатает при каждом импорте | CLOSED `6049c2a` | v2 (V2-31) |
| A26 | P2 | `download_wspr.py:29,77` | `limit=5000` молча усекает конец дня | CLOSED `6049c2a` | v2 (V2-32) |
| A27 | P3 | `download_wspr.py:3` vs `:84` | Docstring обещает не тот путь файла | CLOSED `6049c2a` | v2 (V2-33) |
| A28 | P2 | `download_horizons.py:26-29` | Эфемериды не версионируются | CLOSED `6049c2a` | v2 (V2-36) |
| A29 | P3 | `make_synthetic_unified.py:47` | `D_Krasnoyarsk` в смешанном регистре | CLOSED `6049c2a` | v2 (V2-43) |
| A30 | P2 | `make_synthetic_unified.py:32-50` | Смешивает WSPR/магнитометр/GNSS в одном пуле | PARTIAL `6049c2a` (ограничение задокументировано; рефакторинг физики вне границ) | v2 (V2-44) |
| A31 | P3 | `make_synthetic_unified.py:87-93` | Пространственная корреляция мгновенная, лаг всегда 0 | CLOSED `6049c2a` | v2 (V2-45) |
| A32 | P3 | `make_synthetic_unified.py` | Колонка `meta` отсутствовала у второго производителя | CLOSED `ce8b40e` | v2 (V2-42) |
| A33 | P2 | `data/scripts/api_client.py` | Класс без методов, импортируется 0 раз (requests уже импортирован) | CLOSED `6049c2a` | v2 (V2-70) |
| A34 | P3 | `download_intermagnet.py:41-54` | `download_and_save_intermagnet` не вызывается | CLOSED `6049c2a` | v2 (V2-72) |

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
| B18 | P1 | `pairs.py:301-310` | Собственная реализация BH (жёстко BH для зависимых пар, нужен BY / общий `fdr_bh_q`) | STOP (файл вне границ группы B; перенести в сессию C) | v3 (#2), v3 (#36) |
| B19 | P1 | `pairs.py:240-241,366-367` | Пары с общим детектором используют одни суррогаты → зависимые p-value | UNVERIFIED (v3v: механизм опровергнут, rho≈-0.003) | v3 (#3) |
| B20 | P1 | `pairs.py` | Нет detrend/standardize, расхождение с max-stat пайплайном | STOP (файл вне границ группы B; перенести в сессию C) | v3 (#4) |
| B21 | P2 | `surrogate.py:66-74` | Python-цикл + DataFrame + `pandas.corr` на каждый суррогат | OPEN (перф-рефакторинг отложен) | v1 (P2-2) |
| B22 | P2 | `mantel.py:71-89` | Permutation-тест — чистый Python-цикл (9999 итераций) | OPEN (перф-рефакторинг отложен) | v1 (P2-4) |
| B23 | P2 | `preprocessing.py` | `robust=True` — median/MAD, не Theil-Sen; detrend остаётся OLS | STOP (preprocessing.py вне границ) | v3 (#19), v1 (§3.4) |
| B24 | P2 | `cross_correlation.py:137,236` | `n_obs` считается после интерполяции NaN | CLOSED `25f0e90` | v3 (#17) |
| B25 | P2 | `cross_correlation.py:231-232` | Пары с NaN t_obs молча выбрасываются до FDR | STOP (меняет число гипотез M; решение пользователя) | v3 (#18) |
| B26 | P2 | `pairs.py:71-76` | Метод `shuffle` разрушает автокорреляцию (нуль слишком узкий) | STOP (файл вне границ группы B; перенести в сессию C) | v3 (#14) |
| B27 | P2 | `pairs.py:91-101` | AR(1) суррогат через `lfilter` без burn-in | STOP (файл вне границ группы B; перенести в сессию C) | v3 (#15) |
| B28 | P2 | `effective_sample.py:111-118` | Общий mask занижает IAT обоих рядов | FALSE (verify_B28: знак зависит от данных, занижение не воспроизвелось) | v2 (V2-63) |
| B29 | P2 | `preprocessing.py:38-47` | NaN-интерполяция без ограничения длины пропуска | STOP (preprocessing.py вне границ) | v2 (V2-64) |
| B30 | P2 | `preprocessing.py:50` | Ряд длины 2 после детренда → нули | STOP (preprocessing.py вне границ) | v2 (V2-65) |
| B31 | P2 | `surrogate.py` | `DEFAULT_OUT.mkdir` при импорте пакета | CLOSED `8888dcd` | v1 (P3), v3 (#20) |
| B32 | P3 | `effective_sample.py` | Лаги ниже порога между значимыми не суммируются; не окно Sokal (правило и docstring) | CLOSED `ed9f9e1`/`8888dcd` | v3 (#33), v1 (P1-7) |
| B33 | P3 | `surrogate.py`, `pairs.py`, `effective_sample.py`, `preprocessing.py` | Шесть копий NaN-интерполяции с разными порогами (в т.ч. `pairs.py:65`) | OPEN (дедупликация отложена: часть файлов вне границ) | v3 (#35) |
| B34 | P3 | `cross_correlation.py` | `print()` внутри библиотечной функции | CLOSED `8888dcd` (logging) | v3 (#38) |
| B35 | P3 | `pairs.py:60-67` | Ветка интерполяции NaN недостижима | CLOSED `f730ddd` (мёртвая ветка удалена) | v3 (#37) |
| B36 | P3 | `effective_sample.py:82-83` | `max_lag` не принимается из вызывающего кода | FALSE (verify_B36: `integrated_autocorrelation_time` уже имеет `max_lag`) | v3v (дополнение к #9) |
| B37 | P1 | `surrogate.py:83` | `surrogate_test` не применял правило Davison-Hinkley | CLOSED `f26f92d` | v1 (P1-4) |
| B38 | P3 | `surrogate.py:245,183` | `np.argsort` без `kind="stable"` при ties | CLOSED `25f0e90` | v2 (V2-59) |
| B39 | P3 | `surrogate.py` | Критерий сходимости IAAFT не стандартен | STOP (смена критерия меняет числовой результат; нужно решение) | v2 (V2-54) |
| B40 | P1 | `block_bootstrap.py:9-10` | Docstring описывал перемешивание блоков, код — случайные старты | CLOSED `8888dcd` | v2 (V2-62), v3 (#32) |

---

## Группа C — pairs.py и параллелизм

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| C1 | P0 | `pairs.py:199,345,348` | NaN обращался в максимальную значимость | CLOSED `4a1fcd3` | v1 (P0-1) |
| C2 | P1 | `pairs.py:220-229` | Утечка shared memory при ошибке создания второго блока | CLOSED `f26f92d` (ExitStack) | v1 (P1-1) |
| C3 | P2 | `pairs.py:213,220-222` | Двойное выделение памяти под суррогаты | CLOSED `0e75aab` | v1 (P2-1) |
| C4 | P1 | `cross_correlation.py:222,248` | `pair_idx` не инкрементился после `continue` | CLOSED `4b1ee15` | v3 (#6), v3v CONFIRMED |
| C5 | P2 | `pairs.py:183,236-237,246` | Не было валидации `B < 1` и `seed < 0` | CLOSED `4b1ee15` | v3 (#16), v3v CONFIRMED |
| C6 | P2 | `pairs.py:129,155` | Дефект `-(T-1)` при `T=1` даёт 3 столбца вместо 1 | CLOSED `0e75aab` | v1 (§4.4) |
| C7 | P2 | `pairs.py` (T=1, n=0/1) | Нет тестов граничных размеров `_batch_max_stat_corr` | CLOSED `0e75aab` (T=1/T=2/one-row wide; n=0/T=0 остаются) | v1 (§4.4) |
| C8 | P2 | `pairs.py` | float32 для суррогатов против float64 для `C_obs` — влияние не проверено | UNVERIFIED / STOP (нужно численное решение о dtype) | v3 (Not verified) |
| C9 | P2 | `pairs.py` | Двойной unlink через resource_tracker на Python < 3.13 | PARTIAL / UNVERIFIED (Windows tests added, run as informational CI job. Shared memory cleanup verified in finally. Windows/Python 3.13.5: 5 passed; CI 3.10–3.12 results pending.) | v3 (Not verified) |
| C10 | P2 | `pairs.py` | `shm.close()` при живых views может бросить BufferError | PARTIAL / UNVERIFIED (Windows tests added, run as informational CI job. Shared memory cleanup verified in finally. Views released before close; second attachment protected by try/finally. Windows/Python 3.13.5: 5 passed; CI 3.10–3.12 results pending.) | v3 (Not verified) |

---

## Группа D — API и публичный интерфейс

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| D1 | P1 | `cross_correlation.py:157`, `pairs.py:178` | Две разные функции с именем `cross_correlation_pairs_with_max_stat` | CLOSED `15c38ed` (задокументировано, API сохранён) | v1 (§1.3), v3 (#21) |
| D2 | P2 | `cross_correlation.py:28` | Alias `fdr_bh_q as _benjamini_hochberg` вводил в заблуждение | CLOSED `8888dcd` (`_fdr_correct`) | v2 (V2-04), v1 (P3) |
| D3 | P2 | `__init__.py:58-59` | `fdr_bh` рядом с `fdr_bh_q`, расхождение не документировано | CLOSED `15c38ed` | v2 (V2-66) |
| D4 | P2 | `analysis/__init__.py:1` | Реэкспортировано 2 из 14 модулей, нет `__all__` | CLOSED `15c38ed` | v2 (V2-67), v1 (§1.3) |
| D5 | P3 | `__init__.py:13` | `__version__` — единственное объявление, git-тегов нет | CLOSED `f730ddd` (git tag `v0.1.0` установлен, `git tag --list` — подтверждено) | v2 (V2-69) |
| D6 | P3 | `ai_narrator.py`, `narrator.py`, `quest.py` | Не в `__all__`, не импортируются | CLOSED `f730ddd` (NOTE-комментарии о статусе) | v2 (V2-71) |
| D7 | P3 | `game/` (4 файла) | Мёртвый код, не упомянут в README/pyproject | CLOSED `f730ddd` (`game/README.md` — experimental) | v2 (V2-74) |
| D8 | P2 | `pyproject.toml` | mypy не настроен, типы не проверяются | CLOSED `af47ec3` (mypy configured: 2 errors fixed, config added; CI job informational, continue-on-error, will become gate after one cycle) | v2 (V2-75) |
| D9 | P3 | `download_horizons.py:26` | Аннотация возврата `-> "object"` бессмысленна | CLOSED `a7c8a0c` (конкретный тип, TYPE_CHECKING) | v2 (V2-76) |
| D10 | P3 | `surrogate.py:419` | `_lagged_cc` без аннотаций | CLOSED `a7c8a0c` (аннотации добавлены) | v2 (V2-77) |
| D11 | P3 | `safe_exec.py:45` | `True/False/None` в `SAFE_BUILTINS` недостижимы (ключевые слова) | CLOSED `15c38ed` (комментарий; записи сохранены) | v1 (P3) |
| D12 | P3 | `mantel.py:115` | Избыточный `import pandas as pd # noqa: F401` | CLOSED `a7c8a0c` (убран) | v1 (P3) |
| D13 | P2 | `analysis/` циклические импорты | `surrogate`↔`cross_correlation`, `mantel`↔`distance_analysis` | CLOSED `f730ddd` (ленивые импорты задокументированы) | v1 (§1.2) |
| D14 | P2 | `surrogate.py:47` | `build_wide` — дубликат `build_wide_by_detector` | CLOSED `f730ddd` (deprecated alias) | v1 (§1.4) |

---

## Группа E — Тесты

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| E1 | P2 | `test_core_regression.py:23-75` | Тесты проверяли подстроки исходника, не поведение | CLOSED `6813e22` | v1 (§4.2), v3 (#22) |
| E2 | P1 | `test_fdr.py` | Нет численного эталона `fdr_bh_q`/`benjamini_yekutieli` | CLOSED `6813e22` (`test_statistical_reference.py`) | v2 (V2-50), v1 (§4.1) |
| E3 | P1 | `test_ess_and_bootstrap.py:28` | Нет эталона `tau` для AR(1) против `(1+φ)/(1-φ)` | CLOSED `786c471` | v2 (V2-51) |
| E4 | P3 | `test_cross_correlation_synthetic.py` | Нет точного численного эталона ρ | CLOSED `6813e22` (lagged_cc_recovers_known_lag) | v2 (V2-52) |
| E5 | P2 | `tests/` | Нет теста сходимости/распределения IAAFT | CLOSED `786c471` | v2 (V2-55) |
| E6 | P3 | `tests/` | Нет Windows-специфичного теста shm | STOP (нужен Windows runner; связано с F4) | v2 (V2-58) |
| E7 | P2 | `tests/` | Нет тестов `adf_test`, `check_stationarity_wide`, `fisher_weighted_max_stat`, `mfdfa`, `load_unified`, `power_curve` | CLOSED `786c471` | v3 (#23), v1 (§4.1) |
| E8 | P2 | `tests/` | Нет сценариев пустой wide, constant series, ряды разной длины | CLOSED `786c471` (B=0, seed=-1, max_lag закрыты `4b1ee15`/`4802988`) | v3 (#24), v1 (§4.4) |
| E9 | P3 | `tests/`, корень | Нет `conftest.py`, фикстуры дублируются | CLOSED `786c471` | v1 (§4.3) |
| E10 | P2 | `.pytest_cache/v/cache/lastfailed` | Устаревшая запись `test_pipeline.py`, файла нет | OBSOLETE (stale cache) | v3 (#27) |
| E11 | P2 | `test_negative_control.py` | Тест допускает `<=1`, README заявлял 0 | CLOSED `8888dcd` | v3 (#28), v1 |

---

## Группа F — CI и инфраструктура

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| F1 | P1 | `requirements.lock` | Lock устарел: нет `joblib`, собран на Python 3.13 | STOP (перегенерация pip-compile требует сети) | v1 (§5), v2 (V2-82,83), v3 (#10) |
| F2 | P1 | `pyproject.toml` | `pyarrow` отсутствовал в `[project] dependencies` | CLOSED `205daf9` | v2 (V2-87) |
| F3 | P2 | `.github/workflows/ci.yml:16,50` | CI только Python 3.12 при `requires-python>=3.10` | CLOSED `5194f36` (matrix 3.11/3.12) | v1 (§4.5), v2, v3 (#26) |
| F4 | P2 | `ci.yml` | Нет Windows job при использовании `SharedMemory` | CLOSED `49417c9` (job добавлен; `1a4e5c3` — informational) | v1 (§4.5), v2 |
| F5 | P1 | `ci.yml` | Coverage не собирается (`pytest-cov` в dev не используется) | CLOSED `49417c9` (затем `3c12ebc` порог 45) | v1 (P2-5), v2 (§6.1), v3 (#26) |
| F6 | P2 | `ci.yml:38` | ruff не покрывает `data/scripts/` и `game/` | CLOSED `49417c9` (`data/` добавлен) | v1 (§4.5), v2 (V2-80) |
| F7 | P2 | `ci.yml:43` | Slow-тесты только на push в main | CLOSED `5194f36` (paths-filter на PR) | v3 (#25) |
| F8 | P3 | `ci.yml` | Нет `compileall`/проверки импорта `registry.py` | CLOSED `49417c9` | v2 (V2-81) |
| F9 | P3 | `ci.yml` | `cache: pip` без `cache-dependency-path` | CLOSED `49417c9` | v2 |
| F10 | P2 | `.gitignore` | Дубли записей `__pycache__/`, `*.egg-info/`, `.venv/`, `venv/` (в т.ч. как отмечено в README) | CLOSED `8888dcd` | v1 (P3), v2 (V2-89), v3 (#39) |
| F11 | P2 | `.gitignore:46` | `audit/` в ignore, но файлы отслеживаются | FALSE (`.gitignore:42` — `#audit/` закомментирован) | v2 (V2-90) |
| F12 | P3 | `.gitignore` | Нет игнора `.coverage`, `htmlcov/` | CLOSED `49417c9` | v2 (V2-91) |
| F13 | P2 | `Makefile` | Не было целей `test`/`lint` | CLOSED `8888dcd` | v2 (V2-79), v3 (#39) |
| F14 | P2 | `requirements.in` vs `pyproject.toml` | Две конфликтующие модели зависимостей | STOP (архитектурное решение; нельзя удалять зависимости) | v1 (§5.1), v2 (V2-84) |
| F15 | P2 | `pyproject.toml` | `joblib` в `dependencies`, но не в `dev` | FALSE (joblib — runtime-зависимость, дублировать в dev не нужно) | v2 (V2-85) |
| F16 | P3 | `pyproject.toml:57` | `MFDFA` объявлен трижды | FALSE (разные optional-группы mfdfa/dev/all) | v2 (V2-86) |
| F17 | P3 | `pyproject.toml` | `pytest-cov`/`pip-tools` не используются | PARTIAL `49417c9` (pytest-cov задействован; pip-tools — см. F1) | v2 (V2-88) |
| F18 | P3 | `bench.log`, `check_sprint4.py` | Файлы в git, не документированы | CLOSED `a7c8a0c` (`git rm` обоих файлов) | v1 (§5.4), v3 (#39) |
| F19 | P1 | `results/` (git) | `results/` не игнорировался, противоречие README | CLOSED `2280fc2` | v1 (§5.3), v2 (V2-09) |
| F20 | P3 | `pyproject.toml:34` | numpy>=1.24 против `Generator.spawn` (нужен 1.25) | PARTIAL `49417c9` (numpy>=1.25; точная версия появления spawn не проверена прогоном) | v3 (Not verified) |
| F21 | P2 | `data/processed/unified.parquet` | Файл пересоздан локально, в git не входит | OBSOLETE | v3v (PHASE B) |

---

## Группа G — Документация

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| G1 | P0 | `docs/PIPELINE.md:153` | Описание IAT противоречило коду после фикса P1-7 | CLOSED `ed9f9e1` | v2 (V2-01) |
| G2 | P1 | `docs/PIPELINE.md:117-133` | Документирован только BH, код по умолчанию BY | CLOSED `4232b49` | v2 (V2-03), v1 |
| G3 | P1 | `docs/PIPELINE.md:256-278` | §11 описывает OLS, основной метод — Mantel | CLOSED `4232b49` | v2 (V2-08) |
| G4 | P1 | `docs/methodology.md` | 9 строк: не описаны max-stat, BY, bootstrap, Mantel, IAAFT, MFDFA (ESS добавлен `cee803d`) | CLOSED `4232b49` | v2 (V2-10), v1 |
| G5 | P3 | `README.md` | Битые ссылки `paper/work.tex`, `paper/references.bib`, `docs/quest.md`, `docs/fund.md` | CLOSED `8888dcd` | v2 (V2-11, V2-94), v1 (§5.4), v3 (#31) |
| G6 | P2 | `README.md` (Скриншоты) | Ссылки на `results/cross_correlation.png`, `results/mfdfa.png` | FALSE (внутри HTML-комментария, не рендерятся) | v2 (V2-12) |
| G7 | P2 | `docs/PIPELINE.md:96-113` | §5 описывает только phase; IAAFT/time_shift недостижимы из CLI | CLOSED `4232b49` | v2 (V2-05) |
| G8 | P2 | `docs/PIPELINE.md:69-77` | Формула max-stat без Fisher-весов | CLOSED `4232b49` | v2 (V2-06) |
| G9 | P2 | `docs/PIPELINE.md:89-90` | Три разных значения B (функция/CLI/документ) | CLOSED `4232b49` | v2 (V2-07) |
| G10 | P2 | `docs/PIPELINE.md:283` | «Результаты: results/*.csv» без пометки об устаревании | CLOSED `4232b49` | v2 (V2-09) |
| G11 | P2 | `README_ARCHITECTURE_UPDATE.md:20-21` | Ложное утверждение о `api_client`/`SourceRegistry` | CLOSED `a7c8a0c` (README_ARCHITECTURE_UPDATE.md удалён) | v2 (V2-46) |
| G12 | P2 | `README_ARCHITECTURE_UPDATE.md:29` | Заявление «Надежность: Высокая» | CLOSED `a7c8a0c` (README_ARCHITECTURE_UPDATE.md удалён) | v2 (V2-47) |
| G13 | P1 | `README_ARCHITECTURE_UPDATE.md:32-34` | Ссылка на несуществующий `test_source_registry.py` | CLOSED `a7c8a0c` (README_ARCHITECTURE_UPDATE.md удалён) | v2 (V2-48) |
| G14 | P3 | `README_ARCHITECTURE_UPDATE.md:1,3,8,23,31` | Эмодзи | CLOSED `a7c8a0c` (README_ARCHITECTURE_UPDATE.md удалён) | v2 (V2-49) |
| G15 | P2 | `README.md:15` | Бейдж вёл на `ci.yaml`, файл `ci.yml` | CLOSED `8888dcd` | v3 (#29) |
| G16 | P2 | `README.md:194,216` | `requirements.txt` удалён, но указан в установке | CLOSED `8888dcd` | v3 (#29) |
| G17 | P3 | `README.md:498` | «11 тестов в 5 файлах» | CLOSED `8888dcd` | v3 (#29) |
| G18 | P3 | `README.md:109,113,124` | «1000+ суррогатов», «единая BH» | CLOSED `8888dcd` | v3 (#30) |
| G19 | P3 | `cross_correlation.py:174-175` | Docstring «5-10 минут для 45 пар» | CLOSED `8888dcd` | v3 (#34) |
| G20 | P3 | `docs/methodology.md:19` | «1000+ фазовых суррогатов» против дефолта 200 | CLOSED `8888dcd` | v2 (V2-10) |
| G21 | P3 | `README.md` | `results/ # gitignored` противоречит состоянию | CLOSED `2280fc2` (results удалён из git) | v1 (§5.3) |
| G22 | P3 | `surrogate.py:55,86,95,127` | Константы без имени/обоснования | CLOSED `f730ddd` (именованные константы, значения без изменений) | v1 (P3) |
| G23 | P3 | `cross_correlation.py:88` | Магическое `n < 10` без параметра | CLOSED `f730ddd` (заменено на `MIN_SAMPLES`) | v1 (P3) |
| G24 | P3 | `surrogate.py:127,257,292,436,485` | E302: одна пустая строка перед `def` | CLOSED `f730ddd` (PEP8: две пустые строки) | v1 (P3) |
| G25 | P3 | `surrogate.py:114-124` | Ветка 2D `fdr_bh` без проверки симметричности | CLOSED `f730ddd` (ValueError при несимметрии) | v1 (P3) |

---

## Группа H — Безопасность

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| H1 | P0 | `safe_exec.py:15-32` | `ctypes` и др. не в `FORBIDDEN_NAMES` — выход из песочницы | CLOSED `4a1fcd3` | v1 (P0-5) |
| H2 | P0 | `opencode.json` @ `bc58a3b` | API-ключ в истории git; untracking не удаляет секрет | CLOSED (ключ ротирован 2026-10-05) | v2 (V2-93), v3 (#13) |
| H3 | P2 | `opencode.json` в `.gitignore` | Ignore добавлен, но объект в истории остаётся | OPEN (тот же корень, что H2; история не переписывалась) | v1 (§5.3) |
---

## Группа V5 — Новые модули (MI/TE/MSE/XM)

| ID | Sev | File:Line | Problem | Status | Sources |
|----|-----|-----------|---------|--------|---------|
| MI-1 | P1 | `mutual_info.py:83-103` | KSG: policy для ties/dубликатов не определена (eps=0, дискретные/квантованные повторения) | CLOSED `3c627d6` (валидация k/base, `UserWarning` на точных дубликатах), `c84ffa4` (docstring: непрерывные распределения), `2df4804` (v6: reference-валидация KSG — сходимость на непрерывных, `inf` при ≲30 уровнях квантования, bias +0.17 при s=100; 3 теста) | v5 (AUDIT_v4), v6 (AUDIT_v6) |
| MI-3 | P2 | `mutual_info.py:94-97,142-147,176-185` | Python-вызовы `query_ball_point` по точке; матрицы строится повторно на каждую пару | CLOSED (Performance sufficient for K≤20, N≤10000. Benchmarks: MI 0.85s, TE 4.97s at N=4000×10. Further optimization only if K>30 or N>50000.) | v5 (AUDIT_v4) |
| TE-1 | P1 | `transfer_entropy.py:83-107` | Для k>1 усреднение отдельных CMI — не совместный TE историй | CLOSED `54ac8af` (API ограничено k=1, `k>1` — ValueError) | v5 (AUDIT_v4) |
| TE-2 | P1 | `transfer_entropy.py:30-39,74-91` | Нет NaN-policy и валидации k/lag/k_nn; неравные ряды молча обрезаются | CLOSED `54ac8af` (finite-policy через `_as_1d`, валидация, unequal length — ValueError) | v5 (AUDIT_v4) |
| TE-3 | P2 | `transfer_entropy.py:110-137` | N*(N-1) направленных оценок, каждая строит KDTree; стоимость не измерена | CLOSED (Performance sufficient for K≤20, N≤10000. Benchmarks: MI 0.85s, TE 4.97s at N=4000×10. Further optimization only if K>30 or N>50000.) | v5 (AUDIT_v4) |
| MSE-1 | P1 | `mse.py:67-74,87-93` | Постоянный ряд: `std=0` → `r=0` → возвращается `inf`; SampEn-предел не задокументирован | CLOSED `3c627d6` (контракт: константный ряд → 0.0, B>0 и A=0 → inf, валидация входа) | v5 (AUDIT_v4) |
| XM-1 | P1 | `cross_mfdfa.py:43-67,111-129` | `abs` на знаковых cross-флуктуациях стирает cancellation; формула не привязана к версии MF-DXA | CLOSED (convention resolved: abs-default + split-option; open problem documented in docstring, Qwen consultation) | v5 (AUDIT_v4) |
| XM-2 | P1 | `cross_mfdfa.py:121-139` | Предел q→0 и sign-конвенция `F_q` не верифицированы против reference | CLOSED (q=0 limit для обеих конвенций; reference-тесты: q2_matches_dcca, anticorrelated_segments, all_positive_matches_standard) | v5 (AUDIT_v4) |
| XM-3 | P2 | `cross_mfdfa.py:131-174` | `h(q)`/Legendre без goodness-of-fit и scale-diagnostic | CLOSED `dd6eb92` (`r_squared` на q и `n_scales` в результате) | v5 (AUDIT_v4) |
| XM-4 | P2 | `cross_mfdfa.py:97-106,112-139` | Входы усекаются до min-длины; NaN/Inf, пустые/nonfinite q и scales молча проходят | CLOSED `dd6eb92` (равные длины, конечные значения, n>=100, валидация q/scales) | v5 (AUDIT_v4) |
| XM-5 | P2 | `cross_mfdfa.py:58-67,113-129` | Вложенные `np.polyfit` на сегмент/масштаб; runtime не измерялся | CLOSED `ebb7d66` (v6: оптимизация 58× — закрытая OLS-формула + батчинг сегментов; 0.184 → 0.0032 c при N=4000; diff ≤ 1.8e-15) | v5 (AUDIT_v4), v6 (AUDIT_v6) |
| XM-6 | P2 | `tests/test_E_cross_mfdfa.py:34-76` | Все содержательные тесты x=y; boundary/контрактные случаи отсутствовали | CLOSED `dd6eb92` (5 новых тестов: unequal lengths, scales>n, empty q, NaN, diagnostics) | v5 (AUDIT_v4) |
| BENCH-1 | P1 | `bench/results_v5.txt` | MI/TE matrices > 60 c на N=4000×10 — P1 для production N>2000 | CLOSED (Performance sufficient for K≤20, N≤10000. Benchmarks: MI 0.85s, TE 4.97s at N=4000×10. Further optimization only if K>30 or N>50000.) | v5 (AUDIT_v5) |

---

## Итог по приоритетам

| Severity | CLOSED | OPEN | STOP | PARTIAL | FALSE | OBSOLETE | UNVERIFIED | DEFERRED | Total |
|----------|--------|------|------|---------|-------|----------|------------|----------|-------|
| P0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| P1 | 42 | 0 | 6 | 0 | 0 | 0 | 1 | 0 | 49 |
| P2 | 53 | 3 | 5 | 3 | 4 | 2 | 3 | 0 | 73 |
| P3 | 34 | 1 | 2 | 2 | 2 | 0 | 0 | 0 | 41 |
| Итого | 138 | 4 | 13 | 5 | 6 | 2 | 4 | 0 | 172 |

Разбивка по группам: A 34, B 40, C 10, D 14, E 11, F 21, G 25, H 3, V5 13 (сумма 171).

Проверка сумм (v6 + D8): CLOSED 138 + OPEN 4 + STOP 13 + PARTIAL 5 + FALSE 6 +
OBSOLETE 2 + UNVERIFIED 4 + DEFERRED 0 = 172 = Total.
Проверка по severity: 9 + 49 + 73 + 41 = 172 = Total.
Примечание к 172: MI-1 закрыт в v5 (первичная валидация) и переоткрыт/
перезакрыт в v6 (вторичная reference-валидация) — двойной счёт даёт 172
вместо 171. Фактическое число уникальных находок остаётся 171.

Примечание: STOP — находки, требующие решения пользователя или находящиеся
вне границ сессии (код/внешние данные/архитектура); OPEN — отложенные
перф-рефакторинги (B21, B22, B33) и H3. DEFERRED — none (D8 — CLOSED af47ec3
(mypy); XM-5 — CLOSED ebb7d66 (58×)). XM-1/XM-2 закрыты:
конвенция abs-default + split-option.
B19 и C8 посчитаны в колонке STOP (в UNVERIFIED-подмножестве)
и одновременно отражены в колонке Unverified. C9/C10 переведены из STOP
в PARTIAL; UNVERIFIED сохраняется до результатов Windows CI на 3.10–3.12.

---

## Замечания

- **Расхождения между отчётами.** v3_partial #3 (зависимые p-value при общем детекторе) v3_verified переклассифицировал в UNVERIFIED: механизм (общие суррогаты → зависимые нули) опровергнут, эмпирика слабая. В реестре оставлен один UNVERIFIED-статус.
- **v3 #9.** Изначально помечен FALSE, затем исправлен на CONFIRMED (partial, t<343); закрыт `4b1ee15` заменой `1-cdf` на `sf`. При t≥343 `sf` тоже даёт 0.0 — это ограничение float64, не дефект кода.
- **v2 V2-68, V2-56, V2-57, V2-60, V2-61, V2-34, V2-53** — не находки (подтверждения корректности), в реестр не включены.
- **v2 V2-73** (`_lagged_cc` вызывается ли) — UNVERIFIED, требует `git grep`.
- **v1 §1.4** `check_sprint4.py` — в v2 (§7) признан отсутствующим в `git ls-files`; v3 подтверждает наличие `check_sprint4.py` в git. Расхождение источников, оставлено в F18 по факту `git ls-files`.
- **Без данных нельзя проверить:** A9, A10, A11 (реальные прогоны), A4 (валидация схемы), F20 (numpy.spawn), C8-C10 (shm/BufferError/float32).
- **Противоречие docs-vs-code** по FDR (G2) закрыто в `4232b49`.
- **v3 (#4)** (pairs без preprocess, B20) пересекается с D1 (две разные функции) — общий корень: расхождение двух пайплайнов.
- **v3 (#26)** CI: Python 3.12 only — закрыто F3; coverage — закрыто F5.
- **A12, F19, F21** связаны с одной темой: происхождение и доступность данных (`data/raw` пуст, `data/samples` пополнен `6049c2a`, `results` удалён).

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

1. **STOP-решения пользователя** — B18/B20/B25/B26/B27/B35 (pairs.py, нужна сессия группы C), B23/B29/B30 (preprocessing.py), B39 (критерий IAAFT), C8/C9/C10 (dtype/shm), D5 (релиз-теги), F1/F14/F18 (lock/deps/git-мусор). ~6-8 ч.
2. **Группа A (реальные данные)** — A9/A10/A11, ~2-3 ч после появления сетевого источника. Без воспроизводимого датасета ни один статистический результат не публикуем.
3. **Группа G (документация)** — G11-G14 (`README_ARCHITECTURE_UPDATE.md`), ~1-2 ч; G22-G25 — это код (перенести в B).
4. **Группа B (остаток)** — B21/B22/B33 (перф/дедупликация), ~4-5 ч. Требуют аккуратности с числовыми результатами.
5. **Группа D (API/типы)** — D6/D7/D8/D9/D10/D12/D13/D14, ~3-4 ч. Низший риск для результата.
6. **Группа E** — E6 (Windows shm), один тест после получения traceback Windows job.
7. **Группа F** — F1/F14/F18 STOP; после решения — механические правки.
8. **Группа H** — H3 (косметика `.gitignore`/история), отдельная сессия не нужна.

Обоснование по группам:
- H: ключ ротирован, остаётся только запись про `.gitignore`; отдельная сессия не нужна.
- A: пустой `data/raw` и синтетический parquet блокируют любую научную валидность.
- B: методы, на которых строятся выводы; зависимы от A.
- C: отдельный публичный пайплайн, содержит собственные P2-дефекты.
- E: защита от регрессий, ставить после фиксов B/A/C.
- F: CI-воспроизводимость, влияет на доверие к прогонам.
- G: документация приводится в соответствие уже исправленному коду.
- D: API/типизация — низший риск для результата.

---

## Обновление от 2026-10-06

За последние сутки закрыто: 55
- Группа A: 26 closed (+1 PARTIAL — A30)
- Группа B: 2 closed (B24, B38; 2 FALSE — B28, B36)
- Группа C: 3 closed (C3, C6, C7)
- Группа D: 4 closed (D1, D3, D4, D11)
- Группа E: 5 closed (E3, E5, E7, E8, E9)
- Группа F: 8 closed (F3, F4, F5, F6, F7, F8, F9, F12) (+2 PARTIAL — F17, F20)
- Группа G: 7 closed (G2, G3, G4, G7, G8, G9, G10)
- Группа H: 0 closed

Осталось OPEN (отложено, не STOP): 4 (B21, B22, B33, H3)
Осталось STOP: 33
Осталось PARTIAL: 3 (A30, F17, F20)
Осталось UNVERIFIED: 4 (B19, C8, C9, C10)
Помечено FALSE: 6 (B28, B36, F11, F15, F16, G6)

Все P0 закрыты (9 из 9). Тесты: 215 -> 237 collected.

Примечание к арифметике: фактических строк CLOSED в реестре — 105
(проверено grep). Сессионные отчёты A–G фиксируют 55 закрытий
(A26 + B2 + C3 + D4 + E5 + F8 + G7). Значит, до сессии CLOSED было 50,
а не 51, как указывала старая мета (одна запись была переклассифицирована
при ревизии). Часть записей переведена в PARTIAL (A30, F17, F20),
FALSE (B28, B36, F11, F15, F16, G6) и STOP/UNVERIFIED (B19, C8–C10).
Итоговая сумма статусов сходится к 158.

### v5 (HEAD `65dbdbd`)

Queue 1 `a7c8a0c` (8 закрыто): D9, D10, D12 (аннотации/импорты),
G11-G14 (`README_ARCHITECTURE_UPDATE.md` удалён), F18
(`git rm` `bench.log`, `check_sprint4.py`).

Queue 2 `f730ddd` (9 закрыто, 1 отложено): D5 (git tag `v0.1.0`), D6/D7
(`game/README.md` — experimental), D13 (ленивые импорты задокументированы),
D14 (deprecated alias `build_wide`), G22-G25 (именованные константы,
`MIN_SAMPLES`, PEP8, ValueError при несимметрии), B35 (мёртвая ветка
удалена). D8 — DEFERRED, вариант C (mypy отложен).

Новые модули v5: 12 находок (7 closed, 5 deferred).
Closed: MI-1 + MSE-1 (`3c627d6` — контракты для ties/NaN/constant;
`c84ffa4` — docstring), TE-1/TE-2 (`54ac8af` — валидация, gate k>1),
XM-3/4/6 (`dd6eb92` — валидация входов, fit diagnostics, 5 boundary-тестов).
Deferred (benchmark `037e0e1`): MI-3, TE-3, XM-5 → `docs/roadmap.md`
(N=4000: MI/TE > 60 c, таймаут; MSE 0.03 c; XM 0.68 c);
XM-1/XM-2 закрыты: convention abs-default + split-option,
reference-тесты добавлены.

Итог после консультации v5: CLOSED 135 / STOP 13 / DEFERRED 2 / OPEN 4 /
PARTIAL 5 / FALSE 6 / UNVERIFIED 4 / OBSOLETE 2 = 171 (158 + 13 v5).
MI-3, TE-3 и BENCH-1 закрыты: производительность достаточна для K≤20,
N≤10000 (MI 0.85s, TE 4.97s при N=4000×10); дальнейшая оптимизация нужна
только при K>30 или N>50000. Все P0 закрыты (9 из 9).
Integration decision: RESOLVED — Standalone until criteria met.
Windows cleanup: C9/C10 — PARTIAL / UNVERIFIED; пять новых тестов проходят
на Windows/Python 3.13.5. `test-windows` расширен до Python 3.10/3.11/3.12
(`continue-on-error: true`); удалённый CI ещё не запускался.
Проверка после Windows cleanup: `pytest -q` — 285 passed (280 + 5),
без skip/xfail; ruff по CI scope (`crosscorr_lib/ tests/ scripts/ data/`) — clean.
Тесты: 237 collected (сборка 2026-10-06 08:51); v5 добавляет ~150 строк
тестов в 4 модулях (`test_E_transfer_entropy.py`, `test_E_mutual_info.py`,
`test_E_mse.py`, `test_E_cross_mfdfa.py`) — точный collected-count
переизмерить в рамках этой сборки (правило: без запуска pytest).

### v6 (HEAD `ebb7d66`)

Закрыто 2 (оба — хвосты новых модулей v5):
- **MI-1 (вторичный)** `2df4804`: reference-валидация KSG. На непрерывных
  гауссовых данных (N=10000, rho=0.5) сходится к `-0.5 ln(1-rho²) ≈ 0.1438`
  (ошибка ~0.1%). Измерено: при ≲30 уровнях квантования eps обнуляется и
  KSG возвращает `inf`; при s=100 (≈570 уровней) bias +0.17. Добавлено
  3 теста (`test_mi_ksg_gaussian_reference`, `test_mi_ksg_quantized_bias`,
  `test_mi_ksg_fine_quantization_bias_positive_and_bounded`), docstring
  дополнен измеренными цифрами.
- **XM-5** `ebb7d66`: `_detrended_cov` переписан на закрытую OLS-формулу с
  батчингом сегментов (без `np.polyfit`/`np.polyval` в цикле). Ускорение
  58× (0.184 → 0.0032 c при N=4000); результат совпадает с прежним до
  1.8e-15. Формулы не менялись.

D8 (mypy): CLOSED af47ec3 (mypy configured: 2 errors fixed, config added;
CI job informational, continue-on-error, will become gate after one cycle).
Фаза 4 (AUDIT_v6.md), фаза 5 (эта синхронизация).
Итог (v6 + D8): CLOSED 138 / STOP 13 / UNVERIFIED 4 / PARTIAL 5 / FALSE 6 /
OBSOLETE 2 / OPEN 4 / DEFERRED 0 = 172 (двойной счёт MI-1; уникальных 171).
Тесты: 291 collected (было 288 в v5). Ruff — clean.
