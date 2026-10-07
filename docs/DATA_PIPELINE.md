# Data Pipeline — архитектура

Документ описывает архитектуру системы сбора и унификации данных
CrossCorr. Рассчитан на взрослых читателей: научный руководитель,
рецензент, разработчик, который хочет расширить систему.

## Общая схема

```
                     ┌─────────────────────┐
                     │     config.yaml      │  (даты, станции, объекты)
                     └────────┬────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    ▼                         ▼                         ▼
┌─────────┐            ┌────────────┐           ┌──────────────┐
│  WSPR   │            │  Horizons  │           │ Space Weather │
│ db1.wspr│            │ astroquery │           │ GFZ/Kyoto/NOAA│
│  .live  │            │  .jplhoriz │           │              │
└────┬────┘            └─────┬──────┘           └──────┬───────┘
     │                       │                         │
     ▼                       ▼                         ▼
┌─────────────┐     ┌──────────────┐          ┌─────────────────┐
│download_wspr│     │download_hori │          │download_space   │
│    .py      │     │   zons.py    │          │  _weather.py    │
└──────┬──────┘     └──────┬───────┘          └───────┬─────────┘
       │                   │                          │
       ▼                   ▼                          ▼
  data/raw/wspr/     data/raw/horizons/     data/raw/space_weather/
     *.csv                *.csv                    *.csv

   ┌─────────────────────────────────┐
   │       data/raw/intermagnet/     │  ← ручное скачивание
   │            *.min → *.csv        │     (intermagnet.org)
   └───────────────┬─────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  unify_schema.py │  ← transform-слой
         │  + fit_residuals │     (loaders → concat → residuals)
         └────────┬────────┘
                  │
                  ▼
    ┌──────────────────────────┐
    │ data/processed/          │
    │   unified.parquet        │  ← единая схема, 9 колонок
    └────────────┬─────────────┘
                 │
    ┌────────────┼─────────────┐
    ▼            ▼             ▼
cross_correl   mfdfa      stationarity
  ation.py      .py          .py
```

Все автоматические источники скачиваются одной командой:

```
python data/scripts/fetch_all.py --start YYYY-MM-DD --end YYYY-MM-DD
```

`fetch_all.py` — оркестратор: вызывает download-скрипты по очереди,
собирает результаты, печатает сводку и запускает `unify_schema.py`.

## Источники данных

### WSPR (радиосигналы)

| Параметр | Значение |
|---|---|
| URL | `http://db1.wspr.live/` (ClickHouse SQL-зеркало) |
| Формат | CSV через SQL-запрос (`FORMAT CSVWithNames`) |
| Периодичность | Споты ~каждые 2 минуты; агрегируются до среднего за час |
| Автоматизация | Полная |
| Единица | SNR (dB) |
| Ограничения | Только **прошлые** даты; будущие вешают запрос (timeout 30 с) |
| Скрипт | `data/scripts/download_wspr.py` |

Запрос к ClickHouse: `SELECT time, tx_sign, rx_sign, band, snr, frequency, distance FROM wspr.rx WHERE time>='...' AND time<'...' AND band=N LIMIT 5000`.

В unified-схеме одно наблюдение — средний SNR одного приёмника (rx_call) в один момент времени. Передатчики (tx_call) упаковываются в meta.

### JPL Horizons (эфемериды)

| Параметр | Значение |
|---|---|
| URL | `astroquery.jplhorizons.Horizons` (Python API, обёртка над JPL Telnet) |
| Формат | `astropy.table.Table` → CSV |
| Периодичность | 1 час (настраивается в config.yaml) |
| Автоматизация | Полная для планет и Луны; **sun не работает** |
| Единица | AU (расстояние от Солнца) |
| Ограничения | Sun: `location='@sun'` → `location='500'` (геоцентр) вызывает ошибку в astroquery |
| Скрипт | `data/scripts/download_horizons.py` |

Наблюдаемые объекты: Mercury, Venus, Earth, Moon, Mars, Jupiter, Saturn.
Каждая загрузка сохраняет метаданные запроса (`.json`) и контрольную сумму (`.sha256`) — эфемериды JPL обновляются при смене DE-ядер и не воспроизводимы задним числом.

### Space Weather (Kp, Dst, F10.7)

