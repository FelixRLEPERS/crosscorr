# TODO.md — CrossCorr

## MUST (до submission в Space Weather)
- [ ] Загрузить `data/processed/unified.parquet` в Zenodo/Figshare,
      получить DOI, добавить в Data Availability statement.
- [ ] Добавить CRediT author contributions (A.P., M.P.) в paper.
- [ ] Параметризовать периоды в `scripts/perm_test_18mo_3band.py`
      через CLI / config.yaml (убрать hardcoded '2024-04-01 .. 2025-09-30').

## SHOULD (в течение недели)
- [ ] Поднять `--cov-fail-under` с 45 до 70 в CI.
- [ ] Добавить spatial analysis (Great Circle path geometry) в Future Work.
- [ ] Явно признать small N (N_storm=23) в Limitations.
- [ ] Смягчить формулировку "fixed population of vulnerable paths"
      → "structurally constrained population of marginally viable paths".
- [ ] Ювелирно объяснить §7.5 коэффициент 0.42× для 15 м (MUF depression).
- [ ] Признать non-replication day/night asymmetry как intermittent
      auroral/PCA эффект.

## Технический долг
- [ ] Вынести experimental-модули (`mutual_info.py`, `transfer_entropy.py`,
      `mse.py`, `cross_mfdfa.py`) из main branch или довести до production.
- [ ] Добавить docstrings к публичным функциям (проверить покрытие).
- [ ] Проверить/закрепить версии зависимостей в requirements.lock.

## Nice-to-have
- [ ] Colorblind-friendly палитры (viridis / cmocean) во всех графиках.
- [ ] 95% CI error bars — проверить, что везде есть (v13 — ок).
- [ ] Добавить 2–3 свежих (2024–2025) reference по WSPR / HamSCI.
- [ ] Ссылка на IAGA Kp index documentation.

## Перед arXiv (готово)
- [x] arXiv-ready: аудит подтверждает.
