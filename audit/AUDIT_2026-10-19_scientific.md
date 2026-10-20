# Scientific audit — CrossCorr, 2026-10-19

Полный научный аудит: статья (`paper/`), презентация
(`docs/presentations/hamsci_2026-11-05/`), результаты (`results/`),
код (`crosscorr_lib/`, `scripts/`, `data/scripts/`), тесты/CI,
документация и гигиена репозитория.

Проверяющий: агент (сессия 2026-10-19). Метод: чтение исходников,
независимая перереализация ключевых чисел из `data/processed/unified.parquet`
и `results/*.parquet`, запуск `ruff`/`mypy`/`pytest`, визуальный разбор
всех 5 рисунков.

Ничего в `paper/`, `audit/`, `results/` не изменялось (только чтение).
Отчёт добавлен как новый файл.

---

## 0. Итог одной строкой

Ядро научного результата **воспроизводится точно** и statistically
состоятельно, но в рукописи есть **три дефекта уровня пре-сабмита**:
(1) перевёрнутый вывод §5.3 про percentage vs absolute; (2) набор
claim strength/keypoint, не выдерживающий проверки на 15 m и на Dst;
(3) два рисунка (Fig 2 и Fig 4) заявляют 95% CI, которых на графике нет.
Ниже — полный список с `file:line`, доказательствами и приоритетами.

---

## 1. Что воспроизведено (зелёная зона)

Пересчёт из `data/processed/unified.parquet` (скрипт-реплика логики
`scripts/perm_test_18mo_3band.py`) даёт **побитово те же** числа статьи:

| Величина | Статья | Воспроизведено |
|---|---|---|
| N эпох/полосу | 4 349 | 4 349 |
| N storm / quiet | 198 / 3 035 | 198 / 3 035 |
| quiet-mean 20/40/15 m | 73 718 / 67 105 / 13 386 | совпадает |
| drop 20/40/15 m | −27.7 / −27.2 / −38.7 % | −27.70 / −27.25 / −38.68 % |
| Δ raw (Table 3/10) | −20 421 / −18 285 / −5 178 | совпадает |
| storm days / episodes | 76 / 58 | 76 / 58 |
| средняя длительность эпизода | ≈9 h | 9.0 h |
| Kp ≥ 7 | 38 эпох (114 h, 0.87 %) | 38 / 114 h / 0.87 % |
| cell occupancy | 4.3 | 4.31 |
| r(day_of_week, Kp) | −0.0087 | −0.00867 |
| var-reduction от dow | 12–16 % | 12.7 / 12.7 / 16.1 % |
| ρ₁ / ESS | 0.69–0.75 / 610-793-743 | 0.754/0.691/0.708 → 610/794/743 |
| Table 1: Kp records | 5 069 | 5 069 |
| Table 1: Dst records | 12 508 | 12 508 |
| Dst < −50 / > −20 / mid | 471 / 8 811 / 3 226 | совпадает |
| mean/min Dst | −11.5 / −96 nT | −11.46 / −96.0 |
| F10.7 range, Spearman | 131–246 sfu, r=+0.047 p=0.86 | 131.4–245.6, +0.0466 p=0.8591 |
| Fig 4 (day/night, все 6) | таблица 7 | `results/fig4_day_night.json` — совпадает |
| 8 месяцев «night>day» | 8 | 8 (проверено по месяцам) |
| Held-out drops 20/40/15 | −26.7 / −29.0 / −22.1 | −26.73 / −29.00 / −22.13 |
| Held-out Δ и CI | −22 482 / −26 287 / −3 627 + CI | совпадает |
| Held-out resid p | 2e-5 / 2e-4 / 8e-5 | превышения 0 / 9 / 3 из 50 000 |
| Binned drops (Fig 2, 15 m включительно) | 18.3/16.9, 33.6/34.4, 52.0/53.2, 28.6/50.7/58.9 | совпадает |
| BH по 9 pairwise | 5 significant, q=0.058/0.058/0.097/0.855 | пересчитано — совпадает |
| Сезон-контроль absolute-loss | (не проверялся в статье) | DJF-quiet 40 m на +26 % ниже held-out ⇒ рост сети остаётся объяснением |

