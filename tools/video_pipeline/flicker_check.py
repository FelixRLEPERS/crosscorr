"""Flicker check for generated video backgrounds.

Usage:
    python flicker_check.py <video.mp4> [--sheet out.png] [--metric-only]

Prints:
  - mean(|frame[i+1] - frame[i]|) over the whole clip (0..255 scale)
  - writes a 6-frame contact sheet (start, 20%, 40%, 60%, 80%, end)

Verdict bands (agreed threshold):
  < 5/255    -> OK (safe to upscale)
  5..15      -> borderline, human decision
  > 15/255   -> STOP, do not upscale (fix LTX: motion_scale/sampler/seed)
"""

import argparse
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument(
        "--sheet", default=None, help="contact sheet output path (default: <video>_contact.png)"
    )
    ap.add_argument("--metric-only", action="store_true")
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"cannot open {args.video}")
        sys.exit(1)

    frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()

    n = len(frames)
    if n < 2:
        print(f"only {n} frames, nothing to compare")
        sys.exit(1)

    diffs = []
    for i in range(n - 1):
        d = cv2.absdiff(frames[i + 1], frames[i])
        diffs.append(float(d.mean()))
    metric = float(np.mean(diffs))
    dmax = max(diffs)

    fps = cv2.VideoCapture(args.video).get(cv2.CAP_PROP_FPS)
    print(f"video: {args.video}")
    print(f"frames: {n}, fps: {fps:.2f}, duration: {n / fps:.2f}s")
    print(f"flicker metric mean(|f[i+1]-f[i]|) = {metric:.3f} / 255 (max single pair = {dmax:.3f})")
    if metric > 15:
        verdict = "STOP (>15): flicker, do not upscale"
    elif metric >= 5:
        verdict = "BORDERLINE (5..15): show to human"
    else:
        verdict = "OK (<5): safe to upscale"
    print(f"verdict: {verdict}")

    if args.metric_only:
        return

    sheet_path = args.sheet or args.video.rsplit(".", 1)[0] + "_contact.png"
    idxs = sorted({0, int(n * 0.2), int(n * 0.4), int(n * 0.6), int(n * 0.8), n - 1})
    labels = {0: "start", n - 1: "end"}
    tiles = []
    tw, th = 384, 256
    for i in idxs:
        t = cv2.resize(frames[i], (tw, th), interpolation=cv2.INTER_AREA)
        lab = labels.get(i, f"{round(i / (n - 1) * 100)}%")
        cv2.putText(t, lab, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)

    top = np.hstack(tiles[0:3])
    bottom = np.hstack(tiles[3:6])
    sheet = np.vstack([top, bottom])
    cv2.imwrite(sheet_path, sheet)
    print(f"contact sheet: {sheet_path}")


if __name__ == "__main__":
    main()
