r"""Composite AE content layers over the NEW LTX background for contrast QA.

Usage:
    python qa_composite.py [slides] [--at 0.5]

For each slide: grab one frame from media/video_bg/slide-N.mp4 at fraction
--at of its duration, scale+center-crop to 1920x1080 (same geometry as the
ESRGAN output), then alpha-composite the layer PNGs bottom-up the way
build_full.jsx stacks them. Output: media/ae_layers/_preview/newbg_slide-N.png

Purpose: catch text/panel readability problems BEFORE the expensive
aerender pass (slide-3's bright teal limb and slide-7's bright ring are
the known risk slides).
"""

import argparse
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BG_DIR = r"G:\crosscorr\media\video_bg"
LAYERS = r"G:\crosscorr\media\ae_layers"
OUT_DIR = os.path.join(LAYERS, "_preview")
W, H = 1920, 1080

# bottom-up compositing order, mirroring build_full.jsx
PLAIN = {1: True, 8: True}


def load_rgba(path):
    im = Image.open(path).convert("RGBA")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def frame_at(video, frac):
    cap = cv2.VideoCapture(video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idx = int(n * frac)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot read frame {idx} of {video}")
    # 768x512 -> cover 1920x1080 (same as ESRGAN x4 + center crop)
    s = max(W / fr.shape[1], H / fr.shape[0])
    fr = cv2.resize(
        fr, (int(fr.shape[1] * s), int(fr.shape[0] * s)), interpolation=cv2.INTER_LANCZOS4
    )
    y = (fr.shape[0] - H) // 2
    x = (fr.shape[1] - W) // 2
    fr = fr[y : y + H, x : x + W]
    fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)  # layers come from PIL (RGB)
    rgba = np.dstack([fr.astype(np.float32), np.full((H, W, 1), 255, np.float32)])
    return rgba


def over(dst, src):
    """src-over composite of RGBA float arrays."""
    a = src[..., 3:4] / 255.0
    out = src[..., :3] * a + dst[..., :3] * (1 - a)
    return np.dstack([out, np.full((H, W, 1), 255, np.float32)])


def layers_for(n):
    d = os.path.join(LAYERS, f"slide-{n}")
    files = []
    if not PLAIN.get(n):
        files.append(os.path.join(LAYERS, "shared", "footline-frame.png"))
    blocks = sorted(f for f in os.listdir(d) if f.startswith("block-") and f.endswith(".png"))
    if blocks:  # sub-blocks (slides 1-8) or legacy monolithic content
        files += [os.path.join(d, b) for b in blocks]
    else:
        files.append(os.path.join(d, "block-01-content.png"))
    files.append(os.path.join(LAYERS, "shared", f"hud-onair-0{n}.png"))
    files.append(os.path.join(LAYERS, "shared", "hud-frame.png"))
    return [f for f in files if os.path.exists(f)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides", nargs="?", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--at", type=float, default=0.5)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    for n in (int(x) for x in args.slides.split(",")):
        video = os.path.join(BG_DIR, f"slide-{n}.mp4")
        canvas = frame_at(video, args.at)
        used = []
        for lp in layers_for(n):
            canvas = over(canvas, load_rgba(lp))
            used.append(os.path.basename(lp))
        out = os.path.join(OUT_DIR, f"newbg_slide-{n}.png")
        Image.fromarray(np.clip(canvas[..., :3], 0, 255).astype(np.uint8)).save(out)
        print(f"slide-{n}: {len(used)} layers -> {out}")
        print(f"   {' <- '.join(used)}")


if __name__ == "__main__":
    main()
