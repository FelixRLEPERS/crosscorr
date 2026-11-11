r"""Dense pseudo-text QA sheet for LTX backgrounds.

flicker_check.py cannot see hallucinated glyph shapes: the slide-7
"AI RROIIG EEIORR" artifact passed the flicker metric (<5/255) because
the pseudo-text is *stable*, it just shouldn't be there. This tool samples
the clip densely (default every 0.5 s) and tiles the frames with a time
label so a human (or the agent) can scan for letters.

Usage:
    python pseudo_text_qa.py <video.mp4> [--step 0.5] [--cols 6]
                             [--tile 480x320] [--out path.png]

Verdict is ALWAYS human: this tool only produces the sheet.
"""

import argparse
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_OUT_DIR = r"G:\crosscorr\media\video_bg"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--step", type=float, default=0.5, help="seconds between samples")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--tile", default="480x320", help="WxH of each tile")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"cannot open {args.video}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    tw, th = (int(v) for v in args.tile.lower().split("x"))

    step_frames = max(1, round(args.step * fps))
    idxs = list(range(0, total, step_frames))
    if idxs[-1] != total - 1:
        idxs.append(total - 1)

    tiles = []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        t = cv2.resize(fr, (tw, th), interpolation=cv2.INTER_AREA)
        label = f"t={i / fps:.2f}s f={i}"
        cv2.rectangle(t, (0, 0), (tw - 1, 30), (0, 0, 0), -1)
        cv2.putText(
            t,
            label,
            (6, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        tiles.append(t)
    cap.release()

    if not tiles:
        print("no frames sampled")
        sys.exit(1)

    cols = args.cols
    rows = (len(tiles) + cols - 1) // cols
    blank = np.zeros((th, tw, 3), dtype=np.uint8)
    while len(tiles) < rows * cols:
        tiles.append(blank)

    grid_rows = [np.hstack(tiles[r * cols : (r + 1) * cols]) for r in range(rows)]
    sheet = np.vstack(grid_rows)

    out = args.out or (os.path.splitext(os.path.basename(args.video))[0] + "_textqa.png")
    if not os.path.isabs(out):
        out = os.path.join(DEFAULT_OUT_DIR, out)
    cv2.imwrite(out, sheet)

    print(f"video:  {args.video}")
    print(
        f"frames: {total}, fps={fps:.2f} -> sampled {len(tiles)} tiles "
        f"@ {args.step}s, grid {cols}x{rows}"
    )
    print(f"sheet:  {out} ({sheet.shape[1]}x{sheet.shape[0]})")
    print("verdict: HUMAN ONLY - scan every tile for letters/glyphs")


if __name__ == "__main__":
    main()
