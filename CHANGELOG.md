# Changelog

Значимые изменения проекта документируются в этом файле.
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

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
