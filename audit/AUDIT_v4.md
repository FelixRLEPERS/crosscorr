# CrossCorr — аудит v4

## 0. Мета

- Дата: 2026-10-06.
- HEAD: `72e13a24ee70d4764a1c5e927f84f4481cf7436e`.
- Ветка: `main`; рабочее дерево было чистым до создания отчёта.
- После базового HEAD v3 (`386c5c7`) в истории 11 последующих коммитов на
  текущем HEAD. Три коммита непосредственно расширения: `9aa3006` (формула),
  `616f1af` (классические аналоги), `72e13a2` (MI/TE/MSE/Cross-MFDFA).
  Семейные документы и git-чек-лист вошли в предшествующие им коммиты
  `bc2d865`, `8594df7`.
- Структура: 19 Python-файлов в `crosscorr_lib/analysis/`, 31 тестовый файл,
  8 Markdown-файлов в `docs/`, 17 Markdown-файлов в `audit/`, 3 Python-скрипта
  в `scripts/`.
- Тестовый базис до расширения: 237 collected (235 fast + 2 slow), по журналу
  предыдущей сессии 257 passed после добавления 22 тестов. В текущем аудите
  pytest/ruff не запускались; цифры нового прогона не переутверждаются.
- `BACKLOG.md`, `PROJECT_STATE.md`, `STOP_DECISIONS.md` датированы 2026-10-06,
  но их HEAD/числа относятся к состоянию до последних коммитов. Новые модули
  и findings этого аудита в них не отражены. Считать эти файлы актуальным
  снимком текущего HEAD нельзя без последующей синхронизации.

PHASE 0 DONE.

---

## 1. Новые модули (4 файла)

Severity в этом отчёте означает приоритет проверки/исправления, не
утверждение о публикационной несостоятельности всех результатов.

### 1.1 `crosscorr_lib/analysis/mutual_info.py`

| # | класс | severity | file:line | проблема | fix |
|---|---|---|---|---|---|
| MI-1 | STAT | P1 | `mutual_info.py:83-103` | Формула соответствует KSG-1 для непрерывных данных: max-норма в совместном пространстве, eps — расстояние до k-го соседа без себя, маргинальные подсчёты используют тот же `p=inf`, оценка `ψ(k)+ψ(N)-mean(ψ(nx+1)+ψ(ny+1))`. Но tie/duplicate policy отсутствует: при одинаковых/квантованных точках eps может быть 0; непрерывная KSG-оценка для дискретных повторов неприменима напрямую. | NEW: документировать предположение непрерывных распределений; определить deterministic tie handling либо отклонять дискретные ties; добавить тест на квантованный ряд. |
| MI-2 | BUG | P2 | `mutual_info.py:29-39,75-80,124-130` | NaN интерполируется, но all-nonfinite возвращается как NaN-массив и затем передаётся в cKDTree. `k` и `base` не валидируются (`k<=0`, `base<=0`/`base==1`). Неравные длины молча обрезаются по min, хотя docstring обещает равные. | NEW: строгая проверка k>=1, base>0/base!=1, конечности после подготовки; выбрать и документировать политику длин (ValueError предпочтительнее молчаливого truncation). |
| MI-3 | PERF | P2 | `mutual_info.py:94-97,142-147,176-185` | Для каждой точки выполняются Python-вызовы `query_ball_point`; матрица повторно строит деревья для каждой пары. На N=4000 и десятках колонок стоимость может быть высокой. Runtime не измерялся (запрещено запускать тесты/бенчмарки). | NEW: benchmark на N=4000 и 10/50 каналов; рассмотреть пакетный `query_ball_point`/return_length и ограничение параллелизма только после baseline. |
| MI-4 | TEST | P2 | `tests/test_E_mutual_info.py:19-79` | Есть независимые гауссианы, нелинейный сигнал, Gaussian analytic reference и симметрия матрицы. Нет тестов пустого/all-NaN, unequal lengths, k/base границ, ties и float32; CMI проверен только сравнением с MI при независимом Z. | NEW: добавить перечисленные edge tests и эталон CMI на известном совместном распределении. |

**Статус:** основной KSG-1 путь для непрерывных данных выглядит структурно
верным; безопасная обработка ties/невалидных параметров требует уточнения.

### 1.2 `crosscorr_lib/analysis/transfer_entropy.py`

