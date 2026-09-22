# ============================================================
#  CrossCorr · Media Build System
# ------------------------------------------------------------
#  Единый интерфейс сборки: SVG → PNG → MP4 / GIF / WebM
#
#  Команды:
#    make            показать справку
#    make all        SVG + PNG + MP4
#    make svg        проверить наличие SVG
#    make png        PNG во всех размерах
#    make png-16x9   только 16:9 (YouTube, презентации)
#    make png-9x16   только 9:16 (TikTok, Reels, Shorts)
#    make png-1x1    только 1:1 (Instagram)
#    make mp4        MP4 из анимированного SVG
#    make gif        GIF из MP4
#    make webm       WebM с прозрачностью
#    make clean      удалить exports/
#    make help       эта справка
#
#  Переопределение инструментов:
#    make png RSVG=/usr/local/bin/rsvg-convert
#    make mp4 FFMPEG=/opt/homebrew/bin/ffmpeg
# ============================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ── Пути ────────────────────────────────────────────────────
ASSETS      := assets
EXPORTS     := exports
SCRIPTS     := scripts

ANIM_16X9   := $(ASSETS)/final_frame_animated_16x9.svg
STATIC_16X9 := $(ASSETS)/final_frame_16x9.svg
STATIC_9X16 := $(ASSETS)/final_frame_9x16.svg
LOGO        := $(ASSETS)/logo.svg

# ── Инструменты ─────────────────────────────────────────────
RSVG     ?= rsvg-convert
INKSCAPE ?= inkscape
FFMPEG   ?= ffmpeg
SVGASM   ?= svgasm
NODE     ?= node

# ── Опции рендера ───────────────────────────────────────────
FPS      ?= 30
DURATION ?= 15
CRF      ?= 18

# ── Флаги определения инструментов ──────────────────────────
HAS_RSVG     := $(shell command -v $(RSVG) 2>/dev/null)
HAS_INKSCAPE := $(shell command -v $(INKSCAPE) 2>/dev/null)
HAS_FFMPEG   := $(shell command -v $(FFMPEG) 2>/dev/null)
HAS_SVGASM   := $(shell command -v $(SVGASM) 2>/dev/null)

.PHONY: all svg png png-16x9 png-9x16 png-1x1 mp4 gif webm clean help

# ── ALL ─────────────────────────────────────────────────────
all: svg png mp4

# ── SVG · проверка ──────────────────────────────────────────
svg:
	@printf "\n\033[1;36m▶ SVG files\033[0m\n"
	@for f in $(ANIM_16X9) $(STATIC_16X9) $(STATIC_9X16) $(LOGO); do \
		if [ -f "$$f" ]; then \
			size=$$(du -h "$$f" | cut -f1); \
			printf "  \033[32m✓\033[0m %-55s %s\n" "$$f" "$$size"; \
		else \
			printf "  \033[31m✗\033[0m %-55s MISSING\n" "$$f"; \
			exit 1; \
		fi \
	done
	@echo

# ── PNG · все форматы ───────────────────────────────────────
png: png-16x9 png-9x16 png-1x1

png-16x9:
	@mkdir -p $(EXPORTS)
	@printf "\n\033[1;36m▶ PNG · 16:9\033[0m\n"
	$(call render_png,$(STATIC_16X9),final_16x9_1280,1280,720)
	$(call render_png,$(STATIC_16X9),final_16x9_1920,1920,1080)
	$(call render_png,$(STATIC_16X9),final_16x9_2560,2560,1440)
	$(call render_png,$(STATIC_16X9),final_16x9_3840,3840,2160)

png-9x16:
	@mkdir -p $(EXPORTS)
	@printf "\n\033[1;36m▶ PNG · 9:16\033[0m\n"
	$(call render_png,$(STATIC_9X16),final_9x16_1080,1080,1920)
	$(call render_png,$(STATIC_9X16),final_9x16_2160,2160,3840)

png-1x1:
	@mkdir -p $(EXPORTS)
	@printf "\n\033[1;36m▶ PNG · 1:1\033[0m\n"
	$(call render_png,$(STATIC_16X9),final_1x1_1080,1080,1080)

# ── MP4 · анимация ──────────────────────────────────────────
mp4:
	@mkdir -p $(EXPORTS)
	@printf "\n\033[1;36m▶ MP4 · 16:9\033[0m\n"
ifeq ($(HAS_SVGASM),$(SVGASM))
	@echo "  using svgasm"
	$(SVGASM) -o $(EXPORTS)/final_16x9.mp4 -f $(FPS) -d $(DURATION) $(ANIM_16X9)
