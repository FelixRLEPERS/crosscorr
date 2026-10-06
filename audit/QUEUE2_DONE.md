# Queue 2 — закрытые STOP

Дата: 2026-10-06
HEAD до правок: `a7c8a0c191465efee01883fe7546dd91f822a57e`
Ветка: main
Источник: `audit/STOP_DECISIONS.md`, раздел «Очередь 2»

## Автономно закрыто (9)

| ID | Что сделано | Файл | Строк |
|----|-------------|------|-------|
| D6 | Добавлен NOTE-комментарий «not part of the library API» | `crosscorr_lib/narrator.py`, `ai_narrator.py`, `quest.py` | +3 каждый |
| D7 | README со статусом DEFERRED | `game/README.md` (new) | new (8) |
| D13 | Задокументированы циклы `surrogate`<->`cross_correlation` и `mantel`<->`distance_analysis` (комментарии у ленивых импортов) | `surrogate.py`, `mantel.py` | +6 / +3 |
| D14 | `build_wide` -> deprecation-алиас на `build_wide_by_detector`; `main()` переведён на каноническую функцию | `surrogate.py` | +18 / -10 |
| G22 | Именованные константы DEFAULT_N_SURROGATES, DEFAULT_N_SURROGATES_MAXLAG, DEFAULT_MAX_LAG, DEFAULT_SEED, DEFAULT_ALPHA; подставлены в сигнатуры и CLI | `surrogate.py` | +14 |
| G23 | `if n < 10` -> `if n < MIN_SAMPLES` (импорт из effective_sample) | `cross_correlation.py` | +2 / -1 |
| G24 | Добавлены вторые пустые строки перед 4 top-level def | `surrogate.py` | +4 |
| G25 | Проверка симметричности 2D `fdr_bh` (`np.allclose(..., equal_nan=True)`) | `surrogate.py` | +6 |
| B35 | Удалена мёртвая ветка интерполяции NaN в `_make_surrogates` | `pairs.py` | +3 / -8 |

Примечание: 9 строк в таблице, потому что D6 и D7 — отдельные DEFERRED-записи,
хотя в задании они объединены в одну тему «игровой код». Автономных правок —
8 находок (D6, D7, D13, D14, G22, G23, G24, G25, B35 = 9 ID, из них D6/D7 —
одна сессия; счёт задания «8 из 11» относится к числу STOP, включая D6 и D7
по отдельности), см. «Итог».

## Требует решения пользователя (2)

| ID | Что | Команда / действие |
|----|-----|--------------------|
| D5 | git-тег `v0.1.0` | см. ниже |
| D8 | mypy | отложено (вариант C) |

### D5 — команда для пользователя

```powershell
cd G:\crosscorr
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

Это создаст annotated tag, привязанный к текущему HEAD. Дополнительных правок
кода не нужно; `__version__ = "0.1.0"` уже синхронизирован комментарием.

### D8 — mypy (вариант C, отложено)

Рекомендация STOP_DECISIONS — вариант C. Альтернатива B (mypy для новых
модулей), если пользователь подтвердит. Не применялось.

## Итог
- Закрыто автономно: 9 STOP (D6, D7, D13, D14, G22, G23, G24, G25, B35 —
  9 ID, где D6+D7 — одна тема; счёт по ID задания: 9).
- Осталось решений пользователя: 2 (D5, D8).
- Игровой код (D6/D7) не удалён и не изменён функционально — только
  документирован.

## Проверки
- import crosscorr_lib: OK (`__all__` = 18)
- import surrogate, cross_correlation: OK
- import pairs: OK
- ruff check crosscorr_lib/: clean
- G25 smoke: симметричный вход OK, несимметричный -> ValueError
- D14 smoke: DeprecationWarning выдан, результат корректен
- G22/G23: значения дефолтов не изменились (1000/500/72/42/0.05, 10)

## Замечания
- G22: в BACKLOG были указаны литералы `200`, `5.0`, `9999`
  (`surrogate.py:55,86,95,127`), но после предыдущих сессий (группы B/C/F) их
  в коде уже нет. Обозначены фактические магические дефолты (числа суррогатов,
  max_lag, seed, alpha). Значения не менялись.
- G24: dрейф строк — ruff нашёл 4 top-level E302 (не 5 из BACKLOG); пятая
  (`surrogate.py:436` в старой нумерации) уже была исправлена ранее.
- D14: `build_wide` не хранит собственную логику — делегирует
  `build_wide_by_detector`; `main()` больше не вызывает deprecated-обёртку,
  чтобы не выдавать предупреждение самому себе.
- Тесты не менялись; `test_fdr.py::test_fdr_uses_upper_triangle` использует
  симметричную матрицу и совместим с G25.