| # | класс | severity | file:line | проблема | fix |
|---|---|---|---|---|---|
| TE-1 | STAT | P1 | `transfer_entropy.py:83-107` | Для k=1 временное выравнивание после исправления `y_next=ya[span:]` соответствует `I(Y_{t+1}:X_t|Y_t)`. Для k>1 код НЕ оценивает совместную CMI между полными историями: вычисляет k отдельных `I(Ynext:X_history_j|Y_history_0)` и усредняет. Это иная величина, теряющая взаимодействия/синергию, и слово «консервативная» не подкреплено теоремой. | NEW: либо ограничить API k=1, либо реализовать и проверить multivariate Frenzel–Pompe estimator для полной истории X и Y. Убрать «консервативная» до доказательства. |
| TE-2 | BUG | P1 | `transfer_entropy.py:30-39,74-91` | TE не применяет NaN policy MI/preprocess: NaN пройдут в CMI/cKDTree. Неравные ряды молча обрезаются. `k`, `lag`, `k_nn` не валидируются на положительность; lag=0 и отрицательные параметры могут дать неверное выравнивание/ошибки низкого уровня. | NEW: единая finite-input policy; валидировать `k>=1`, `lag>=1`, `k_nn>=1`; unequal lengths явно отклонять или документировать align. |
| TE-3 | PERF | P2 | `transfer_entropy.py:110-137` | Матрица рассчитывает N*(N−1) направленных оценок; каждая строит несколько KDTree и pointwise neighbor counts. Для 50 рядов это 2450 оценок; затратность на N=4000 неизвестна. | NEW: benchmark реального типичного размера и документация ожидаемой стоимости; не обещать production-scale до измерения. |
| TE-4 | TEST | P2 | `tests/test_E_transfer_entropy.py:29-60` | Тесты независимости и авторегрессионной направленности полезны, но нет тестов lag>1, k>1, NaN/empty/unequal length и closed-form CMI Gaussian VAR(1). Матрица проверена только на одной паре. | NEW: добавить boundary tests и численный reference для VAR(1); k>1 тест после TE-1. |

**Статус:** Schreiber definition задана правильно; реализация обоснована для
k=1, но k>1 — отдельная, пока неэквивалентная оценка.

### 1.3 `crosscorr_lib/analysis/mse.py`

| # | класс | severity | file:line | проблема | fix |
|---|---|---|---|---|---|
| MSE-1 | BUG | P1 | `mse.py:67-74,87-93` | При константном ряде `std=0`, значит default `r=0`; функция возвращает `inf` до подсчёта шаблонов (`:71-74`). При обычной SampEn-конвенции с расстоянием `<=r` все m- и (m+1)-шаблоны совпадают, A=B и SampEn=0. Текущий код не документирует альтернативную конвенцию и выдаёт бесконечность для валидного предельного сигнала. Кроме того, A=0 также возвращается как inf. | NEW: определить стандартное поведение для constant/zero-tolerance; тестировать constant series, A=0, B=0; при нулевой variance возвращать согласованное значение либо явный missing marker. |
| MSE-2 | BUG | P2 | `mse.py:25-35,67-73,132-140` | all-NaN после helper остаётся NaN и может дойти до cKDTree; `m<=0` и `r` nonfinite не валидируются. Для масштаба s>len(x) возвращается NaN — это допустимо, но не является ошибкой/предупреждением и может скрыть недостаточную длину. | NEW: finite/m/r validation; явно задокументировать NaN для недоступных масштабов. |
| MSE-3 | STAT | P2 | `mse.py:71-73,104-140` | Если r=None, r=0.2*std(coarse) пересчитывается на каждом масштабе. Это вариант MSE, но сравнение масштаба смешивает сложность процесса и меняющийся порог; классический вариант часто фиксирует r относительно исходной серии. | NEW: явно назвать convention; опционально поддержать `r` fixed-from-original, сохранив совместимость/документировав оба варианта. |
| MSE-4 | TEST | P2 | `tests/test_E_mse.py:19-62` | Белый шум эталон SampEn≈2.2 с atol=0.2 зависит от finite N/seed и метода; тест использует общий seeded fixture, но обоснование допуска не приведено. Проверка периодической MSE сравнивает s=50,100 с s=10, а не доказывает локальный пик. Нет NaN, constant, s>n, invalid m/r. | NEW: документировать finite-sample rationale для atol; тестировать scale peak локально и edge cases. |

**Статус:** алгоритмический скелет соответствует Costa-style coarse-graining,
но r-per-scale convention и edge outputs нуждаются в явном контракте.

### 1.4 `crosscorr_lib/analysis/cross_mfdfa.py`