Три индекса космической погоды из трёх разных источников. Каждый скачивается независимо — падение одного не прерывает остальные.

#### Kp (геомагнитная активность)

| Параметр | Значение |
|---|---|
| URL | `https://kp.gfz-potsdam.de/app/json/` |
| Формат | JSON: `{"datetime": [...], "Kp": [...]}` |
| Периодичность | 3 часа |
| Автоматизация | Полная |
| Единица | Безразмерный (0–9) |
| Скрипт | `data/scripts/download_space_weather.py:fetch_kp` |

#### Dst (геомагнитные возмущения)

| Параметр | Значение |
|---|---|
| URL | `http://wdc.kugi.kyoto-u.ac.jp/dst_realtime/<YYYY><MM>/dst<YY><MM>.for.request` |
| Формат | Текстовые строки: `DSTyymm*dd...` → 24 часовых значения |
| Периодичность | 1 час |
| Автоматизация | Полная |
| Единица | нТ |
| Ограничения | Real-time endpoint; окончательные (final) данные — с задержкой несколько месяцев |
| Скрипт | `data/scripts/download_space_weather.py:fetch_dst` |

#### F10.7 (солнечный радиопоток)

| Параметр | Значение |
|---|---|
| URL | `https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json` |
| Формат | JSON-массив: `[{"time-tag": "YYYY-MM", "f10.7": N}, ...]` |
| Периодичность | **Месячная** (дневные значения недоступны через этот источник) |
| Автоматизация | Полная |
| Единица | sfu (10⁻²² W/m²/Hz) |
| Ограничения | Только месячные средние |
| Скрипт | `data/scripts/download_space_weather.py:fetch_f107` |

### INTERMAGNET (магнитные обсерватории)

| Параметр | Значение |
|---|---|
| URL | `https://intermagnet.org` — ручное скачивание через веб-интерфейс |
| Формат | IAGA-2002 (`.min` файлы) → CSV |
| Периодичность | 1 минута (resampled до 1 часа в unified) |
| Автоматизация | **Ручная** (требуется аккаунт) |
| Единица | нТ |
| Скрипт | `data/scripts/download_intermagnet.py` |

Станции по умолчанию: MOS (Москва), ESK (Eskdalemuir), OTT (Ottawa).
`fetch_all.py` печатает инструкцию со ссылками на страницу каждой станции.

## Схема unified.parquet

Файл `data/processed/unified.parquet` — единая таблица всех наблюдений.
Формат: Apache Parquet (колоночное хранение, сжатие snappy).

| Колонка | Тип | Описание |
|---|---|---|
| `timestamp_utc` | datetime64[ns, UTC] | Время измерения по UTC |
| `detector_id` | str | Уникальный ID датчика (позывной, имя станции, `kp_index` и т.д.) |
| `detector_type` | str | Тип: `wspr`, `magnetometer`, `ephemeris`, `kp`, `dst`, `f107`, `ballistic`, `gnss`, `ionosonde` |
| `value` | float64 | Сырое измерение |
| `residual` | float64 | Остаток после удаления baseline-модели (confounders) |
| `residual_method` | str | Метод: `mixedlm_ballistic`, `ols_geomagnetic`, или `none` (если confounders не переданы) |
| `unit` | str | Единицы: `dB` (WSPR), `nT` (магнитометры, Dst), `AU` (эфемериды), `sfu` (F10.7), `""` (Kp) |
| `quality_flag` | str | `"ok"` — качественные данные, `"missing"` — NaN в residual |
| `meta` | str (JSON) | Метаданные: для WSPR — `{"tx": "...", "band": "..."}`, для Kp — `{"granularity": "3h"}` |

### residual и residual_method

`residual` — это `value` минус вклад конфаундеров, оценённый через OLS-регрессию:

```
detector(t) = α + β₁·Kp(t) + β₂·Dst(t) + β₃·F10.7(t) + residual(t)
```

Базовая модель оценивается **по типу детектора** (все WSPR-приёмники вместе, все магнитометры вместе и т.д.), а не по каждому файлу отдельно.

Если файл `data/confounders.csv` не существует, модель не оценивается: `residual_method == "none"` и `residual == value`. Конфаундеры в проекте — синтетические (генерируются в `confounders.csv`).

