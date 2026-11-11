r"""Split monolithic block-01-content.png of slides 1,2,4,6,7,8 into
sub-blocks for the sequential text reveal in build_full.jsx.

Why raster and not LaTeX: the monolithic PNGs are the ground truth render
of the deck. Cutting them by axis-aligned rectangles that fall on fully
empty alpha rows/columns keeps every glyph intact, needs no .tex edits and
guarantees the union of the blocks equals the original pixel-for-pixel.
(The \vphantom layer mechanism in slides_ru_layers.tex cannot hide
multi-line text blocks: \\ is swallowed in LR mode, flushleft/center/\par
break \phantom -- verified by xelatex tests 2026-11-10.)

Usage:
    python split_blocks.py            # split all configured slides
    python split_blocks.py 1,7        # subset

Config semantics per block: (id, y0, y1, x0, x1) — rows [y0, y1), cols
[x0, x1) of the 1920x1080 canvas. Blocks of a slide must TIGHTLY tile the
canvas; every cut line must be free of ink (alpha=0), otherwise a glyph
would be torn between two blocks. Output: slide-N/block-NN-<id>.png
(full canvas, only that block's pixels). The monolithic source is renamed
to _src-block-01-content.png so build_full.jsx's block-*.png glob never
picks it up again. Reruns read from _src-... if block-01-content.png is
gone.
"""

import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"G:\crosscorr\media\ae_layers"
W, H = 1920, 1080

# --- split config (cut lines taken from alpha row/column gap analysis) ----
# slide: [(block_id, y0, y1, x0, x1), ...]  (canvas tiling, top->bottom,
# within a band left->right = reveal order)
SPLITS = {
    1: [  # hero: kicker+title+rules / subtitle / authors / stats+logo
        ("title", 0, 444, 0, W),
        ("subtitle", 444, 551, 0, W),
        ("authors", 551, 717, 0, W),
        ("bottom", 717, H, 0, W),
    ],
    2: [  # title | (panel | objective) | statrow
        ("title", 0, 300, 0, W),
        ("panel", 300, 746, 0, 1097),
        ("objective", 300, 746, 1097, W),
        ("statrow", 746, H, 0, W),
    ],
    4: [  # title | statrow | panel
        ("title", 0, 300, 0, W),
        ("statrow", 300, 550, 0, W),
        ("panel", 550, H, 0, W),
    ],
    6: [  # title(+illusnote) | (panel | alert)
        ("title", 0, 300, 0, W),
        ("panel", 300, H, 0, 1066),
        ("alert", 300, H, 1066, W),
    ],
    7: [  # title(+illusnote) | (card-01 | card-02) | panel
        ("title", 0, 300, 0, W),
        ("card-01", 300, 700, 0, 948),
        ("card-02", 300, 700, 948, W),
        ("panel", 700, H, 0, W),
    ],
    8: [  # quote(+kicker+rules) | logo | github+thanks
        ("quote", 0, 475, 0, W),
        ("logo", 475, 800, 0, W),
        ("thanks", 800, H, 0, W),
    ],
}


def verify(slide, blocks, alpha):
    """Tiling + empty cut lines + non-empty blocks. Raises on failure."""
    errs = []

    # 1) y ranges tile [0, H)
    ys = sorted({(b[1], b[2]) for b in blocks})
    if ys[0][0] != 0 or ys[-1][1] != H:
        errs.append("y ranges must start at 0 and end at %d" % H)
    for (a0, a1), (b0, b1) in zip(ys, ys[1:]):
        if a1 != b0:
            errs.append("y ranges do not touch: %d != %d" % (a1, b0))

    # 2) within each y band, x ranges tile [0, W)
    for y0, y1 in ys:
        xs = sorted(b[3:5] for b in blocks if b[1] == y0 and b[2] == y1)
        if xs[0][0] != 0 or xs[-1][1] != W:
            errs.append("x ranges for y=[%d,%d) must tile width" % (y0, y1))
        for (a0, a1), (b0, b1) in zip(xs, xs[1:]):
            if a1 != b0:
                errs.append("x ranges do not touch in y=[%d,%d)" % (y0, y1))

    # 3) cut rows empty (whole width): a row with ink must not straddle
    for y0, y1 in ys[1:]:
        if alpha[y0].any():
            errs.append("cut row y=%d has ink (tears glyphs)" % y0)

    # 4) cut columns empty within their band
    for y0, y1 in ys:
        xs = sorted({b[3:5] for b in blocks if b[1] == y0 and b[2] == y1})
        for x0, _x1 in xs[1:]:
            if alpha[y0:y1, x0].any():
                errs.append("cut col x=%d has ink in y=[%d,%d)" % (x0, y0, y1))

    # 5) every block carries ink
    for bid, y0, y1, x0, x1 in blocks:
        if not alpha[y0:y1, x0:x1].any():
            errs.append("block %s is empty" % bid)

    if errs:
        raise AssertionError("slide-%d split invalid:\n  " % slide + "\n  ".join(errs))


def split(slide, blocks):
    d = os.path.join(ROOT, "slide-%d" % slide)
    mono = os.path.join(d, "block-01-content.png")
    src = mono if os.path.exists(mono) else os.path.join(d, "_src-block-01-content.png")
    if not os.path.exists(src):
        print("  slide-%d: SKIP (no source PNG)" % slide)
        return False

    im = Image.open(src).convert("RGBA")
    if im.size != (W, H):
        raise AssertionError("slide-%d: unexpected size %s" % (slide, im.size))
    arr = np.asarray(im)
    alpha = arr[..., 3] > 0
    verify(slide, blocks, alpha)

    for i, (bid, y0, y1, x0, x1) in enumerate(blocks, start=1):
        crop = arr[y0:y1, x0:x1].copy()  # copy, then paste on empty canvas
        out = np.zeros_like(arr)
        out[y0:y1, x0:x1] = crop
        rel = "block-%02d-%s.png" % (i, bid)
        Image.fromarray(out).save(os.path.join(d, rel))
        n = int((out[..., 3] > 0).sum())
        print("  slide-%d -> %s  bbox=y[%d,%d) x[%d,%d) ink=%d" % (slide, rel, y0, y1, x0, x1, n))

    # move the monolithic source aside (never matched by block-*.png)
    if os.path.exists(mono):
        shutil.move(mono, os.path.join(d, "_src-block-01-content.png"))
        print("  slide-%d: block-01-content.png -> _src-block-01-content.png" % slide)
    return True


def main():
    slides = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else sorted(SPLITS)
    rc = 0
    for n in slides:
        if n not in SPLITS:
            print("  slide-%d: no split config, SKIP" % n)
            continue
        print("=== slide-%d ===" % n)
        try:
            split(n, SPLITS[n])
        except AssertionError as e:
            print(e)
            rc = 1
    print("OK" if rc == 0 else "FAILED")
    return rc


if __name__ == "__main__":
    sys.exit(main())
