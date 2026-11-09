r"""Финальный MVP-экспорт AE-слоёв после chrome-фиксов.

shared/:
  hud-frame.png        = hud-режим MINUS вырез ON AIR (уголки + CROSSCORR)
  footline-frame.png   = cfoot-режим, стр.2 (кадр1 plain -> берём 2)
  hud-onair-01..08     = onair-режим стр.N (номера) + ON AIR из hud-рендера
  hud-onair-template   = только ON AIR (пустой слот под номер для AE Source Text)
slide-3/:
  block-01-hud        = композит hud-frame + onair-03
  block-02-title      = \AEonly{3}{title}
  block-03..05        = (уже экспортированы, не трогаем)
slide-5/:
  block-01-hud        = композит hud-frame + onair-05
  block-02-title      = \AEonly{5}{title}
  block-03..06        = (уже экспортированы)
"""

import os
import re
import shutil
import subprocess
import sys

from PIL import Image

D = r"G:\crosscorr\docs\presentations\school_ru"
SRC = os.path.join(D, "slides_ru_layers.tex")
ROOT = r"G:\crosscorr\media\ae_layers"
XEL = ["xelatex", "-interaction=nonstopmode", "-halt-on-error"]

with open(SRC, encoding="utf-8") as f:
    BASE = f.read()

SW_RE = re.compile(r"^\\AE(?:only|chrome)\{.*$", re.M)


def render(switch_line, base, page):
    m = SW_RE.search(BASE)
    assert m, "switch line not found"
    src = BASE[: m.start()] + switch_line + BASE[m.end() :]
    tex = os.path.join(D, base + ".tex")
    with open(tex, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    for ext in (".aux", ".log", ".nav", ".snm", ".toc", ".out", ".synctex.gz"):
        p = os.path.join(D, base + ext)
        if os.path.exists(p):
            os.remove(p)
    for _ in range(2):
        r = subprocess.run(XEL + [base + ".tex"], cwd=D, capture_output=True, text=True)
        if r.returncode != 0:
            print("  XELATEX FAIL", base, (r.stdout or "")[-400:])
            return None
    pdf = os.path.join(D, base + ".pdf")
    out = os.path.join(D, "_exp_%s_%d" % (base, page))
    for f0 in (out + "-1.png", out + "-%d.png" % page):
        if os.path.exists(f0):
            os.remove(f0)
    r = subprocess.run(
        [
            "pdftocairo",
            "-png",
            "-transp",
            "-scale-to-x",
            "1920",
            "-scale-to-y",
            "1080",
            "-f",
            str(page),
            "-l",
            str(page),
            pdf,
            out,
        ],
        capture_output=True,
        text=True,
    )
    produced = out + "-%d.png" % page
    if r.returncode != 0 or not os.path.exists(produced):
        print("  PDFTOCAIRAIL FAIL", base, r.stderr[:300])
        return None
    return produced


def alpha_stats(path):
    img = Image.open(path).convert("RGBA")
    px = img.load()
    w, h = img.size
    n0 = n255 = nmid = 0
    for y in range(h):
        for x in range(w):
            al = px[x, y][3]
            if al == 0:
                n0 += 1
            elif al == 255:
                n255 += 1
            else:
                nmid += 1
    tot = w * h
    return 100.0 * n0 / tot, 100.0 * n255 / tot, 100.0 * nmid / tot


def save_png(img, rel):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p)
    return p


# ===== режим --content: цельный контент-оверлей слайда (FULL, вариант A) =====
# Страница N рендерится в режиме L (\AEonly): chrome (hud/footline) гасится
# vphantom'ом, \setbg пуст -> прозрачный PNG со всем контентом слайда.
#   * слайды 2/4/6/7: id="title" -> узел \slidetitle (единственный \AElayer
#     на странице) совпадает и рендерится, остальной контент не обёрнут
#     в \AElayer и рендерится в режиме L безусловно;
#   * обложки 1/8 (plain): \AElayer-узлов нет вовсе -> любой id, берём
#     "content" (не совпадает ни с чем, ничего не гаснет).
if "--content" in sys.argv:
    TITLE_SLIDES = {2, 4, 6, 7}
    arg = sys.argv[sys.argv.index("--content") + 1]
    rc = 0
    for n in [int(x) for x in arg.split(",")]:
        layer_id = "title" if n in TITLE_SLIDES else "content"
        rel = "slide-%d/block-01-content.png" % n
        p = render("\\AEonly{%d}{%s}" % (n, layer_id), "x_content%02d" % n, n)
        if not p:
            print("  FAIL slide-%d" % n)
            rc = 1
            continue
        dest = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(p, dest)
        print(
            "  slide-%d -> %s alpha=" % (n, rel),
            alpha_stats(dest),
        )
    sys.exit(rc)


