"""Generate video backgrounds for presentation slides via ComfyUI (LTX-Video 2B T2V).

Usage:
    python gen_video_bg.py [--slides 3,5] [--out-dir DIR] [--force]

Reads storyboard.json (same dir), builds the LTX t2v graph per segment,
submits to the local ComfyUI (/prompt), polls /history and moves the
resulting mp4 to <out-dir>/slide-<N>.mp4 (default: G:/crosscorr/media/video_bg).

Existing outputs are skipped unless --force.
The original LTX API template lives in D:\\STRATA\\tools\\media_studio\\
(ltxvideo-t2v_api.json); the graph below is that template with per-segment
patching (prompt, length, seed, frame_rate, filename_prefix).
"""

import argparse
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
STORYBOARD = os.path.join(HERE, "storyboard.json")
DEFAULT_OUT = r"G:\crosscorr\media\video_bg"

CKPT = "ltx-video-2b-v0.9.5.safetensors"
CLIP = "t5xxl_fp16.safetensors"


def build_workflow(seg):
    """Flat API-format graph: LTX-Video 2B T2V with STG guider."""
    return {
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["38", 0], "text": seg["bg_prompt"]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["38", 0], "text": seg["negative_prompt"]},
        },
        "38": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": CLIP, "type": "ltxv", "device": "default"},
        },
        "44": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "69": {
            "class_type": "LTXVConditioning",
            "inputs": {"positive": ["6", 0], "negative": ["7", 0], "frame_rate": seg["fps"]},
        },
        "79": {"class_type": "LTXVApplySTG", "inputs": {"model": ["44", 0], "block_indices": "14"}},
        "82": {
            "class_type": "STGGuider",
            "inputs": {
                "model": ["79", 0],
                "positive": ["69", 0],
                "negative": ["69", 1],
                "cfg": 3,
                "stg": 1,
                "rescale": 0.75,
            },
        },
        "71": {
            "class_type": "LTXVScheduler",
            "inputs": {
                "latent": ["84", 0],
                "steps": 20,
                "max_shift": 2.05,
                "base_shift": 0.95,
                "stretch": True,
                "terminal": 0.1,
            },
        },
        "73": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "gradient_estimation"}},
        "83": {"class_type": "RandomNoise", "inputs": {"noise_seed": seg["seed"]}},
        "84": {
            "class_type": "EmptyLTXVLatentVideo",
            "inputs": {
                "width": seg["width"],
                "height": seg["height"],
                "length": seg["frames"],
                "batch_size": 1,
            },
        },
        "81": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["83", 0],
                "guider": ["82", 0],
                "sampler": ["73", 0],
                "sigmas": ["71", 0],
                "latent_image": ["84", 0],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["81", 0], "vae": ["44", 2]}},
        "88": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["8", 0],
                "frame_rate": seg["fps"],
                "loop_count": 0,
                "filename_prefix": f"video_bg/slide-{seg['slide']}",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }


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


def free_vram():
    post("/free", {"unload_models": True, "free_memory": True}, timeout=15)
    time.sleep(1)


def generate(seg, out_dir, force):
    out_path = os.path.join(out_dir, f"slide-{seg['slide']}.mp4")
    if os.path.exists(out_path) and not force:
        print(f"slide-{seg['slide']}: exists, skip ({out_path})", flush=True)
        return out_path

    print(
        f"slide-{seg['slide']}: {seg['frames']}f @ {seg['fps']}fps "
        f"{seg['width']}x{seg['height']} seed={seg['seed']}",
        flush=True,
    )
    print(f"  prompt: {seg['bg_prompt'][:90]}...", flush=True)

    free_vram()
    t0 = time.time()
    try:
        resp = post(
            "/prompt", {"prompt": build_workflow(seg), "client_id": "gen_video_bg"}, timeout=30
        )
    except urllib.error.HTTPError as e:
        print(f"SUBMIT HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:2000]}", flush=True)
        sys.exit(1)

    pid = resp["prompt_id"]
    print(f"  queued id={pid}", flush=True)

    h = {}
    limit = 3600
    while time.time() - t0 < limit:
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
                print(
                    f"  node {m[1].get('node_id')} "
                    f"({m[1].get('node_type')}): "
                    f"{m[1].get('exception_type')}: "
                    f"{str(m[1].get('exception_message'))[:700]}",
                    flush=True,
                )
        sys.exit(1)

    produced = None
    for _nid, o in h.get(pid, {}).get("outputs", {}).items():
        for gi in o.get("gifs", []) + o.get("images", []):
            produced = gi.get("fullpath") or os.path.join(
                r"C:\Users\FelixR\Documents\ComfyUI\output",
                gi.get("subfolder", ""),
                gi.get("filename", ""),
            )

    if not produced or not os.path.exists(produced):
        print("  no output produced", flush=True)
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    shutil.move(produced, out_path)
    print(
        f"  OUTPUT: {out_path} ({round(os.path.getsize(out_path) / 1024 / 1024, 2)} MB)", flush=True
    )
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--slides",
        default=None,
        help="comma-separated slide numbers (default: all storyboard entries)",
    )
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true", help="regenerate even if output exists")
    args = ap.parse_args()

    with open(STORYBOARD, encoding="utf-8") as f:
        board = json.load(f)

    if args.slides:
        wanted = {int(s) for s in args.slides.split(",")}
        board = [s for s in board if s["slide"] in wanted]

    if not board:
        print("no matching segments in storyboard.json", flush=True)
        sys.exit(2)

    t_all = time.time()
    for seg in board:
        generate(seg, args.out_dir, args.force)
    print(f"total: {round(time.time() - t_all, 1)}s", flush=True)


if __name__ == "__main__":
    main()
