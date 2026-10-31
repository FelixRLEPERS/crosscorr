# TODO.md — CrossCorr

## MUST (до submission в Space Weather)
- [x] Загрузить `data/processed/unified.parquet` в Zenodo/Figshare,
      получить DOI, добавить в Data Availability statement.
      (Готово: Zenodo v11, DOI 10.5281/zenodo.23802881, 2026-10-30.)
- [x] Добавить CRediT author contributions (A.P., M.P.) в paper.
      (Готово: секция Author Contributions, `paper/main.tex`.)
- [ ] Параметризовать периоды в `scripts/perm_test_18mo_3band.py`
      через CLI / config.yaml (убрать hardcoded '2024-04-01 .. 2025-09-30').
      (Проверено 2026-10-31: НЕ сделано — argparse: только
      --exclude-flares/--flare-threshold/--norm-tx/--out; даты
      захардкожены в строках 57 и 328 скрипта.)

## SHOULD (в течение недели)
- [x] Поднять `--cov-fail-under` с 45 до 70 в CI (2026-10-27, `ci.yml:64`).
- [ ] Добавить spatial analysis (Great Circle path geometry) в Future Work.
- [x] Явно признать small N (N_storm=47 frozen / 70 extended) в Limitations —
      реализовано в main.tex:1535.
- [ ] Смягчить формулировку "fixed population of vulnerable paths"
      → "structurally constrained population of marginally viable paths".
- [ ] Ювелирно объяснить §7.5 коэффициент 0.42× для 15 м (MUF depression).
- [ ] Признать non-replication day/night asymmetry как intermittent
      auroral/PCA эффект.

## Технический долг
- [ ] Вынести experimental-модули из main branch или довести до production.
      `mse.py` и `cross_mfdfa.py` — **вынесены в ветку `experimental`**
      (2026-10-27, в `main` отсутствуют); `mutual_info.py` и
      `transfer_entropy.py` остаются exploratory в `main` (на них ссылается
      статья, Limitations).
- [ ] Добавить docstrings к публичным функциям (проверить покрытие).
- [ ] Проверить/закрепить версии зависимостей в requirements.lock.

## Nice-to-have
- [ ] Colorblind-friendly палитры (viridis / cmocean) во всех графиках.
- [ ] 95% CI error bars — проверить, что везде есть (v13 — ок).
- [ ] Добавить 2–3 свежих (2024–2025) reference по WSPR / HamSCI.
- [ ] Ссылка на IAGA Kp index documentation.

## Перед arXiv (готово)
- [x] arXiv-ready: аудит подтверждает.
