# Методология

1. **Унификация** — приведение всех данных к формату `timestamp_utc, detector_id, detector_type, value, residual, residual_method, unit, quality_flag, meta`.
   `value` — сырое наблюдение, `residual` — остаток после базовой модели.
2. **Базовая модель** — оценка остатков `residual = value - model(value)` в `crosscorr_lib/analysis/residuals.py`:
   - `detector_type == "ballistic"` — смешанная линейная модель (statsmodels MixedLM)
     по формуле `value ~ charge_temp + mass + (1|range_id)`, т.е. остаток после
     вычета температуры заряда, массы и случайного эффекта полигона;
   - остальные типы детектора — МНК `value ~ kp + dst + f107` (физические
     конфаундеры: Kp, Dst, F10.7);
   - если конфаундеры не переданы, модель не оценивается: `residual_method = "none"`, `residual = value`.
   При ошибке фита `residual = NaN`, `quality_flag = 1`.
   Латинские имена колонок `charge_temp`, `mass`, `range_id` — контракт модуля:
   в `README.md` та же формула записана по-русски как `v0 ~ T_заряда + масса + (1|полигон)`.
3. **Пространственная модель** — PyMC с экспоненциальным ядром ковариации (planned).
4. **Кросс-корреляция** — матрица корреляций между детекторами по колонке `residual`.
   Перед расчётом вызывается `preprocess` (снятие линейного дрейфа + стандартизация).
   Для лаговой гипотезы используется **max-statistic null** через суррогаты
   (`max_lag_surrogate_pvalue`): тестируется $T = \max_\tau |r(\tau)|$ против
   того же максимума на суррогатах; по умолчанию `fisher=True` (веса
   $\sqrt{n_\text{valid}-3}$).
5. **MFDFA** — мультифрактальный анализ (`crosscorr_lib/analysis/mfdfa.py`).
6. **Surrogate-тесты** — фазовые суррогаты по умолчанию (200 из CLI, 500 в
   `max_lag_surrogate_pvalue`, 1000+ для публикаций). Доступны также `iaaft`
   (сохраняет распределение) и `time_shift` через параметр `surrogate_method`.
   Альтернатива для нестационарных рядов — **block bootstrap**
   (`crosscorr_lib/analysis/block_bootstrap.py`).
7. **FDR-коррекция** — контроль ложных обнаружений. По умолчанию
   Benjamini-Yekutieli (`method="by"`), Benjamini-Hochberg доступен
   опционально. Реализация: `crosscorr_lib/analysis/surrogate.py:fdr_bh_q`.
8. **Distance-based analysis** — основной метод Mantel test
   (`crosscorr_lib/analysis/mantel.py`), OLS-регрессия как опция
   (`crosscorr_lib/analysis/distance_analysis.py`, `--method ols`).

## ESS: область применимости

`correlation_pvalue_with_ess` (`crosscorr_lib/analysis/effective_sample.py`)
считает корреляцию на **нулевом лаге** и эффективный размер выборки
`N_eff = N / max(τ_x, τ_y)`, где `τ_x`, `τ_y` — интегрированные времена
автокорреляции каждой серии отдельно.

**Ограничение (P1-11).** Совместная (кросс-)корреляционная структура
`x` и `y` в `N_eff` не входит, поэтому для связанных с лагом пар
`N_eff` завышается, а p-value становится антиконсервативным. Модуль
пригоден только для тестов на нулевом лаге; для лаговой гипотезы —
основной гипотезы проекта — используйте max-statistic null через
суррогаты (`max_lag_surrogate_pvalue`). Флаг CLI `--use-ess`
сохранён как deprecated и требует `--use-naive`; он не рекомендуется
для публикационных результатов.

## Что измеряется в `value`

Единица зависит от типа детектора и задана в `DETECTOR_UNITS`
(`crosscorr_lib/analysis/residuals.py`): WSPR — SNR в дБ, магнитометр —
X-компонента в нТ, эфемериды — гелиоцентрическое расстояние в а.е.
Смешивать эти величины в один ряд нельзя, поэтому корреляции всегда
считаются между детекторами одного типа, а сравнение идёт по `residual`
после вычитания физической модели.