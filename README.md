<p align="center">
  <img src="images/logo.svg" alt="CrossCorr — global data stream logo" width="400"/>
</p>

<h1 align="center">CrossCorr</h1>

<p align="center"><i>Cross-correlation analysis of anomalies in heterogeneous time series</i></p>

<p align="center"><i>Русская версия. English version coming soon.</i></p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
  <a href="https://streamlit.io/"><img src="https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="https://github.com/FelixRLEPERS/crosscorr/actions">
    <img src="https://github.com/FelixRLEPERS/crosscorr/actions/workflows/ci.yaml/badge.svg" alt="CI">
</a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status">
  <a href="https://github.com/FelixRLEPERS/crosscorr/commits/main"><img src="https://img.shields.io/github/last-commit/FelixRLEPERS/crosscorr" alt="Last commit">
</a>
</p>

---

## 📖 Оглавление

- [О проекте](#о-проекте)
- [Методология](#методология)
- [Научная строгость](#научная-строгость)
- [Структура репозитория](#структура-репозитория)
- [Быстрый старт](#быстрый-старт)
- [Данные](#данные)
- [Пайплайн анализа](#пайплайн-анализа)
- [Игра и голосовой наставник](#игра-и-голосовой-наставник)
- [Финансирование: CrossCorr Fund](#финансирование-crosscorr-fund)
- [Результаты](#результаты)
- [Статус проекта](#статус-проекта)
- [Команда](#команда)
- [Документация](#документация)
- [Вклад ИИ](#вклад-ии)
- [Скриншоты](#скриншоты)
- [Лицензия](#лицензия)
- [Контакты](#контакты)

---

## 🎯 О проекте

**CrossCorr** — это открытый исследовательский проект, который объединяет разнородные временные ряды и проверяет гипотезы о наличии кросс-корреляций между ними. Мы не ищем «магическую связь», а строим воспроизводимый пайплайн: от загрузки и унификации данных до статистических тестов с контролем ложных обнаружений.

Проект задуман как семейный: папа отвечает за стратегию и код, мама — за коммуникации и тексты, Макар — за исследования, Егор — за данные и визуализацию. Мы хотим показать, что настоящая наука может быть совместным семейным делом.

**Ключевые принципы:**

- Открытые данные и открытый код.
- Воспроизводимость каждого шага.
- Статистическая строгость: surrogate-тесты, FDR-коррекция, байесовские модели.
- Игровые форматы для вовлечения детей.
- Прозрачность: явно указываем, где помогал ИИ.

---

## 🔬 Методология

1. **Унификация данных.**
   Все источники приводятся к единому формату:

   ```text
   timestamp_utc, detector_id, detector_type, residual, meta
   ```

2. **Базовая модель.**
   Оценка остатков через смешанную линейную модель:

   ```text
   v0 ~ T_заряда + масса + (1|полигон)
   ```

   Реализация: `statsmodels` MixedLM.

3. **Пространственная модель.**
   Байесовская модель с экспоненциальным ядром ковариации для учёта пространственной структуры.
   Реализация: `PyMC`.

4. **Кросс-корреляционный анализ.**
   Построение матрицы корреляций между детекторами и временными рядами.
   Реализация: [`crosscorr_lib/analysis/cross_correlation.py`](crosscorr_lib/analysis/cross_correlation.py).

5. **Мультифрактальный анализ.**
   MFDFA для оценки фрактальных свойств рядов.
   Реализация: [`MFDFA`](https://pypi.org/project/MFDFA/), [`crosscorr_lib/analysis/mfdfa.py`](crosscorr_lib/analysis/mfdfa.py).

6. **Surrogate-тесты.**
   Генерация 1000+ фазовых суррогатов для проверки значимости наблюдаемых корреляций.
   Реализация: [`crosscorr_lib/analysis/surrogate.py`](crosscorr_lib/analysis/surrogate.py).

7. **FDR-коррекция.**
   Контроль доли ложных обнаружений (Benjamini–Hochberg) при множественных сравнениях.

Подробнее: [docs/methodology.md](docs/methodology.md)

---


## Научная строгость

- **Max-statistic null** — p-value учитывает поиск по всем лагам, а не только по лучшему.
  Без этого значимость завышалась бы (145 тестов на пару).
- **Negative controls** — на чистом шуме 45 пар: **0 ложных срабатываний** (alpha=0.05).
- **FDR** — единая реализация Benjamini–Hochberg в `crosscorr_lib/analysis/surrogate.py`,
  поддержка 1D и 2D входов.
- **Distance-based analysis** — регрессия `correlation ~ distance_km`.
  Подтверждена гипотеза: близкие детекторы коррелируют сильнее.
- **Block bootstrap** — реализован (`crosscorr_lib/analysis/block_bootstrap.py`).
- **Effective sample size** — реализован (`crosscorr_lib/analysis/effective_sample.py`).
- **Physical confounders** (Kp, Dst, F10.7) — реализованы (`crosscorr_lib/analysis/confounders.py`).
- **ADF stationarity test** — реализован (`crosscorr_lib/analysis/stationarity.py`).

Проверки запускаются одной командой:

```bash
python -m pytest tests/ -v -k "not negative_control"
```

---

## 📁 Структура репозитория

```text
crosscorr/
├── assets/                      # SVG-логотипы и финальные кадры
├── crosscorr_lib/               # ядро проекта
│   ├── analysis/                # cross_correlation, surrogate, mfdfa, distance_analysis
│   ├── safe_exec.py             # безопасное выполнение кода (P0-6)
│   ├── ai_narrator.py
│   ├── narrator.py
│   └── quest.py
├── data/
│   ├── scripts/                 # download_*, unify_schema, make_sample
│   ├── detectors.csv            # координаты детекторов (lat, lon)
│   └── processed/               # unified.parquet (gitignored)
├── scripts/
│   └── make_synthetic_unified.py # генератор тестовых данных
├── tests/                       # pytest-тесты
│   ├── test_cross_correlation_synthetic.py
│   ├── test_fdr.py
│   ├── test_max_statistic.py
│   ├── test_negative_control.py
│   └── test_distance_analysis.py
├── results/                     # выходные CSV (gitignored)
├── docs/
├── README.md
└── requirements.txt
```

---

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- Git
- Streamlit
- Рекомендуется виртуальное окружение

### Установка

```bash
git clone https://github.com/FelixRLEPERS/crosscorr.git
cd crosscorr
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### Запуск игры

```bash
streamlit run crosscorr_lib/quest.py
```

### Запуск голосового наставника

```bash
python crosscorr_lib/narrator.py
```

### Запуск AI-наставника

```bash
python crosscorr_lib/ai_narrator.py
```

---

## 🗄️ Данные

Проект использует открытые источники. Сырые данные **не коммитятся** в репозиторий — только скрипты загрузки и небольшие примеры (`data/samples/`).

| Источник | Тип данных | Ссылка |
|---|---|---|
| WSPR | Распространение радиосигналов | [wsprnet.org](https://wsprnet.org/) |
| NGL | GNSS-данные | [ngl.unavco.org](https://ngl.unavco.org/) |
| INTERMAGNET | Магнитное поле Земли | [intermagnet.org](https://intermagnet.org/) |
| Oulu | Ионосферные данные | [cosmic.rl.ac.uk](https://cosmic.rl.ac.uk/) |
| Ammolytics | Баллистические данные | [ammolytics.com](https://ammolytics.com/) |
| BIPM | Метрологические данные | [bipm.org](https://www.bipm.org/) |
| 1000 Genomes | Генетические данные | [internationalgenome.org](https://www.internationalgenome.org/) |
| JPL Horizons | Эфемериды | [ssd.jpl.nasa.gov](https://ssd.jpl.nasa.gov/horizons/) |

Формат унифицированной таблицы и правила добавления данных описаны в [data/README.md](data/README.md).
JSON-схема: [data/schema/unified_schema.json](data/schema/unified_schema.json).

---

## 🔬 Пайплайн анализа

Полное описание: [crosscorr_lib/analysis/README.md](crosscorr_lib/analysis/README.md).

Кратко:

```bash
# 1. Скачать данные
python data/scripts/download_wspr.py --date 2025-01-01
python data/scripts/download_intermagnet.py --file path/to/file.min
python data/scripts/download_horizons.py --planet mars --start 2025-01-01 --stop 2025-02-01

# 2. Унифицировать
python data/scripts/unify_schema.py

# 3. Сделать сэмпл для тестов
python data/scripts/make_sample.py

# 4. Кросс-корреляция
python crosscorr_lib/analysis/cross_correlation.py --freq 1h --method spearman

# 5. Surrogate-тесты и FDR
python crosscorr_lib/analysis/surrogate.py --n 1000 --alpha 0.05

# 6. MFDFA
python crosscorr_lib/analysis/mfdfa.py

# 7. Distance-based analysis (корреляция vs расстояние)
python -m crosscorr_lib.analysis.distance_analysis

# 8. Тесты (без долгих negative_control)
python -m pytest tests/ -v -k "not negative_control"

# 9. Долгие negative controls (по желанию, ~2 минуты)
python -m pytest tests/test_negative_control.py -v -s -n 2

```

Артефакты анализа сохраняются в `results/`:

- `results/distance_analysis.csv` — пары + distance_km
- `results/distance_summary.csv` — сводка по бинам расстояний
- `results/cross_correlation_pairs.csv` — tidy-формат: `detector_1, detector_2, lag, correlation, p_value, q_value, n_obs, significant`
- `results/cross_correlation.png`
- `results/surrogate_pvalues.csv`
- `results/surrogate_significant.csv`
- `results/mfdfa_spectra.csv`

### Безопасность выполнения кода

Код, который пишет ребёнок, выполняется в **изолированном subprocess** с timeout 5 секунд. Опасные имена (`open`, `exec`, `eval`, `__import__`, `import os`, `import sys`) блокируются через **AST-парсер** — не наивный поиск подстроки.

- `while True: pass` — прерывается через timeout.
- `import os; os.system(...)` — блокируется до выполнения.
- `pos = 5` (содержит `os`) — **разрешается**, ложных срабатываний нет.

Реализация: [`crosscorr_lib/safe_exec.py`](crosscorr_lib/safe_exec.py).

---

## 🎮 Игра и голосовой наставник

Игровой модуль для детей 11–13 лет. Сюжет — «Охота на призрака»: ребёнок ищет сверхмалые корреляции в данных.

- [`crosscorr_lib/quest.py`](crosscorr_lib/quest.py) — интерактивный квест (Streamlit, видео-фон, музыка).
- [`crosscorr_lib/narrator.py`](crosscorr_lib/narrator.py) — голосовой наставник на базе `edge-tts` (бесплатно, без API-ключей).
- [`crosscorr_lib/ai_narrator.py`](crosscorr_lib/ai_narrator.py) — AI-наставник, объясняющий результаты анализа.

Подробное описание сюжета и уровней: [docs/quest.md](docs/quest.md).

---

## 💰 Финансирование: CrossCorr Fund

**CrossCorr Fund** — это концепция децентрализованного фонда, который финансирует научные проекты не через заявки и экспертизу, а через **автоматическую верификацию результатов** с помощью сенсорных сетей и метода CrossCorr.

**Основная идея:** деньги перечисляются учёному не за обещания, а за подтверждённый результат. Датчики фиксируют, что эксперимент проведён, реакция прошла, вещество синтезировано. Смарт-контракт автоматически проверяет условие и перечисляет средства.

**Три ключевых инновации:**

1. **Автоматическая верификация** — датчики фиксируют результат, CrossCorr Engine проверяет значимость, смарт-контракт перечисляет деньги.
2. **Пространственно-временная привязка** — каждый результат привязан к времени и месту, что делает данные уникальными и защищает от подделки.
3. **Децентрализованное управление** — держатели токенов $CROSS голосуют за правила, совет экспертов решает спорные случаи, код выполняет решения автоматически.

**Токеномика (кратко):**

| Параметр | Значение |
|---|---|
| Название | CrossCorr Token |
| Символ | $CROSS |
| Всего | 1 000 000 000 |
| Стандарт | ERC-20 (Ethereum + Polygon) |
| Распределение | Команда 15%, Инвесторы 25%, Казначейство 30%, Сообщество 20%, Резерв 10% |

**Дорожная карта (кратко):**

| Этап | Срок | Бюджет | Команда |
|---|---|---|---|
| Концепт | 1–3 мес | $10,000 | 3 чел. |
| MVP | 4–9 мес | $100,000 | 7 чел. |
| Запуск | 10–18 мес | $500,000 | 15 чел. |
| Масштаб | 19–36 мес | $2,000,000 | 50 чел. |
| Экосистема | 37–60 мес | $10,000,000 | 200 чел. |

Подробное описание: [docs/fund.md](docs/fund.md)
Полный whitepaper: [docs/fund-whitepaper.md](docs/fund-whitepaper.md)

---

## 📈 Результаты

Раздел будет пополняться по мере прогонов пайплайна.

- [x] Синтетический бенчмарк: лаговая CC восстанавливает lag=6
- [x] Negative controls: 0 ложных срабатываний на 45 парах шума
- [x] Distance-based analysis: slope < 0 (близкие коррелируют сильнее)
- [x] Max-statistic null: p-value учитывает поиск по всем лагам
- [ ] Первый прогон на реальных WSPR + Horizons
- [ ] Кросс-корреляционная матрица за неделю
- [ ] Surrogate-тесты (n=1000) с FDR
- [ ] MFDFA-спектры по всем детекторам

Графики появятся в `results/` и будут вставлены в [Скриншоты](#скриншоты).

---

## 📌 Статус проекта

- ✅ Голосовой наставник (`crosscorr_lib/narrator.py`)
- ✅ AI-наставник (`crosscorr_lib/ai_narrator.py`)
- ✅ Безопасное выполнение кода (`crosscorr_lib/safe_exec.py`)
- ✅ Тесты (`pytest`, 11 тестов в 5 файлах)
- ✅ Distance-based analysis (`correlation ~ distance_km`)
- ✅ Max-statistic null для лагов
- ✅ Negative controls (0 ложных на шуме)
- ✅ Единая FDR (1D + 2D)
- 🚧 MixedLM для остатков
- 🚧 CI (GitHub Actions)
- 🚧 Physical confounders (Kp, Dst, F10.7)
- 🚧 Effective sample size
- 🚧 Block bootstrap

Актуальный план: [docs/roadmap.md](docs/roadmap.md)

---

## 👨‍👩‍👦 Команда

| Роль | Участник | Зона ответственности |
|---|---|---|
| CEO | Папа | Стратегия, архитектура, код |
| Communications | Мама | Тексты, презентации, связи |
| Research | Макар | Исследования, эксперименты |
| Researcher | Егор | Данные, визуализация |

**Для CrossCorr Fund (план):**

| Роль | Кто | Опыт |
|---|---|---|
| CTO | (найм) | Blockchain, Solidity |
| CFO | (найм) | Финансы, аудит |
| Legal | (аутсорс) | Крипто-право |

---

## 📚 Документация

- [Методология](docs/methodology.md)
- [План развития](docs/roadmap.md)
- [Игра и сюжет](docs/quest.md)
- [CrossCorr Fund](docs/fund.md)
- [Whitepaper фонда](docs/fund-whitepaper.md)
- [Пайплайн анализа](crosscorr_lib/analysis/README.md)
- [Описание данных](data/README.md)
- [Статья (LaTeX)](paper/work.tex)
- [Библиография](paper/references.bib)

---

## 🤖 Вклад ИИ

Проект использует ИИ как вспомогательный инструмент. Это указано явно, чтобы избежать вопросов о самостоятельности исследования.

**Что делает ИИ:**

- генерация черновиков кода и текстов,
- помощь в формулировке гипотез,
- озвучка (через `edge-tts`),
- структурирование документации.

**Что делает человек:**

- постановка задачи и гипотез,
- выбор методов и интерпретация результатов,
- валидация кода и данных,
- финальные выводы и публикации.

---

## 🖼️ Скриншоты

![Скриншот игры](images/quest_screenshot.png)

<!-- Раскомментировать после первого прогона пайплайна:

![Кросс-корреляционная матрица](results/cross_correlation.png)

![MFDFA-анализ](results/mfdfa.png)

-->

---

## 📄 Лицензия

Проект распространяется под лицензией **MIT**. Подробнее: [LICENSE](LICENSE).

---

## 📬 Контакты

- GitHub Issues: [github.com/FelixRLEPERS/crosscorr/issues](https://github.com/FelixRLEPERS/crosscorr/issues)
- Email: [felixrlepers@gmail.com](mailto:felixrlepers@gmail.com)
- Сайт проекта: [felixrlepers.github.io/crosscorr](https://felixrlepers.github.io/crosscorr/)

---

> Если вы нашли ошибку или хотите предложить идею — создайте Issue или Pull Request. Мы открыты к сотрудничеству.