| # | класс | severity | file:line | проблема | fix |
|---|---|---|---|---|---|
| XM-1 | STAT | P1 | `cross_mfdfa.py:43-67,111-129` | `_detrended_cov` фактически формирует локальные кросс-ковариации. Далее `F_q` использует signed moments, но `:128-129` берёт модуль результата по каждому scale, стирая cancellation/sign. Для cross-correlation scaling, где сегменты могут иметь разнонаправленную ковариацию, это меняет статистику; формула в docstring/реализации не привязана к точной версии MF-DXA. | NEW: выбрать точное определение Podobnik–Stanley/Zhou, зафиксировать sign/cancellation convention, сверить с reference implementation, добавить x/y и x/−y эталоны. |
| XM-2 | STAT | P1 | `cross_mfdfa.py:121-139` | q=0 применяет `exp(0.5*mean(log(abs(covs))))`, корректный геометрический предел лишь при конкретной трактовке `F_xy^2`; `abs` удаляет знак и затем `tau=q*h-1` применяется к cross exponent без обоснования в коде. Тест q=0 проверяет только h≈1 на синтезированном pink noise. | NEW: вывести предел q→0 из выбранной формулы, сравнить q=±ε с q=0; верифицировать tau_q для q=0 reference. |
| XM-3 | STAT | P2 | `cross_mfdfa.py:131-174` | `h(q)` получен OLS от log F против log scale; `f(alpha)` — Legendre transform. Формулы структурно знакомы, но нет goodness-of-fit, scale-window diagnostics и reference-spectrum comparison. `max(f)≈1` на x=y белом шуме — слабая проверка нормировки, не подтверждение всего спектра. | NEW: вернуть fit diagnostics (R²/число масштабов) либо отдельно проверить линейность; сравнить с проверенной MFDFA reference для x=y и synthetic multifractal signal. |
| XM-4 | BUG | P2 | `cross_mfdfa.py:97-106,112-139` | Входы усекаются до min длины; NaN/Inf не обрабатываются. `q_values` может быть пустым/nonfinite; scales могут быть <=0, дублированными или слишком крупными. `_default_scales` корректен лишь при валидных n; custom scales с <3 валидными точками дают h=NaN без причины в результате. | NEW: выбрать равные длины vs align, конечность проверять, валидировать q/scales; вернуть диагностику/ясную ошибку для пустого fit. |
| XM-5 | PERF | P2 | `cross_mfdfa.py:58-67,113-129` | Два `np.polyfit` на каждом сегменте каждого масштаба; N=4000×десятки scale — Python nested loops. Runtime для типичных сенсорных серий не измерялся. | NEW: benchmark N=4000; линейный fit можно вычислять закрытой OLS-формулой на центрированном t без повторного `polyfit`. |
| XM-6 | TEST | P2 | `tests/test_E_cross_mfdfa.py:34-76` | Все содержательные тесты берут x=y, поэтому не проверяют genuinely cross-свойство, знак и независимость. Розовый шум генерируется random-phase спектральным методом; тест один фиксированный seed. | NEW: добавить x≠y known-coupling, independent, anti-correlated x/−x, NaN/unequal length/q=0 limit; один seed не доказывает robustness. |

**Статус:** module self-contained, но является независимой реализацией
критичной формулы; до reference cross-check нельзя считать публикационно
валидированной.

PHASE 1 DONE.

---

## 2. Интеграция новых модулей с pipeline

- Новые модули **не экспортируются** через `crosscorr_lib/__init__.py` или
  `analysis/__init__.py`. Это согласуется с правилом в `analysis/__init__.py:3-5`
  «реэкспортируются только нужные символы»: модули доступны импортом
  `crosscorr_lib.analysis.<module>`, но не как верхнеуровневый API.
- Поиск call sites: новые production-модули вызывают только друг друга
  (TE → conditional MI); вызовов из `cross_correlation.py`, `pairs.py`,
  `power_curve.py`, scripts/ или data/ нет. Это набор standalone utilities,
  не интеграция с main analysis pipeline. Это само по себе не дефект, если
  явно считать их experimental/opt-in.
- `mutual_information_matrix` и `transfer_entropy_matrix` принимают pandas
  DataFrame и возвращают DataFrame. MSE matrix тоже DataFrame. xarray не
  поддержан и не требуется заявленным контрактом.
- Новые файлы не меняют публичный `__all__`, как и требует ограничение
  предыдущей задачи. Это означает, что API существует по module path, но
  пока нет стабильной гарантии API/версирования.

### Расширенная формула vs реализация

