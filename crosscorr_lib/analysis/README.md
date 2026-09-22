# Анализ

Пайплайн анализа (запускать в этом порядке):

1. `python data/scripts/download_wspr.py --date 2025-01-01`
2. `python data/scripts/download_intermagnet.py --file path/to/file.min`
3. `python data/scripts/download_horizons.py --planet mars --start 2025-01-01 --stop 2025-02-01`
4. `python data/scripts/unify_schema.py`
5. `python data/scripts/make_sample.py`
6. `python code/analysis/cross_correlation.py`
7. `python code/analysis/surrogate.py --n 1000`
8. `python code/analysis/mfdfa.py`

Результаты складываются в `results/`.