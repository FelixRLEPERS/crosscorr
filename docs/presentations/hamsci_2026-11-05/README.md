# HamSCI Science Telecon — 5 November 2026

Материалы 10-минутной презентации "Scale-dependent WSPR response to
geomagnetic storms". Докладчик: Alexey Petrov; соавтор: Makar Petrov
(в чате, не на сцене).

## Файлы

- slides.tex — исходник Beamer (тёмная тема, палитра из aep/CC_Data.js)
- slides.pdf — собранная дека, 10 слайдов, 16:9
- speaker_notes.md — дословный текст выступления: EN (что говорить) +
  RU (перевод и подсказки), по слайдам, с таймингом
- Q_and_A.md — 10 ответов на типичные вопросы (EN-ответ + RU-смысл)
- figures/ — копии фигур статьи (fig1–fig5, байт-в-байт из paper/figures)

## Сборка PDF

    cd docs/presentations/hamsci_2026-11-05
    pdflatex -interaction=nonstopmode -file-line-error slides.tex
    pdflatex -interaction=nonstopmode -file-line-error slides.tex

(второй прогон — для перекрёстных ссылок). Или из корня репозитория:

    python tmp_fix_pres_2_build.py

Скрипт сам проверяет slides.log на ошибки (строки "!", file:line,
Undefined Reference/Citation) и на число страниц (должно быть 10).

## Как добавить кадры из After Effects (PNG)

Слайды 1 и 2 содержат слоты под статичные кадры AE:

- figures/ae_network.png — кадр композиции CC_Network (напр. t = 8 с)
- figures/ae_links.png — кадр композиции CC_Links (напр. t = 10 с)

Пока файлов нет, LaTeX показывает безобидный плейсхолдер ("AE still
not exported") — дека собирается и без них.

Экспорт из After Effects:

1. Открыть проект с композициями CC_* (см. aep/README_VIZ.md).
2. Открыть CC_Network, поставить плейхед на ~8-й секунде.
3. Composition → Add to Render Queue.
4. Output Module → формат PNG Sequence (или "Save Frame As → PNG"
   из меню композиции — быстрее для одного кадра).
5. Переименовать нужный кадр в ae_network.png и положить в figures/.
6. Повторить для CC_Links (t ≈ 10 с) → ae_links.png.
7. Пересобрать: pdflatex дважды.

Альтернатива через ffmpeg из уже отрендеренного MP4:

    ffmpeg -i cc_network.mp4 -ss 00:00:08 -frames:v 1 figures/ae_network.png
    ffmpeg -i cc_links.mp4 -ss 00:00:10 -frames:v 1 figures/ae_links.png

Видео в PDF НЕ встраиваем (ненадёжно при screen-share). Если хочется
показать анимацию — открыть MP4 отдельным окном плеера после слайда 2
или в Q&A (CC_Main, 70 с).

## Происхождение чисел и фигур

Все числа слайдов сверены якорями по paper/main.tex (v1.3.1)
скриптом tmp_fix_pres_1_slides.py (Phase 1: 63 чека, все пройдены).
Копии фигур сделаны байтовыми, md5 совпадает с paper/figures/.

Палитра слайдов: aep/CC_Data.js → PALETTE
(фон #060911, акцент #5CE1DB, текст #F1F5FB, приглушение #828BA0).

## Регенерация

    python tmp_fix_pres_1_slides.py   # slides.tex + копии figures/
    python tmp_fix_pres_2_build.py    # slides.pdf (pdflatex x2 + лог)
    python tmp_fix_pres_3_notes.py    # speaker_notes / Q_and_A / README

Правила — как в AGENTS.md: двухфазные скрипты, write_bytes после
ALL OK, никаких heredoc.

## Что не входит в деку

- CC_Main (70 с) — слишком долго для 10 минут; показывать в Q&A.
- CC_Breathe_Sim — синтетические данные; не для научного телекона.
- Числа из audit/NUMBERS_MAP_2026-10-15.md там, где они устарели
  (+38 % → +35 %; N=23 → 47) — презентация следует за main.tex v1.3.1.