# ===== 1) chrome renders ====================================================
print("=== render chrome ===")
hud_png = render("\\AEchrome{hud-frame}", "x_hud", 1)
print("  hud:", hud_png)
onair_pngs = {}
for n in range(1, 9):
    p = render("\\AEchrome{onair}", "x_onair%02d" % n, n)
    onair_pngs[n] = p
    print("  onair%02d:" % n, p)
cfoot_png = render("\\AEchrome{footline-frame}", "x_cfoot", 2)
print("  cfoot:", cfoot_png)

# ===== 2) shared/hud-frame.png = hud MINUS ON AIR ===========================
# ON AIR регион (после phantom-фикса): x 1400..1750, y 30..110.
# Уголок правого верха начинается с x=1752 -- не задеваем.
print("=== shared/hud-frame ===")
hud_img = Image.open(hud_png).convert("RGBA")
hpx = hud_img.load()
for y in range(0, 120):
    for x in range(1380, 1751):
        r, g, b, a = hpx[x, y]
        if a > 0:
            hpx[x, y] = (r, g, b, 0)
save_png(hud_img, "shared/hud-frame.png")
print("  saved, alpha=", alpha_stats(os.path.join(ROOT, "shared", "hud-frame.png")))

# ON AIR вырез (кусок для композита onair и template)
onair_zone = hud_img.crop((1380, 0, 1751, 120))  # уже очищенный hud НЕ нужен ->
# берем ИСХОДНЫЙ hud для ON AIR:
hud_orig = Image.open(hud_png).convert("RGBA")
onair_text = hud_orig.crop((1380, 0, 1751, 120))

# ===== 3) shared/footline-frame.png (стр.2, полный кадр) ====================
print("=== shared/footline-frame ===")
cfoot_img = Image.open(cfoot_png).convert("RGBA")
save_png(cfoot_img, "shared/footline-frame.png")
print("  saved, alpha=", alpha_stats(os.path.join(ROOT, "shared", "footline-frame.png")))

# ===== 4) shared/hud-onair-01..08 = номера (onair стр.N) + ON AIR ===========
print("=== shared/hud-onair-01..08 ===")
for n in range(1, 9):
    img = Image.open(onair_pngs[n]).convert("RGBA")
    img.alpha_composite(onair_text, (1380, 0))
    save_png(img, "shared/hud-onair-%02d.png" % n)
    print(
        "  hud-onair-%02d alpha=" % n,
        alpha_stats(os.path.join(ROOT, "shared", "hud-onair-%02d.png" % n)),
    )

# ===== 5) shared/hud-onair-template.png = ON AIR без номера =================
save_png(onair_text.copy(), "shared/hud-onair-template.png")
print("=== shared/hud-onair-template.png saved ===")

# ===== 6) слои title ========================================================
print("=== slide-3/5 titles ===")
for sl, rel in ((3, "slide-3/block-02-title.png"), (5, "slide-5/block-02-title.png")):
    p = render("\\AEonly{%d}{title}" % sl, "x_title%d" % sl, sl)
    if p:
        shutil.move(p, os.path.join(ROOT, rel))
        print(f"  {rel} alpha=", alpha_stats(os.path.join(ROOT, rel)))

# ===== 7) block-01-hud композиты ===========================================
print("=== block-01-hud composites ===")
for sl, rel in ((3, "slide-3/block-01-hud.png"), (5, "slide-5/block-01-hud.png")):
    base = Image.open(os.path.join(ROOT, "shared", "hud-frame.png")).convert("RGBA")
    num = Image.open(os.path.join(ROOT, "shared", "hud-onair-%02d.png" % sl)).convert("RGBA")
    base.alpha_composite(num)
    save_png(base, rel)
    print(f"  {rel} alpha=", alpha_stats(os.path.join(ROOT, rel)))

# ===== итог ================================================================
print()
print("=== FILES ===")
for r0, _d0, f0 in os.walk(ROOT):
    if "_preview" in r0:
        continue
    for fn in sorted(f0):
        p = os.path.join(r0, fn)
        print("  %-50s %7d bytes" % (os.path.relpath(p, ROOT), os.path.getsize(p)))
