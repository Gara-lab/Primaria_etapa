import glob
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE_DIR = os.path.join(ROOT, "media", "library", "faces")
DEFAULT_MODEL = "gemini-3-pro-image"
RESPONSE_MODALITIES = ["IMAGE"]


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


def get_args_multi(args, name):
    out, i = [], 0
    while i < len(args):
        if args[i] == name and i + 1 < len(args):
            out.append(args[i + 1]); i += 2
        else:
            i += 1
    return out


def rel(path):
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def mime_for(path):
    ext = os.path.splitext(path)[1].lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp"}.get(ext, "image/jpeg")


def to_youtube_jpg(png_path, jpg_path, max_bytes=2_000_000, min_w=1280):
    from PIL import Image
    im = Image.open(png_path).convert("RGB")
    if im.width < min_w:
        print(f"  ! render is only {im.width}px wide (<{min_w}); YouTube min not met")
    for q in (95, 90, 85, 80, 72):
        im.save(jpg_path, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(jpg_path) <= max_bytes:
            break
    kb = os.path.getsize(jpg_path) // 1024
    print(f"  jpg  -> {rel(jpg_path)}  ({im.width}x{im.height}, q{q}, {kb}KB)")


def _gemini_image(api_key, model, prompt, refs, aspect, size, seed):
    from google import genai
    from google.genai import types

    contents = [prompt]
    for r in refs:
        with open(r, "rb") as f:
            contents.append(types.Part.from_bytes(data=f.read(), mime_type=mime_for(r)))

    cfg_kwargs = dict(
        response_modalities=RESPONSE_MODALITIES,
        image_config=types.ImageConfig(aspect_ratio=aspect, image_size=size),
    )
    if seed is not None and "seed" in types.GenerateContentConfig.model_fields:
        cfg_kwargs["seed"] = seed

    client = genai.Client(api_key=api_key)
    try:
        resp = client.models.generate_content(
            model=model, contents=contents,
            config=types.GenerateContentConfig(**cfg_kwargs))
    except Exception as e:
        sys.exit(f"Gemini API error: {type(e).__name__}: {e}")

    img_bytes, texts = None, []
    for cand in (resp.candidates or []):
        for part in ((cand.content.parts if cand.content else None) or []):
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                img_bytes = inline.data
            elif getattr(part, "text", None):
                texts.append(part.text)
    return img_bytes, texts


PROVIDERS = {
    "gemini": _gemini_image,
}


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    want_jpg = "--jpg" in args

    prompt = get_arg(args, "--prompt")
    pf = get_arg(args, "--prompt-file")
    if pf:
        prompt = open(pf, encoding="utf-8").read()
    out = get_arg(args, "--out")
    if not prompt or not out:
        sys.exit("need --prompt/--prompt-file and --out. See --help in the file header.")

    model = get_arg(args, "--model", DEFAULT_MODEL)
    aspect = get_arg(args, "--aspect", "16:9")
    size = get_arg(args, "--size", "2K")
    seed = get_arg(args, "--seed")
    seed = int(seed) if seed is not None else None

    refs = get_args_multi(args, "--ref")
    if not refs:
        refs = sorted(glob.glob(os.path.join(FACE_DIR, "*.jpg"))
                      + glob.glob(os.path.join(FACE_DIR, "*.png")))
    refs = [r for r in refs if os.path.exists(r)]

    print(f"model={model}  aspect={aspect}  size={size}  seed={seed}")
    print(f"refs ({len(refs)}):", ", ".join(rel(r) for r in refs) or "(none)")
    print(f"out -> {rel(out)}")
    print(f"prompt ({len(prompt)} chars):\n  " + prompt.strip().replace("\n", "\n  ")[:600]
          + ("…" if len(prompt) > 600 else ""))

    if not refs:
        print("  ! no reference images -- face consistency will be weak. "
              "Drop a shot in media/library/faces/ or pass --ref.")

    if dry:
        print("\n[dry-run] validated; no API call made.")
        return

    env = load_env()
    provider_name = (env.get("IMAGE_PROVIDER") or "gemini").strip() or "gemini"
    provider = PROVIDERS.get(provider_name)
    if provider is None:
        sys.exit(f"Unknown IMAGE_PROVIDER '{provider_name}'. Implement a function with the "
                  f"same signature as _gemini_image() and add it to PROVIDERS in this file.")

    api_key = env.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        sys.exit("GEMINI_API_KEY not set in .env — cannot generate. (Add it, or use --dry-run.)")

    img_bytes, texts = provider(api_key, model, prompt, refs, aspect, size, seed)
    if texts:
        print("  model text:", " ".join(texts)[:300])
    if not img_bytes:
        sys.exit("No image returned. Model text above may explain (safety block / refusal / "
                 "wrong model id). Try a different --model or adjust the prompt.")

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(img_bytes)
    print(f"  png  -> {rel(out)}  ({len(img_bytes)//1024}KB)")

    sidecar = os.path.splitext(out)[0] + ".json"
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump({
            "prompt": prompt, "model": model, "aspect_ratio": aspect, "image_size": size,
            "seed": seed, "refs": [rel(r) for r in refs],
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  meta -> {rel(sidecar)}")

    if want_jpg:
        to_youtube_jpg(out, os.path.splitext(out)[0] + ".jpg")


if __name__ == "__main__":
    main()