| Символ | Документация/код | Статус аудита |
|---|---|---|
| τ | lagged cross-correlation в `analysis/cross_correlation.py` | реализовано |
| d | Mantel и distance analysis | реализовано, но не определяет pairwise-distance колонку в основном max-stat output автоматически |
| f | wavelet coherence | не найдено в исходниках/roadmap на текущей ревизии — roadmap/placeholder |
| s | MSE есть как utility; cross-MFDFA есть как utility | не интегрировано в основной pipeline; standalone |
| g | confounders Kp/Dst/F10.7 | функции удаления есть, но условное вычисление C(…|g) не реализовано как единый estimator |
| w | внешний скрипт `scripts/simulate_snapshots.py` создаёт 12 snapshots | не параметр core pipeline/API; визуализационный эксперимент |
| effect | `C_obs`, `rho_max` в разных путях | отдельного согласованного поля effect size нет |
| CI | bootstrap module существует | доверительные интервалы для основного estimand в output отсутствуют |
| robustness/sensitivity | power curve/снапшоты частично измеряют устойчивость | единая sensitivity/robustness процедура не подключена к основному output |

Finding DOC-1 — DOCS, P2, NEW: `docs/methodology.md:75-103,139-153` помечает
`lagged_cc`, `windowed_stability`, `distance_dependence` как реализованные, но
эти имена не подтверждены как публичные функции единого pipeline по текущему
поиску. `w` существует в отдельном генераторе snapshots, а не как pipeline
параметр. Таблица должна различать «есть отдельный инструмент» и «включено в
основной анализ», иначе читатель воспринимает все оси как реализованные.

PHASE 2 DONE.

---

## 3. Документация vs код

### `docs/methodology.md`

- Новая секция честно утверждает, что библиотека не квантовая, и прямо
  запрещает перенос метафор RT в сенсорный контекст — это сильная редакционная
  часть.
- DOC-5 (DOCS, P2, `docs/methodology.md:180-186`): quantum↔classical таблица
  помечает Shannon mutual information, transfer entropy, MSE и Cross-MFDFA как
  «запланировано», хотя соответствующие модули теперь существуют. Это
  документальная рассинхронизация; точнее указать «реализовано как standalone
  utility, не интегрировано в основной pipeline».
- Расхождение DOC-1 выше: статусы осей смешивают standalone utility,
  experiments и core integration.
- `w — многоснапшотный анализ реализовано`: snapshots — отдельный генератор и
  AE-артефакт, не включённый в `crosscorr_lib` API/pipeline. Квалифицировать
  как «внешний эксперимент», не core.
- «MERA scale axis» и «entanglement log-scaling» остаются аналогиями. В тексте
  это названо аналогом, но для научной публикации стоит повторять, что это
  analogy only, не физическая эквивалентность.

### `docs/roadmap.md`

- На дату HEAD roadmap «актуально на 2026-10-06», но ближайшие задачи всё ещё
  говорят «добавить docs/academy/» и `CONTRIBUTING.md`, которые уже существуют
  (`docs/roadmap.md:26-28`). Это конкретный stale roadmap finding.
- Порог покрытия 53→70%, реальные данные, Zenodo и детские PR — явные
  направления; сроков в календарных кварталах нет, только интервалы, это
  приемлемо для семейного roadmap.
- Новые четыре меры в roadmap не внесены; предыдущая задача запрещала менять
  roadmap. Теперь требуется обновить статус/приоритет отдельным коммитом.

### `docs/academy/README.md`

- Возрастное разделение и конкретные файлы/команды есть; большая часть
  задач выполнима.
- `docs/academy/README.md:59-63` предлагает создать
  `tests/test_safe_exec.py`; файл отсутствует на HEAD (подтверждено `ls`).
  Это корректно как новая задача, не broken reference.
- `docs/academy/README.md:69` ожидает fixture `rng`; она определена в
  `tests/conftest.py`, поэтому технически выполнимо.
- Риск: добавление строк в CSV не гарантирует тестовую валидность — формат и
  schema должны соблюдаться; task говорит «поменять время/значения», не
  предупреждает про обязательные поля/уникальность.

### `CONTRIBUTING.md`

- PR workflow и запреты на ядро/инфраструктуру изложены ясно.
- Команда советует оба запуска: pytest + ruff; новичкам может потребоваться
  помощь с venv/dependencies, но `pyproject.toml` и README содержат установку.
- Указывает Макару `visualization.py`, но его роль/зона чуть шире в README;
  существенного конфликта нет.

### `docs/academy/git_checklist.md`