Вывод: численное ядро статьи репродуцируемо и внутренне согласовано.
Проблемы — в формулировках, визуализации и трассируемости артефактов,
а не в самих результатах.

Инфраструктура: `ruff check .` — чисто; `mypy crosscorr_lib` — чисто;
`pytest -m "not slow"` — 288 passed, 2 deselected; coverage 58 %
(fail-under=45 в CI). CI зелёный по конфигурации.

---

## 2. Блокеры (исправить до submission)

### B1. §5.3: перевёрнутый вывод «percentage vs absolute» — концептуальная ошибка
`paper/main.tex:1012-1022`

Текст: *«Percentage metrics are network-dependent: Percentage-based metrics
are unstable when the denominator (network size) changes over time.
Absolute spot loss per hour is a physically meaningful alternative...»*

Это **инвертировано**:
- percentage-drop = (storm − quiet)/quiet — величина, нормированная на
  текущий размер сети, т.е. по построению устойчива к росту сети;
- absolute loss (spots/h) масштабируется с размером сети.

Собственные данные статьи это подтверждают: при росте сети +35 %
percentage-drops почти не изменились (27.7→26.7, 27.2→29.0), а absolute
изменился на ratio 1.44. См. также abstract (`main.tex:82-84`) и
Plain Language Summary (`main.tex:82-84`), где **сказано правильно**:
«absolute number … is not stable …, whereas percentage drops remain a
usable monitoring metric». Т.е. §5.3 прямо противоречит abstract.

Затронуты также: `Q_and_A.md:134-142` (Q8), `speaker_notes.md:146`.
Правка обязательна и до выступления (слайд 6, notes).

