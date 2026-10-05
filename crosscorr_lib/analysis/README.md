# Анализ

Пайплайн анализа (запускать в этом порядке):

```bash
# 1. Скачать данные
python data/scripts/download_wspr.py --date 2025-01-01
python data/scripts/download_intermagnet.py --file path/to/file.min
python data/scripts/download_horizons.py --planet mars --start 2025-01-01 --stop 2025-02-01

# 2. Унифицировать
python data/scripts/unify_schema.py

# 3. Проверить стационарность
python -m crosscorr_lib.analysis.stationarity

# 4. Кросс-корреляция (max-statistic, по умолчанию)
#    max-statistic is now default; naive path opt-in via --use-naive
python -m crosscorr_lib.analysis.cross_correlation

# 5. Кросс-корреляция с ESS (научно)
#    ESS применяется только к single-lag корреляциям, поэтому
#    требует наивного пути: --use-ess без --use-naive завершается ошибкой.
python -m crosscorr_lib.analysis.cross_correlation --use-naive --use-ess

# 6. Surrogate-тесты и FDR
python -m crosscorr_lib.analysis.surrogate --n 1000 --alpha 0.05

# 7. MFDFA
python -m crosscorr_lib.analysis.mfdfa

# 8. Distance-based analysis
python -m crosscorr_lib.analysis.distance_analysis
```

## Модули

| Модуль | Назначение |
|---|---|
| `cross_correlation.py` | Лаговая CC, max-statistic null, CLI |
| `surrogate.py` | Фазовые суррогаты, FDR (BY/BH), Davison-Hinkley p-value |
| `effective_sample.py` | ESS / IAT (только zero-lag, deprecated для лагов) |
| `block_bootstrap.py` | Block bootstrap для нестационарных рядов |
| `preprocessing.py` | Detrend + standardize |
| `confounders.py` | Удаление Kp/Dst/F10.7 (МНК) |
| `stationarity.py` | ADF-тест |
| `mantel.py` | Mantel test матриц корреляции и расстояния |
| `distance_analysis.py` | CC-vs-расстояние (Mantel default, OLS опция) |
| `mfdfa.py` | Мультифрактальный анализ |
| `residuals.py` | Базовая модель остатков (MixedLM / МНК) |
| `power_curve.py` | Оценка мощности теста |
| `benchmark_utils.py` | Утилиты бенчмарка |
| `visualization.py` | Графики (scatter, heatmap) |