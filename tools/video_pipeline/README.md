# video_pipeline — Phase 2 (deck → animated video)

Инструменты сборки видео-презентации CrossCorr: 8 слайдов деки →
LTX-видео фоны → AE-компы → склейка → звук → `media/crosscorr_video.mp4`.

## Стек и пути

- LTX-генерация: ComfyUI `http://127.0.0.1:8000` (ComfyUI Desktop).
- AE 2026: `C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\`
  (`AfterFX.exe` для GUI-скриптов, `aerender.exe` для CLI-рендера).
- ffmpeg/ffprobe: WinGet `Gyan.FFmpeg ...\bin\` (переопределяются env
  `FFMPEG`/`FFPROBE`/`COMFY_URL`).
- Python: `D:\STRATA\.venv\Scripts\python.exe`.

## Пошаговый конвейер (STEP 0 … финал)

| Шаг | Инструмент | Выход |
|---|---|---|
| 0. спасение temp-скриптов | коммит `b14b29e` | скрипты в этом каталоге |
| 1. генерация фонов | `gen_video_bg.py --slides 1,2,4,6,7,8` | `media/video_bg/slide-N.mp4` (768×512, 24fps, 177f) |
| 2. flicker-тест | `flicker_check.py <video>` | вердикт: `<5/255` OK, `5..15` human, `>15` STOP + `_contact.png` |
| 3. апскейл | `upscale_bg.py <video>` (~5 мин/клип) | `slide-N_1080.mp4` (ESRGAN → 1920×1280 → crop 1920×1080) |
| 4–5. слои LaTeX | `export_layers.py --content 1,2,4,6,7,8` | `media/ae_layers/slide-N/block-01-content.png` (Alpha 1920×1080) |
| 6. компы AE | `build_full.jsx` (см. ниже) | 6 новых компов + swap 3/5 PNG→video, копия `.aep` |
| 7. рендер | `aerender -project <copy.aep> -comp CrossCorr_slide-N -output slide-N.avi -OMtemplate Lossless` | `media/video_final/slide-N.mp4` (AVI lossless → H.264 crf16; AVI-мастера удалять) |
| 8. склейка | `merge_video.py` | `media/crosscorr_video_no_audio.mp4` (xfade 0.3s, crf 18) |
| 9. звук | `gen_ambient.py "tags" 60 [seed]` | mp3 V0, 60 BPM, ambient |
| 10. муш | `ffmpeg -i video -i audio … -shortest` + loudnorm I=-14 | `media/crosscorr_video.mp4` |

Storyboard (промпты/seeds/длительности): `storyboard.json` — 8 сегментов,
seeds 42–49, 161/177/193 кадров @24fps.

## Правила AE (нарушение = зависший headless-рендер)

- Никогда `app.quit()`, никаких `alert`/диалогов в headless-скриптах.
- `JSON.stringify` в ExtendScript виснет — сериализовать вручную.
- Запуск: `AfterFX.exe -s "$.evalFile(new File('C:/.../script.jsx'))"`,
  лог писать в `%TEMP%\opencode\ae_log.txt` (append).
- Оригинал `aep/crosscorr.aep` НЕ перезаписывать — всегда
  `app.project.save()` в копию (`media/video_bg/crosscorr_full.aep`).
- **Gotcha (AE 2026):** дефолтный Output Module нового AE —
  `H.264 - Match Render Settings - 15 Mbps`. Без `-OMtemplate Lossless`
  aerender молча пишет `slide-N.mp4` (15 Mbps) вместо AVI, а `-output ...avi`
  переопределяет путь, но НЕ формат. Проверять `Format: AVI` в логе рендера.

## Слои (вариант A)

- Слайды 3 и 5 — по-блочно (`\AElayer{N}{id}`, counter-анимации главных цифр).
- Остальные 6 — один контент-оверлей `block-01-content.png` на слайд;
  гейт: `\AEonly{N}{title}` для 2/4/6/7, `\AEonly{N}{content}` для
  plain-обложек 1/8 (в .tex ноль правок).
- Хром у всех 8: `shared/hud-frame.png` + `shared/hud-onair-0N.png`;
  `shared/footline-frame.png` — только слайды 2–7 (на plain 1/8 бара нет).
- `\setbg` в `slides_ru_layers.tex` — пустой макрос → экспорт прозрачный.

## Склейка (merge_video.py)

Длительности через ffprobe; offset_i = cumsum(d[:i]) − i×fade;
xfade chain → `[v7]`; проверка длительности выхода против расчётной
(±0.2с). Smoke-test: `--slides 3,5` → 14.458s ≈ 14.450s расчёта.

## Звук (gen_ambient.py)

Локальный вариант `D:\STRATA\tools\media_studio\gen_audio.py`: на текущем
ComfyUI Desktop (0.22.3) нет ноды `SaveAudioAdvanced` (граф из
`gen_audio_api.json`), поэтому нода 106 заменяется на core
`SaveAudioMP3` (mp3 V0) + `bpm=60` (в графе был 100). Теги — instrumental,
60 BPM, тёмная cyan/amber палитра. Длительность 60с (~9 ГБ VRAM); при OOM —
2×30с + crossfade, НИКОГДА не луупить короткий трек и не выпускать без звука
без крайней необходимости.

## Железные правила

- Один тяжёлый GPU-процесс за раз (ген/апскейл/ACE-Step — последовательно).
- Промпты только на английском.
- `media/` в .gitignore — видеофайлы не коммитить.
- LTX: длина кадров кратна 8n+1 (161/177/193); fps 24 и в
  `LTXVConditioning`, и в `VHS_VideoCombine`; не пере-энодить `ffmpeg -r 24`.
