# Данные

## Формат унифицированной таблицы

| Колонка | Тип | Описание |
|---|---|---|
| timestamp_utc | datetime64[ns, UTC] | Время наблюдения |
| detector_id | string | Уникальный идентификатор источника/детектора |
| detector_type | string | Тип: wspr, magnetometer, gnss, ionosonde, ballistic, ... |
| value | float | Сырое наблюдение до применения модели |
| residual | float | Остаток после базовой модели (`value - model`) |
| residual_method | string | Какая модель дала остаток: mixedlm_ballistic, ols_geomagnetic, none |
| unit | string | Единица `value`: dB (WSPR), nT (магнитометр), AU (эфемериды) |
| quality_flag | int | 0 — наблюдение есть и модель оценена; 1 — нет данных или модель не сошлась |
| meta | json | Доп. поля (широта, долгота, оператор и т.п.) |

Базовая модель выбирается по `detector_type` и описана в
[`crosscorr_lib/analysis/residuals.py`](../crosscorr_lib/analysis/residuals.py).
Если конфаундеры (`data/confounders.csv`) недоступны, модель не оценивается:
`residual_method = "none"`, `residual = value`.

## Источники

См. таблицу в корневом README.md.

## Лицензии

Каждый источник имеет свою лицензию. Перед публикацией данных
убедитесь, что условия позволяют редистрибуцию.
Сырые данные в репозиторий НЕ коммитятся — только скрипты загрузки.