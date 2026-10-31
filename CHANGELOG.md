# Changelog

Значимые изменения проекта документируются в этом файле.
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

## [Unreleased]

## [1.6.1] - 2026-10-31
### Added
- Примечание о воспроизводимости живых API: абзац в Data Availability
  (для анализа удерживаемого периода использовать заархивированный
  снимок Zenodo, а не живые-запросы `wspr.live`) и пункт Limitations
  «API dependence» — EN+RU (`paper/main.tex`, `paper/main_ru.tex`).
- Version mapping в README: манускрипт (submission v1.0) ↔ тег кода
  `v1.6.1` ↔ dataset snapshot v11.
- `checksums_v1.6.1.txt` (8 файлов; только tracked-пути).
### Changed
- Cover letter (`docs/submission/Cover_Letter_SpaceWeather.tex`): дата
  зафиксирована явно (October 31, 2026 вместо `\today`), DOI кода
  обновлён до 10.5281/zenodo.23838116; README и CITATION.cff
  синхронизированы с этим DOI (version 1.6.1).

## [1.6.0] - 2026-10-31
### Added
- Major statistical audit (Q1): IAAFT-суррогаты вместо phase-рандомизации, ESS через τ_int (интегральное время автокорреляции) вместо AR(1), снятие двойного Fisher Z в max-stat (сырой max|r|).
- Physical controls: исключение GOES X-ray вспышек M1.0+ (`--exclude-flares`), нормировка на активные передатчики (TX normalization, `scripts/spatial_analysis.py`), обсуждение Doppler spread (decode-channel loss) в Discussion.
- Расширенный удерживаемый период Jan–Jun 2026 (sensitivity check):
  Limitations + Appendix `tab:heldout_sensitivity` (EN+RU); primary
  held-out остаётся Jan–Mar 2026.
- HamSCI review addressed (Gwyn Griffiths, G3ZIL): 15 комментариев → point-by-point `docs/submission/Response_to_HamSCI.md`; 8 sub-rows закрыты в манускрипте (commit `3f68d55`); cover letter `docs/submission/Cover_Letter_SpaceWeather.tex` (Space Weather, Dr. Steven K. Morley).
### Changed
- Zenodo v11 опубликован (Version DOI: 10.5281/zenodo.23802881); манускрипт EN/RU готов к подаче, статус: HOLD (awaiting HamSCI feedback).

## [1.5.0] - 2026-10-27
### Added
- 102 новых теста: 43 для `safe_exec.py`, 24 для `power_curve.py`, 11 для `distance_analysis.py`, 11 для `mantel.py`, 8 для `stationarity.py`, 5 для `mfdfa.py` (всего в наборе 369 тестов, покрытие 58% -> 85%).
- Жесткий порог покрытия 70% в CI (`--cov-fail-under=70`).
### Fixed
- Баг в `benchmark_utils.py`: флаг `--null` теперь корректно передается в `max_lag_surrogate_pvalue`.
- Баг в `power_curve.py`: параметр `ar` теперь передается в `benchmark()`.
- Баг в `mantel.py`: `build_dist_matrix()` теперь корректно заполняет диагональ нулями.
- `PowerPoint.null_model` записывает фактически использованную модель (неизвестные имена, например `block`, нормализуются в `phase`).
### Removed
- Мертвый код (`mse.py`, `cross_mfdfa.py`) перенесен в ветку `experimental`.
