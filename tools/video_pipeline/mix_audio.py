r"""Финальная звуковая стадия: наррация + ambient (ducking) -> media/crosscorr_video.mp4.

Usage:
    python mix_audio.py [--video ...] [--narration-dir ...]
                        [--ambient <mp3>] [--ambient2 <mp3>]
                        [--duck -20] [--ramp 0.1] [--out ...]

What it does
------------
1. Segment offsets: probes each media/video_final/slide-N.mp4 duration and
   reproduces merge_video.py's xfade timeline
       offset_i = sum(d[:i]) - i * fade   (fade = 0.3, i = 1..N-1, offset_0 = 0)
   so each narration clip starts exactly at its segment's start on the merged
   timeline (same numbers as the video, so no drift).
2. Narration: 9 wavs (intro.wav + media/narration/slide-0N.wav) mixed at
   those offsets (adelay + amix, normalize=0, no level surprises).
   intro.wav = "Всем привет — это кросскорр!" cut from the slide-01 take
   (orig backup: narration/orig/slide-01.wav; slide-01.wav holds the rest).
3. Ambient: full video length. If one clip is too short -> declared fallback
   with --ambient2 and acrossfade (never loop/clip a short track silently).
   Ducking: volume expression, eval=frame, gain 1 outside narration windows,
   `duck` (default -20 dB -> factor 0.1) inside them, `ramp` (0.1 s) ramps on
   each edge. Window = whole narration clip extent (incl. its 0.5 s pads), so
   ducking eases in before speech and out after it.
4. Two-pass loudnorm (I=-14:TP=-1.5:LRA=11; pass 1 measures, pass 2
   normalizes with measured_* in dynamic mode) + safety limiter at
   -2.5 dBFS so the final true peak stays <= -1.5 dBTP after AAC,
   resample 48 kHz, mux video (stream copy) + AAC 320k, faststart.

Nothing here touches paper/, audit/, results/, tags or Zenodo.
"""

import argparse
import json
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

DEFAULT_VIDEO = r"G:\crosscorr\media\crosscorr_video_no_audio.mp4"
DEFAULT_NDIR = r"G:\crosscorr\media\narration"
DEFAULT_SEG_DIR = r"G:\crosscorr\media\video_final"
DEFAULT_OUT = r"G:\crosscorr\media\crosscorr_video.mp4"
# Segment tokens in timeline order: "intro" = CrossCorr_intro logo comp
# (narration: intro.wav, cut from slide-01 recording 2026-11-10), then 8 slides.
SEG_TOKENS = ["intro", "1", "2", "3", "4", "5", "6", "7", "8"]
MERGE_FADE = 0.3


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


def segment_offsets(slide_durations: list[float], fade: float) -> list[float]:
    """Same math as merge_video.py's build_xfade_chain (offset_i = cum - i*fade)."""
    offsets = [0.0]
    for i in range(1, len(slide_durations)):
        offsets.append(sum(slide_durations[:i]) - i * fade)
    return offsets


def segment_file(token: str) -> str:
    """'intro' -> intro.mp4 (logo comp); '3' -> slide-3.mp4."""
    return f"{token}.mp4" if token == "intro" else f"slide-{int(token)}.mp4"


def narration_path(n_dir: str, token: str) -> str:
    """intro -> intro.wav; slides -> slide-0N.wav (recorded) / slide-N.wav."""
    if token == "intro":
        for cand in ("intro.wav", "intro.WAV"):
            p = os.path.join(n_dir, cand)
            if os.path.exists(p):
                return p
        raise FileNotFoundError(
            f"intro narration wav not found in {n_dir} (tried intro.wav) - "
            f"cut from media/narration/orig/slide-01.wav first"
        )
    index = int(token)
    for cand in (
        f"slide-{index:02d}.wav",
        f"slide-{index}.wav",
        f"slide-{index:02d}.WAV",
    ):
        p = os.path.join(n_dir, cand)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        f"narration wav for segment {token} not found in {n_dir} "
        f"(tried slide-{index:02d}.wav / slide-{index}.wav)"
    )


