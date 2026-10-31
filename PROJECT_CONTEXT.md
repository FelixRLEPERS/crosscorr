# PROJECT_CONTEXT.md — CrossCorr

## Назначение
Исследование отклика ионосферных ВЧ-трасс на геомагнитные бури по данным
распределённой сети WSPR. Основная гипотеза: фиксированная популяция
уязвимых трасс демонстрирует baseline invariance; отклик scale-dependent
по Kp.

## Стек и окружение
Python 3.10+, ruff, mypy, pytest (369 тестов), CI на 3.11/3.12 + Windows job.
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
- Все 3 диапазона (20/40/15 м) — негативный отклик в шторм.
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

## Статус (обновлено 2026-10-30)

**Q1 Audit Passed. Manuscript (EN/RU) ready for submission to Space Weather.
Cover Letter addressed to Dr. Steven K. Morley. Zenodo v11 published
(Version DOI: 10.5281/zenodo.23802881). Status: HOLD (awaiting HamSCI feedback).**

- **HamSCI review (Gwyn Griffiths, G3ZIL, 15 комментариев):** 8 sub-rows
  закрыты в манускрипте (commit `3f68d55`) — L1 Key Points (plain language),
  L3b+L4c+L4f (один joint-Limitations «Index scaling and path diversity»:
  quasi-log Kp, hop-count, FT8), L4b Doppler spread, L5 F-region,
  L11 avg(snr) (геометрическое среднее линейного SNR), L12 Station
  geography; 6 solved ранее, 2 stale, 2 editorial (A1/A2) — за авторами.
  Point-by-point: `docs/submission/Response_to_HamSCI.md`.
- **3 статфикса Q1:** IAAFT-суррогаты вместо phase (`surrogate.py`,
  default `surrogate_method="iaaft"`); ESS через интегральное время
  автокорреляции τ_int (не AR(1)); снято двойное Fisher Z в max-stat
  (сырой max|r|, `fisher=False`).
- Cover letter: `docs/submission/Cover_Letter_SpaceWeather.tex`.
- arXiv: готово. Бывшие MUST-пункты закрыты: Zenodo DOI → v11,
  CRediT → есть в `paper/main.tex` (Contributor Roles Taxonomy);
  hardcoded даты — под правилом AGENTS.md (CLI/config).
- Оценка Reviewer 2: 8.0/10, Accept with minor revisions (исторично).

## Известные риски
- Критично: данные не в репо → reproducibility блокер для журнала.
- Small N в held-out (N_storm=47 frozen / 70 extended).
- Spatial aggregation маскирует регион-специфичные эффекты (PCA vs mid-lat MUF).
- Overclaiming "fixed population of vulnerable paths" — смягчить формулировку.
- Low coverage threshold (45%).
- Экспериментальные модули в main branch.
