r"""ACE-Step ambient generator for the merged video (Phase 2 FULL, step 9).

Local variant of media_studio/gen_audio.py: the running ComfyUI (Desktop
0.22.3) no longer provides the SaveAudioAdvanced node the captured graph
uses, so node 106 is swapped to core SaveAudioMP3 (same mp3 V0 output)
before submission. D:\STRATA tooling is left untouched.

Usage:
    python gen_ambient.py "style tags" [duration_sec] [seed] [prefix]

Output: ComfyUI output\audio\<prefix>_NNNNN.mp3 — path printed on success.
Fallback for OOM on long clips: call again with a shorter duration and
crossfade the pieces at mux time (never loop a short clip).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8000")
BASE = r"D:\STRATA\tools\media_studio\gen_audio_api.json"
OUT_DIR = r"C:\Users\FelixR\Documents\ComfyUI\output"

if len(sys.argv) < 2:
    print('usage: gen_ambient.py "style tags" [duration] [seed] [prefix]')
    sys.exit(2)

TAGS = sys.argv[1]
DURATION = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 7
PREFIX = sys.argv[4] if len(sys.argv) > 4 else "audio/crosscorr_ambient"


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


def build_graph():
    g = json.load(open(BASE, encoding="utf-8"))["prompt"]

    g["94"]["inputs"]["tags"] = TAGS
    g["94"]["inputs"]["seed"] = SEED
    g["94"]["inputs"]["duration"] = int(DURATION)
    g["94"]["inputs"]["bpm"] = 60  # spec: ambient 60 BPM (graph default was 100)
    g["98"]["inputs"]["seconds"] = DURATION
    g["3"]["inputs"]["seed"] = SEED
    g["106"]["inputs"]["filename_prefix"] = PREFIX

    # SaveAudioAdvanced -> core SaveAudioMP3 (audio link kept, mp3 V0)
    n = g["106"]
    n["class_type"] = "SaveAudioMP3"
    n["_meta"]["title"] = "Save Audio (MP3)"
    n["inputs"].pop("format", None)
    quality = n["inputs"].pop("format.quality", None) or "V0"
    n["inputs"]["quality"] = quality
    return g


def main() -> int:
    g = build_graph()
    print(f"tags: {TAGS}\nduration: {DURATION}s seed: {SEED}", flush=True)

    try:
        post("/free", {"unload_models": True, "free_memory": True}, timeout=15)
        time.sleep(1)
        resp = post("/prompt", {"prompt": g, "client_id": "gen_ambient"}, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"SUBMIT HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:2000]}")
        return 1
    except Exception as e:  # noqa: BLE001 - report any transport failure
        print(f"SUBMIT failed: {e}")
        return 1

    pid = resp["prompt_id"]
    print(f"queued id={pid}", flush=True)

    t0 = time.time()
    limit = int(os.environ.get("GEN_AMBIENT_LIMIT", "900"))
    h = {}
    while time.time() - t0 < limit:
        time.sleep(2)
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
    print(f"status={st.get('status_str')} time={elapsed}s", flush=True)

    if st.get("status_str") == "error":
        for m in st.get("messages", []):
            if m[0] == "execution_error":
                print(
                    f"node {m[1].get('node_id')} ({m[1].get('node_type')}): "
                    f"{m[1].get('exception_type')}: "
                    f"{str(m[1].get('exception_message'))[:700]}",
                    flush=True,
                )
        return 1

    rc = 1
    for _nid, o in h.get(pid, {}).get("outputs", {}).items():
        for v in o.get("audio", []) + o.get("gifs", []) + o.get("images", []):
            fp = v.get("fullpath") or os.path.join(
                OUT_DIR, v.get("subfolder", ""), v.get("filename", "")
            )
            sz = os.path.getsize(fp) if os.path.exists(fp) else 0
            print(f"OUTPUT: {fp}")
            print(f"size: {round(sz / 1024, 1)} KB ({sz} bytes)")
            rc = 0
    print(f"total time: {elapsed}s")
    return rc


if __name__ == "__main__":
    sys.exit(main())
