import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

from cutlib import AudioProbe, active_keeps, load_words, plan_clip

SR = 48000

ENC = {
    "preview": ["-vf", "scale=1280:-2,format=yuv420p", "-c:v", "h264_nvenc", "-preset", "p4",
                "-rc", "vbr", "-cq", "30", "-b:v", "0"],
    "final": ["-c:v", "hevc_nvenc", "-preset", "p5", "-profile:v", "main10",
              "-pix_fmt", "p010le", "-rc", "vbr", "-cq", "19", "-b:v", "0"],
}
AUDIO_BITRATE = {"preview": "160k", "final": "256k"}


def render_segment(src: Path, seg: tuple[float, float], out: Path, enc: list[str]) -> None:
    start, end = seg
    dur = end - start
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-hwaccel", "cuda",
           "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
           "-map", "0:0", "-an", *enc, str(out)]
    subprocess.run(cmd, check=True)


def is_finalized(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1024:
        return False
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() not in ("", "N/A")


def video_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames,avg_frame_rate,duration",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)["streams"][0]
    try:
        return int(st["nb_frames"]) / float(Fraction(st["avg_frame_rate"]))
    except (KeyError, ValueError, ZeroDivisionError):
        return float(st["duration"])


def render_audio_segment(src: Path, start: float, dur: float, out: Path) -> None:
    n = round(dur * SR)
    fades = (f"atrim=end_sample={n},"
             f"afade=t=in:d=0.01,afade=t=out:st={max(n / SR - 0.01, 0):.4f}:d=0.01")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-ss", f"{start:.3f}", "-t", f"{dur + 0.2:.3f}", "-i", str(src),
           "-vn", "-ar", str(SR), "-ac", "1", "-af", fades,
           "-c:a", "pcm_s16le", str(out)]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--style", required=True)
    ap.add_argument("--mode", choices=["preview", "final"], default="preview")
    args = ap.parse_args()

    project = Path(__file__).resolve().parent.parent / args.project
    data = json.loads((project / "work" / "analysis" / "cuts.json").read_text(encoding="utf-8"))
    style = data["styles"][args.style]
    probe = AudioProbe(project)

    jobs = []
    by_id = {c["id"]: c for c in data["clips"]}
    for cid in data["clip_order"]:
        clip = by_id[cid]
        words = load_words(project, cid)
        for seg in plan_clip(cid, active_keeps(clip), words, style, probe, clip.get("cuts")):
            jobs.append((project / clip["file"], seg))

    total = sum(e - s for _, (s, e) in jobs)
    print(f"{args.style}/{args.mode}: {len(jobs)} segments, output ~ {total / 60:.1f} min")

    seg_dir = project / "work" / "render" / f"{args.style}-{args.mode}"
    seg_dir.mkdir(parents=True, exist_ok=True)
    outs = [seg_dir / f"seg_{i:03d}.mp4" for i in range(len(jobs))]

    todo = [(src, seg, out) for (src, seg), out in zip(jobs, outs) if not is_finalized(out)]
    if len(todo) < len(jobs):
        print(f"  resuming: {len(jobs) - len(todo)} segments already encoded, {len(todo)} to go")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(render_segment, src, seg, out, ENC[args.mode]) for src, seg, out in todo]
        for i, f in enumerate(futs):
            f.result()
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(todo)} segments encoded")

    stale = [o for o in outs if not is_finalized(o)]
    if stale:
        raise SystemExit(f"{len(stale)} segments did not finalize, first: {stale[0]}")

    bsf = "hevc_mp4toannexb" if args.mode == "final" else "h264_mp4toannexb"
    ts_files = []
    for o in outs:
        ts = o.with_suffix(".ts")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(o),
                        "-c", "copy", "-bsf:v", bsf, "-f", "mpegts", str(ts)], check=True)
        ts_files.append(ts)
    list_file = seg_dir / "list.txt"
    list_file.write_text("\n".join(f"file '{t.as_posix()}'" for t in ts_files), encoding="utf-8")
    video_concat = seg_dir / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(list_file), "-c", "copy", "-fflags", "+genpts",
                    str(video_concat)], check=True)

    print("building drift-free audio track...")
    wavs = []
    for (src, (start, _end)), out in zip(jobs, outs):
        dur = video_duration(out)
        wav = out.with_suffix(".wav")
        render_audio_segment(src, start, dur, wav)
        wavs.append(wav)
    alist = seg_dir / "alist.txt"
    alist.write_text("\n".join(f"file '{w.as_posix()}'" for w in wavs), encoding="utf-8")
    audio_concat = seg_dir / "audio.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(alist), "-c", "copy", str(audio_concat)], check=True)

    out_name = f"{'preview' if args.mode == 'preview' else 'master'}-{args.style}.mp4"
    out_path = project / "output" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(video_concat), "-i", str(audio_concat),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", AUDIO_BITRATE[args.mode],
                    str(out_path)], check=True)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
