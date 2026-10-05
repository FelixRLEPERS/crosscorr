# Audit v3 — partial

## Findings (столько, сколько успел)

Все находки получены чтением кода и git; ничего не запускалось.

| # | class | severity | file:line | problem (1 строка) |
|---|---|---|---|---|
| 1 | stat/semantics | P0 | cross_correlation.py:242; surrogate.py:373-374; mantel.py:135-137; visualization.py:232 | Колонка `correlation` в max-stat пайплайне хранит Fisher-score abs(z)*sqrt(n-3) (неотрицательный, не ограничен 1), а Mantel, OLS и heatmap читают её как Spearman r в [-1,1]. |
| 2 | stat | P1 | pairs.py:301-310 | В pairs.py жёстко BH для пар с общими детекторами, хотя surrogate.py:165 сам говорит, что PRDS не выполнен и нужен BY. |
| 3 | stat | P1 | pairs.py:240-241, 366-367 | Пары с общим детектором используют одни и те же B суррогатов этого детектора, поэтому p-value пар зависимы. |
| 4 | stat/consistency | P1 | pairs.py:217 (нет импорта preprocess) | pairs.py не делает detrend/standardize, тогда как cross_correlation.py:105,165 делает это по умолчанию; два пайплайна считают разное. |
| 5 | correctness | P1 | surrogate.py:421-431 (вызов :367) | В `_count_valid_at_lag` при n < abs(tau) < 2n срезы a и b получаются разной длины, что по чтению даёт ValueError при max_lag > n. |
| 6 | repro/correctness | P1 | cross_correlation.py:222, 231-232, 248 | `pair_idx` не увеличивается при `continue`, поэтому следующая пара получает тот же child_rng и seed. |
| 7 | stat | P1 | surrogate.py:404 (суррогат из :602-642) | Для time_shift веса Fisher берутся из n_lags наблюдения, хотя у суррогата NaN на краях и другое реальное n. |
| 8 | stat | P1 | surrogate.py:80, 84, 88-91 | Наблюдаемая корреляция считается с попарным удалением NaN, а нулевая на ряду с mean-импутацией: разная статистика в наблюдении и в нуле. |
| 9 | stat/numerics | P1 | effective_sample.py:175 | `2*(1 - stats.t.cdf(...))` при большом abs(t) округляется до p=0.0 (нужен sf); пол p есть только для abs(r)>=1 (:157-165). |
| 10 | repro | P1 | requirements.lock (нет joblib); requirements.in:13; pyproject.toml:39 | Lock не содержит joblib, устарел относительно requirements.in (2026-09-23 против 2026-10-05), собран на Python 3.13 (:2), CI его не использует (ci.yml:30). |
| 11 | repro | P1 | git status | Рабочее дерево грязное: 11 изменённых файлов и неотслеживаемые residuals.py, test_residuals.py, test_unify_schema.py; результат не привязан к коммиту. |
| 12 | repro | P1 | data/samples/ (пусто); README.md:241 | README обещает примеры в data/samples/, каталог пуст, `*.parquet` в .gitignore, воспроизвести запуск без загрузки данных нельзя. |
| 13 | security (не подтверждено) | P1 | opencode.json @ bc58a3b; коммит a91257b | Файл с «exposed API key» был в истории; grep по ключевым словам на bc58a3b дал 0 совпадений, ротация ключа неизвестна. |
| 14 | stat | P2 | pairs.py:71-76 | Метод `shuffle` разрушает автокорреляцию, нулевое распределение слишком узкое для автокоррелированных рядов (по умолчанию используется phase). |
| 15 | stat | P2 | pairs.py:91-101 | AR(1) суррогат через lfilter без burn-in: дисперсия в начале ряда занижена. |
| 16 | validation | P2 | pairs.py:183, 236-237, 246 | Нет проверки B<1 и seed<0 (B=0 даёт пустой shm, seed=-1 отвергает default_rng) — ошибка без внятного сообщения. |
| 17 | data/stat | P2 | cross_correlation.py:137, 236; preprocessing.py:59-67 | `n_obs` считается после интерполяции NaN в preprocess, то есть интерполированные точки учитываются как наблюдения. |
| 18 | stat | P2 | cross_correlation.py:231-232 | Пары с NaN t_obs молча выбрасываются до FDR, число гипотез M уменьшается, поправка слабее. |
| 19 | stat/preprocess | P2 | preprocessing.py:70-77, 80-91 | `robust=True` делает устойчивым только масштаб (median/MAD), detrend остаётся OLS, не Theil-Sen; при MAD=0 масштабирование не выполняется. |
| 20 | arch | P2 | surrogate.py:19 | `DEFAULT_OUT.mkdir` выполняется при импорте пакета (через __init__.py:38) и создаёт results/ как побочный эффект. |
| 21 | arch/API | P2 | cross_correlation.py:157; pairs.py:178; __init__.py:25 | Две разные функции с именем cross_correlation_pairs_with_max_stat (разные статистика, колонки, FDR); в корне экспортируется только первая. |
| 22 | tests | P2 | test_core_regression.py:35-55 | Тесты fix2, fix3, fix4 проверяют подстроки исходника (n//4, **(1/3), .spawn(), а не поведение; баг из #6 их не ловит. |
| 23 | tests | P2 | tests/ (grep) | Нет тестов для adf_test, check_stationarity_wide, fisher_weighted_max_stat, mfdfa, load_unified, power_curve; нет conftest.py. |
| 24 | tests | P2 | tests/ (grep) | Нет сценариев B=0, seed=-1, max_lag>=n, пустой wide (0 колонок) и constant series для pairs и max-stat. |
| 25 | ci | P2 | ci.yml:43 | Slow-тесты (negative control) идут только на push в main, на pull request не запускаются. |
| 26 | ci | P2 | ci.yml:16, 30, 36-38; pyproject.toml:10, 27-29 | CI только на Python 3.12 при заявленных 3.10-3.12, без покрытия (pytest-cov в dev не используется), ruff после pytest. |
| 27 | tests | P2 | .pytest_cache/v/cache/lastfailed | Там упавший tests/test_pipeline.py::...::test_unified_schema_time_sync; файла нет и в истории git его нет. |
| 28 | docs/tests | P3 | test_negative_control.py:79; README.md:123, 481 | Тест допускает <=1 значимой пары, README утверждает 0 ложных срабатываний. |
| 29 | docs | P3 | README.md:15, 194, 216, 498 | Бейдж ведёт на ci.yaml (файл ci.yml); requirements.txt удалён, но указан в установке; «11 тестов в 5 файлах» против 132 def test_ в 15 файлах. |
| 30 | docs | P3 | README.md:109, 113, 124; surrogate.py:121, 226; cross_correlation.py:161 | README говорит про 1000+ суррогатов и «единую BH», по умолчанию BY и 200 суррогатов. |
| 31 | docs | P3 | README.md:435, 472-473, 546-547 | Ссылки на docs/quest.md, docs/fund.md, docs/fund-whitepaper.md, paper/work.tex, paper/references.bib — NOT FOUND. |
| 32 | docs | P3 | block_bootstrap.py:9-10 против :48-52; :38 | Docstring описывает перемешивание блоков, код тянет случайные старты с возвращением; block_size молча режется до n//4. |
| 33 | docs/stat | P3 | effective_sample.py:83-91 | Лаги ниже порога между значимыми не добавляются в сумму; это не окно Sokal, хотя коммит ed9f9e1 называет его так. |
| 34 | docs | P3 | cross_correlation.py:174-175 против :211-212 | Docstring обещает 5-10 минут для 45 пар, собственная оценка в коде даёт около 13 с. |
| 35 | dup | P3 | surrogate.py:43, 460, 570; pairs.py:65; effective_sample.py:52; preprocessing.py:61 | Шесть копий NaN-интерполяции с разными порогами (2 или 4 конечных значения). |
| 36 | dup | P3 | pairs.py:301-310 | Собственная реализация BH вместо fdr_bh_q (surrogate.py:223); NaN в p-value не обрабатываются. |
| 37 | dead code | P3 | pairs.py:60-67 | Ветка интерполяции NaN недостижима: NaN отсекаются на :218. |
| 38 | style | P3 | cross_correlation.py:208-212, 250 | print() внутри библиотечной функции. |
| 39 | hygiene | P3 | Makefile:1-25; корень репозитория | Makefile только для медиа (SVG/PNG/MP4), целей test и lint нет; bench.log и check_sprint4.py в git, в .gitignore есть дубли записей. |

## In progress

Остановился на чтении stationarity.py:40-79 и mfdfa.py:85-112; отчёт v3 до этого момента не записывался.

## Not verified

- Ничего не запускалось: ни одна находка не воспроизведена, #5 и #9 выведены из семантики срезов и арифметики float.
- shm.close() при живых numpy-views может бросать BufferError (pairs.py:247, 255, 390-391); тест на утечку есть (test_pairs.py:122), не запускался.
- Двойной unlink через resource_tracker в воркерах на Python < 3.13 (pairs.py:359-360).
- Точные исключения при B=0 (SharedMemory size=0), seed=-1 и T=0 в pairs.py.
- Влияние float32 для суррогатов против float64 для C_obs (pairs.py:186, 236, 363) на p-value.
- Детерминизм n_jobs=1 против n_jobs=8 (в тестах только n_jobs=2, test_pairs.py:47).
- Устойчивость test_pure_noise_all_noise (test_pairs.py:70) к смене версии numpy и поток Generator.
- Пригодность requirements.lock (Python 3.13) на Python 3.10 и 3.11.
- Предупреждения Node.js в CI для checkout@v4 и setup-python@v5.
- Генерация numpy>=1.24 (pyproject.toml:34) против Generator.spawn (cross_correlation.py:197), возможно требуется 1.25.
- Влияние линейной интерполяции длинных пропусков на автокорреляцию и кросс-корреляцию (preprocessing.py:59-67).
- Утверждение «block_size обычно >= IAT» (block_bootstrap.py:73-74).
- Величина эффекта #7 (time_shift с Fisher-весами) и #1 на реальных выходах.
- Содержимое opencode.json в истории и факт ротации ключа.
- Не читались: residuals.py, confounders.py, visualization.py (кроме vmin/vmax), data/scripts/*, unified_schema.json, docs/methodology.md (незакоммиченный diff), mfdfa.py (параметры), mantel.py:178+.
- Время выполнения и скорость (README: 15.72 s) не измерялись.
