# CrossCorr — аудит v5

## 0. Мета

- Дата: 2026-10-06.
- HEAD: `b84170a36b5fbba484b34245e330cc0d7e4f82f4`
- Ветка: `main`; рабочее дерево чистое на момент отчёта.
- Что изменилось с v4: закрыты TE-1, TE-2, MI-1, MSE-1, XM-3, XM-4, XM-6;
  проведён бенчмарк N=4000 (`037e0e1`); синхронизирован реестр
  (BACKLOG/PROJECT_STATE/STOP_DECISIONS, `b84170a`): группа V5 — 12 findings,
  всего 170 (130 closed, 15 STOP, 6 deferred).

## 1. Что закрыто с v4

| ID | класс | был severity | коммит | что сделано |
|---|---|---|---|---|
| TE-1 | STAT | P1 | `54ac8af` | API gated: `k>1` → `NotImplementedError`; покомпонентное усреднение CMI удалено; k=1 — Schreiber TE |
| TE-2 | BUG | P1 | `54ac8af` | `_validate_inputs`: finite-policy через `_as_1d`, валидация k/lag/k_nn ≥ 1, unequal length → ValueError |
| MI-1 | STAT | P1 | `3c627d6` + `c84ffa4` | `UserWarning` на точных дубликатах, валидация k/base, docstring: «предполагает непрерывные распределения» |
| MSE-1 | BUG | P1 | `3c627d6` | Контракт: константный ряд → SampEn 0.0, A=0 при B>0 → inf; валидация empty/m/r/all-NaN; тесты |
| XM-3 | STAT | P2 | `dd6eb92` | Добавлены `r_squared` (по q) и `n_scales`; UserWarning при R² < 0.95 |
| XM-4 | BUG | P2 | `dd6eb92` | Равные длины, конечность, n ≥ 100, валидация q/scales (пустые/nonfinite/≤0/ > n → ValueError) |
| XM-6 | TEST | P2 | `dd6eb92` | 5 новых тестов: unequal lengths, scales > n, пустой q, NaN/Inf, diagnostics |

## 2. Что осталось открытым

- XM-1, XM-2 — DEFERRED; причина: reference-валидация (см. §1.4 AUDIT_v4.md);
  формула не трогалась, в docstring `TODO(XM-1, XM-2)`.
- MI-3, TE-3, XM-5 — DEFERRED; причина: оптимизация; бенчмарк проведён
  (`037e0e1`), задача — в `docs/roadmap.md`.
- MI-2, MI-4, TE-4, MSE-2, MSE-3, MSE-4 — P2, не приоритет.

## 3. Новые findings v5

- MI/TE matrices > 60 сек на N=4000 × 10 каналов (bench подтвердил PERF-заметки
  MI-3, TE-3 из AUDIT_v4; commit `037e0e1`).
- Категория: PERF, severity P1 (для production N>2000).

## 4. Performance benchmarks

Источник: `bench/results_v5.txt` (N=4000, 10 каналов; лимит 60 сек; память
трассировалась tracemalloc в отдельном процессе):

| Модуль | Время | Память |
|---|---|---|
| MI matrix (`mutual_information_matrix`) | > 60 сек | не измерено |
| TE matrix (`transfer_entropy_matrix`) | > 60 сек | не измерено |
| MSE | 0.03 сек | 0.2 МБ |
| Cross-MFDFA | 0.68 сек | 0.2 МБ |

## 5. Классификация findings v5

| ID | класс | severity | статус | Кратко |
|---|---|---|---|---|
| MI-1 | STAT | P1 | CLOSED `3c627d6` + `c84ffa4` | KSG: policy для ties — UserWarning + валидация |
| MI-3 | PERF | P2 | DEFERRED `037e0e1` | pointwise KDTree range queries; bench: > 60 c на N=4000 |
| TE-1 | STAT | P1 | CLOSED `54ac8af` | k>1 gated, joint-history estimator не реализован |
| TE-2 | BUG | P1 | CLOSED `54ac8af` | валидация входов: finite, равные длины, k/lag/k_nn |
| TE-3 | PERF | P2 | DEFERRED `037e0e1` | N*(N-1) оценок; bench: > 60 c на N=4000 |
| MSE-1 | BUG | P1 | CLOSED `3c627d6` | constant → 0.0; контракт SampEn-пределов зафиксирован |
| XM-1 | STAT | P1 | DEFERRED | sign/abs cross-fluctuation: нужна reference-валидация §1.4 |
| XM-2 | STAT | P1 | DEFERRED | q→0 limit и sign-конвенция: нужна reference-валидация §1.4 |
| XM-3 | STAT | P2 | CLOSED `dd6eb92` | fit-diagnostics: `r_squared`, `n_scales` |
| XM-4 | BUG | P2 | CLOSED `dd6eb92` | валидация входов: длины, конечность, q, scales |
| XM-5 | PERF | P2 | DEFERRED `037e0e1` | nested polyfit; bench: 0.68 c при N=4000 |
| XM-6 | TEST | P2 | CLOSED `dd6eb92` | 5 новых тестов: cross-контрактные случаи |
| BENCH-1 | PERF | P1 | NEW (v5) | MI/TE matrices > 60 c на N=4000×10 — P1 для production N>2000 |

## 6. Топ-5 действий на v6

1. Reference-валидация Cross-MFDFA (XM-1, XM-2).
2. Reference-валидация KSG/CMI ties (MI-1 вторичный).
3. Оптимизация MI/TE matrices (пакетные запросы cKDTree).
4. Integration decision: standalone vs pipeline.
5. Синхронизация METHODOLOGY с реальным статусом.

## 7. Что осталось на v6

- Научные reference-валидации.
- Performance-оптимизация.
- Integration decision.
- Реальные WSPR/INTERMAGNET данные.