### B2. Keypoints/abstract «scale-dependence» — числа справедливы только для 20/40 m
`paper/main.tex:29` (keypoint 2), `:44-46` (abstract), `:151-154` (intro #2),
`:587` (Table 4)

Написано «при Kp 5–6 ∼−18 %, при Kp ≥ 6 −42.8 %» и «∼−18 % … ∼−53 %»,
но для 15 m воспроизведено **−28.6 %** (Kp 5–6) и **−54.8 %** (Kp ≥ 6).
Table 4 (`tab:scale`) вообще содержит только 20 m и 40 m, хотя Fig 2 и
текст §4.2 оперируют 15 m (−50.7 / −58.9). Читатель/рецензент получает
неполную картину: «nearly doubles» верно для всех полос (1.9×/2.6×/1.9×),
но приведённые абсолютные значения — только 20 m (для −42.8) и 20/40 m
(для −18). Нужно либо указать полосу, либо дать полный набор.

### B3. Held-out «replicates on all three bands» для 15 m держится только на residual-тесте
`paper/main.tex:1169-1171` (conclusion 3), `:44-49` (abstract), `:29` (keypoint 2),
slides `slides.tex:172`, speaker_notes `:163-167`

Факты (артефакты `results/heldout_3band_2026-10-15.json`,
`results/heldout_resid_2026-10-15.json`):
- 15 m raw p = **0.258** (не значимо), raw 95 % CI **[−7 172, +3 738]** — включает 0;
- 15 m residual p = 8e-5 — значимо.

Дополнительная проверка чувствительности (выполнена здесь, блок-пермутация,
15 m held-out):

| baseline | Δ (spots/h) | p |
|---|---|---|
| raw | −3 627 | 0.26 |
| mean(month) | −3 060 | 0.37 |
| mean(hour_of_day) | −6 122 | 1.5e-4 |
| mean(month, hour) | −5 532 | 3.5e-4 |
| mean(month, hour, dow) | −5 146 | 1.0e-4 |

Т.е. значимость 15 m создаётся **только** снятием суточного хода, а
величина эффекта плавает в ~2 раза в зависимости от модели baseline.
Утверждение «replicates on all three bands» без оговорки «residual-based,
raw CI includes 0» — превышение силы claim. Статья оговаривает это в
§4.5 (`:797-801`), но abstract/keypoint/conclusion/slides — нет.

### B4. Keypoint 2 подразумевает репликацию scale-dependence — она не обеспечена
`paper/main.tex:29-30`, `:810-813`

Keypoint 2 ставит рядом «scale-dependent … replicated on all three bands
held-out». Репликация scale-dependence опирается на N_storm = 10 в бине
Kp 6–7 (§4.5, Table 9); сами Limitations (`:1068`) называют это
«directionally confirmed, not independently powered». Keypoint это
скрывает. Нужно развести: «primary effect replicates; scale-dependence
directionally consistent».

### B5. Dst p-значения не подкреплены артефактом; floor теста — 2e-4, не 2e-5
`paper/main.tex:447-450`, `:549-551` (Table 5), `:413-415`

- Table 5 заявляет для Dst `p = 2×10⁻⁵` по трём полосам.
- Единственный артефакт — `results/perm_test_18mo_3band_fdr.json`:
  `n_iter = 5000`, `p_raw = 0.0` (без add-one), `delta` — от другой модели
  residual (no-dow). При 5 000 итерациях add-one floor = **2×10⁻⁴**.
- Независимая репликация Dst-теста (здесь, `n_iter=5000`, add-one):
  0 превышений ⇒ p = 2.0e-4 для всех трёх полос; без add-one = 0.0.
  `delta` воспроизводится точно: −22 081.4 / −15 038.2 / −5 142.6.

Т.е. либо Dst-тест реально гонялся на 50 000 итераций, и это нигде не
зафиксировано, либо статья завышает разрешение p. Блокер до сабмита:
перегенерировать Dst на 50 000 с add-one, сохранить артефакт, иначе
писать 2e-4. `m5` в `docs/AUDIT_START_NEXT_SESSION.md:268-270` помечен
«stale/skip» — но именно этот артефакт питает Table 5, так что формально
он не «stale», а «отсутствует».

### B6. Dst-тест использует блок 24 ч, а Methods обещает 72 ч
`paper/main.tex:375-411` (block = 24 эпохи = 72 h), `:413-415`

Dst-ряд — **часовой** (`N = 12 508`, подтверждено), а в артефакте
`block_size = 24`. 24 строки часового ряда = **24 ч = один** суточный
цикл, а не три. Methods глобально утверждает «three full diurnal cycles» —
для Dst это неверно. На вывод не влияет (проверено: при block=72 результат
тот же — 0 превышений), но описание метода некорректно и должно быть
исправлено явной оговоркой.

### B7. «42 storm events» для Dst не воспроизводится
`paper/main.tex:283`

Пересчёт: gap > 12 h ⇒ **48** эпизодов (полностью совпадает с пометкой
`docs/AUDIT_START_NEXT_SESSION.md:271-272`); gap > 24 h ⇒ 41; runs ⇒ 96.
Ни одно правило не даёт 42. Число осталось в §2.2. Источник — старая
`docs/first_result.md:130`. Удалить/исправить.

### B8. «2.4× more storm samples (471 vs 198)» — сравнение разных единиц
`paper/main.tex:282-285`

471 — это **часы**, 198 — **3-часовые эпохи** (= 594 ч). По штормовым
часам Dst-выборка (471 ч) **меньше** Kp-выборки (594 ч), а не в 2.4 раза
больше. Аналогично «2.9× larger total sample size (12 508 vs 4 349)» —
12 508 ч против 4 349×3 = 13 047 ч, т.е. фактически столько же. Сравнение
некорректно; корректная формулировка: Dst даёт 471 штормовой час с другой
классификацией и finer temporal resolution.

### B9. «Reproducible execution via the project Makefile» — неверно
`paper/main.tex:1234` (Code Availability)

`Makefile` — это **медиа-конвейер** (SVG→PNG→MP4/GIF/WebM, см.
`Makefile:1-23,60,99`), в нём нет ни одной цели для анализа статьи
(perm-теста, биннинга, фигур). Репродукция анализа идёт через
`scripts/perm_test_18mo_3band.py` и `scripts/make_paper_figures.py`.
Формулировку в Code Availability нужно переписать (или добавить
`make paper`).

### B10. Fig 2 и Fig 4 заявляют 95% bootstrap CI, но рисуют нулевые усы
`scripts/make_paper_figures.py:106-112` (fig2), `:258-286` (fig4)

В коде знаки CI инвертированы (`cis_lo = abs(percentile2.5)` — это
**верхняя** граница, `cis_hi = abs(percentile97.5)` — нижняя), после чего
`yerr = [drop − cis_lo, cis_hi − drop]` даёт оба компонента отрицательными
и `np.clip(...,0,None)` обнуляет их. Итог: у обоих рисунков **нулевой
доверительный интервал**, хотя заголовок гласит «with 95% bootstrap CI»
(Fig 4) и «with 95% bootstrap CI» (Fig 2). Реальные CI огромны:
Fig 2 — 8.2–26.5 п.п. (напр. 20 m ≥7: [−61.5, −41.0]); Fig 4 — до 30 п.п.
(15 m night: [−34.4, −4.4]). Fig 3 сделан правильно (там порядок CI
корректен). Рецензент увидит «плоские» бары и сделает вывод о высокой
точности — это визуальная дезинформация. Починить оба рисунка и
пересобрать PDF.

---

## 3. Средние находки

### M1. Fig 3: подписи (bootstrap mean) ≠ текст/таблица (point estimate)
`scripts/make_paper_figures.py:546` — `freq_drops[band] = -drop_dist.mean()`.
На рисунке 27.6 / 27.3 / 38.6, в тексте и Table 3 — 27.7 / 27.2 / 38.7.
Известно (`docs/OPEN_LOOPS_2026-10-16.md`, Finding 1), для деки сделана
правильная копия `fig3_frequency_dependence_pointest.png`, но
`paper/figures/fig3_frequency_dependence.png` (md5 `83b81c6…`) не
исправлен. Перед submission поправить (0.1 п.п., но видно).

### M2. День/ночь по UTC на глобальной сети — интерпретационный риск
`paper/main.tex:686-759`, `:1090`

Окна 12–18 UTC и 00–06 UTC для **глобального** счётчика WSPR не равны
«день/ночь пути»: в 12–18 UTC над Тихим океаном ночь, в 00–06 UTC над
Азией день. Вся интерпретация «nighttime 40 m ⇒ particle absorption»
опирается на этот прокси. Ограничение №4 признаёт глобальное усреднение,
но не этот конкретный источник ошибки. Рекомендация: либо честно назвать
окна «UTC-секторами», либо считать локальное время путей (future work уже
обещан).

### M3. Absolute-loss ratio 1.44: сезон не учтён (но проверка в пользу статьи)
`paper/main.tex:255-257`, `:916-935`

Held-out — Jan–Mar, training-baseline — среднее по 18 месяцам. Проверено:
quiet-mean 40 m DJF = 71 857 против held-out 90 653 ⇒ даже при
сравнении с тем же сезоном остаётся +26 %; сезон объясняет лишь ~7 % из
+35 %. Т.е. вывод про рост сети **усиливается**, но в статье сезон-контроль
не показан. Стоит добавить одну фразу/число.

### M4. Дек/заметки: FDR назван неверно и цифра неверна
- `slides.tex:90`, `speaker_notes.md:66`: «Benjamini–Yekutieli», в статье —
  **Benjamini–Hochberg** (`main.tex:447`, `:604`). У BY q-values были бы
  другими; 6/6 всё равно survived, 5/9 pairwise — тоже, но подпись ложная.
- `speaker_notes.md:167`: «significant — at or below ten to the minus four» —
  для 40 m p = 2×10⁻⁴, что **выше** 1e-4. Должно быть «at or below 2×10⁻⁴».
- `speaker_notes.md:88-89`: «At Kp five to six the drop is about eighteen
  percent» — это 20/40 m; для 15 m −28.6 %.

### M5. Q&A Q1 описывает другой метод
`Q_and_A.md:14-19`: «we shuffle storm labels in blocks of seventy-two hours» —
статья **не** переставляет Kp-метки, а тасует residual-блоки при
фиксированных Kp (`main.tex:379-391`). Там же «month, hour-of-week» вместо
«month, hour-of-day, day-of-week». На вопрос рецензента это даст неверное
описание метода.

### M6. `paper/README.md` устарел и вводит в заблуждение
`paper/README.md:59,60,72-78`:
- «12-page LaTeX preprint» — в реальности 26 страниц;
- «30+ BibTeX references» — 21 (проверено: 21/21 cited=used);
- «fig4/fig5 currently use approximate placeholder plots» — неверно, фигуры
  генерируются;
- «references … marked [TODO …]» — в `references.bib` 0 вхождений TODO;
- «AGU class option `draft` is set» — в `main.tex` опция не задана.
Переписать.

### M7. Presentation README: два фактически неверных утверждения
`docs/presentations/hamsci_2026-11-05/README.md:14,31,39,48`:
- «figures — побайтовые копии из paper/figures/, md5 совпадает» — для fig3
  неверно: md5 `201c1ef…` (pointest) ≠ `83b81c6…` (paper). Остальные 4 —
  действительно идентичны (проверено хэшами).
- Ссылка на `tmp_fix_pres_2_build.py` (строки 24, 50) — коммит `340467d`
  заявил «remove reference to obsolete regeneration script», но ссылки
  остались.

### M8. Трассируемость «Δ»: три разных значения для одного эффекта
- `paper/main.tex:509-511` (Table 3) — Δ raw: −20 421 / −18 285 / −5 178;
- `results/perm_test_18mo_3band.json` — `delta` (residual+dow):
  −19 793 / −14 847 / −4 362;
- `results/perm_test_18mo_3band_fdr.json` — Δ (residual, no-dow):
  −22 779 / −17 084 / −5 254.

Все три корректны для **разных** величин, но ключ называется одинаково
`delta`, и Table 3 берёт raw. Читатель, воспроизводящий по JSON, получит
другие числа. Переименовать поля (`delta_raw`, `delta_resid_full`,
`delta_resid_nodow`) и сохранить raw-артефакт.

### M9. `results/heldout_3band_2026-10-15.json`: `p_value` — raw, а статья
цитирует residual
`results/heldout_3band_2026-10-15.json` хранит raw p (20 m 6.8e-4,
40 m 6.8e-4, 15 m **0.258**), тогда как Table 8 печатает residual p
(2e-5/2e-4/8e-5) из отдельного `heldout_resid_2026-10-15.json`. Оба JSON
рядом, но без перекрёстной ссылки. Тот же риск неверного воспроизведения.
(Побочно: raw p для 20 m и 40 m совпадают до 16 знаков — совпадение числа
превышений; стоит проверить, что это не общий агрегат.)

### M10. Table 1: held-out «~5 850» не сходится с живой выгрузкой
`paper/main.tex:186`. Сырые часовые записи Jan–Mar 2026 в
`data/raw/wspr_hourly/` = 1 800/1 824/1 800 ⇒ **5 424**; ожидаемо при
полном покрытии — 6 480; анализ-пакет имеет 720 эпох/полосу (= 2 160
3-часовых точек). «~5 850» не соответствует ни одному из этих чисел.
Уточнить происхождение или заменить на фактические N из артефакта.

### M11. Мелкие несоответствия метаданных
- `pyproject.toml`: email автора `felixrlepers@gmail.com`, в статье
  (`main.tex:1259`) — `felixrpetrov@gmail.com`. Расхождение контакта.
- `pyproject.toml`: `Development Status :: 3 - Alpha` при v1.3.1 и
  поданной статье.
- `results/abs_loss_ci_heldout.json`: `"source": "live-download 2026-10-13"`,
  но значения совпадают с выгрузкой 2026-10-15 ⇒ устаревшая строка
  провенанса.
- AI-дисклозер (`main.tex:1261-1265`, `docs/AI_ASSISTANCE.md`): модели
  «Bonsai 2 27B (Ternary)» и «Qwen 3.8 27B» — нестандартные/непроверяемые
  имена версий. Для AGU стоит указать точные идентификаторы моделей.

### M12. Novelty-claim «no prior study has examined…»
`paper/main.tex:136-143`. Существуют WSPR/ionosphere-работы (Frissell 2016,
LaBelle 2023, Cerwin 2026, Potter 2026, HamSCI PSWS). Формулировка «no prior
study» сильная; корректнее «no prior study has quantified the multi-band
scale-dependence and network-size stability simultaneously».

---

## 4. Низкий приоритет / гигиена репозитория

- **L1. Отслеживаемый мусор в корне:** `quiet_all_agg.parquet`,
  `results_tau_regression.csv`, `tau_vs_d_by_band.png`, `paper.zip`
  (0.79 MB) — tracked (`git ls-files`), при том что `*.parquet`/`results/*`
  в `.gitignore`. Перенести/убрать.
- **L2. Ключевые JSON-артефакты не в git:** `results/*` игнорируется
  (кроме `*.txt`/`*.csv`), поэтому `perm_test_18mo_3band.json`,
  `heldout_resid_2026-10-15.json`, `fig4_day_night.json` **не попадут**
  ни в GitHub, ни в Zenodo-архив (если архивируется репо). Пометить их
  `!results/*.json` или явно включить в Zenodo.
- **L3. Zenodo v1.3.0 staging** (`zenodo_v1.3.0/`) содержит только
  held-out parquet/json + README + finding. В paper Data Availability
  (`main.tex:1212-1213`) обещаны «Unified parquet dataset and analysis
  scripts» на Zenodo, но `unified.parquet` (1.7 MB) в staging нет.
  Проверить фактическую запись Zenodo — иначе нарушение AGU Data Policy.
- **L4. `scripts/diag_*.py` в `.gitignore`**, хотя на них ссылаются
  `docs/AUDIT_START_NEXT_SESSION.md:309-310` как на доступные
  диагностики. Либо расшарить, либо убрать ссылки.
- **L5. Пропуски Kp на границах месяцев:** 4 × 24 ч (2024-09-30,
  2024-10-31, 2024-12-31, 2025-03-31) ⇒ 28 из 4 377 ожидаемых эпох
  (~0.6 %). Совпадает с `N=4 349 < 4 377`. В статье не упомянуто;
  на выводы не влияет, но стоит зафиксировать в Data/QA.
- **L6. Расхождения с AGENTS.md:** заявлено «20 модулей» в
  `crosscorr_lib/analysis/` — фактически 18 + `__init__`; заявлено
  «291 тест» — `pytest -m "not slow"` даёт 288 (+2 deselected, +slow).
  Обновить цифры.
- **L7. `make_paper_figures.py:363-365`:** поля `growth` = 17/38/25
  не соответствуют статье (+14/+35/+22) и, судя по коду, не используются.
  Удалить или исправить (иначе следующий редактор унаследует ошибку).
- **L8. `main.bak0…15` (16 файлов) и `main.tex.bak`** лежат в `paper/`
  (gitignored через `paper/*.bak*`, но физически в дереве). Раз они
  `*.bak`, риск случайного использования низок, но чистка перед
  архивацией желательна.
- **L9. Библиография:** `royrvik1977` («Pulsating aurora») цитируется как
  источник морфологии аврорального поглощения (`main.tex:731`) — связь
  слабая; `tsurutani2003` (событие 1859 г.) цитируется для общей передачи
  энергии в ионосферу-термосферу (`:98`) — лучше Gonzalez 1994.
  AGU не требует, но стоит уточнить. Все 21 ключа используются, TODOs нет.

---

## 5. Презентация (HamSCI, 2026-11-05)

`slides.tex` (10 слайдов), `slides.pdf` (700 KB, собирается без неопределённых
ссылок, 1 overfull vbox ~2 pt), `speaker_notes.md`, `Q_and_A.md`.

Числа слайдов сверены с `main.tex v1.3.1` — совпадают (27.7/27.2/38.7;
18/34/53; day/night; 18 285/18 304/26 287, ratio 1.44; held-out 26.7/29.0/22.1;
DO1 v1.3.1 = 23402384). Замечания:

- **Слайд 3 и notes:29**: «Benjamini–Yekutieli» вместо BH (M4).
- **notes:167**: «at or below 1e-4» — фактически 2e-4 (M4).
- **Слайд 6 / notes:146**: перевёрнутый тезис «percentage network-dependent,
  absolute more physical» (B1) — обязательно переформулировать до доклада.
- **Слайд 4 / notes:88**: «about eighteen percent» подано универсально;
  для 15 m 28.6 % (B2).
- **Слайд 7**: «all three bands p<1e-3» — формально верно, но для 15 m это
  residual-only; стоит добавить «raw CI includes zero» (B3). В Limitations
  (слайд 8) это есть.
- **README презентации**: см. M7.

Плюсы: дек честно выносит «absolute-loss not established (1.44)» в
keypoints/слайд 6 — сильный ход; ограничения перечислены; фигуры 1/2/4/5
в деке побайтово совпадают с paper (fig3 — исправленная копия).

---

## 6. Матрица верификации (числа статьи → артефакт)

| Утверждение | Источник | Статус |
|---|---|---|
| 39 456 WSPR-часов, 13 152/полосу | `unified.parquet` | OK |
| 4 349 эпох, 198/3 035 | пересчёт | OK |
| drops 27.7/27.2/38.7, p=2e-5 | `perm_test_18mo_3band.json` | OK (p), Δ в JSON иной (M8) |
| Table 3 Δ raw | пересчёт | OK |
| Table 5 Dst Δ | пересчёт | OK |
| Table 5 Dst p=2e-5 | артефакт 5k/0.0 | **НЕ подтверждён** (B5) |
| Table 5 block=72 h | артефакт `block_size=24` часового ряда | **24 ч** (B6) |
| «42 storm events» | — | **НЕ воспроизводится** (B7) |
| Table 8 held-out drops | `heldout_3band_2026-10-15.json` | OK |
| Table 8 p | `heldout_resid_2026-10-15.json` | OK (residual) |
| Table 9 scale replication | пересчёт | OK (N=10) |
| Table 10 abs loss/CI/ratios | пересчёт | OK |
| Fig 2/4 «95 % CI» | код | **нулевые усы** (B10) |
| Fig 3 подписи | код | 0.1 п.п. расхождение (M1) |
| Fig 4 day/night, 8 месяцев | `fig4_day_night.json` + пересчёт | OK |
| F10.7 gate | `f107_spearman_monthly.txt` | OK |
| Makefile-репродукция | `Makefile` | **неверно** (B9) |

---

## 7. Рекомендованный порядок правок

1. **B10** (фигуры 2/4) — пересобрать `make_paper_figures.py`, проверить
   md5 остальных фигур, пересобрать `main.pdf`.
2. **B1** (§5.3 + Q&A Q8 + notes slide 6) — перевернуть аргумент.
3. **B2, B3, B4** — уточнить keypoints/abstract/conclusion/slides:
   полосо-специфичные числа; «replicates (residual-based; raw 15 m CI
   includes zero)»; развести primary и scale-dependence.
4. **B5, B6** — перегенерировать Dst-тест на 50 000 с add-one, сохранить
   артефакт, исправить описание блока (24 ч для часового Dst).
5. **B7, B8** — удалить «42 events», исправить сравнение единиц.
6. **B9** — переписать Code Availability (или добавить `make paper`).
7. **M1–M7** — перед submission/arXiv.
8. **L2, L3** — привести Data/Code Availability в соответствие с реально
   заархивированным (unified.parquet + JSON-артефакты).

После B1–B10 правок в коде анализа **не требуется** — численное ядро
верно; правки касаются текста, подписей и артефактов.

---

## 8. Что не проверено

- Содержимое фактической записи Zenodo (оффлайн недоступно) — Data
  Availability проверена только по staging.
- `aep/`, `game/`, `media/` (After Effects / интерактив) — вне научного
  контура; репозиторная гигиена отмечена в L1.
- Точные идентификаторы/версии моделей в AI-дисклозере.
- Точность библиографических записей по внешним БД (DOI присутствуют у
  17/21; проверка резолва не выполнялась).
