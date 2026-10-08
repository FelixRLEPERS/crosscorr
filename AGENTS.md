# AGENTS.md — CrossCorr

## Что это за проект
CrossCorr — воспроизводимый научный артефакт для анализа ионосферных бурь
по данным WSPR (citizen science) + независимым индексам космической погоды.
Целевая площадка: AGU / Space Weather (Wiley).

## Стек
- Python 3.10+ (CI: 3.11, 3.12)
- pyproject.toml (PEP 621), pip-tools, requirements.lock
- ruff, mypy, pytest, pytest-cov
- pandas / numpy / statsmodels / scipy
- LaTeX (AGU template) в `paper/`
- Parquet для unified-схемы

## Структура (ключевое)
- `crosscorr_lib/analysis/` — 20 модулей статистического ядра
- `data/scripts/` — 13 ETL-скриптов; `data/processed/unified.parquet` — gitignored
- `scripts/` — 15 скриптов анализа
- `tests/` — 291 тест
- `paper/` — статья (AGU)
- `docs/` — методология, pipeline, AI_ASSISTANCE.md
- `audit/` — версионированные аудиты (не удалять, это часть прозрачности)

## Команды
- Установка: `pip install -e ".[dev,all]"`
- Линт: `ruff check .`
- Типы: `mypy crosscorr_lib`
- Быстрые тесты: `pytest -m "not slow"`
- Все тесты: `pytest`
- Покрытие: `pytest --cov=crosscorr_lib --cov-fail-under=45` (план: поднять до 70)
- ETL: `python data/scripts/fetch_all.py`
- Главный результат: `python scripts/perm_test_18mo_3band.py`

## Правила для агентов
- НЕ менять исходный код без явного подтверждения пользователя.
- НЕ логировать секреты, .env, API-токены. При находке — маскировать.
- НЕ коммитить `data/raw/`, `data/processed/unified.parquet`, артефакты LaTeX.
- НЕ удалять и не переписывать файлы в `audit/` — это доказательная база.
- НЕ трогать `paper/` без запроса (там завязана submission-версия).
- Все новые параметры анализа — через CLI-флаги или `config.yaml`,
  без hardcoded дат.
- Экспериментальные модули (`mutual_info.py`, `transfer_entropy.py`, `mse.py`,
  `cross_mfdfa.py`) не трогать как production — либо доводить, либо выносить
  в отдельную ветку.
- Перед пушем — ruff + mypy + pytest (not slow).
- Всё важное для будущих чатов писать в файлы репозитория, а не в память чата.

## Известные системные ограничения
- WSPR API (`wspr.live`) требует VPN из некоторых регионов.
- Windows: см. `tests/test_shared_memory_cleanup.py` (shared_memory cleanup).
- Held-out период (Jan–Mar 2026) содержит N_storm = 23 часа — статистическая
  мощность ограничена, это ожидаемо и признано в Limitations.