- Все 12 разделов присутствуют, однако две технические формулировки требуют
  исправления:
  - `:257`: `git restore <файл>` не откатывает уже staged изменения; для них
    нужен другой шаг. Формулировка «откатить до сохранённого» двусмысленна.
  - `:261`: `git log` показывает committed history, но не гарантирует
    восстановление uncommitted/force-pushed данных; «ничего не потеряно» —
    чрезмерное обещание.
  - `:262`: «можно перезаписать свою ветку» рискованно для детей и не уточняет
    запрет force-push на shared branches. Для семейного чек-листа безопаснее
    сказать «остановись и позови Алексея», а не общую санкцию на overwrite.
- Branch tree соответствует `feature/`, однако examples `fix/papa-...`,
  `docs/mama-...` не совпадают с таблицей команды, где рекомендуется имя
  «Алексей»/«Мама»; только косметический consistency issue.

### `README.md`

- На текущем HEAD `README.md:475` всё ещё говорит «более 150 тестов», тогда как
  актуально 257. Строки 461–464 перечисляют реальные data run как незавершённые;
  это согласуется с STOP A9–A11.
- README таблица статуса содержит 0-level/feature claims и не перечисляет
  четыре новые standalone measures (ожидаемо, но нужно решить — публиковать ли
  их как experimental).
- Ссылки на новую methodology/academy/fund/CONTRIBUTING проверены statically
  ранее; полную link-suite не запускаю (pytest запрещён).

PHASE 3 DONE.

---

## 4. Тесты новых модулей

Новые тестовые файлы: 4; тестов по предыдущему прогону: 22. Все тестируют
численные свойства, но покрытие границ неоднородно.

| Модуль | Сильные проверки | Пробелы | Flaky-риск |
|---|---|---|---|
| MI | независимый MI≈0; Gaussian analytic `-0.5 ln(1-rho²)`; нелинейное x²; симметрия matrix; CMI≈MI при независимом Z | NaN/all-NaN, empty, unequal lengths, k/base validation, quantized ties | Низкий: фиксированный `rng` fixture и допуск 0.05/0.15; `rng` seed смотреть в `conftest` |
| TE | независимые пары; направленный source→target; asymmetric matrix; self finite | lag>1, k>1 (особенно с текущим покомпонентным estimator), NaN, unequal length, known Gaussian VAR reference | Низкий/средний: строгие `<0.05`, `>3x` зависят от fixed fixture/seed, нужно проверить запас к порогам без запуска тестов нельзя |
| MSE | SampEn white-noise reference ≈2.2; periodic; white MSE rough-flat; matrix shape | constant/A=0/B=0 convention, NaN, scale>n, m/r invalid; «flat <0.6» и периодические comparisons — эмпирические пороги без CI/reference обоснования | Средний: white-noise `max-min <0.6` может зависеть от seed/N; sample entropy finite-size variation |
| Cross-MFDFA | h white≈0.5, random walk≈1.5, pink≈1.0; F positive/increasing; spectrum max≈1 | все основные случаи x=y; нет independent/cross coupling/anti-correlation, q→0 continuity, NaN/scales validation, reference MF-DFA | Низкий-средний: pink noise один фиксированный seed, tolerances 0.08–0.15 без confidence study |

Особенно важная точность: задание просило h(q=0)≈1 для белого шума и ≈0.5
для 1/f. Тесты исправили это на стандартные DFA значения (белый 0.5,
1/f 1.0), что корректно. Но cross-MFDFA — это не автоматически одиночный DFA;
для публикации нужен reference comparison именно к выбранному cross-DFA
определению.

Непроверенные входы четырёх модулей: пустые массивы, все NaN, бесконечности,
несовпадающие длины, float32, отрицательные/нулевые k/lag/scales/base.
`mutual_info.py` и `mse.py` пытаются интерполировать NaN, TE и Cross-MFDFA —
нет; это конкретная inconsistency, не общий совет.

PHASE 4 DONE.

---

## 5. UNVERIFIED и STOP из v3

Проверка статическая по текущим исходникам и CI config; без реальных данных,
разных Python runners и пользовательских решений некоторые статусы нельзя
закрыть.

### UNVERIFIED

