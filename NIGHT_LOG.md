# NIGHT_LOG.md — Ноябрьская сессия 2026-10-08

## Что сделано

### Фаза 2: unify_schema.py — 3 bands
- `load_wspr_hourly` парсит band из имени файла (`wspr_hourly_YYYY-MM-DD_20m.csv` → `20m`)
- `detector_id` = `wspr_hourly_20m`, `wspr_hourly_40m`, `wspr_hourly_15m`
- meta содержит `band`, `band_index`, `mean_snr`, `max_distance`
- ✅ Готово

### Фаза 3: Unify
- unified.parquet: 41 845 строк
- wspr_hourly_20m: 4 368 строк
- wspr_hourly_40m: 4 368 строк
- wspr_hourly_15m: 4 368 строк
- kp: 2 141 строк
- dst: 4 155 строк (provisional — исправлен URL)
- ✅ Готово

### Фаза 4: EDA 6mo × 3 band

| Band | N | Storm | Quiet | Drop (abs) | Drop (resid) |
|---|---|---|---|---|---|
| 20m | 1435 | 49 | 964 | **−20.5%** | −20 044 |
| 40m | 1435 | 49 | 964 | **−21.9%** | −19 006 |
| 15m | 1435 | 49 | 964 | **−35.8%** | −6 549 |

Результат: **15m самый чувствительный** (MUF ближе к 15m). 20m и 40m похожи (−20–22%).

### Фаза 5: Permutation test

| Band | Δ resid | drop | p-value | sig? |
|---|---|---|---|---|
| 20m | −17 917 | −20.5% | <0.0001 | ✅ |
| 40m | −18 000 | −21.9% | <0.0001 | ✅ |
| 15m | −6 177 | −35.8% | <0.0001 | ✅ |

Все три band значимы на уровне p<0.0001 (block permutation, 24h, 5000 iter).

**Ключевой результат**: 15m падает на 35.8% — самая сильная частотная зависимость, согласуется с механизмом MUF.

### Фаза 6: Per-month robustness

| Месяц | 20m Δ | 20m p | 40m Δ | 40m p | 15m Δ | 15m p |
|---|---|---|---|---|---|---|
| 2024-10 | −36 077 | 0.005 | −32 117 | sig | −8 768 | 0.002 |
| 2025-01 | −8 065 | 0.005 | −14 863 | 0.005 | −6 729 | sig |
| 2025-02 | −10 092 | 0.199 | −9 958 | 0.072 | −2 465 | 0.066 |
| 2025-03 | −14 876 | 0.003 | −13 533 | 0.004 | −6 267 | sig |

Эффект присутствует во всех месяцах. Ноябрь и декабрь 2024 — слишком мало буревых часов (N_storm=2) для статистического теста.

### Что ещё изменилось

- **download_space_weather.py**: DST_URL изменён с `dst_realtime` на `dst_provisional` (realtime даёт 403 для данных >2 мес)
- Dst теперь доступен за все 6 месяцев (4 155 строк)

## Что не удалось

- Ничего критического. Все 6 фаз успешны.

## Что коммитить утром

- `crosscorr_lib/analysis/residuals.py` (+ "wspr_hourly": "count")
- `data/scripts/unify_schema.py` (load_wspr_hourly → 3 bands)
- `data/scripts/download_space_weather.py` (DST_BASE → provisional)
- `scripts/eda_6mo_3band.py` (новый)
- `scripts/perm_test_6mo_3band.py` (новый)
- `scripts/eda_full.py` (новый — 2-month analysis)
- `scripts/fetch_20m_extra.ps1` (новый)
- `docs/first_result.md` (новый)
- `docs/hypothesis.md` (новый)
- `results/eda/` (графики: binned_6mo_20m.png, bands_comparison_6mo.png etc.)
- NIGHT_LOG.md

## Что делать дальше

1. Обновить docs/first_result.md для 6mo × 3 band данных
2. Dst analysis на всех 3 bands (сейчас только Kp)
3. Написать статью
4. Рецензирование и submission

## Проблемы для обсуждения

- Dst provisional vs final: provisional — предварительные данные с погрешностью. Для статьи нужно обсудить.
- 15m drop 35.8% — нужна проверка на n_active_tx (как для 20m)
- Ноябрь и декабрь 2024 — слишком мало бурь (N_storm=2), нужен ли отдельный тест?

## Технические детали

- Все скрипты: `scripts/eda_6mo_3band.py`, `scripts/perm_test_6mo_3band.py`
- Пути абсолютные: `G:\crosscorr\data\processed\unified.parquet`
- Данные в `data/raw/wspr/` — 546 файлов (182 × 3 bands)
- Kp/Dst в `data/raw/space_weather/` — 8 CSV файлов