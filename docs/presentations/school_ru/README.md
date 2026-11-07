# CrossCorr — школьная презентация (RU)

Beamer-дека «Магия радиоволн» (CrossCorr family science mission), v5 «Stark edition».

## Сборка

```powershell
xelatex -interaction=nonstopmode -halt-on-error slides_ru.tex
xelatex -interaction=nonstopmode -halt-on-error slides_ru.tex   # второй прогон (навигация)
```

Только XeLaTeX (unicode + system fonts). PDF/aux в .gitignore, PNG-растеры в репо не коммитить.

## Зависимости

- **Franklin Gothic Medium** (`\newfontfamily\techfont`) — Windows-шрифт Microsoft,
  в репо НЕ входит. На чистом клоне Linux/macOS дека соберётся с дефолтным
  fallback, но визуал сломается.
  Замена: Oswald или Barlow Condensed (Google Fonts) — в `slides_ru.tex`
  поменять одну строку `\newfontfamily\techfont{Franklin Gothic Medium}`
  на `\newfontfamily\techfont{Oswald}` (после `tlmgr install` или
  локальной установки шрифта).
- Остальные семейства (JetBrains Mono и пр.) — как в исходной деке.

## figures/

Только растеризованные версии SVG-логотипов из `assets/`:

| файл | назначение |
|---|---|
| `logo-square-ru-dark.png` | квадратный, footline |
| `logo-horizontal-ru-dark.png` | горизонтальный, панель `#0b1220` (исходник) |
| `logo-horizontal-ru-dark-alpha.png` | то же, фон удалён (для сл.1 и сл.8) |

Фоны `pres-bg-*.png` / `illo-*.png` живут в `media/generated/` (gitignored) и
сюда не копируются — в `.tex` ссылаются на них по относительному пути.

## Рендер кадров для After Effects (1920×1080)

```powershell
pdftoppm -scale-to-x 1920 -scale-to-y 1080 slides_ru.pdf ae_frame
```
