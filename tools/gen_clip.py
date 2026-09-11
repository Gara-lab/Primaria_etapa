import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL = "fal-ai/veo3.1/fast"
QUEUE = "https://queue.fal.run"


def load_env():
    env = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return {**env, **os.environ}


def get_arg(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def parse_val(v):
    try:
        return json.loads(v)
    except (ValueError, json.JSONDecodeError):
        return v


def req_json(url, key, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Authorization": f"Key {key}",
                                        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"fal API error {e.code} at {url}:\n{e.read().decode()[:800]}")


def find_video_url(obj):
    if isinstance(obj, dict):
        u = obj.get("url")
        if isinstance(u, str) and (".mp4" in u or "video" in obj.get("content_type", "")):
            return u
        for v in obj.values():
            found = find_video_url(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_video_url(v)
            if found:
                return found
    return None


def _fal_generate_video(model, payload, out, timeout):
    key = load_env().get("FAL_KEY", "").strip()
    if not key:
        sys.exit("FAL_KEY not set in .env (get one at https://fal.ai/dashboard/keys)")

    sub = req_json(f"{QUEUE}/{model}", key, body=payload)
    status_url = sub.get("status_url") or f"{QUEUE}/{model}/requests/{sub['request_id']}/status"
    response_url = sub.get("response_url") or f"{QUEUE}/{model}/requests/{sub['request_id']}"
    print(f"queued: {sub.get('request_id')}")

    t0 = time.time()
    last = ""
    while True:
        st = req_json(f"{status_url}?logs=1", key)
        s = st.get("status", "?")
        if s != last:
            print(f"  {s}  (+{int(time.time()-t0)}s)")
            last = s
        if s == "COMPLETED":
            break
        if s in ("FAILED", "ERROR", "CANCELLED"):
            sys.exit(f"generation {s}: {json.dumps(st)[:800]}")
        if time.time() - t0 > timeout:
            sys.exit(f"timeout after {int(timeout)}s (request {sub.get('request_id')} may still finish; "
                     f"re-poll {response_url})")
        time.sleep(5)

    result = req_json(response_url, key)
    url = find_video_url(result)
    if not url:
        sys.exit("no video url in response:\n" + json.dumps(result)[:800])

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    urllib.request.urlretrieve(url, out)
    print(f"video -> {os.path.relpath(out, ROOT)}  ({os.path.getsize(out)//1024}KB)")

    return sub.get("request_id"), url


PROVIDERS = {
    "fal": _fal_generate_video,
}


def main():
    args = sys.argv[1:]
    model = get_arg(args, "--model", DEFAULT_MODEL)
    prompt = get_arg(args, "--prompt")
    out = get_arg(args, "--out")
    aspect = get_arg(args, "--aspect", "9:16")
    timeout = float(get_arg(args, "--timeout", "900"))
    dry = "--dry-run" in args

    if not prompt or not out:
        sys.exit("need --prompt and --out (--model, --aspect, --set k=v, --timeout, --dry-run also available)")

    payload = {"prompt": prompt, "aspect_ratio": aspect}
    for i, a in enumerate(args):
        if a == "--set":
            k, _, v = args[i + 1].partition("=")
            payload[k] = parse_val(v)

    print(f"model = {model}")
    print("payload =", json.dumps(payload, indent=2)[:600])
    if dry:
        print("[dry-run] no API call.")
        return

    provider = (load_env().get("VIDEO_PROVIDER") or "fal").strip() or "fal"
    generate = PROVIDERS.get(provider)
    if generate is None:
        sys.exit(f"unknown VIDEO_PROVIDER '{provider}': implement a function with the same "
                 f"signature as _fal_generate_video(model, payload, out, timeout) and add it "
                 f"to PROVIDERS in this file")

    request_id, url = generate(model, payload, out, timeout)

    sidecar = os.path.splitext(out)[0] + ".json"
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump({"model": model, "payload": payload, "request_id": request_id,
                   "source_url": url, "created": time.strftime("%Y-%m-%dT%H:%M:%S")},
                  f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"meta  -> {os.path.relpath(sidecar, ROOT)}")


if __name__ == "__main__":
    main()
