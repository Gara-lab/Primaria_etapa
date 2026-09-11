import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

QUEUE = "https://queue.fal.run"

MODELS = {
    "kling": ("fal-ai/kling-video/v2.5-turbo/pro/image-to-video", 0.07,
              "cheap, good motion, iterate here first"),
    "seedance": ("fal-ai/bytedance/seedance/v1/pro/image-to-video", 0.05,
                 "tops the i2v leaderboard, strong cinematic motion"),
    "veo": ("fal-ai/veo3.1/image-to-video", 0.20,
            "best prompt adherence — use when the action is complex"),
}


def load_env_key(repo_root: Path, name: str) -> str:
    env = repo_root / ".env"
    if not env.exists():
        sys.exit(f"no .env at {env}")
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(name + "="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    sys.exit(f"{name} not found in .env  (add it: {name}=...)")


def duration_seconds(raw: str) -> float:
    try:
        return float(str(raw).strip().rstrip("sS"))
    except ValueError:
        return 0.0


def duration_field(raw: str, endpoint: str) -> str:
    n = str(raw).strip().rstrip("sS")
    return f"{n}s" if "veo" in endpoint else n


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def submit(headers: dict, endpoint: str, payload: dict) -> dict:
    r = requests.post(f"{QUEUE}/{endpoint}", headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        sys.exit(f"submit failed HTTP {r.status_code}: {r.text[:1500]}")
    return r.json()


def poll(headers: dict, status_url: str, response_url: str, timeout_s: int) -> dict:
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        r = requests.get(status_url, headers=headers, timeout=60)
        r.raise_for_status()
        st = r.json()
        state = st.get("status")
        if state != last:
            print(f"  {state}" + (f" (queue position {st['queue_position']})"
                                  if st.get("queue_position") is not None else ""), flush=True)
            last = state
        if state == "COMPLETED":
            rr = requests.get(response_url, headers=headers, timeout=120)
            rr.raise_for_status()
            return rr.json()
        if state in ("FAILED", "CANCELLED", "ERROR"):
            sys.exit(f"job {state}: {json.dumps(st)[:1500]}")
        time.sleep(3)
    sys.exit(f"timed out after {timeout_s}s (job may still finish; re-poll {status_url})")


def _fal_generate_video(repo_root: Path, endpoint: str, payload: dict, out: Path, timeout: int):
    headers = {"Authorization": "Key " + load_env_key(repo_root, "FAL_KEY"),
               "Content-Type": "application/json"}

    job = submit(headers, endpoint, payload)
    print(f"submitted {job['request_id']}")
    result = poll(headers, job["status_url"], job["response_url"], timeout)

    video = (result.get("video") or {}).get("url")
    if not video:
        sys.exit(f"no video in response: {json.dumps(result)[:1500]}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(video, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    print(f"wrote {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    return job, result


PROVIDERS = {
    "fal": _fal_generate_video,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", help="local reference image for image-to-video")
    ap.add_argument("--prompt")
    ap.add_argument("--negative-prompt", default="blur, distort, low quality, text, watermark, "
                                                 "deformed face, extra limbs, extra fingers")
    ap.add_argument("--model", default="kling",
                    help="alias (kling|seedance|veo) or a full fal endpoint id")
    ap.add_argument("--duration", default="5",
                    help="seconds of generated video, with or without a trailing 's' "
                         "(kling: 5 or 10 · veo 3.1: 4, 6 or 8)")
    ap.add_argument("--resolution", help="e.g. 720p or 1080p; only sent when given "
                                         "(veo 3.1 defaults to 720p without it)")
    ap.add_argument("--cfg-scale", type=float, default=0.5)
    ap.add_argument("--out", help="where to write the mp4")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--save-json", action="store_true", help="also write the raw fal response")
    args = ap.parse_args()

    if args.list_models:
        for alias, (ep, price, note) in MODELS.items():
            print(f"  {alias:9} ${price:.2f}/s  {ep}\n            {note}")
        return

    for req in ("prompt", "out"):
        if not getattr(args, req):
            sys.exit(f"--{req} is required")

    repo_root = Path(__file__).resolve().parent.parent

    endpoint, price, _ = MODELS.get(args.model, (args.model, None, ""))
    duration = duration_field(args.duration, endpoint)
    payload = {"prompt": args.prompt, "duration": duration,
               "negative_prompt": args.negative_prompt, "cfg_scale": args.cfg_scale}
    if args.resolution:
        payload["resolution"] = args.resolution
    if args.image:
        img = Path(args.image)
        if not img.exists():
            sys.exit(f"no such image: {img}")
        payload["image_url"] = data_uri(img)
        print(f"reference: {img}  ({img.stat().st_size // 1024} KB, inlined)")

    est = f"~${price * duration_seconds(args.duration):.2f}" if price else "unknown"
    res = f"   resolution: {args.resolution}" if args.resolution else ""
    print(f"model: {endpoint}\nduration: {duration}   est cost: {est}{res}")
    print(f"prompt: {args.prompt}")

    provider_name = (os.environ.get("VIDEO_PROVIDER") or "fal").strip() or "fal"
    generate = PROVIDERS.get(provider_name)
    if generate is None:
        sys.exit(f"unknown VIDEO_PROVIDER '{provider_name}': implement a function with the same "
                 f"signature as _fal_generate_video(repo_root, endpoint, payload, out, timeout) "
                 f"and add it to PROVIDERS in this file")

    out = Path(args.out)
    job, result = generate(repo_root, endpoint, payload, out, args.timeout)

    if args.save_json:
        js = out.with_suffix(".fal.json")
        js.write_text(json.dumps({"request_id": job["request_id"], "endpoint": endpoint,
                                  "duration": duration, "resolution": args.resolution,
                                  "image": args.image,
                                  "prompt": args.prompt,
                                  "negative_prompt": args.negative_prompt,
                                  "result": result}, indent=1),
                      encoding="utf-8")
        print(f"wrote {js}")


if __name__ == "__main__":
    main()