## Как добавить новый источник

### 1. Напиши download-скрипт

Создай `data/scripts/download_<name>.py`. Скрипт должен:
- Принимать `--start` и `--end` (даты YYYY-MM-DD)
- Скачивать данные из API / файла
- Сохранять CSV в `data/raw/<name>/`
- Возвращать путь к сохранённому файлу

Образец: `download_space_weather.py` (три независимых функции — `fetch_kp`, `fetch_dst`, `fetch_f107`).

### 2. Добавь loader в unify_schema.py

В `data/scripts/unify_schema.py`:
- Напиши функцию `load_<name>(path) → pd.DataFrame`
  - Читает CSV из `path`
  - Возвращает DataFrame с колонками: `timestamp_utc`, `detector_id`, `detector_type`, `value`, `meta`
- Добавь в словарь `LOADERS`: `"<name>": load_<name>`

Если твой источник — подтип существующей папки (как kp/dst/f107 — подпапки `space_weather`), добавь его в `_route_sw()` (или напиши аналогичный роутер).

### 3. Добавь detector_unit

В `crosscorr_lib/analysis/residuals.py` добавь запись в словарь `DETECTOR_UNITS`:
```python
"<detector_type>": "<unit>"
```

### 4. Обнови config.yaml

Добавь секцию с параметрами нового источника:
```yaml
<name>:
  param1: value1
  param2: value2
```

### 5. Добавь в fetch_all.py

В `data/scripts/fetch_all.py`:
- Добавь функцию `_fetch_<name>_range(start, end, config) → int`
- Добавь вызов в `main()` (по образцу WSPR или space_weather)
- Добавь имя в `KNOWN_SOURCES` и `resolve_sources()`

### 6. Обнови документацию

- `data/README.md` — добавь в таблицу источников и troubleshooting
- `docs/DATA_PIPELINE.md` — добавь в таблицу источников и схему

## Известные ограничения

| Проблема | Причина | Обходной путь |
|---|---|---|
| WSPR: будущие даты вешают запрос | Сервер не возвращает ответ, если данных нет | Использовать **только прошлые даты** |
| Horizons sun: ошибка | `astroquery.jplhorizons` не поддерживает observation target = Sun | Исключить sun из `config.yaml → horizons.objects` |
| F10.7: только месячные | NOAA SWPC даёт только monthly means | Заполнять `confounders.csv` синтетикой или найти другой источник ежедневных F10.7 |
| INTERMAGNET: ручное скачивание | API требует авторизации, закрыт | Скачивать .min файлы вручную через intermagnet.org → класть в `data/raw/intermagnet/` |
| Confounders: синтетические | Реальные Kp/Dst/F10.7 дневного разрешения недоступны как единый файл | Использовать `confounders.csv` (генерируется скриптом) |
| Kp/Dst коллинеарны | Оба индекса измеряют геомагнитную активность | OLS использует Moore-Penrose pseudoinverse — устойчив к мультиколлинеарности |

## Troubleshooting

### WSPR timeout

Если WSPR-запрос висит дольше 30 секунд — дата в будущем.
Решение: проверить, что `--end` < сегодня. При необходимости увеличить timeout в `download_wspr.py:76` (параметр `timeout=30`).

### Horizons ошибка

Если `fetch_ephemeris` падает с ошибкой astroquery — проверить:
1. Версию astroquery: `pip show astroquery` (должна быть ≥0.4.6)
2. Что sun исключён из `config.yaml → horizons.objects`
3. Интернет-соединение (JPL Telnet API требует прямого доступа)

### unify_schema падает

Типичные причины:
- Новый CSV имеет другой набор колонок → проверить loader в `unify_schema.py`
- Время не парсится → проверить формат дат в CSV (должен быть ISO 8601)
- `confounders.csv` повреждён → удалить файл (unify продолжит с `residual_method="none"`)

Лог пишется в stdout — ошибки помечены `[SKIP]` с именем файла и сообщением.

### INTERMAGNET: файлы не читаются

Парсер поддерживает два формата IAGA-2002 (канонический с пробелами и фиксированно-ширинный). Если файл не читается — открой его в текстовом редакторе и сравни с примерами в `download_intermagnet.py:1-42`.