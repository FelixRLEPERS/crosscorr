"""ESRGAN-only upscale of a video background to 1920x1080 (fps preserved).

Usage:
    python upscale_bg.py <video.mp4> [--out-dir DIR] [--width 1920]

Pipeline (no RIFE, no fps change — unlike STRATA gen_enhance.py):
  1. ComfyUI: RealESRGAN_x4plus -> lanczos scale to <width>x<even_h>
     (aspect preserved; 768x512 -> 1920x1280)
  2. ffmpeg: center-crop 1920x1080, source fps kept, re-encode crf 16

Outputs: <out-dir>/<stem>_1080.mp4  (final)
         <out-dir>/<stem>_up<W>x<H>.mp4  (intermediate, for debug)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8000")
FFMPEG = os.environ.get(
    "FFMPEG",
    r"C:\Users\FelixR\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe",
)
DEFAULT_OUT = r"G:\crosscorr\media\video_bg"


def post(path, obj, timeout=30):
    req = urllib.request.Request(
        f"{URL}{path}",
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw) if raw.strip() else None
    except ValueError:
        return None


def probe(src):
    import cv2

    cap = cv2.VideoCapture(src)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return w, h, fps


def run_upscale(src, out_w, out_h, fps, tmp_prefix):
    """ComfyUI ESRGAN x4 + lanczos downscale. Returns produced file path."""
    graph = {
        "100": {
            "class_type": "VHS_LoadVideoPath",
            "inputs": {
                "video": src,
                "force_rate": 0,
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1,
            },
        },
        "101": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "RealESRGAN_x4plus.pth"},
        },
        "102": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["101", 0], "image": ["100", 0]},
        },
        "103": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["102", 0],
                "upscale_method": "lanczos",
                "width": out_w,
                "height": out_h,
                "crop": "disabled",
            },
        },
        "106": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["103", 0],
                "frame_rate": fps,
                "loop_count": 0,
                "filename_prefix": tmp_prefix,
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }

    post("/free", {"unload_models": True, "free_memory": True}, timeout=15)
    time.sleep(1)

    t0 = time.time()
    try:
        resp = post("/prompt", {"prompt": graph, "client_id": "upscale_bg"}, timeout=30)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:2000]
        print(f"SUBMIT HTTP {e.code}: {body}")
        sys.exit(1)

    pid = resp["prompt_id"]
    print(f"  queued id={pid}", flush=True)

    h = {}
    while time.time() - t0 < 3600:
        time.sleep(4)
        try:
            with urllib.request.urlopen(f"{URL}/history/{pid}", timeout=15) as r:
                h = json.loads(r.read())
        except Exception:
            continue
        st = h.get(pid, {}).get("status", {})
        if st.get("completed") or st.get("status_str") in ("success", "error"):
            break

    elapsed = round(time.time() - t0, 1)
    st = h.get(pid, {}).get("status", {})
    print(f"  status={st.get('status_str')} time={elapsed}s", flush=True)

    if st.get("status_str") == "error":
        for m in st.get("messages", []):
            if m[0] == "execution_error":
                print(f"  node {m[1].get('node_id')}: {str(m[1].get('exception_message'))[:600]}")
        sys.exit(1)

    for _nid, o in h.get(pid, {}).get("outputs", {}).items():
        for gi in o.get("gifs", []) + o.get("images", []):
            return gi.get("fullpath") or os.path.join(
                r"C:\Users\FelixR\Documents\ComfyUI\output",
                gi.get("subfolder", ""),
                gi.get("filename", ""),
            )
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--width", type=int, default=1920)
    args = ap.parse_args()

    src = os.path.abspath(args.video)
    w, h, fps = probe(src)
    if not w:
        print(f"cannot probe {src}")
        sys.exit(1)
    print(f"src: {w}x{h} @ {fps:.2f}fps", flush=True)

    # aspect preserved, height rounded to even (VHS/h264-safe)
    out_w = args.width
    out_h = round(out_w * h / w / 2) * 2
    print(f"target (pre-crop): {out_w}x{out_h}", flush=True)

    stem = os.path.splitext(os.path.basename(src))[0]
    os.makedirs(args.out_dir, exist_ok=True)
    tmp_prefix = f"bg_up/{stem}_up"

    produced = run_upscale(src, out_w, out_h, fps, tmp_prefix)
    if not produced or not os.path.exists(produced):
        print("no upscale output")
        sys.exit(1)

    final = os.path.join(args.out_dir, f"{stem}_1080.mp4")
    if out_h >= 1080 and out_w >= 1920:
        x = (out_w - 1920) // 2
        y = (out_h - 1080) // 2
        cmd = [
            FFMPEG,
            "-y",
            "-v",
            "error",
            "-i",
            produced,
            "-vf",
            f"crop=1920:1080:{x}:{y}",
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-r",
            f"{fps:.6f}",
            final,
        ]
        print(f"  center-crop 1920:1080 (from {out_w}x{out_h}) @ {fps:.2f}fps", flush=True)
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            print(f"ffmpeg failed rc={rc}")
            sys.exit(1)
    else:
        print(f"size {out_w}x{out_h} < target, copying without crop")
        shutil.copyfile(produced, final)

    mid = os.path.join(args.out_dir, f"{stem}_up{out_w}x{out_h}.mp4")
    shutil.move(produced, mid)

    print(f"FINAL: {final} ({round(os.path.getsize(final) / 1024 / 1024, 2)} MB)")
    print(f"mid:   {mid}")


if __name__ == "__main__":
    main()