| ID | Статус сейчас | Можно ли закрыть сейчас | Что блокирует |
|---|---|---|---|
| B19 | `UNVERIFIED` (BACKLOG) | частично: статический механизм текущего кода читаем, но статистическую зависимость p-value статически доказать нельзя | нужны Monte Carlo simulation с заранее заданной мощностью/CI, не только корреляция малой выборки |
| C8 | `UNVERIFIED/STOP` | частично | float32 surrogate vs float64 observation виден в `pairs.py` worker storage; влияние на p/verdict требует контролируемого precision experiment |
| C9 | `UNVERIFIED/STOP` | нет только чтением | resource_tracker двойной unlink нужно проверить на Python 3.10–3.12 Linux/Windows |
| C10 | `UNVERIFIED/STOP` | частично | жизненный цикл shared-memory views виден, но наличие BufferError зависит от runtime/worker exit; нужен reproducible test |
| F20 | `PARTIAL` (Backlog) | статически частично | numpy>=1.25 сейчас; минимальная версия для Generator.spawn требует version matrix/документации upstream |

Счётчики BACKLOG содержат UNVERIFIED=4 и PARTIAL=3; F20 относится к PARTIAL,
не к четырём UNVERIFIED.

### STOP — требует внешних данных или окружения

- A9/A10/A11: `data/raw` пусто/результат синтетический; требуются лицензированные
  реальные WSPR/INTERMAGNET/Horizons данные, затем `unify_schema.py` и analysis.
- E6, C9: нужны Windows и Python 3.10–3.12 runner/logs; Windows CI currently
  informational (`continue-on-error`).
- F1: lock помечен как pip-compile no-index, отсутствует joblib по реестру; для
  воспроизводимой генерации нужен доступ к совместимым пакетам/выбранному Python.

### STOP — решение пользователя/архитектура

- B18/B20/B25/B26/B27/B29/B30/B39, C8/C10: требуют научного решения о методе,
  множестве гипотез, null model, dtype, или preprocessing; нельзя закрыть одним
  статическим чтением.
- D5: git tag `v0.1.0` — git write/релизное решение.
- D6/D7: судьба игрового кода; сейчас уже имеется `game/README.md`, но backlog
  статусы не синхронизированы после новых коммитов.
- D8: mypy — решение о введении нового quality gate.
- F14: выбрать единственный source of truth зависимостей.
- F18: удалить/сохранить `bench.log`, `check_sprint4.py` — владелец решает.
- G11–G14: сам файл README_ARCHITECTURE_UPDATE.md удалён коммитом Queue 1; эти
  STOP фактически закрыты, но BACKLOG остаётся OPEN/STOP (не обновлялся).
- D5 также устарел: `git tag --list` показывает `v0.1.0`; решение/действие уже
  выполнено после STOP_DECISIONS, но BACKLOG/STOP_DECISIONS не синхронизированы.
- G22–G25: изменения Queue 2 уже в коде (константы, MIN_SAMPLES, E302, 2D
  symmetry guard); BACKLOG ещё помечает их STOP — статус устарел.
- D9/D10/D12, F18, E6, B35: Queue 1/2 закрывали часть, но реестр не синхронен.

### Queue 3/4 из STOP_DECISIONS

Queue 3 содержит A9–A11 и статистические/архитектурные пункты B18/B20/B23/
B25–B30/B39, E6, F1: часть заблокирована внешними ресурсами, часть ожидает
решения метода. Queue 4 F14 (единый dependency source) — можно отложить без
прямой ошибки выполнения, но мешает reproducible install. Точный текущий
статус по файлам нельзя считать синхронизированным из-за устаревшего HEAD в
аудитных документах.

PHASE 5 DONE.

---

## 6. Инфраструктура

### pyproject / зависимости

- `requires-python >=3.10`; runtime включает numpy>=1.25, scipy>=1.10,
  pandas>=2, joblib, pyarrow. Новые модули используют существующие numpy,
  scipy (`cKDTree`, `digamma`) и pandas — новых зависимостей нет.
- Extras `astro`, `bayes`, `mfdfa`, `game`, `dev`, `all` разделены.
- F14 остаётся: `requirements.in` и `requirements.lock` существуют параллельно
  с pyproject. Lock заголовком говорит `pip-compile --no-index` под Python 3.13;
  `.lock` не следует считать универсальным lock для CI 3.11/3.12 до проверки.
- `mypy` по-прежнему не настроен. Тесты/ruff не были запущены в этом аудите;
  версии dependency freshness/security не проверялись (pip-audit не запускался).

### CI

- Matrix fast Python 3.11+3.12; slow Python 3.12; Windows Python 3.12 с
  `continue-on-error: true`.
- Coverage gate 45%, ниже последнего известного локального 53%; разумно как
  временный floor, но не защищает рост регрессии выше 45.