else ifneq ($(HAS_FFMPEG),)
	@echo "  using Chrome headless + ffmpeg"
	@$(NODE) $(SCRIPTS)/render_frames.js
	$(FFMPEG) -y -framerate $(FPS) -i $(EXPORTS)/frame_%04d.png \
		-c:v libx264 -pix_fmt yuv420p -crf $(CRF) \
		$(EXPORTS)/final_16x9.mp4
	@rm -f $(EXPORTS)/frame_*.png
else
	@echo "  \033[31m✗\033[0m Ни svgasm, ни ffmpeg не найдены."
	@echo "    Установите:  cargo install svgasm  или  brew install ffmpeg"
	@exit 1
endif
	@ls -lh $(EXPORTS)/final_16x9.mp4

# ── GIF ─────────────────────────────────────────────────────
gif: $(EXPORTS)/final_16x9.mp4
	@printf "\n\033[1;36m▶ GIF · 16:9\033[0m\n"
	$(FFMPEG) -y -i $(EXPORTS)/final_16x9.mp4 \
		-vf "fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" \
		$(EXPORTS)/final_16x9.gif
	@ls -lh $(EXPORTS)/final_16x9.gif

# ── WebM · прозрачность ────────────────────────────────────
webm: $(EXPORTS)/final_16x9.mp4
	@printf "\n\033[1;36m▶ WebM · 16:9\033[0m\n"
	$(FFMPEG) -y -i $(EXPORTS)/final_16x9.mp4 \
		-c:v libvpx-vp9 -pix_fmt yuva420p -crf 30 -b:v 0 \
		$(EXPORTS)/final_16x9.webm
	@ls -lh $(EXPORTS)/final_16x9.webm

$(EXPORTS)/final_16x9.mp4:
	@$(MAKE) mp4

# ── Clean ───────────────────────────────────────────────────
clean:
	@printf "\n\033[1;33m▶ Очистка %s/\033[0m\n" "$(EXPORTS)"
	@rm -rf $(EXPORTS)
	@echo "  \033[32m✓\033[0m done"
	@echo

# ── Help ────────────────────────────────────────────────────
help:
	@echo
	@echo "  \033[1;36mCrossCorr · Media Build System\033[0m"
	@echo "  ────────────────────────────────────────────"
	@echo "  \033[1mmake all\033[0m        SVG + PNG + MP4"
	@echo "  \033[1mmake svg\033[0m        проверить SVG-файлы"
	@echo "  \033[1mmake png\033[0m        все PNG (16:9, 9:16, 1:1)"
	@echo "  \033[1mmake png-16x9\033[0m   PNG 16:9"
	@echo "  \033[1mmake png-9x16\033[0m   PNG 9:16"
	@echo "  \033[1mmake png-1x1\033[0m    PNG 1:1"
	@echo "  \033[1mmake mp4\033[0m        MP4 из анимированного SVG"
	@echo "  \033[1mmake gif\033[0m        GIF из MP4"
	@echo "  \033[1mmake webm\033[0m       WebM с прозрачностью"
	@echo "  \033[1mmake clean\033[0m      удалить exports/"
	@echo "  \033[1mmake help\033[0m       эта справка"
	@echo
	@echo "  Переменные: FPS=$(FPS)  DURATION=$(DURATION)  CRF=$(CRF)"
	@echo "  Инструменты:"
	@echo "    RSVG      = $(if $(HAS_RSVG),$(HAS_RSVG),\033[31mне найден\033[0m)"
	@echo "    FFMPEG    = $(if $(HAS_FFMPEG),$(HAS_FFMPEG),\033[31mне найден\033[0m)"
	@echo "    SVGASM    = $(if $(HAS_SVGASM),$(HAS_SVGASM),\033[33mопционально\033[0m)"
	@echo

# ── Внутренний helper ───────────────────────────────────────
define render_png
	@if [ -n "$(HAS_RSVG)" ]; then \
		$(RSVG) -w $(3) -h $(4) $(1) -o $(EXPORTS)/$(2).png; \
		printf "  \033[32m✓\033[0m %s.png (%s×%s)\n" "$(2)" "$(3)" "$(4)"; \
	elif [ -n "$(HAS_INKSCAPE)" ]; then \
		$(INKSCAPE) $(1) --export-type=png --export-width=$(3) --export-filename=$(EXPORTS)/$(2).png >/dev/null 2>&1; \
		printf "  \033[32m✓\033[0m %s.png (Inkscape)\n" "$(2)"; \
	else \
		printf "  \033[31m✗\033[0m rsvg-convert или inkscape не найдены\n"; \
		exit 1; \
	fi
endef