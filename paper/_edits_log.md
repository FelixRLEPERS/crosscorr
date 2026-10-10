# Edit Log — 2026-10-10

## Внесённые правки

### Сессия 1 (main.tex)
| № | Место | Что изменено |
|---|-------|--------------|
| 1 | §4.2    | Уточнение: 15 m и 20 m при Kp ≥ 7 |
| 2 | Key Points | Добавлено "On the 40 m band" |
| 3 | §2.1    | Пояснение про разрыв Oct–Dec 2025 |
| 4 | §3.3    | Пояснение об исключении Kp 3–5 |
| 5 | §5.5 п.4 | Ограничение по F10.7 (131–246 sfu, ratio ~1.9) |
| 6 | Code Avail. | Placeholders [FILL: commit hash], [FILL: Zenodo DOI] |

### Сессия 2 (references.bib + main.tex)
| № | Файл | Место | Что изменено |
|---|------|-------|--------------|
| 7 | references.bib | ~254 | Удалён TODO из cerwin2026 |
| 8 | references.bib | ~257–264 | potter2026: @article → @inproceedings |
| 9 | main.tex | ~937–938 | \url вокруг DOI вынесен за скобки |

## Результат компиляции
- main.pdf: 833357 байт, 20 страниц
- Дата компиляции: 2026-10-10 12:06
- Ошибки LaTeX: 0
- Undefined references: 0
- TeX Live 2026 (C:\texlive\2026\bin\windows)

## Placeholders, требующие ручного заполнения
- [FILL: commit hash] — main.tex:937
  Команда: git -C G:\crosscorr rev-parse --short HEAD
- [FILL: Zenodo DOI] — main.tex:938
  После настройки Zenodo-GitHub integration и создания release

## Требует проверки перед submission
- F10.7 range (131–246 sfu, ratio ~1.9) — сверить с NOAA SWPC
  Источник: data/processed/unified.parquet, detector_type='f107'
- Выброс F10.7 2026-09-15 = 105.41 sfu — вне training period,
  проверить откуда в parquet
- Пропуск Oct 2024 в F10.7 — проверить, есть ли данные в источнике

## Что осталось до submission
1. Заполнить [FILL: commit hash]
2. Заполнить [FILL: Zenodo DOI]
3. Сверить F10.7 с NOAA SWPC
4. Проверить выброс 2026-09-15
5. Разобраться с пропуском Oct 2024
6. git tag v1.0-paper + git push
7. Zenodo release → получить DOI → вставить в main.tex
8. Финальная компиляция
9. Анонс в HamSCI mailing list