- Ruff охватывает `crosscorr_lib/ tests/ scripts/ data/`; compileall есть.
- Paths-filter для slow не перечисляет новые тестовые файлы MI/TE/MSE/Cross-MFDFA
  отдельно. Но все новые модули лежат в `crosscorr_lib/analysis/**`, поэтому
  изменение production module включает slow job; изменение только нового test
  без analysis может не запускать slow job (fast job всё равно запускается).
- Исторический runner outage из PROJECT_STATE (3.11/slow не acquired) — это
  исторический факт; текущий статус GitHub Actions в этом аудите не запрашивался.

### .gitignore / coverage

- Игнорируются `results/`, `aep/`, parquet, mp4/mp3, `.coverage`, htmlcov,
  `.env`, `opencode.json`; `.aep` покрывается `aep/`.
- `audit/` намеренно НЕ игнорируется (`#audit/`), поэтому служебные verify
  скрипты и audit trail остаются tracked. Это может быть осознанно, но шумит
  в репозитории.
- `.coverage_report.txt` tracked и не в `.gitignore` (подтверждалось предыдущей
  инспекцией; проверить актуальность отдельным git status/ls-files перед чисткой).
- Coverage 53% — последнее подтверждённое значение до новых модулей; новый
  coverage не запускался в этом аудите.

PHASE 6 DONE.

---

## 7. Семейная модель

- Стратегия Г явно формулируется как «наука + обучение + портфолио детей» в
  `docs/roadmap.md:3`; роли и возраста повторяются в README/CONTRIBUTING.
- `docs/academy/README.md` даёт задачи и проверки для Егора (11) и Макара (13).
  Конкретные файлы существуют, кроме запланированного `tests/test_safe_exec.py`
  (отсутствует, что допустимо для future task).
- `CONTRIBUTING.md` задаёт автор→peer-child→Алексей→merge, защищает core/CI и
  запрещает секреты. В целом возрастно-адекватно.
- Риск git-чек-листа: `git restore <файл>` не откатывает staged содержимое;
  «git log найдёт старую версию, ничего не потеряно» неверно для uncommitted/
  force-pushed данных; разрешение overwrite своей ветки нужно ограничить.
  Это конкретный DOCS finding, low-to-medium severity из-за потери данных.
- README и Fund: Fund вынесен в docs/fund.md как отдельное направление, что
  соответствует методологическому предупреждению не смешивать научное ядро,
  образовательную игру и crypto concept. При этом README всё ещё содержит
  большой Fund link/план — научному positioning можно уделить отдельный edit.
- Семейная модель не размывает научное ядро сама по себе: проблемы возникают,
  когда roadmap/README маркируют экспериментальные аналоги как реализованные
  свойства основного pipeline.

PHASE 7 DONE.

---

## 8. Новые P0/P1

### P1

1. **TE k>1 — неверная целевая статистика** (`transfer_entropy.py:98-107`):
   покомпонентное усреднение CMI не равно joint-history TE. Ограничить k=1
   или реализовать full multivariate estimator до публикационного применения.
2. **Cross-MFDFA sign/definition risk** (`cross_mfdfa.py:111-139`): модуль
   берёт abs signed cross-fluctuation и не cross-reference-tested; может
   уничтожить sign cancellation. Нужна сверка формулы и anti-correlation test.
3. **KSG undefined edge contracts** (`mutual_info.py:29-39,75-80`; TE аналогично):
   all-NaN, ties, k/base/lag validation, unequal-length truncation. Для данных
   с квантованием это реальный statistical robustness risk.

P0: новых P0 не установлено по статическому аудиту.

---

## 9. Приоритезированные действия (топ-10)

1. Исправить/ограничить Transfer Entropy k>1; добавить joint-history reference.
2. Cross-MFDFA: выбрать одну опубликованную формулу, сохранить знак, сверить
   x=y, x=-y, independent и q→0 с reference implementation.
3. Зафиксировать входной контракт MI/TE/MSE/Cross-MFDFA: NaN/all-NaN,
   unequal lengths, ties, dtype, invalid k/r/base/scales.
4. Добавить численные тесты на дискретные/tied данные и крайние параметры.
5. Benchmark новых методов при N=4000 и матрицах 10/50 датчиков; описать
   память/runtime. Не включать в production pipeline до baseline.
6. Переименовать статус в methodology: «standalone utility», «core integrated»,
   «planned»; `w` snapshots не core parameter, `s` MSE/Cross-MFDFA standalone.
