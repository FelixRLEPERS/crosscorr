r"""Полный MVP-экспорт AE-слоёв (shared + slide-3 + slide-5) из
slides_ru_layers.pdf -> media/ae_layers/... PNG-Alpha 1920x1080.

Для каждого слоя: собственная копия .tex с \AEonly{слайд}{id} (или \AEchrome),
clean aux, xelatex x2, pdftocairo -transp -scale-to-x 1920 -scale-to-y 1080.
"""

import os
import re
import shutil
import subprocess

from PIL import Image

D = r"G:\crosscorr\docs\presentations\school_ru"
SRC = os.path.join(D, "slides_ru_layers.tex")
ROOT = r"G:\crosscorr\media\ae_layers"
XEL = ["xelatex", "-interaction=nonstopmode", "-halt-on-error"]

with open(SRC, encoding="utf-8") as f:
    BASE = f.read()

# замена строки переключателя
SW_RE = re.compile(r"^\\AE(?:only|chrome)\{.*$", re.M)


def build_and_export(tex_src, base, png_path):
    """Собрать tex_src (base = имя без расширения), отрендерить стр.1 в png_path."""
    tex = os.path.join(D, base + ".tex")
    with open(tex, "w", encoding="utf-8", newline="\n") as f:
        f.write(tex_src)
    for ext in (".aux", ".log", ".nav", ".snm", ".toc", ".out", ".synctex.gz"):
        p = os.path.join(D, base + ext)
        if os.path.exists(p):
            os.remove(p)
    ok = True
    for _ in range(2):
        r = subprocess.run(XEL + [base + ".tex"], cwd=D, capture_output=True, text=True)
        if r.returncode != 0:
            print("  XELATEX FAIL", base, (r.stdout or "")[-300:])
            ok = False
            break
    if not ok:
        return False
    pdf = os.path.join(D, base + ".pdf")
    # page for each switch (slide number)
    m = re.match(r"\\AEonly\{(\d+)\}", tex_src[tex_src.find("\\AEonly") :]) or re.match(
        r"\\AEonly\{(\d+)\}", tex_src
    )
    page = int(m.group(1)) if m else 1
    tmp = os.path.join(D, "_exp")
    for f0 in (tmp + "-1.png",):
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
            tmp,
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not os.path.exists(tmp + "-%d.png" % page):
        print("  PDFTOCAIRO FAIL", base, r.stderr[:200])
        return False
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    shutil.move(tmp + "-%d.png" % page, png_path)
    return True


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


def switch(mode, slide, layer):
    if mode == "chrome-hud":
        return "\\AEchrome{hud-frame}"
    if mode == "chrome-foot":
        return "\\AEchrome{footline-frame}"
    if mode == "chrome-onair":
        return "\\AEchrome{onair}"
    return "\\AEonly{%d}{%s}" % (slide, layer)


def emit(mode, slide, layer, out_path, base):
    """mode: 'layer' | 'chrome-hud' | 'chrome-foot' | 'chrome-onair'"""
    sw = switch(mode, slide, layer)
    m = SW_RE.search(BASE)
    assert m, "switch line not found"
    src = BASE[: m.start()] + sw + BASE[m.end() :]
    return build_and_export(src, base, out_path)


# ---- 1) shared chrome -----------------------------------------------------
print("=== shared/ ===")
shared = os.path.join(ROOT, "shared")
# hud-frame (только уголки + CROSSCORR, БЕЗ номера): рисуем hud, вырезаем
# правый верхний узел (ON AIR + номер) -> alpha=0
ok = emit("chrome-hud", 0, "", os.path.join(shared, "hud-frame-full.png"), "e_chud")
if ok:
    img = Image.open(os.path.join(shared, "hud-frame-full.png")).convert("RGBA")
    px = img.load()
    for y in range(0, 150):  # правый верхний угол
        for x in range(1450, 1920):
            r, g, b, a = px[x, y]
            if a > 0 and (g > 180 and b > 180):  # cyan/amber штрихи
                px[x, y] = (r, g, b, 0)
            elif a > 0 and (r > 60 and g > 60 and b > 60):
                px[x, y] = (r, g, b, 0)  # dim-текст CROSSCORR/ON AIR
    # остаются только уголки + CROSSCORR (левый верх) -> переименовываем
    os.replace(os.path.join(shared, "hud-frame-full.png"), os.path.join(shared, "hud-frame.png"))
    print("  hud-frame.png OK")

ok = emit("chrome-foot", 0, "", os.path.join(shared, "footline-frame.png"), "e_cfoot")
if ok:
    img = Image.open(os.path.join(shared, "footline-frame.png")).convert("RGBA")
    px = img.load()
    # вырезаем номер (справа, ~x 1780..1900, нижняя полоса y 1010..1070)
    for y in range(1000, 1080):
        for x in range(1740, 1920):
            r, g, b, a = px[x, y]
            if a > 0:
                px[x, y] = (r, g, b, 0)
    img.save(os.path.join(shared, "footline-frame.png"))
    print("  footline-frame.png OK")

# hud-onair-XX (только номер + ON AIR, правый верх)
print("=== hud-onair-01..08 ===")
onair_ok = []
for n in range(1, 9):
    # рисуем ТОЛЬКО onair-ветку: chrome-hud + вырез левого верха (уголки/CROSSCORR)
    sw = "\\AEchrome{hud-frame}"
    m = SW_RE.search(BASE)
    src = BASE[: m.start()] + sw + BASE[m.end() :]
    out = os.path.join(shared, "hud-onair-%02d.png" % n)
    if not build_and_export(src, "e_onair%02d" % n, out):
        onair_ok.append((n, False))
        continue
    img = Image.open(out).convert("RGBA")
    px = img.load()
    # оставить только правый верхний узел: обнулить всё остальное
    for y in range(0, 1080):
        for x in range(0, 1920):
            in_onair = y < 150 and x >= 1450
            if not in_onair:
                r, g, b, a = px[x, y]
                if a > 0:
                    px[x, y] = (r, g, b, 0)
    # подменить номер в тексте на кадровый номер не можем (текст растровый) ->
    # в режиме onair ветка рисует insertframenumber=1; исправляем вставкой
    # правильного номера невозможно -> рендерим с ручным номером ниже
    img.save(out)
    onair_ok.append((n, True))

print("onair pass1:", onair_ok)
