# Publication Plan — Zenodo DOI

**Date:** 2026-10-08
**Status:** План (не выполнять сейчас)

---

## Story arc for preprint

The paper tells a five-layer story, each building on the previous:

1. **Primary result:** WSPR spot density drops during geomagnetic storms
   (Kp ≥ 5) — all 3 HF bands, 18 months, p < 0.0001. Confirmed by
   independent replication (Jan–Mar 2026, all p ≤ 0.014).

2. **Scale-dependence (novel):** The effect grows non-linearly with
   Kp. Kp 5–6 → ~−18%; Kp 6–7 → ~−34%; Kp ≥ 7 → −52 to −59%.
   Replicates on held-out data when matched by Kp bin (0.85–0.95×
   at Kp 6–7). Not previously characterised for WSPR.

3. **Frequency dependence:** 15m (−38.7%) > 20m (−27.7%) ≈ 40m (−27.2%).
   Consistent with two mechanisms: MUF suppression (15m) and D-layer
   absorption (20m/40m). Partially replicates — frequency gradient not
   detectable in 3 months of independent data.

4. **Day/night asymmetry:** 40m night > day in 9/10 training months.
   Evidence for intermittent auroral/PCA absorption at night during
   storms. Does not independently replicate — intermittent mechanism
   requiring longer observation.

5. **Absolute effect is baseline-invariant:** 40m loses ~18 300 spots/h
   in both training and held-out, despite 38% more stations in 2026.
   The storm effect is physically real, not a network-size artifact.

**Novel contributions:**
- Scale-dependent WSPR response to Kp (not previously reported)
- Frequency-dependent signature across 3 bands (dual mechanism)
- Independent replication confirming physical reality of the effect
- Day/night asymmetry as evidence for particle precipitation

**Target journal:** Space Weather (AGU)

## Шаг 1: arXiv pre-print

1. Подготовить `manuscript/main.tex` (или PDF из first_result.md)
2. Выбрать категорию: `physics.space-ph` (Space Physics)
3. Зарегистрироваться на arXiv.org:
   - Author registration: https://arxiv.org/register
   - Институт: неаффилированный (independent researcher)
4. Загрузить:
   - PDF статьи
   - Source (LaTeX или исходный first_result.md)
   - Соавторы: Alexey Petrov, Makar Petrov
5. Получить arXiv ID (например, `2410.12345`)

## Шаг 2: Zenodo DOI

### Что выгрузить

```
crosscorr-zenodo/
├── README.md                        # Краткое описание, ссылка на GitHub
├── data/
│   ├── unified.parquet              # 78 736 строк (ключевой датасет)
│   └── README.txt                   # Описание колонок из docs/DATA_PIPELINE.md
├── scripts/
│   ├── fetch_all.py                 # data/scripts/fetch_all.py
│   ├── download_wspr.py             # data/scripts/download_wspr.py
│   ├── download_space_weather.py    # data/scripts/download_space_weather.py
│   ├── unify_schema.py              # data/scripts/unify_schema.py
│   ├── eda_18mo_3band.py            # scripts/eda_18mo_3band.py
│   └── perm_test_18mo_3band.py      # scripts/perm_test_18mo_3band.py
├── results/
│   ├── perm_test_18mo_3band.json    # Основные числа
│   ├── perm_test_18mo_3band_fdr.json# FDR-коррекция
│   └── perm_test_6mo_3band.json     # Для сравнения
├── docs/
│   ├── first_result.md              # Научный документ
│   └── DATA_PIPELINE.md             # Архитектура пайплайна
└── LICENSE                          # MIT (код) + CC-BY-4.0 (данные)
```

### Что НЕ выгружать

```
data/raw/                            # Публично доступно в wspr.live/GFZ/Kyoto
data/processed/wspr_hourly_*.csv     # Можно восстановить через unify_schema.py
.mypy_cache/                          # Артефакты сборки
.pytest_cache/
.ruff_cache/
```

### Метаданные Zenodo

| Поле | Значение |
|------|----------|
| Title | Scale-dependent WSPR response to geomagnetic storms — 18-month analysis with independent replication |
| Authors | Petrov, Alexey; Petrov, Makar |
| Description | Dataset and analysis scripts supporting "Scale-dependent WSPR response to geomagnetic storms" |
| Keywords | WSPR, ionosphere, geomagnetic storms, Kp index, Dst index, HF propagation, scale-dependence, citizen science |
| License | MIT (code) + CC-BY-4.0 (data) |
| DOI | Получим после upload |
| Related identifiers | Link to arXiv pre-print (when available) |

### Процесс

1. Зарегистрироваться на https://zenodo.org (можно через GitHub OAuth)
2. Создать новый upload
3. Заполнить метаданные (таблица выше)
4. Загрузить zip-архив `crosscorr-zenodo.zip`
5. Сохранить как draft → показать научному руководителю
6. После одобрения → Publish
7. DOI станет активен

### Порядок публикации

1. **Сначала arXiv** (pre-print, без DOI Zenodo)
2. **Параллельно/после**: Zenodo (данные + код)
3. **После рецензии**: финальные версии с cross-references

### Примечания

- arXiv и Zenodo — независимые системы. DOI Zenodo не требуется для arXiv.
- Zenodo автоматически версионирует: v1, v2, v3 при обновлении данных.
- GitHub-репозиторий можно связать с Zenodo через Webhook (автоархивация
  каждого release).
- Размер unified.parquet (79k строк) — несколько MB, подходит для Zenodo
  (ограничение 50 GB per dataset).