7. Обновить `docs/roadmap.md`: убрать уже выполненные academy/CONTRIBUTING items,
   выбрать, входят ли MI/TE/MSE/Cross-MFDFA в ближайшую научную ветку.
8. Синхронизировать audit backlog/project state с текущим HEAD; учесть Queue
   1/2 закрытия и четыре новых модуля. Не переоткрывать старые CLOSED findings.
9. Обновить README «более 150 тестов» до проверенного актуального числа и
   пометить четыре новых метода как experimental/standalone.
10. После пользовательского решения о `research/`: вариант A — папка research
    для экспериментов, B — отдельный `crosscorr-quantum`, C — не создавать.

---

## 10. Что осталось на v5

- Reference-валидация KSG/CMI и полная multivariate TE.
- Cross-MFDFA formula, sign convention, q=0 limit и внешний reference check.
- Sensitivity/edge tests для NaN, ties, unequal lengths, invalid params.
- N=4000 performance measurements и memory profile.
- Новые модули — pipeline integration decision, exports/public API decision.
- Реальные WSPR/INTERMAGNET данные и пересчёт A9–A11.
- Проверка Windows shared-memory C9/C10 на поддерживаемых Python.
- Выбор по research/ (A/B/C) и синхронизация audit ledger.

---

## Классификация findings v4

| ID | класс | severity | статус | Кратко |
|---|---|---|---|---|
| MI-1 | STAT | P1 | NEW | KSG ties/discrete observations undefined |
| MI-2 | BUG | P2 | NEW | NaN/k/base/length validation |
| MI-3 | PERF | P2 | NEW | pointwise KDTree range queries; no benchmark |
| MI-4 | TEST | P2 | NEW | edge/ties/CMI reference gaps |
| TE-1 | STAT | P1 | NEW | k>1 component-wise average is not joint TE |
| TE-2 | BUG | P1 | NEW | NaN/length/k/lag validation inconsistent |
| TE-3 | PERF | P2 | NEW | N*(N-1) expensive KSG estimates, unbenchmarked |
| TE-4 | TEST | P2 | NEW | k>1, lag>1, boundary/reference gaps |
| MSE-1 | BUG | P1 | NEW | constant input returns inf at r=0; SampEn boundary unspecified |
| MSE-2 | BUG | P2 | NEW | all-NaN / invalid m,r / coarse-scale contract |
| MSE-3 | STAT | P2 | NEW | r recomputed per scale changes MSE convention |
| MSE-4 | TEST | P2 | NEW | empirical thresholds and missing edge tests |
| XM-1 | STAT | P1 | NEW | abs of signed cross-fluctuation may alter MF-DXA definition |
| XM-2 | STAT | P1 | NEW | q=0 limit/sign convention not reference-validated |
| XM-3 | STAT | P2 | NEW | h/tau/Legendre transform lacks reference diagnostics |
| XM-4 | BUG | P2 | NEW | NaN, unequal lengths, invalid q/scales silently accepted |
| XM-5 | PERF | P2 | NEW | nested polyfit per segment/scale, unbenchmarked |
| XM-6 | TEST | P2 | NEW | tests x=y only; no cross-specific behavior |
| DOC-1 | DOCS | P2 | NEW | formula status confuses standalone and integrated axes |
| DOC-2 | DOCS | P2 | NEW | roadmap still lists Academy/CONTRIBUTING as todo |
| DOC-3 | DOCS | P3 | NEW | README test count is vague (>150 vs 257 known) |
| DOC-4 | DOCS | P2 | NEW | git checklist recovery commands overpromise safety |
| DOC-5 | DOCS | P2 | NEW | quantum-classical table still marks implemented modules as planned |

## Замечание о v3 STOP и статусе реестра

На HEAD v4 backlog не синхронизирован: BACKLOG показывает 34 STOP и старые
Queue 1/2 items. По истории HEAD `a7c8a0c` закрывает Queue 1, `f730ddd`
закрывает Queue 2; README_ARCHITECTURE_UPDATE.md удалён. Кандидаты G22/G23/G24/
G25/B35 изменялись этими очередями, но audit/backlog status не обновлён. Не
помечать остальные STOP автоматически закрытыми: например B18/B20/B25/B26/B27/
B29/B30/B39 и A9–A11 всё ещё требуют решения/данных; F1/F14/F18 требуют
решения по deps/repo hygiene. C8/C9/C10 требуют runtime/precision проверки.

Статусы здесь классифицированы как `UNVERIFIED_FROM_v3` только если опираются
на v3 unresolved item; новые findings помечены NEW. В BACKLOG их не записывал.
