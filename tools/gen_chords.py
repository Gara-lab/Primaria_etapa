import argparse
import array
import json
import math
import os
import subprocess
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.dirname(HERE)
SFX_DIR = os.path.join(CORE, "media", "library", "sfx")
CLIPS_DIR = os.path.join(SFX_DIR, "clips")
CATALOG = os.path.join(SFX_DIR, "catalog.json")

SR = 44100
TARGET_LUFS = -20.0
PEAK_CEIL = -1.5


def midi_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69) / 12.0))


NOTE_BASE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def midi(name: str, octave: int) -> int:
    return 12 * (octave + 1) + NOTE_BASE[name]


CHORDS = [
    ("piano-c-maj", "C major triad (I) — warm electric-piano voicing", [("C", 3), ("C", 4), ("E", 4), ("G", 4)]),
    ("piano-g-maj", "G major triad (V)", [("G", 2), ("G", 3), ("B", 3), ("D", 4)]),
    ("piano-a-min", "A minor triad (vi)", [("A", 2), ("A", 3), ("C", 4), ("E", 4)]),
    ("piano-f-maj", "F major triad (IV)", [("F", 2), ("F", 3), ("A", 3), ("C", 4)]),
]

DUR = 2.6


def synth_chord(notes, dur=DUR):
    n = int(SR * dur)
    buf = [0.0] * n

    HARMONICS = [(1, 1.00), (2, 0.32), (3, 0.14), (4, 0.07), (6, 0.03)]

    for i, (name, octv) in enumerate(notes):
        f0 = midi_hz(midi(name, octv))
        note_amp = 0.62 if i == 0 else 1.0
        delay = int(SR * 0.006 * i)
        detune = 1.0 + (0.0006 * (i - 1.5))

        for h, hamp in HARMONICS:
            f = f0 * h * detune
            if f > SR / 2.2:
                continue
            w = 2.0 * math.pi * f / SR
            decay = 2.6 + 0.85 * h
            a = note_amp * hamp
            for s in range(delay, n):
                t = (s - delay) / SR
                env = math.exp(-decay * t)
                if env < 1e-4:
                    break
                atk = min(1.0, t / 0.009)
                buf[s] += a * atk * env * math.sin(w * (s - delay))

    peak = max(abs(v) for v in buf) or 1.0
    return [v / peak * 0.89 for v in buf]


def write_wav(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        pcm = array.array("h", (int(max(-1.0, min(1.0, v)) * 32767) for v in samples))
        w.writeframes(pcm.tobytes())


def normalize_to_mp3(wav_path, mp3_path):
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", wav_path,
         "-af", f"loudnorm=I={TARGET_LUFS}:TP={PEAK_CEIL}:LRA=11",
         "-ar", "44100", "-ac", "1", "-b:a", "192k", mp3_path],
        check=True,
    )


def probe(path, entries):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", f"format={entries}", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-synthesize clips that already exist")
    ap.add_argument("--only", help="just this chord id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    os.makedirs(CLIPS_DIR, exist_ok=True)
    catalog = json.load(open(CATALOG, encoding="utf-8"))
    by_id = {c["id"]: c for c in catalog["clips"]}

    todo = [c for c in CHORDS if not args.only or c[0] == args.only]
    if not todo:
        sys.exit(f"no chord matches --only {args.only}")

    made = 0
    for cid, desc, notes in todo:
        mp3 = os.path.join(CLIPS_DIR, f"{cid}.mp3")
        rel = os.path.relpath(mp3, SFX_DIR).replace("\\", "/")

        if os.path.exists(mp3) and not args.force:
            print(f"  = {cid:14} exists, skipping")
            continue
        if args.dry_run:
            print(f"  + {cid:14} WOULD synth {' '.join(n+str(o) for n, o in notes)}")
            continue

        pitches = " ".join(f"{n}{o}({midi_hz(midi(n, o)):.1f}Hz)" for n, o in notes)
        print(f"  + {cid:14} {pitches}")
        samples = synth_chord(notes)
        with tempfile.TemporaryDirectory() as td:
            wav = os.path.join(td, "c.wav")
            write_wav(wav, samples)
            normalize_to_mp3(wav, mp3)

        entry = by_id.get(cid, {"id": cid})
        entry.update({
            "id": cid,
            "file": rel,
            "desc": desc,
            "function": "content",
            "source": "gen_chords.py (deterministic additive synth, equal temperament A4=440)",
            "duration_s": round(float(probe(mp3, "duration")), 3),
        })
        entry.setdefault("used_in", [])
        if cid not in by_id:
            catalog["clips"].append(entry)
            by_id[cid] = entry
        made += 1

    if not args.dry_run and made:
        json.dump(catalog, open(CATALOG, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"\ncatalog updated -> {CATALOG}  ({made} chord clip(s))")


if __name__ == "__main__":
    main()
