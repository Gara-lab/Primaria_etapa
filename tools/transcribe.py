import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://api.assemblyai.com/v2"

SPEECH_MODELS = ["universal-3-5-pro", "universal-2"]
PROMPT = (
    "Verbatim transcription of a solo YouTube tutorial recording with multiple takes. "
    "Transcribe exactly as spoken: keep false starts, repeated words, self-corrections, "
    "and filler words (um, uh) — do not clean them up."
)


def load_keyterms(project: Path) -> list[str]:
    f = project / "work" / "keyterms.txt"
    if not f.exists():
        return []
    terms = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def load_env_key(repo_root: Path, name: str) -> str:
    for line in (repo_root / ".env").read_text().splitlines():
        line = line.strip()
        if line.startswith(name + "="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    sys.exit(f"{name} not found in .env")


def upload(headers: dict, wav: Path) -> str:
    with open(wav, "rb") as f:
        r = requests.post(f"{API_BASE}/upload", headers=headers, data=f, timeout=300)
    r.raise_for_status()
    return r.json()["upload_url"]


def submit(headers: dict, audio_url: str, keyterms: list[str]) -> str:
    payload = {
        "audio_url": audio_url,
        "speech_models": SPEECH_MODELS,
        "language_detection": True,
        "punctuate": True,
        "format_text": True,
        "disfluencies": True,
        "prompt": PROMPT,
    }
    if keyterms:
        payload["keyterms_prompt"] = keyterms
    r = requests.post(f"{API_BASE}/transcript", headers=headers, json=payload, timeout=60)
    if r.status_code == 400:
        print(f"  400 ({r.json().get('error', '?')}), retrying without disfluencies flag")
        payload.pop("disfluencies")
        r = requests.post(f"{API_BASE}/transcript", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def _assemblyai_transcribe(repo_root: Path, project: Path, audio_dir: Path, out_dir: Path,
                           clips: list[str] | None, force: bool) -> None:
    headers = {"authorization": load_env_key(repo_root, "ASSEMBLYAI_API_KEY")}

    keyterms = load_keyterms(project)
    print(f"keyterms: {len(keyterms)} loaded from work/keyterms.txt"
          if keyterms else "keyterms: none (no work/keyterms.txt) — add this video's terms for better accuracy")

    jobs = {}
    for wav in sorted(audio_dir.glob("*.wav")):
        clip = wav.stem
        if clips and clip not in clips:
            continue
        if not force and (out_dir / f"{clip}.json").exists():
            print(f"{clip}: transcript exists, skipping")
            continue
        print(f"{clip}: uploading {wav.stat().st_size // 1024} KB...")
        jobs[clip] = submit(headers, upload(headers, wav), keyterms)
        print(f"{clip}: submitted, transcript id {jobs[clip]}")

    pending = dict(jobs)
    while pending:
        time.sleep(5)
        for clip, tid in list(pending.items()):
            r = requests.get(f"{API_BASE}/transcript/{tid}", headers=headers, timeout=60)
            r.raise_for_status()
            data = r.json()
            if data["status"] == "completed":
                (out_dir / f"{clip}.json").write_text(json.dumps(data, indent=1))
                model = data.get("speech_model_used") or data.get("speech_model") or "?"
                print(f"{clip}: completed, {len(data.get('words') or [])} words, model={model}")
                del pending[clip]
            elif data["status"] == "error":
                print(f"{clip}: ERROR {data.get('error')}")
                del pending[clip]

    print("done")


PROVIDERS = {
    "assemblyai": _assemblyai_transcribe,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--clips", nargs="*", help="clip ids, default all")
    ap.add_argument("--outdir", default="transcripts")
    ap.add_argument("--force", action="store_true", help="re-transcribe even if output exists")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    project = repo_root / args.project
    audio_dir = project / "work" / "audio"
    out_dir = project / "work" / args.outdir
    out_dir.mkdir(parents=True, exist_ok=True)

    provider_name = (os.environ.get("TRANSCRIBE_PROVIDER") or "assemblyai").strip() or "assemblyai"
    transcribe = PROVIDERS.get(provider_name)
    if transcribe is None:
        sys.exit(f"unknown TRANSCRIBE_PROVIDER '{provider_name}': implement a function with the same "
                 f"signature as _assemblyai_transcribe(repo_root, project, audio_dir, out_dir, clips, force) "
                 f"and add it to PROVIDERS in this file")

    transcribe(repo_root, project, audio_dir, out_dir, args.clips, args.force)


if __name__ == "__main__":
    main()
