# PROJECT_CONTEXT.md — CrossCorr

## Назначение
Исследование отклика ионосферных ВЧ-трасс на геомагнитные бури по данным
распределённой сети WSPR. Основная гипотеза: фиксированная популяция
уязвимых трасс демонстрирует baseline invariance; отклик scale-dependent
по Kp.

## Стек и окружение
Python 3.10+, ruff, mypy, pytest (291 тест), CI на 3.11/3.12 + Windows job.
Data pipeline: `data/scripts/fetch_all.py` → `unified.parquet`
(schema: detector_type, detector_id, value, timestamp_utc, unit, quality_flag).

## Источники данных
| Source | Resolution | Access |
|---|---|---|
| wspr.live | 1 h | Public ClickHouse API |
| GFZ Potsdam | 3 h | Public JSON |
| WDC Kyoto | 1 h | Public |
| NOAA SWPC | Monthly | Public |
| JPL Horizons | 1 h | Public API |

Период анализа: 2024-04-01 .. 2025-09-30.
Held-out: Jan–Mar 2026.

## Методология (ядро)
- Block permutation test (block_size = 24 h, 10 000 итераций, seed=42).
- Residuals: value − mean(month × hour_of_day × day_of_week).
- Kp bins: [5,6), [6,7), [7,∞), все попарные сравнения + FDR.
- FDR: Benjamini-Hochberg (основной) + Benjamini-Yekutieli (консервативный).
- ESS/IAT, block bootstrap, mixed-effects residuals (`residuals.py`).
- Negative controls, statistical reference tests.

## Ключевой результат
- Все 3 диапазона (10/15/20 м?) — негативный отклик в шторм.
- Scale-dependence: Kp≥6 → −42.8%.
- Baseline invariance для 15 м: коэффициент 0.42× (требует аккуратной
  формулировки в §7.5).
- Day/night asymmetry: НЕ воспроизвелась в held-out (признано).

## Ключевые файлы
- `crosscorr_lib/analysis/surrogate.py` (28 KB) — суррогаты, FDR, Davison-Hinkley
- `crosscorr_lib/analysis/block_bootstrap.py` — блок-бутстрап
- `crosscorr_lib/analysis/effective_sample.py` — ESS/IAT
- `crosscorr_lib/analysis/residuals.py` (18 KB) — MixedLM/OLS
- `crosscorr_lib/analysis/power_curve.py` — power analysis
- `scripts/perm_test_18mo_3band.py` — главный тест
- `docs/first_result.md` (40 KB) — отчёт по результатам
- `docs/methodology.md` (14 KB)
- `docs/AI_ASSISTANCE.md` — disclosure

## Состояние перед submission
- arXiv: готово.
- Space Weather: при условии 3 MUST-действий:
  1. Zenodo/Figshare DOI для `unified.parquet`.
  2. CRediT statement.
  3. Параметризация периодов анализа (убрать hardcoded даты).
- Оценка Reviewer 2: 8.0/10, Accept with minor revisions.

## Известные риски
- Критично: данные не в репо → reproducibility блокер для журнала.
- Small N в held-out (N_storm=23).
- Spatial aggregation маскирует регион-специфичные эффекты (PCA vs mid-lat MUF).
- Overclaiming "fixed population of vulnerable paths" — смягчить формулировку.
- Low coverage threshold (45%).
- Экспериментальные модули в main branch.