def duck_expr(windows: list[tuple[float, float]], duck: float, ramp: float) -> str:
    """gain(t) = 1 outside narration windows, `duck` factor inside, `ramp` ramps."""
    if ramp <= 0:
        raise ValueError("ramp must be > 0")
    # trapezoid per window: 0 outside [s-ramp, e+ramp], 1 inside [s, e].
    # NOTE: ffmpeg's min()/max() take exactly TWO arguments (3+ -> "Error when
    # evaluating the volume expression" at filter init), so everything is
    # nested pairwise: min(1, a, b) == min(min(1, a), b).
    parts = []
    for s, e in windows:
        lo = s - ramp
        hi = e + ramp
        a = f"(t-({lo:.4f}))/{ramp:.4f}"
        b = f"((({hi:.4f})-t)/{ramp:.4f})"
        parts.append(f"max(0,min(min(1,{a}),{b}))")
    # union of windows (pairwise max)
    union = parts[0]
    for p in parts[1:]:
        union = f"max({union},{p})"
    factor = f"{10 ** (duck / 20.0):.6f}"
    return f"1-(1-{factor})*max({union},0)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video", default=DEFAULT_VIDEO)
    ap.add_argument("--narration-dir", default=DEFAULT_NDIR)
    ap.add_argument("--seg-dir", default=DEFAULT_SEG_DIR)
    ap.add_argument("--ambient", required=True, help="main ambient track (mp3)")
    ap.add_argument(
        "--ambient2",
        default=None,
        help="second ambient clip (declared OOM fallback: 2 clips + crossfade)",
    )
    ap.add_argument("--duck", type=float, default=-20.0, help="dB under voice")
    ap.add_argument("--ramp", type=float, default=0.1, help="ramp seconds")
    ap.add_argument("--fade", type=float, default=MERGE_FADE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", help="print plan, do not run ffmpeg")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        raise FileNotFoundError(f"{args.video} missing - run merge_video.py first")
    for p in [args.ambient] + ([args.ambient2] if args.ambient2 else []):
        if not os.path.exists(p):
            raise FileNotFoundError(f"ambient missing: {p}")

    # 1. timeline ----------------------------------------------------------------
    seg_durs = [probe_duration(os.path.join(args.seg_dir, segment_file(tok))) for tok in SEG_TOKENS]
    offsets = segment_offsets(seg_durs, args.fade)
    narration = [narration_path(args.narration_dir, tok) for tok in SEG_TOKENS]
    narr_durs = [probe_duration(p) for p in narration]
    video_dur = probe_duration(args.video)

    # speech must end inside its segment (report, don't fail on tiny slack)
    over = [
        (SEG_TOKENS[i], offsets[i] + narr_durs[i], offsets[i] + seg_durs[i])
        for i in range(len(SEG_TOKENS))
        if offsets[i] + narr_durs[i] > offsets[i] + seg_durs[i] + 0.05
    ]

    windows = [(offsets[i], offsets[i] + narr_durs[i]) for i in range(len(SEG_TOKENS))]

    # 2. ambient build -------------------------------------------------------------
    a_dur = probe_duration(args.ambient)
    amb_inputs = [args.ambient]
    amb_chain = None
    required = video_dur
    if args.ambient2:
        d2 = probe_duration(args.ambient2)
        amb_inputs.append(args.ambient2)
        need = max(0.5, a_dur + d2 - required)
        if a_dur + d2 < required:
            raise SystemExit(
                f"ambient fallback too short: {a_dur:.1f}s + {d2:.1f}s < "
                f"video {required:.1f}s - regenerate longer (never loop)"
            )
        amb_chain = f"[1:a][2:a]acrossfade=duration={need:.3f}:curve=tri[ca]"
        amb_src = "[ca]"
        amb_len = a_dur + d2 - need
    else:
        amb_src = "[1:a]"
        amb_len = a_dur
        if amb_len < required:
            raise SystemExit(
                f"ambient too short ({amb_len:.1f}s < video {required:.1f}s) - "
                f"pass --ambient2 (declared fallback: 2 clips + crossfade) or "
                f"a longer ambient"
            )

    # inputs: 0=video, 1..len(amb_inputs)=ambient, then narration wavs (9)
    n_base = 1 + len(amb_inputs)
    expr = duck_expr(windows, args.duck, args.ramp)

    lines = []
    if amb_chain:
        lines.append(amb_chain)
    # trim/pad ambient to exact video length, then duck it
    amb_trim = (
        f"{amb_src}atrim=0:{required:.3f},asetpts=PTS-STARTPTS,"
        f"volume='{expr}':eval=frame,apad=whole_dur={required:.3f}[amb]"
    )
    lines.append(amb_trim)
    narr_parts = []
    for i in range(len(SEG_TOKENS)):
        idx = n_base + i
        label = f"n{i}"
        ms = int(round(offsets[i] * 1000))
        lines.append(f"[{idx}:a]adelay={ms}:all=1[{label}]")
        narr_parts.append(f"[{label}]")
    lines.append(
        "".join(narr_parts) + f"amix=inputs={len(SEG_TOKENS)}:normalize=0:duration=longest[out0]"
    )
    lines.append("[amb][out0]amix=inputs=2:normalize=0:duration=longest[mix]")
    # Pre-loudnorm chain (identical in both passes). loudnorm runs in TWO
    # passes: pass 1 measures the mix (print_format=json), pass 2 normalizes
    # with measured_* (dynamic mode; see the pass-2 note for why not linear)
    # + a -2.5 dBFS safety limiter for the true-peak ceiling.
    pre = ";".join(lines)
    ln_params = "I=-14:TP=-1.5:LRA=11"
    fc_pass1 = pre + f";[mix]loudnorm={ln_params}:print_format=json[a1]"

    # report -------------------------------------------------------------------
    print("=== plan ===")
    print(f"video: {args.video} ({video_dur:.3f}s)")
    print(f"segment durations: {[round(d, 3) for d in seg_durs]}")
    print(f"offsets (fade {args.fade}s): {[round(o, 3) for o in offsets]}")
    print(
        "narration: "
        + ", ".join(
            f"{SEG_TOKENS[i]}@{offsets[i]:.2f}s+{narr_durs[i]:.2f}s" for i in range(len(SEG_TOKENS))
        )
    )
    if over:
        print(f"WARNING: narration overruns its segment: {over}")
    print(
        f"ambient: {args.ambient} ({a_dur:.1f}s)"
        + (f" + {args.ambient2} (fallback, crossfade)" if args.ambient2 else "")
        + f" -> duck {args.duck} dB inside {len(windows)} windows, "
        f"ramp {args.ramp}s"
    )
    print(
        f"final: loudnorm {ln_params} (two-pass, dynamic) + alimiter "
        f"-2.5 dBFS, 48 kHz, "
        f"AAC 320k -> {args.out}"
    )
    if args.dry_run:
        print("filter_complex (pass 1, measure):")
        print(fc_pass1)
        return 0

    inputs = [FFMPEG, "-y", "-loglevel", "error", "-stats", "-i", args.video]
    for p in amb_inputs:
        inputs += ["-i", p]
    for p in narration:
        inputs += ["-i", p]

    def inputs_cmd() -> list:
        return list(inputs)

    # pass 1: measure (loudnorm prints its JSON at loglevel info) --------------
    print("=== pass 1: measure ===")
    r = subprocess.run(
        inputs_cmd()
        + [
            "-loglevel",
            "info",
            "-filter_complex",
            fc_pass1,
            "-map",
            "[a1]",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"loudnorm measure failed rc={r.returncode}")
        print((r.stderr or "")[-2000:])
        return r.returncode
    err = r.stderr or ""
    start = err.rfind("{")
    end = err.rfind("}")
    if start < 0 or end <= start:
        print("loudnorm JSON not found in ffmpeg output:")
        print(err[-2000:])
        return 1
    m = json.loads(err[start : end + 1])
    print("measured: I={input_i} TP={input_tp} LRA={input_lra} thresh={input_thresh}".format(**m))

    # Pass 2: normalize + encode.
    # NOTE on mode choice: the measured input has I=-18.7 / TP=+0.62, i.e.
    # PLR=19.4 dB, while the spec requires final PLR = TP-I = 12.5 dB. Linear
    # mode would clamp gain to -2.1 dB to honor TP and land at I~-21 LUFS, so
    # dynamic mode (two-pass, with measured_*) is used for loudness, plus a
    # safety limiter at -2.5 dBFS so the final true peak stays <= -1.5 dBTP
    # after AAC (verified with ebur128=peak=true after the run).
    fc_pass2 = (
        pre + f";[mix]loudnorm={ln_params}" + ":measured_I={input_i}:measured_TP={input_tp}"
        ":measured_LRA={input_lra}:measured_thresh={input_thresh}"
        ":offset={target_offset}"
        # GOTCHA: in this ffmpeg build alimiter's `level` (auto level)
        # defaults to TRUE and applies makeup gain (+2.5 dB at limit=0.75) -
        # it must be disabled explicitly or the whole mix gets boosted.
        ",alimiter=limit=0.75:level=disabled"
        ",aresample=48000:async=1[aout]"
    ).format(**m)
    print("=== pass 2: normalize + encode ===")
    cmd = inputs_cmd() + [
        "-filter_complex",
        fc_pass2,
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac_mf",  # native "aac" undershoots -b:a 320k (245-283 kbps
        # measured on this ffmpeg 9 build); MediaFoundation hits 323 kbps
        "-b:a",
        "320k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-shortest",
        args.out,
    ]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"ffmpeg failed rc={r.returncode}")
        return r.returncode
    if not os.path.exists(args.out):
        print("output missing")
        return 1
    d = probe_duration(args.out)
    print(f"OK: {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB, {d:.3f}s)")
    if abs(d - video_dur) > 0.25:
        print(f"WARNING: duration {d:.3f} vs video {video_dur:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
