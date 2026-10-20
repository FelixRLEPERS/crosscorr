# HamSCI Science Telecon — 5 November 2026

Материалы 10-минутной презентации "Scale-dependent WSPR response to
geomagnetic storms". Докладчик: Alexey Petrov; соавтор: Makar Petrov
(в чате, не на сцене).

## Файлы

- slides.tex — исходник Beamer (тёмная тема, палитра из aep/CC_Data.js)
- slides.pdf — собранная дека, 10 слайдов, 16:9
- speaker_notes.md — дословный текст выступления: EN (что говорить) +
  RU (перевод и подсказки), по слайдам, с таймингом
- Q_and_A.md — 11 ответов на типичные вопросы (EN-ответ + RU-смысл)
- figures/ — статичные фигуры из paper/figures/ (fig1, fig2, fig4, fig5 и fig3_frequency_dependence_pointest)

## Сборка PDF

    cd docs/presentations/hamsci_2026-11-05
    pdflatex -interaction=nonstopmode -file-line-error slides.tex
    pdflatex -interaction=nonstopmode -file-line-error slides.tex

(второй прогон — для перекрёстных ссылок). Или из корня репозитория:

    python tmp_fix_pres_2_build.py

Скрипт сам проверяет slides.log на ошибки (строки "!", file:line,
Undefined Reference/Citation) и на число страниц (должно быть 10).

## Фигуры

Все фигуры статичные и лежат в figures/ — побайтовые копии из
paper/figures/. Динамических кадров и видео в деке нет; слайды 1 и 2
текстовые.

## Происхождение чисел и фигур

Все числа слайдов сверены с paper/main.tex (round-3 revision):
на экране — raw drops, adjusted-проверки только в speaker_notes и Q&A.
Q&A содержит 11 ответов. Копии фигур сделаны байтовыми, md5 совпадает
с paper/figures/.

Палитра слайдов: aep/CC_Data.js → PALETTE
(фон #060911, акцент #5CE1DB, текст #F1F5FB, приглушение #828BA0).

## Регенерация

Для пересборки достаточно запустить pdflatex дважды из папки
docs/presentations/hamsci_2026-11-05/ (или использовать
tmp_fix_pres_2_build.py, если он есть локально).

    python tmp_fix_pres_2_build.py    # slides.pdf (pdflatex x2 + лог)
    python tmp_fix_pres_3_notes.py    # speaker_notes / Q_and_A / README

Правила — как в AGENTS.md: двухфазные скрипты, write_bytes после
ALL OK, никаких heredoc.

## Что не входит в деку

- CC_Main (70 с) — слишком долго для 10 минут; показывать в Q&A.
- CC_Breathe_Sim — синтетические данные; не для научного телекона.
- Числа из audit/NUMBERS_MAP_2026-10-15.md там, где они устарели
  (+38 % → +35 %; N=23 → 47) — презентация следует за текущей
  round-3 версией main.tex.
