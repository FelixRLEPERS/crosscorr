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

# 4. Кросс-корреляция (наивная, быстро)
python -m crosscorr_lib.analysis.cross_correlation

# 5. Кросс-корреляция с ESS (научно)
python -m crosscorr_lib.analysis.cross_correlation --use-ess

# 6. Surrogate-тесты и FDR
python -m crosscorr_lib.analysis.surrogate --n 1000 --alpha 0.05

# 7. MFDFA
python -m crosscorr_lib.analysis.mfdfa

# 8. Distance-based analysis
python -m crosscorr_lib.analysis.distance_analysis