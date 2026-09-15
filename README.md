<p align="center">
  <img src="images/logo.svg" alt="CrossCorr — global data stream logo" width="400"/>
</p>

<h1 align="center">CrossCorr</h1>
<p align="center"><i>Cross-correlation analysis of anomalies in heterogeneous time series</i></p>
<p align="center"><i>Русская версия. English version coming soon.</i></p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
  <a href="https://streamlit.io/"><img src="https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status">
  <a href="https://github.com/FelixRLEPERS/crosscorr/commits/main"><img src="https://img.shields.io/github/last-commit/FelixRLEPERS/crosscorr" alt="Last commit"></a>
</p>

---

## 📖 Оглавление

- [О проекте](#о-проекте)
- [Методология](#методология)
- [Структура репозитория](#структура-репозитория)
- [Быстрый старт](#быстрый-старт)
- [Данные](#данные)
- [Пайплайн анализа](#пайплайн-анализа)
- [Игра и голосовой наставник](#игра-и-голосовой-наставник)
- [Результаты](#результаты)
- [Статус проекта](#статус-проекта)
- [Команда](#команда)
- [Документация](#документация)
- [Вклад ИИ](#вклад-ии)
- [Скриншоты](#скриншоты)
- [Лицензия](#лицензия)
- [Контакты](#контакты)

---

## 🎯 О проекте

**CrossCorr** — это открытый исследовательский проект, который объединяет разнородные временные ряды и проверяет гипотезы о наличии кросс-корреляций между ними. Мы не ищем «магическую связь», а строим воспроизводимый пайплайн: от загрузки и унификации данных до статистических тестов с контролем ложных обнаружений.

Проект задуман как семейный: папа отвечает за стратегию и код, мама — за коммуникации и тексты, Макар — за исследования, Егор — за данные и визуализацию. Мы хотим показать, что настоящая наука может быть совместным семейным делом.

**Ключевые принципы:**

- Открытые данные и открытый код.
- Воспроизводимость каждого шага.
- Статистическая строгость: surrogate-тесты, FDR-коррекция, байесовские модели.
- Игровые форматы для вовлечения детей.
- Прозрачность: явно указываем, где помогал ИИ.

---

## 🔬 Методология

1. **Унификация данных.**
   Все источники приводятся к единому формату:

   ```text
   timestamp_utc, detector_id, detector_type, residual, meta
