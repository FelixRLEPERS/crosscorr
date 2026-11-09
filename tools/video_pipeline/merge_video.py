r"""Merge rendered slide segments into one video with xfade transitions.

Usage:
    python merge_video.py [--slides 1,2,3,4,5,6,7,8] [--fade 0.3] [--out ...]

Reads each segment's duration via ffprobe, builds a sequential xfade chain:

    offset_i = sum(durations[:i]) - i * fade     (i = 1..N-1)

i.e. transition i starts fade seconds before the merged timeline reaches the
end of segment i, so every crossfade lands exactly on the segment boundary.
Encodes with libx264 crf 18, 24 fps, yuv420p.

Output is video-only: audio is muxed in a later step (ACE-Step ambient).
"""

import argparse
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FFMPEG = os.environ.get(
    "FFMPEG",
    r"C:\Users\FelixR\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe",
)
FFPROBE = os.environ.get("FFPROBE", FFMPEG.replace("ffmpeg.exe", "ffprobe.exe"))
SEG_DIR = r"G:\crosscorr\media\video_final"
DEFAULT_OUT = r"G:\crosscorr\media\crosscorr_video_no_audio.mp4"


def probe_duration(path: str) -> float:
    r = subprocess.run(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        raise RuntimeError(f"ffprobe failed for {path}: {r.stderr.strip()}")
    return float(out)


def build_xfade_chain(n: int, durations: list[float], fade: float) -> str:
    """Sequential xfade: [0:v][1:v]->[v1], [v1][2:v]->[v2], ... final [v{n-1}]."""
    parts = []
    prev = "0:v"
    merged = durations[0]
    for i in range(1, n):
        offset = merged - fade
        if offset < 0:
            raise ValueError(
                f"offset {offset:.3f} < 0 at transition {i} "
                f"(fade {fade}s too long for cumulative {merged:.3f}s)"
            )
        label = f"v{i}"
        parts.append(
            f"[{prev}][{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.6f}[{label}]"
        )
        prev = label
        merged += durations[i] - fade
    return ";".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slides", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--fade", type=float, default=0.3)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    slides = [int(x) for x in args.slides.split(",")]
    n = len(slides)
    if n < 2:
        print("need at least 2 segments")
        return 1

    paths = [os.path.join(SEG_DIR, f"slide-{s}.mp4") for s in slides]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print("MISSING segments:")
        for p in missing:
            print(f"  {p}")
        return 1

    durations = [probe_duration(p) for p in paths]
    total_in = sum(durations)
    expected = total_in - (n - 1) * args.fade
    for s, p, d in zip(slides, paths, durations, strict=True):
        print(f"slide-{s}: {d:.3f}s  {os.path.basename(p)}")
    print(f"input total: {total_in:.3f}s, after {n - 1}x{args.fade}s xfade: {expected:.3f}s")

    chain = build_xfade_chain(n, durations, args.fade)

    cmd = [FFMPEG, "-y"]
    for p in paths:
        cmd += ["-i", p]
    cmd += [
        "-filter_complex",
        chain,
        "-map",
        f"[v{n - 1}]",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "24",
        "-movflags",
        "+faststart",
        args.out,
    ]
    print("running ffmpeg ...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"ffmpeg failed rc={r.returncode}")
        return r.returncode

    got = probe_duration(args.out)
    size_mb = os.path.getsize(args.out) / 1e6
    print(f"OUT: {args.out}  duration={got:.3f}s  size={size_mb:.1f} MB")
    if abs(got - expected) > 0.2:
        print(f"WARNING: duration {got:.3f}s != expected {expected:.3f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
