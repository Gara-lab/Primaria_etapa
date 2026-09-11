# Code Map

Hand-authored and hand-maintained, same as every other spec doc in this project — no
AST parsing, no doc-generation script (keep this lightweight; only reach for tooling
later if maintaining this file by hand actually becomes a bottleneck, not
preemptively). This is the sole home for non-obvious implementation-level
why/invariant/gotcha content that would otherwise end up as an inline code comment.

Per CLAUDE.md, source code carries zero comment lines once this project has real
implementation files. Anything that isn't self-evident from naming, and isn't already
owned by another spec doc (ARCHITECTURE.md, CONTRACTS.md, or whatever else this
project's `planner`/lead agent created), belongs here instead.

**Rule going forward:** any code change that introduces a new non-obvious
why/invariant/gotcha must add or update an entry here as part of that task's own
deliverables, and must not introduce a comment instead. A genuine product/business
decision found while writing an entry does not belong here either — promote it into
the applicable spec doc (e.g. ARCHITECTURE.md's decision log) instead of leaving it in
CODE_MAP.md.

Entries are grouped by file, one entry per non-obvious code region — not one per file,
and not one per every function. Most functions need no entry because their behavior is
self-evident from naming/signature or is already specified elsewhere.

Format:

---

## <file path>

**Location:** `<file> → <functionOrRegion>()`
**Why / invariant / gotcha:** <the actual content — what would have been the comment,
trimmed of anything that just restates the code or duplicates another spec doc>
**Spec cross-reference (if any):** <a pointer only, e.g. "ARCHITECTURE.md D3" — never a
restatement of that doc's content>

---

## tools/gen_voice.py

**Location:** `tools/gen_voice.py → main() / PROVIDERS dispatch loop`
**Why / invariant / gotcha:** Generates each VO line individually via the TTS provider (rather than one batched call) so a single flagged line can be re-rolled without re-billing or regenerating every other line; each line is cached to disk keyed by a content hash of (voice, model, tts-text), so unchanged lines are skipped unless `--force` is passed.
**Spec cross-reference (if any):**

**Location:** `tools/gen_voice.py → main() tempo-fit loop / MAX_ATEMPO`
**Why / invariant / gotcha:** When a generated line's raw audio overflows the time window implied by beats.json (next line's start minus this line's start), it is sped up with ffmpeg atempo rather than truncated or re-prompted; MAX_ATEMPO=1.3 caps the speed-up at 30% so it never sounds unnatural, and any remaining overflow is logged ("OVERFLOW") rather than silently clipped.
**Spec cross-reference (if any):**

**Location:** `tools/gen_voice.py → main() (writes beats["voiceStatus"], line["end"], line["words"] back to beats_path)`
**Why / invariant / gotcha:** The tool writes the ACTUAL measured line end-time and word-level alignment (scaled by the applied tempo factor) back into beats.json, because downstream TSX captions retime themselves from these actual values rather than from the original estimated start/end in the input file.
**Spec cross-reference (if any):**

**Location:** `tools/gen_voice.py → _elevenlabs_tts()`
**Why / invariant / gotcha:** The `text` argument may contain ElevenLabs v3 delivery tags like "[excited]" that steer vocal delivery but must never appear as captions; after alignment, any word entry whose text starts/ends with a bracket is filtered out of the returned word map. Separately: if the requested model rejects the `/with-timestamps` endpoint (HTTP 400/404/422), the function silently retries with plain TTS and returns an empty word map, so callers fall back to beats.json's estimated timing for that line. Also: eleven_v3 models reject the classic voice_settings block and the previous_text/next_text context-stitching parameters, so those are only sent for non-v3 models — v3's own server-side defaults are already tuned correctly.
**Spec cross-reference (if any):**

**Location:** `tools/gen_voice.py → DEFAULT_VOICE`
**Why / invariant / gotcha:** The literal ElevenLabs voice ID "TX3LPaxmHKxFdv7VOQHJ" is the premade voice named "Liam" — not derivable from the ID string itself.
**Spec cross-reference (if any):**

## tools/gen_vo.mjs

**Location:** `tools/gen_vo.mjs → _elevenlabsTts() (previousRequestIds.slice(-3))`
**Why / invariant / gotcha:** Consecutive per-beat TTS requests are stitched together via the API's previous_request_ids parameter so prosody stays consistent across the whole Short; the API only accepts the 3 most recent request IDs, hence the slice(-3).
**Spec cross-reference (if any):**

**Location:** `tools/gen_vo.mjs → beats input file format (module-level usage note)`
**Why / invariant / gotcha:** The beats input JSON maps beat-id -> TTS text, where SSML `<break/>` tags are allowed and numbers must be spelled the way they should be SPOKEN (e.g. "p fifty" not "p50") since the text is sent verbatim to the TTS engine.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log (locked voice identity)

## tools/gen_sfx.py

**Location:** `tools/gen_sfx.py → module header`
**Why / invariant / gotcha:** Requires ffmpeg/ffprobe on PATH (used for duration probing, peak/LUFS measurement, and gain normalization); without ffmpeg on PATH the script runs but all measurements silently come back None.
**Spec cross-reference (if any):**

**Location:** `tools/gen_sfx.py → catalog['note'] / write_catalog()`
**Why / invariant / gotcha:** catalog.json is a cross-file contract: it's read by tools/mix_sfx.py and the /suggest-sfx skill, and clips meant to live inside a Remotion TSX shot must instead go in remotion/public/media/library/sfx/ via staticFile() rather than this library.
**Spec cross-reference (if any):**

**Location:** `tools/gen_sfx.py → load_env()`
**Why / invariant / gotcha:** Deliberately reinvents a minimal .env parser instead of adding a python-dotenv dependency.
**Spec cross-reference (if any):**

**Location:** `tools/gen_sfx.py → measure_lufs() / normalize_clip()`
**Why / invariant / gotcha:** ebur128 integrated-loudness readings are unreliable/gated for clips under ~1s (typical SFX transients); normalize_clip() falls back to peak-only normalization when lufs is None or below -50. It always clamps gain so peak never exceeds ceiling_db even if that undershoots target_lufs.
**Spec cross-reference (if any):**

## tools/gen_music.py

**Location:** `tools/gen_music.py → module header`
**Why / invariant / gotcha:** Requires ffmpeg/ffprobe on PATH for the same duration/loudness/normalization steps as gen_sfx.py.
**Spec cross-reference (if any):**

**Location:** `tools/gen_music.py → catalog['note'] / write_catalog()`
**Why / invariant / gotcha:** catalog.json here is read by tools/mix_music.py; beds are meant to sit under the voice as a continuous ducked bed, not as one-off clips.
**Spec cross-reference (if any):**

**Location:** `tools/gen_music.py → measure_lufs()`
**Why / invariant / gotcha:** Contrast with gen_sfx.py: for music beds (multi-second, non-gated) the ebur128 integrated-loudness reading is reliable, so the short-clip fallback branch (lufs is None or < -50) exists only for edge cases here, not as the expected path.
**Spec cross-reference (if any):**

## tools/gen_image.py

**Location:** `tools/gen_image.py → PRESETS`
**Why / invariant / gotcha:** Preset ids (pro/fast/lite -> gemini-3-pro-image / gemini-3.1-flash-image / gemini-3.1-flash-lite-image) were confirmed against the live Gemini models endpoint on 2026-07-10. If generation starts failing with a model-not-found error, these ids likely changed upstream and need re-confirming.
**Spec cross-reference (if any):**

**Location:** `tools/gen_image.py → main() refs handling`
**Why / invariant / gotcha:** Deliberately has no default reference-image kit — refs are optional and only added via explicit --ref. This differs from its sibling tools/gen_thumbnail.py, which defaults to the whole media/library/faces/ kit when no --ref is passed, for face consistency.
**Spec cross-reference (if any):**

## tools/gen_thumbnail.py

**Location:** `tools/gen_thumbnail.py → DEFAULT_MODEL`
**Why / invariant / gotcha:** Defaults to gemini-3-pro-image (Nano Banana Pro) rather than a cheaper tier because Pro is the tier whose in-image text rendering (the thumbnail hook word) is reliably legible. The tradeoff is occasional garbled/misspelled AI-rendered text, which the /packaging skill's verify step is expected to catch by reading every render back before showing it to the user.
**Spec cross-reference (if any):**

**Location:** `tools/gen_thumbnail.py → RESPONSE_MODALITIES`
**Why / invariant / gotcha:** Set to ["IMAGE"] only for this file (image models can also emit a 'thinking' text part alongside the image); if the API starts rejecting ["IMAGE"] for a given model, switch this to ["TEXT", "IMAGE"] as tools/gen_image.py already does.
**Spec cross-reference (if any):**

**Location:** `tools/gen_thumbnail.py → rel()`
**Why / invariant / gotcha:** Catches ValueError from os.path.relpath because that call raises (rather than returning a usable relative path) when the two paths are on different drives on Windows; falls back to the raw absolute path in that case.
**Spec cross-reference (if any):**

**Location:** `tools/gen_thumbnail.py → to_youtube_jpg()`
**Why / invariant / gotcha:** max_bytes=2_000_000 and min_w=1280 encode YouTube's published thumbnail upload spec (16:9, minimum 1280px wide, maximum 2MB file size) — not arbitrary values.
**Spec cross-reference (if any):**

**Location:** `tools/gen_thumbnail.py → load_env()`
**Why / invariant / gotcha:** Implements a minimal hand-rolled .env parser instead of depending on python-dotenv, matching the same approach used in gen_sfx.py so tools/ doesn't need two different env-loading conventions.
**Spec cross-reference (if any):**

## tools/gen_clip.py

**Location:** `tools/gen_clip.py → module design`
**Why / invariant / gotcha:** Model-agnostic by design within the fal provider: the fal model id is just a string passed via --model, so swapping models is a flag change, never a code change.
**Spec cross-reference (if any):**

**Location:** `tools/gen_clip.py → main() sidecar write`
**Why / invariant / gotcha:** Writes a sidecar `<out>.json` with model, payload, and request id alongside every generated clip so the generation is reproducible later.
**Spec cross-reference (if any):**

**Location:** `tools/gen_clip.py → cost/pricing workflow`
**Why / invariant / gotcha:** fal costs are per-model and change over time; check fal's pricing page before generating and state the cost when proposing a clip in a video plan.
**Spec cross-reference (if any):**

## tools/gen_video.py

**Location:** `tools/gen_video.py → data_uri() / args.image`
**Why / invariant / gotcha:** Reference images are passed as local files and inlined as base64 data URIs specifically so nothing of the presenter's likeness leaves the machine except to the video provider for that one request. For likeness continuity, extract the reference frame from the master at the cut point (e.g. via `ffmpeg -ss <t> -frames:v 1`) so the generated clip continues the real take.
**Spec cross-reference (if any):**

**Location:** `tools/gen_video.py → payload construction (no audio field)`
**Why / invariant / gotcha:** Generated clips never need an audio track because bake.py muxes the master audio over everything downstream, so any generated audio would be discarded anyway.
**Spec cross-reference (if any):**

**Location:** `tools/gen_video.py → duration_field()`
**Why / invariant / gotcha:** Vendors validate duration spelling differently: veo 3.1 rejects a bare number and only accepts '4s'|'6s'|'8s', while kling/seedance reject the 's' suffix and want a bare number; this function normalizes a single CLI --duration value into whichever spelling the target endpoint expects.
**Spec cross-reference (if any):**

**Location:** `tools/gen_video.py → module scope`
**Why / invariant / gotcha:** This tool is for generated beats that TSX/Remotion cannot fake (physical gags, presenter-likeness inserts). Anything a browser/terminal/diagram can show should still be a Remotion shot, not a generated clip.
**Spec cross-reference (if any):**

## tools/gen_avatar.mjs

**Location:** `tools/gen_avatar.mjs → language choice`
**Why / invariant / gotcha:** Written in Node rather than Python specifically because the avatar/lipsync endpoints require a real upload step and the target machine had no Python available; Node's built-in fetch avoided adding any dependency.
**Spec cross-reference (if any):**

**Location:** `tools/gen_avatar.mjs → uploadToFal()`
**Why / invariant / gotcha:** fal rejects base64 data-URIs for audio inputs, so local audio (and, for consistency, image) files must be uploaded to the fal CDN first via an initiate+PUT flow, and the returned URL is what gets sent in the payload.
**Spec cross-reference (if any):**

**Location:** `tools/gen_avatar.mjs → reencode()`
**Why / invariant / gotcha:** Some models return H.264 High 4:4:4 (yuv444p) output that Windows players and some NLEs refuse to play; --reencode normalizes the file to yuv420p via ffmpeg.
**Spec cross-reference (if any):**

**Location:** `tools/gen_avatar.mjs → args.image usage`
**Why / invariant / gotcha:** These avatar models follow the aspect ratio of the input image, so a 9:16 Short needs a 9:16 reference image fed in.
**Spec cross-reference (if any):**

**Location:** `tools/gen_avatar.mjs → main() sidecar write / MODELS`
**Why / invariant / gotcha:** Every run writes a sibling `<out>.fal.json` with the request id, endpoint, inputs, and raw response so any clip can be traced back to what produced it. Each MODELS entry's 'kind' field records what the endpoint drives the face from ('image' vs 'video'), controlling whether the code sends image_url or video_url; price is USD per second of output video.
**Spec cross-reference (if any):**

## tools/transcribe.py

**Location:** `tools/transcribe.py → load_keyterms()`
**Why / invariant / gotcha:** Reads per-video vocabulary from `<project>/work/keyterms.txt` (one term/phrase per line, blank lines and '#'-lines ignored) to bias the transcription provider's keyterms prompt toward this video's proper nouns/product/tech names. Missing file returns [] — transcription still works, just with more errors on specialty words. Draft the file per video from the topic; never hardcode a video's terms in this source file.
**Spec cross-reference (if any):**

**Location:** `tools/transcribe.py → submit()`
**Why / invariant / gotcha:** PROMPT is a generic instruction (solo YouTube tutorial, verbatim, keep false starts/filler words) that holds true for every recording this pipeline processes, hence a global constant. keyterms_prompt is only added to the payload when the keyterms list is non-empty. A 400 response is retried once with the disfluencies flag removed from the payload, because that older parameter is rejected by the API when combined with the newer speech models.
**Spec cross-reference (if any):**

## tools/clean_voice.py

**Location:** `tools/clean_voice.py → main() (audio extraction)`
**Why / invariant / gotcha:** Audio is downmixed to mono before cleaning because the source master is dual-mono, so mono halves file size and loses nothing.
**Spec cross-reference (if any):**

**Location:** `tools/clean_voice.py → main() (rnnoise branch, model path)`
**Why / invariant / gotcha:** arnndn's model path goes inside the ffmpeg filtergraph string, where ':' (option separator) and '\\' (escape) mangle a Windows absolute path. ffmpeg is therefore run with cwd=ROOT and given a relative, forward-slash, colon-free model path instead.
**Spec cross-reference (if any):**

**Location:** `tools/clean_voice.py → main() (loudness preservation)`
**Why / invariant / gotcha:** Cleaned audio is gain-matched to the source's RMS level (speech-dominated, ungated) rather than integrated LUFS, because LUFS is gated and inflated by the noise that was just removed and would over-boost the voice into clipping. The gain offset is capped (CEIL = -1.0 dBFS) so the isolated track's peak never exceeds that ceiling.
**Spec cross-reference (if any):**

## tools/notion_sync.py

**Location:** `tools/notion_sync.py → find_row()`
**Why / invariant / gotcha:** Ideas get parked early: a tracker row usually already exists under a rough working name months before the project folder does, so matching is tried on the Project property first (authoritative) and falls back to matching by title — a blind create would produce a duplicate row.
**Spec cross-reference (if any):**

**Location:** `tools/notion_sync.py → synced_from() / clear_tail()`
**Why / invariant / gotcha:** Only the 'Source of truth' callout and everything after it is treated as the synced, replaceable body. Anything above that callout (early idea notes, comments) is intentionally never touched or cleared. One deletion pass is not enough: Notion's children listing is eventually consistent, so a scan right after a large append can under-report and leave survivors above the fresh body — clear_tail() re-scans and deletes until nothing remains past `keep`, giving up after `passes` attempts.
**Spec cross-reference (if any):**

**Location:** `tools/notion_sync.py → module (stdout wrapping) / rt() / module constants`
**Why / invariant / gotcha:** stdout is rewrapped as UTF-8 (errors='replace') because the script's own output is full of em dashes and emoji. Text pieces are chunked into <=1900-character segments because Notion's rich_text field has a hard 2000-character cap per block. BATCH is 90, not 100, because Notion caps block-children append requests at 100 per call; PAUSE is 0.35s to stay under Notion's ~3 requests/second rate limit.
**Spec cross-reference (if any):**

**Location:** `tools/notion_sync.py → find_db()`
**Why / invariant / gotcha:** NOTION_LONGS_PAGE_ID points at the Content Plan page, not a database directly, so this walks that page's children to find the 'YouTube Videos' child database by title.
**Spec cross-reference (if any):**

## tools/yt_upload.py

**Location:** `tools/yt_upload.py → module (REPO vs ROOT)`
**Why / invariant / gotcha:** REPO is the engine root (holds OAuth creds under .youtube/); ROOT is the parent project root, and plan paths like 'video' and 'description_file' are resolved relative to ROOT, not REPO — the two roots are deliberately different.
**Spec cross-reference (if any):**

**Location:** `tools/yt_upload.py → module (SCOPES) / module (stdout reconfigure)`
**Why / invariant / gotcha:** The plain '.../auth/youtube' scope is requested in addition to '.../youtube.upload' specifically because it covers thumbnails.set and other post-upload edits. Windows consoles default to cp1252, so stdout is reconfigured to UTF-8 (errors=replace) to let box-drawing/checkmark glyphs print without crashing.
**Spec cross-reference (if any):**

**Location:** `tools/yt_upload.py → do_upload() (thumbnail set)`
**Why / invariant / gotcha:** For a vertical <=3-minute upload (Shorts-shaped) YouTube usually ignores the thumbnails.set API call — it returns success but the cover stays blank. The only reliable way to set a Shorts cover is the YouTube mobile app; Desktop Studio and the API cannot do it.
**Spec cross-reference (if any):**

**Location:** `tools/yt_upload.py → build_body() / main() (draft mode default) / module (quota)`
**Why / invariant / gotcha:** Standard YouTube Data API quota is 10,000 units/day and an upload costs ~100 units, giving roughly 100 uploads/day; some new Cloud projects start at 0 queries/day and must request quota via YouTube's Audit & Quota Extension form.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log (draft-mode-default upload policy)

## tools/yt_stats.py

**Location:** `tools/yt_stats.py → module / get_creds() (token separation)`
**Why / invariant / gotcha:** Uses its own OAuth token at .youtube/token-analytics.json with read-only scopes, kept separate from yt_upload's token.json (write scopes), so pulling stats can never touch or invalidate the upload credentials.
**Spec cross-reference (if any):**

**Location:** `tools/yt_stats.py → METRICS`
**Why / invariant / gotcha:** impressionClickThroughRate (CTR) is deliberately excluded from METRICS — it is YouTube Studio-only and the Analytics API 400s on it. CTR must be pulled by hand from Studio for packaging calibration; this omission is intentional, not a gap to fill in later.
**Spec cross-reference (if any):**

**Location:** `tools/yt_stats.py → fetch()`
**Why / invariant / gotcha:** The Analytics query window runs from the video's publish date to today (lifetime stats) and is owner-only — it fails cleanly, falling back to public Data API stats only, if the authorized account doesn't own the video.
**Spec cross-reference (if any):**

## tools/bakeoff_clip.py

**Location:** `tools/bakeoff_clip.py (no PROVIDER dispatch)`
**Why / invariant / gotcha:** This tool's whole purpose is comparing multiple fal.ai video models side-by-side in one run — there is no single generic capability to swap behind a provider dispatch, since the point is calling several vendor endpoints in parallel and comparing them. The MODELS registry is kept as a plain fal-specific comparison, not collapsed into a PROVIDERS dict.
**Spec cross-reference (if any):**

**Location:** `tools/bakeoff_clip.py → module (derived cost notes) / FPS constant`
**Why / invariant / gotcha:** Costs are derived from published per-model pricing formulas rather than trusted at face value: Seedance is token-priced (tokens = h*w*fps*dur/1024, $1.2/1M audio-off — formula reproduces fal's own worked example to the cent), Wan 2.5 is resolution-tiered (the flat $0.05 people quote is only the 480p rate), and cheap "$0.03-0.05/s Veo" figures belong to Veo 3.1 LITE, not Fast. FPS=24 is hardcoded because it was validated against fal's own Seedance worked example — changing it would silently invalidate the derived Seedance cost.
**Spec cross-reference (if any):**

**Location:** `tools/bakeoff_clip.py → billed_costs() / req_json()`
**Why / invariant / gotcha:** The fal usage API for actual billed cost needs an ADMIN-scoped key; with a regular key it 403s, so this falls back silently to the derived cost and panels get labelled 'est' instead of 'billed'. req_json() raises exceptions instead of calling sys.exit (unlike gen_clip.py's equivalent helper) because this one runs inside worker threads, where sys.exit would only terminate that thread.
**Spec cross-reference (if any):**

**Location:** `tools/bakeoff_clip.py → build_grid() / MODELS`
**Why / invariant / gotcha:** When only one panel is requested, its filter output is renamed directly to [grid] instead of going through hstack, because ffmpeg's hstack filter requires at least 2 inputs. Kling's resolution lambda always returns '1080p' regardless of --resolution because Kling has no resolution knob. generate_audio is forced False on every model that exposes the flag because voice/SFX come from the dedicated voice/SFX pipeline, and audio-off also halves Seedance's token rate.
**Spec cross-reference (if any):**

## tools/gen_chords.py

**Location:** `tools/gen_chords.py → module (tool boundary)`
**Why / invariant / gotcha:** gen_music.py/gen_sfx.py call generative APIs and cannot produce an exact pitch/length; a music-theory short treats an out-of-tune chord as a factual error, so chord one-shots are synthesized deterministically instead (equal temperament, A4=440Hz) for exact pitch, exact length, zero API cost, byte-identical output on every run.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log (brand tone + chords-not-melody)

**Location:** `tools/gen_chords.py → TARGET_LUFS / normalize_to_mp3()`
**Why / invariant / gotcha:** Loudness target (-20 LUFS) matches the rest of the SFX library so a clip's gain_db field stays meaningful relative to other library clips.
**Spec cross-reference (if any):**

**Location:** `tools/gen_chords.py → synth_chord()`
**Why / invariant / gotcha:** Additive synth tuned to read as a struck instrument, not a synth test tone: harmonics fall off fast, the bass root sits back at 0.62 amplitude so the triad reads as a chord rather than a drone, each note is staggered ~6ms and slightly detuned, higher harmonics decay faster than the fundamental, and a 9ms attack ramp avoids a click at the transient. Harmonics above SR/2.2 are dropped to stay clear of Nyquist.
**Spec cross-reference (if any):**

**Location:** `tools/gen_chords.py → main() catalog entry`
**Why / invariant / gotcha:** Tagged "content" (not background/transition) because the chord IS the subject of the video (diegetic), the same convention used for e.g. a chess-piece-thock sound.
**Spec cross-reference (if any):**

## tools/cutout.py

**Location:** `tools/cutout.py → main() method selection`
**Why / invariant / gotcha:** The soft white-key matte ("key" method) fails when the subject's light tones match the background/shadow in distance-to-white — proven on a real cutout where the contact shadow was indistinguishable from the glaze. rembg (ML matting) is preferred whenever importable; key is only the fallback. The matte is eroded 1px before feathering specifically to kill the bright halo the white-key method leaves at the silhouette edge.
**Spec cross-reference (if any):**

**Location:** `tools/cutout.py → build_matte_fast()`
**Why / invariant / gotcha:** numpy reimplementation of build_matte() used opportunistically when numpy is importable because it is roughly 100x faster on real image sizes; build_matte() is the pure-Python fallback.
**Spec cross-reference (if any):**

## tools/capture_web.py

**Location:** `tools/capture_web.py → wait_http() / start_serve_web()`
**Why / invariant / gotcha:** The serve-web readiness poll targets 127.0.0.1 explicitly, not localhost, to avoid false negatives from hostname resolution differences (e.g. IPv6 ::1) while the server is actually up. On Windows, `code` is a .cmd shim; `Popen([...], shell=True)` would hand the argument list to cmd.exe rather than to code, so the command is instead run explicitly via `cmd /c` with the full arg list intact.
**Spec cross-reference (if any):**

**Location:** `tools/capture_web.py → start_serve_web() workbench URL / settings seeding`
**Why / invariant / gotcha:** The workbench folder URL needs the URI-path form: a leading slash plus a lowercased drive letter (e.g. /d:/path) — a plain `d:/path` or `D:/path` loses the drive letter and the folder opens as an error item. User settings.json under the server data dir is pre-seeded (startup editor none, workspace trust disabled, tips disabled) before first boot so the workbench opens clean.
**Spec cross-reference (if any):**

## tools/mix_music.py

**Location:** `tools/mix_music.py → mix_one() sidechaincompress`
**Why / invariant / gotcha:** ratio = max(2.0, duck/3.0) is tuned so the bed drops roughly `duck` dB under the voice and recovers smoothly in the gaps; release=450ms is deliberately slow to avoid audible pumping.
**Spec cross-reference (if any):**

**Location:** `tools/mix_music.py → main() output path resolution`
**Why / invariant / gotcha:** Audition renders are written next to the base video (whatever project/output dir it lives in) rather than to a fixed output directory, so a mix audition stays colocated with the video it was generated from.
**Spec cross-reference (if any):**

## tools/mix_sfx.py

**Location:** `tools/mix_sfx.py → rp() vs proj()`
**Why / invariant / gotcha:** rp() resolves engine/library paths (the shared SFX catalog and clip files) relative to ROOT (the shared engine). proj() resolves project-data paths (plan, preview, output) relative to CWD — the workspace you actually run the tool from, NOT ROOT. Swapping the two silently resolves paths against the wrong root. The same rp()/proj() split appears in tools/bake.py and tools/make_stems.py.
**Spec cross-reference (if any):**

**Location:** `tools/mix_sfx.py → module top / main() sidechaincompress`
**Why / invariant / gotcha:** stdout is reconfigured to UTF-8 (errors replaced) because Windows consoles default to cp1252, which cannot print this tool's unicode cue-sheet characters. The sidechain duck here is deliberately gentle (threshold=0.15, ratio=2) because each cue's per-event gain_db already sets its level under the voice — this sidechain only cleans up incidental overlaps and must never bury the SFX.
**Spec cross-reference (if any):**

## tools/analyze_cut.py

**Location:** `tools/analyze_cut.py → module (checks 5 and 6)`
**Why / invariant / gotcha:** Checks 5 (hard entries) and 6 (low-confidence tokens) exist because of a real incident: a mistimed ASR token made the automated cut clip a word onset. The companion RENDER-side check is tools/verify_cut.py — an untranscribed false-start syllable and a genuine clipped word release both measure +20..+32 dB over the noise floor, so energy heuristics alone cannot tell them apart; only a second ASR pass over the rendered preview can. verify_cut.py must be run after every preview render.
**Spec cross-reference (if any):**

**Location:** `tools/analyze_cut.py → entry_check()`
**Why / invariant / gotcha:** A segment start is flagged as a "hard entry" when RMS just before it is >15dB over the noise floor, since that signals the cut sliced into ongoing sound — a breath intake alone sits around +12dB, real speech +20dB and up. This is only checked at REAL cut joins (raw gap to the previous segment > 0.75s); at a compressed intra-keep pause, the preceding audio is legitimately part of the same phrase, so it is not flagged.
**Spec cross-reference (if any):**

## tools/bake.py

**Location:** `tools/bake.py → module (timeline.json shot-type semantics)`
**Why / invariant / gotcha:** Master AUDIO plays throughout as the spine. 'cutaway' spans replace the master video with the shot's rendered mp4. 'overlay' spans composite an alpha shot (.mov, ProRes 4444) over the master. 'split' spans scale+crop the master into a design-space box and composite an alpha .mov over it for a split-screen/PIP. 'insert' entries pause the master clock at master_at_s: the insert's own mp4 (video AND audio) plays in full while the master freezes, then everything resumes — every later beat lands duration_s later in the output. Insert points are also added as segment boundaries. Everywhere else, the master passes through unchanged.
**Spec cross-reference (if any):**

**Location:** `tools/bake.py → main() segmentation method`
**Why / invariant / gotcha:** The timeline is split into atomic segments at every shot boundary, each rendered to an identically-encoded clip, then concatenated and muxed with master audio 0..end. Per-segment frame counts are derived from rounded cumulative boundaries (round(b*FPS) - round(a*FPS)), not from each segment's own duration, specifically so the total frame count matches the audio exactly with no cumulative rounding drift.
**Spec cross-reference (if any):**

**Location:** `tools/bake.py → main() VSEG/VOUT defaults / concat with inserts`
**Why / invariant / gotcha:** Default libx264 settings are tuned for a 1080p30 preview bake; a 4K60 bake needs GPU encoding since libx264 at 4K60 is hours per pass and bake already encodes twice — hence vcodec_seg/vcodec_out are overridable from the timeline's preview block. Without inserts, output audio is simply master[0..END]; with inserts, it's master segments interleaved with each insert's own audio, concatenated in order, so narration pauses exactly where the video freezes. A positive insert gain_db gets a limiter appended (alimiter) so a boosted insert's peaks can't clip.
**Spec cross-reference (if any):**

## tools/cutlib.py

**Location:** `tools/cutlib.py → module`
**Why / invariant / gotcha:** This module is deliberately general/parameterized with no per-video constants — every timing knob (head, tail, gaps) comes from the `styles` block in cuts.json, so a new video's edit style is authored as data, not code.
**Spec cross-reference (if any):**

**Location:** `tools/cutlib.py → load_words()`
**Why / invariant / gotcha:** Checks 'transcripts-u35' before 'transcripts' and returns the first that exists — this lets a newer/higher-quality transcription pass silently supersede the original without deleting or renaming the old dir.
**Spec cross-reference (if any):**

**Location:** `tools/cutlib.py → AudioProbe.snap_tail() / tail_for()`
**Why / invariant / gotcha:** snap_tail() walks forward from a word's end until RMS decays to floor+margin, so the kept tail is exactly as long as needed for the word's natural release. tail_for() decides landing style from the following gap size: no/large gap gets a soft landing with more room; a small mid-flow pause gets a punchy, tighter tail. The tail is clamped to never run past the next atom's lead-in head.
**Spec cross-reference (if any):**

**Location:** `tools/cutlib.py → active_keeps()`
**Why / invariant / gotcha:** Keep spans are never deleted from cuts.json. An auto-applied fluff span just hides the keeps it covers by filtering them out at read time here, so undoing an auto-removal is a one-field flip of that fluff entry's status back to 'suggested' rather than restoring lost data.
**Spec cross-reference (if any):**

**Location:** `tools/cutlib.py → plan_clip()`
**Why / invariant / gotcha:** The optional `cuts` argument must be passed whenever cut spans exist: snap_tail walks forward through silence to find decay, but if the material right after a kept atom is cut SPEECH (not silence), it walks straight through and cut words ride into the render — measured as 0.70s of a cut phrase surviving this way on a real project. The gap clamp in tail_for does not catch this because it only guards against reaching the next KEPT atom, not a cut span sitting in between; plan_clip's own span-clamping loop is what fixes it.
**Spec cross-reference (if any):**

## tools/render_cuts.py

**Location:** `tools/render_cuts.py → module / render pipeline`
**Why / invariant / gotcha:** Segments MUST be cut video-only with audio assembled separately (never let each segment carry its own AAC): video rounds to whole frames while per-segment AAC rounds to 1024-sample frames, and concatenating mp4 segments with `-c copy` accumulates that per-cut rounding difference into lip-sync drift (~15-20ms/cut, ~1s over 34 segments — a real incident). Fix: concat video segments via an MPEG-TS intermediate (avoids mp4's trailing-frame-padding accumulation on `concat -c copy`), separately cut raw audio to each segment's ACTUAL sample-exact frame count, concat that PCM gaplessly, and encode/mux the AAC once at the end.
**Spec cross-reference (if any):**

**Location:** `tools/render_cuts.py → is_finalized()`
**Why / invariant / gotcha:** Checks for a readable moov atom (ffprobe nb_frames succeeds), not just file existence/size, because a long final render can be an hour of encoding — treating a not-yet-flushed or crashed file as done would force redoing the whole batch. Also guards the inverse: probing a segment before its moov atom is flushed reads as corrupt and kills the later TS/concat stage, even though the encode itself exited 0.
**Spec cross-reference (if any):**

**Location:** `tools/render_cuts.py → main() (HEVC final PTS drift)`
**Why / invariant / gotcha:** Known unresolved quirk: the HEVC final stamps frame PTS ~0.1% fast on 59.94fps footage — an hevc_nvenc/TS artifact a stream copy cannot fix, separate from the mp4-concat drift bug fixed elsewhere in this file. Workaround at delivery: prepend `-r 60000/1001` (the source fps) BEFORE `-i` when transcoding to re-stamp every frame to true CFR with no frame loss; verify by comparing `ffprobe stream=duration` on v:0 vs a:0 (must be equal).
**Spec cross-reference (if any):**

## tools/verify_cut.py

**Location:** `tools/verify_cut.py → module`
**Why / invariant / gotcha:** This tool cross-checks a RENDERED preview/master (via a second ASR pass) against the intended cut, distinct from the raw-side QA in analyze_cut.py. It exists because a raw-side energy heuristic cannot distinguish a ghost syllable from a genuine word release (both peak +20..+32 dB over the noise floor) — an untranscribed false start survived into a render on a real project undetected until a second ASR pass over the render surfaced it.
**Spec cross-reference (if any):**

**Location:** `tools/verify_cut.py → norm()`
**Why / invariant / gotcha:** Only a '.' or '/' that PRECEDES a word is expanded to its spoken form ('.env' -> 'dot env'); trailing sentence punctuation is stripped, not spoken. This exists because ASR formatting for the same audio differs between runs, which would otherwise cause spurious diff mismatches.
**Spec cross-reference (if any):**

**Location:** `tools/verify_cut.py → main() (interior-gap check / A/V drift check)`
**Why / invariant / gotcha:** A big pause is only flagged when it falls between two rendered tokens mapped to the SAME keep — a pause at a join between two different keeps is expected. The A/V drift check's lookup matching a raw timestamp to its planned video time MUST also match on clip id: raw timestamps restart at 0 in every clip, so a bare time-only lookup returns the first coincidentally-overlapping segment and silently reports nonsense drift on any multi-clip project.
**Spec cross-reference (if any):**

## tools/composite_logo.py

**Location:** `tools/composite_logo.py → module`
**Why / invariant / gotcha:** Exists because an image model given only a reference image redraws the logo from scratch every generation — petal counts drift, brand colour shifts, brightness is inconsistent. For a fixed vector asset that's the wrong tool: this script paints out the model's drawn version with a feathered patch and composites the real logo file pixel-exact, with a controlled multi-radius bloom so it reads as a light source rather than a flat sticker.
**Spec cross-reference (if any):**

**Location:** `tools/composite_logo.py → make_tile() / key_out_white()`
**Why / invariant / gotcha:** Tile mode exists because a bare mark only fills ~22% of its bounding box and dissolves at browse/thumbnail size, whereas a filled tile holds ~95% of the box. The alpha formula `(255 - v) * 255 / 168` assumes the flat source logo bottoms out around channel value 87 against a white (255) background; 168 is that fixed value range (255-87), not an arbitrary constant.
**Spec cross-reference (if any):**

## tools/thumb_scrim.py

**Location:** `tools/thumb_scrim.py → module`
**Why / invariant / gotcha:** Exists because the scrim behind a thumbnail headline is a graphic overlay, not photography, and the image model treats prompted darkness as a suggestion — a rendered scrim can plateau well short of the target contrast ratio no matter how the prompt is worded. This script darkens the scrim deterministically in post to hit any target ratio exactly, while excluding saturated headline-fill pixels from the darkening so only the ground behind the lettering goes down.
**Spec cross-reference (if any):**

**Location:** `tools/thumb_scrim.py → main() (protect mask)`
**Why / invariant / gotcha:** MaxFilter(5) is applied to the headline-protection mask specifically to grow it over the anti-aliased rim of the lettering, so the darkening doesn't leave a thin bright halo around each protected letter.
**Spec cross-reference (if any):**

## tools/make_proxy.py

**Location:** `tools/make_proxy.py`
**Why / invariant / gotcha:** No non-obvious behavior beyond what's already covered by tools/render_cuts.py's rounding/finalization notes above — builds a 720p editor proxy + waveform from raw footage via ffmpeg (nvenc).
**Spec cross-reference (if any):**

## tools/make_stems.py

**Location:** `tools/make_stems.py → run()`
**Why / invariant / gotcha:** ffmpeg's -filter_complex can outgrow the Windows command-line length limit once a plan has ~100 cues, so every filter graph in this tool is written to a scratch file under .stems_tmp/ and passed via -filter_complex_script instead of inline on the command line.
**Spec cross-reference (if any):**

**Location:** `tools/make_stems.py → build_sfx() / build_music()`
**Why / invariant / gotcha:** SFX cues are rendered in batches of 30 (not all at once) purely to keep the ffmpeg input list well inside the OS argv length limit; batches are summed afterward. Each rendered music section is built xf seconds longer than its nominal span ("carries xf of tail") so the following section can crossfade over that tail. Per-bed gain staging order is: optional compression, then RMS body-match to the plan's reference level, then the section's own artistic gain_db, then the tail fade-out — reordering changes the perceived loudness/dynamics.
**Spec cross-reference (if any):**

**Location:** `tools/make_stems.py → build_voice() / build_pickup()`
**Why / invariant / gotcha:** The voice stem is taken from the master cut (a copy, not a re-encode) to avoid a second lossy AAC generation; it is trimmed to stem length but NOT level-adjusted and NOT spliced with pickups. The padded pickup track uses apad (not -t) to reach full stem length, because -t only ever truncates and the pickup source audio ends long before the stem duration does.
**Spec cross-reference (if any):**

**Location:** `tools/make_stems.py → final_mux()`
**Why / invariant / gotcha:** alimiter's level=disabled is load-bearing, not decorative: alimiter's `level` flag defaults to true and renormalizes output back up to the ceiling whenever limiting engages, which measurably made a real mix louder instead of quieter. With level=disabled, limit=0.79 is a real sample-ceiling in dBFS, leaving headroom for AAC's inter-sample overshoot.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log (deliverable-stems pipeline split)

## tools/editor/index.html

**Location:** `tools/editor/index.html → buildSegments() / rebuildPlan()`
**Why / invariant / gotcha:** Live in-browser playback of the "edited" plan is only an APPROXIMATION of tools/render_cuts.py's real cut: the editor has no per-word timestamps or audio analysis available client-side, so it cannot reproduce internal-pause tightening or snap-to-audio soft tails — those only appear correctly in the actual rendered preview.
**Spec cross-reference (if any):**

**Location:** `tools/editor/index.html → computeGaps()`
**Why / invariant / gotcha:** Kept specifically for save(): it recomputes each keep's gap-to-next metadata (silence vs. cut, duration) so that metadata is persisted into cuts.json on save, separately from buildSegments()'s playback-only approximation used for live preview.
**Spec cross-reference (if any):**

## tools/make_verdict_page.mjs

**Location:** `tools/make_verdict_page.mjs → video 'play' listener`
**Why / invariant / gotcha:** Only one candidate video is allowed to play at a time (starting one pauses all others) as a deliberate UX choice: comparing two candidates simultaneously gives no usable signal for the PASS/MAYBE/NO judgment this page exists for.
**Spec cross-reference (if any):**

## remotion/remotion.config.ts

**Location:** `remotion/remotion.config.ts → Config.setPublicDir('../media')`
**Why / invariant / gotcha:** publicDir is one directory above `remotion/` (i.e. `PROJECT/media`), not `remotion/public/`. `staticFile('library/logos/x')` resolves to `media/library/x` (the shared, reusable asset library); `staticFile('projects/<proj>/x')` resolves to `media/projects/<proj>/x` (per-video or per-short generated assets). This setting only governs `remotion studio` / the CLI render path — `remotion/scripts/*.mjs` render programmatically via `bundle()`, which never reads `remotion.config.ts`, so each of those scripts passes the identical `publicDir` explicitly (see their own entries below).
**Spec cross-reference (if any):**

## remotion/src/Root.tsx

**Location:** `remotion/src/Root.tsx → RemotionRoot`
**Why / invariant / gotcha:** Every shot file under `src/shots/**/*.tsx` exports `compositionConfig` + a default component; `scripts/gen-registry.mjs` scans for that shape and (re)writes `src/registry.gen.tsx` (imported here as `shots`) and `src/shots.manifest.json`. Root.tsx itself never lists shots by hand — adding/removing a shot means re-running `npm run gen` (gen-registry.mjs), not editing this file.
**Spec cross-reference (if any):**

## remotion/scripts/frames.mjs

**Location:** `remotion/scripts/frames.mjs → module`
**Why / invariant / gotcha:** Usage: `node scripts/frames.mjs <CompId> <f1,f2,...> [--scale=0.5]`; writes `out/qa/<id>-f<frame>.png` for phone-scale legibility QA of shorts. Same explicit-`publicDir` requirement as remotion.config.ts's entry above.
**Spec cross-reference (if any):**

## remotion/scripts/gen-registry.mjs

**Location:** `remotion/scripts/gen-registry.mjs → module / parseConfig()`
**Why / invariant / gotcha:** Extracts each shot's `compositionConfig` with a regex over the raw file text (not a real TS parse), and writes `src/registry.gen.tsx` (consumed by Root.tsx) + `src/shots.manifest.json` (consumed by render-all.mjs). Must be re-run after adding a shot or editing its `compositionConfig`; nothing watches for changes automatically.
**Spec cross-reference (if any):**

**Location:** `remotion/scripts/gen-registry.mjs → typeOfGroup()`
**Why / invariant / gotcha:** The optional `--type=<longs|channel|faceless|lectures>` flag narrows the generated registry to one shot group so a given workspace's Studio only shows its own video type; it maps the shot's top-level folder name (`src/shots/<group>/`) to a type by prefix (`video-` → channel-longs, `short-` → faceless, `ch-`/`cover` → channel, `bwa-`/`ebq` → lectures), and any unrecognized folder prefix falls through to `'other'` rather than erroring.
**Spec cross-reference (if any):**

**Location:** `remotion/scripts/gen-registry.mjs → header string literal`
**Why / invariant / gotcha:** The `'// AUTO-GENERATED ... do not edit.\n'` string in this file is DATA — it is written verbatim into the generated `registry.gen.tsx` output, not a comment in this source file. It must not be deleted or rephrased as part of any future no-comments cleanup of this file; it is the only comment line the generated artifact is allowed to carry, since that artifact is itself exempt from the hand-authored no-comments rule by virtue of being machine-generated and never hand-edited.
**Spec cross-reference (if any):**

## remotion/scripts/render-all.mjs

**Location:** `remotion/scripts/render-all.mjs → module`
**Why / invariant / gotcha:** Bulk-renders every shot listed in `shots.manifest.json` (generated by gen-registry.mjs) at scale 2 — shots are authored at 1080p and rendered near-4K so they composite crisply over a 4K master. A shot whose `compositionConfig` sets `transparent: true` renders to `out/<id>.mov` (ProRes 4444 + alpha) for overlay/split compositing; every other shot renders to `out/<id>.mp4` (h264). Same explicit-`publicDir` requirement as remotion.config.ts's entry above.
**Spec cross-reference (if any):**

## remotion/scripts/qa-frames.mjs

**Location:** `remotion/scripts/qa-frames.mjs → module`
**Why / invariant / gotcha:** Usage: `node scripts/qa-frames.mjs <CompId> [--out dir] name=frame [name=frame ...]`; renders each named still at scale 0.5 into `<out>/<name>.jpeg` — for eyeballing specific beats during QA, not a delivery render.
**Spec cross-reference (if any):**

## remotion/src/lib (general convention, applies across the library)

**Location:** `remotion/src/lib/*.tsx → per-component \`at\` / cue-frame props`
**Why / invariant / gotcha:** Unless a prop is explicitly documented otherwise, animation cue props (`at`, `enterAt`, cue-map keys, etc.) across this library are LOCAL to the component's own mount point (its surrounding `<Sequence from={...}>`), not global/master composition frames — this holds for chess.tsx's move `at`, collage.tsx's Layer `at`, sheet.tsx's cue frames, math.tsx's TimesElevenDemo cue frames, and terminal.tsx's line `at`. Callers (shots, and `/suggest-sfx` when it converts a shot moment to master/global seconds) must add the shot's own `sequence_from` before converting to seconds: `at_s = (local_frame + sequence_from) / fps`.
**Spec cross-reference (if any):** `.claude/skills/suggest-sfx/SKILL.md` (the same local→global frame conversion, from the SFX-authoring side)

## remotion/src/brand.ts

**Location:** `remotion/src/brand.ts → BRAND.wordmark`
**Why / invariant / gotcha:** `wordmark` is always a 3-string tuple; any shot that renders the channel name must read it as `[part0, part1, part2]` and render `part1` in the accent color (a two-part mark is written as `['Acme', 'Labs', '']`, i.e. the empty string is the convention for "no third segment," not an error case to guard against).
**Spec cross-reference (if any):** ARCHITECTURE.md decision log (brand-triad placeholder pick)

**Location:** `remotion/src/brand.ts → EASINGS`
**Why / invariant / gotcha:** Shots must use these four named easings, never Remotion's own `Easing.out(...)`/`Easing.in(...)` wrapper helpers directly — the wrapper helpers produce a different, less restrained curve than the brand's confirmed bezier values, so swapping one in changes the felt motion even though both compile.
**Spec cross-reference (if any):** `.claude/skills/vidtsx-2d-generator/SKILL.md` (the general "Easing.bezier not wrapper syntax" rule this reinforces)

## remotion/src/fonts.ts

**Location:** `remotion/src/fonts.ts → FONT_SERIF vs FONT_EDITORIAL`
**Why / invariant / gotcha:** Two different serifs exist for two different jobs and are not interchangeable: `FONT_SERIF` (Spectral) is picked specifically as a close match to the Claude Code app's own serif, for wordmark clones in `kit.tsx`'s terminal/editor shots; `FONT_EDITORIAL` (Source Serif 4) exists only because Spectral tops out at weight 600 and reads too light/bookish as a large editorial headline over vox-collage layers (`collage.tsx`'s SerifStatement), so the vox engine needed a heavier serif that goes to 900. `fonts.ts`, `brand.ts`, and `brand.md` are meant to be edited together — `/brand-setup` rewrites all three in one pass; if any one of them is hand-edited instead, keep the other two in sync manually.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log (brand-triad placeholder pick — also flags a known FONT_SERIF/FONT_EDITORIAL vs brand.md §4 wordmark-font mismatch inherited from this merge)

## remotion/src/lib/algo.tsx

**Location:** `remotion/src/lib/algo.tsx → module / makeShuffle() / step generators`
**Why / invariant / gotcha:** Every comparison/swap drawn on screen is a real operation replayed from an instrumented sort run over a seeded shuffle (LCG + Fisher-Yates) — never a hand-keyframed animation of "looking like" a sort. `Math.random` must never be used anywhere in this file (or introduced by an edit): renders must be frame-deterministic and reproducible on every scrub/re-render, which an unseeded RNG would break. Replay position is driven by `opsDone = elapsed × opsPerSec` and state-at-`opsDone` is a pure function of the recorded step list, so scrubbing to any frame is safe.
**Spec cross-reference (if any):**

## remotion/src/lib/chart.tsx

**Location:** `remotion/src/lib/chart.tsx → module (shot/lib split)`
**Why / invariant / gotcha:** Every exported piece is frame-driven and fully prop-controlled: the calling shot owns the choreography (when things happen), this file only owns the drawing (what a given progress value looks like). Same contract as `lib/prob.tsx` and `lib/math.tsx` — a component here must never read the current frame itself to decide its own progress.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/chart.tsx → futureValue() (annuity convention)`
**Why / invariant / gotcha:** Modeled as an ordinary annuity: each month's deposit lands at the END of the month, so month 0 is exactly 0 and the final sampled month's deposit contributes no growth yet. Getting this convention backwards (deposit-at-start / annuity-due) shifts every point in the curve.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/chart.tsx → Scale (no React context)`
**Why / invariant / gotcha:** The pixel scale is passed explicitly as a prop to every component rather than provided via context, specifically so one shot can draw two charts side by side at different scales if a future niche needs that — introducing a scale context would silently break that case.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/chart.tsx → GapArea`
**Why / invariant / gotcha:** The shaded region between two series must be sliced with the SAME progress `p` on both edges (never two independent progress values) so the shading always terminates exactly under both curves' current head position — this is also the component's whole rhetorical point (a fee/rate gap is an area, not a line), so an edit that lets the two edges drift out of sync breaks the visual argument, not just the geometry.
**Spec cross-reference (if any):**

## remotion/src/lib/chess.tsx

**Location:** `remotion/src/lib/chess.tsx → module (piece art asset)`
**Why / invariant / gotcha:** The piece sprites resolved via `staticFile(\`library/chess/${sp.code}.svg\`)` (i.e. `media/library/chess/` per this project's publicDir convention, not `remotion/public/`) are the cburnett set (Wikimedia Commons, tri-licensed GPL/BSD/GFDL — the same set Lichess uses); that license/attribution travels with the asset files themselves, not with any code in this file, so it must be preserved if the sprite set is ever swapped or redistributed.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/chess.tsx → ChessBoard (mount + \`at\` frames)`
**Why / invariant / gotcha:** Moves are scripted as `{ from, to, at }` and replayed deterministically up to the current frame, so scrubbing, rewinds, and captures all work without a real chess engine. `at` frames are local to the `<Sequence>` this component is mounted inside, per the library-wide local-frame convention.
**Spec cross-reference (if any):** this file's own entry in "remotion/src/lib (general convention)" above

## remotion/src/lib/collage.tsx

**Location:** `remotion/src/lib/collage.tsx → module (camera + parallax model)`
**Why / invariant / gotcha:** The vox collage engine models every scene as layers on a paper board under one virtual camera: `CollageBoard`'s `cam` keyframes are board-local frames (global only when CollageBoard is mounted at the composition root), and each `Layer`'s `depth` prop is read back through context to compute its own parallax displacement from the camera's motion — a layer that doesn't consume that context won't move with the camera at all, which looks like a bug rather than a static layer.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/collage.tsx → Grain (mount order) / PaperBG (depth)`
**Why / invariant / gotcha:** The film-grain overlay must be mounted last and outside the `CollageBoard`, or it will pick up the board's own parallax/camera transform instead of sitting flat over the whole frame; it re-seeds its noise pattern every 2 frames rather than every frame, which is a deliberate texture choice, not a missed optimization. `PaperBG` is meant to be sized to the full canvas at `depth ≈ -0.06` (i.e. slightly BEHIND the nominal camera plane) so it drifts opposite the parallax direction of foreground layers.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/collage.tsx → RubberStamp / SerifStatement`
**Why / invariant / gotcha:** `RubberStamp` always renders its text uppercase regardless of the casing passed in — callers should write short, "uppercase-worthy" text rather than relying on their own casing. `SerifStatement`'s marker-sweep highlight and bare-ink text both lose contrast against sepia/duotone photo layers (e.g. `ArchivalPhoto`), so a statement placed over a photo layer needs the `backing` (cream strip) option turned on.
**Spec cross-reference (if any):**

## remotion/src/lib/kit.tsx

**Location:** `remotion/src/lib/kit.tsx → module`
**Why / invariant / gotcha:** Deliberately lives outside `src/shots/` and exports no `compositionConfig`, specifically so `scripts/gen-registry.mjs`'s directory scan never picks it up as a renderable composition — it is a shared-components module, not a shot. Its Claude Code / VS Code chrome clones are matched against real reference screenshots of those apps, not an arbitrary UI design, so visual fidelity edits should be checked against the real app rather than "improved" freehand.
**Spec cross-reference (if any):** remotion/scripts/gen-registry.mjs entry above (what the scanner actually matches on)

## remotion/src/lib/map.tsx

**Location:** `remotion/src/lib/map.tsx → module (real-projection philosophy)`
**Why / invariant / gotcha:** This library never fakes map distortion with a hand-tuned animation: `mercY` is the literal Mercator formula, and "sliding a country to another latitude" actually re-projects its true coordinates, so any on-screen size change is a real, computed consequence of the projection rather than an authored keyframe. See ARCHITECTURE.md's decision log entry for why this "compute it, don't fake it" rule is a house content policy, not just this file's own taste.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log ("honest-by-construction" niche content policy)

**Location:** `remotion/src/lib/map.tsx → MAX_LAT / fitScale()`
**Why / invariant / gotcha:** `MAX_LAT = 85.05` clamps latitude before projecting because Mercator sends the poles to infinity (the same clamp every web map applies). Mercator is conformal, so the x and y pixel scales must share a single `k` factor — scaling them independently (e.g. to force-fit an aspect ratio) would shear every country's shape.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/map.tsx → transport (carrying a country to another latitude)`
**Why / invariant / gotcha:** Naively adding a fixed `dLat`/`dLon` to every vertex is WRONG and looks plausible until rendered: Mercator's x depends only on longitude, so a country dragged toward the equator keeps its full longitude span while its height compresses, arriving squashed and too wide. The correct transport rescales each vertex's east-west offset from the country's centre by `cos(lat)/cos(lat')` (the real convergence of meridians) so the country arrives at its true rendered size — the visual "shrink" is a side effect of correct spherical geometry, never a separate keyframed scale applied on top.
**Spec cross-reference (if any):**

## remotion/src/lib/orbit.tsx

**Location:** `remotion/src/lib/orbit.tsx → module (real-physics philosophy)`
**Why / invariant / gotcha:** Nothing here is a keyframed arc: `integrate()` numerically integrates Newton's law of gravitation from a real initial state, so whether a launched object lands, orbits, or escapes falls out of the math rather than being asserted. Same house content policy as `map.tsx` and `prob.tsx` (see ARCHITECTURE.md).
**Spec cross-reference (if any):** ARCHITECTURE.md decision log ("honest-by-construction" niche content policy)

**Location:** `remotion/src/lib/orbit.tsx → gAt() / sagitta()`
**Why / invariant / gotcha:** `gAt(r)` and every function taking a radius `r` measure from Earth's CENTRE, not from the ground or from altitude — passing an altitude directly instead of `R_EARTH + altitude` silently produces a physically wrong result with no type error. `sagitta()` is deliberately computed from the ORBITING SHELL's radius (`R_EARTH + altitude`), not the ground's radius: the ground, being more sharply curved, drops a different amount over the same arc than the shell the object is actually on, and only the shell number is exactly consistent with "the object falls at the same rate the shell curves away" (the physical claim these shorts make).
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/orbit.tsx → integrate() (velocity Verlet)`
**Why / invariant / gotcha:** Uses velocity Verlet specifically because it is symplectic — a circular orbit stays circular over thousands of integration steps, whereas naive Euler integration would visibly spiral in/out over the same step count. Swapping the integrator for a simpler one (e.g. forward Euler) would reintroduce that drift.
**Spec cross-reference (if any):**

## remotion/src/lib/piano.tsx

**Location:** `remotion/src/lib/piano.tsx → module (pitch contract) / noteToMidi() / STRIKE ENVELOPE`
**Why / invariant / gotcha:** Notes are named (`"C4"`, `"A#3"`) and converted to MIDI using the same equal-temperament formula (A4 = 440 Hz) that `tools/gen_chords.py` uses to synthesize the actual audio — what lights up on the keyboard and what plays must always be derived from this one shared definition of a note, never hand-matched by eyeballing frame numbers against an audio file. The strike-envelope brightness curve (fast attack, long release) intentionally mirrors the amplitude envelope `gen_chords.py` gives the synthesized audio, so the key's glow and the note's decay read as the same physical event.
**Spec cross-reference (if any):** `tools/gen_chords.py` entries in this file (equal-temperament synthesis)

## remotion/src/lib/prob.tsx

**Location:** `remotion/src/lib/prob.tsx → mulberry32() / seeded sim`
**Why / invariant / gotcha:** `mulberry32` must stay byte-identical to the same-named generator in `scratchpad/monty_seed.mjs` — that scratchpad script was used to hand-verify seed 15 produces exactly 66 switch-wins, and any change to this implementation (even a refactor that should be equivalent) silently invalidates that verification and any shot that hardcodes results derived from it.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log ("honest-by-construction" niche content policy)

## remotion/src/lib/sheet.tsx

**Location:** `remotion/src/lib/sheet.tsx → default grid geometry constants`
**Why / invariant / gotcha:** The default grid geometry is shared specifically so the hook/loop's composed grid and the live Flash-Fill demo grid land pixel-for-pixel identical — if a shot changes one grid's geometry without the other, the seamless hook-to-loop cut (frame 0 == last frame) visibly jumps.
**Spec cross-reference (if any):**

## remotion/src/lib/shorts.tsx

**Location:** `remotion/src/lib/shorts.tsx → module (platform-UI safe zones)`
**Why / invariant / gotcha:** Captions and other critical info must stay above roughly y1420 (in the 1080×1920 canvas): the bottom ~500px of a real YouTube Shorts player is occupied by the handle, title, description, and right-side action-button rail. This threshold came from measuring a real mobile screenshot (a ch-3 lesson) after a previous short's captions were actually obscured by the platform UI — it is not a guessed margin.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/shorts.tsx → Captions (word timing)`
**Why / invariant / gotcha:** Caption components retime themselves from whatever word-timing data they're given — real per-word alignment from `tools/gen_voice.py` when present, else an estimate that distributes the line's time window weighted by word length. This lets a shot be built and QA'd against estimated timings before real voice exists, then swapped to real timings later with no component changes.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/shorts.tsx → dev-only safe-area guides`
**Why / invariant / gotcha:** The safe-area guide overlay is a development aid only and must never be mounted in a final render — it exists purely so a shot author can visually confirm captions/UI clear the platform safe zones above while iterating.
**Spec cross-reference (if any):**

## remotion/src/lib/story.tsx

**Location:** `remotion/src/lib/story.tsx → MOVES presets / base scale`
**Why / invariant / gotcha:** Ken-burns base scale is kept `>= 1.12` (≈6% margin per side, with `|translate| <= 2%`) specifically because AI-generated story stills often bleed into a soft watercolor "paper" edge or deckled white border right at the image bounds; a smaller base scale would let that border crop into frame at some point during the pan/zoom.
**Spec cross-reference (if any):**

## remotion/src/lib/screencast.tsx

**Location:** `remotion/src/lib/screencast.tsx → module (fraction coordinate convention)`
**Why / invariant / gotcha:** Cursor keys and zoom/scroll focal points are FRACTIONS, not pixels, and the fraction is of two different things depending on which prop: cursor `x`/`y` are a fraction of the VIEWPORT (the page area under the chrome), while zoom `fx`/`fy` are a fraction of the IMAGE. This split is deliberate — fractions of their respective boxes survive any resize of the browser frame, whereas pixel coordinates would not.
**Spec cross-reference (if any):**

**Location:** `remotion/src/lib/screencast.tsx → page layering / WebBrowserFrame region`
**Why / invariant / gotcha:** Only the active (top) page and pages already arrived are painted; a future (not-yet-arrived) page is skipped entirely rather than painted at opacity 0, and pages are stacked in painter's order so a later page's crossfade naturally covers the earlier one without extra z-index bookkeeping. The viewport region is sized with explicit width/height rather than `inset: 0`, because `WebBrowserFrame`'s translateY wrapper is itself a transformed (and therefore zero-height-establishing) containing block — `inset: 0` against it collapses to nothing instead of filling the viewport.
**Spec cross-reference (if any):**

## remotion/src/lib/browser.tsx

**Location:** `remotion/src/lib/browser.tsx → uiScale / url prop (node form)`
**Why / invariant / gotcha:** `uiScale` is a calibrated legibility constant, not a free design choice: desktop 16:9 shots use `1`, but a vertical 1080-wide short needs roughly `1.9` for the URL bar text to stay legible at phone viewing size. The `url` prop accepts a React node (not just a string) specifically so per-segment URL annotations (highlights/strikes/labels) can render UNCLIPPED — passed as a plain string it renders as the normal ellipsised single line instead.
**Spec cross-reference (if any):**

## remotion/src/lib/geo/world.ts

**Location:** `remotion/src/lib/geo/world.ts → module`
**Why / invariant / gotcha:** Auto-generated from Natural Earth 110m (public domain) outlines by a `scratchpad/build_world.py` script that was NOT ported into this project's `tools/` during this backfill — regenerating or updating these outlines currently requires recreating that script, not just editing this file by hand. `lib/map.tsx` and `lib/orbit.tsx` project these raw outlines themselves at render time, which is why the outlines are stored as data here rather than as a pre-rendered image.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log ("honest-by-construction" niche content policy)

## remotion/src/shots/brand/BrandProof.tsx

**Location:** `remotion/src/shots/brand/BrandProof.tsx → module`
**Why / invariant / gotcha:** Not a video beat — a utility composition that `/brand-setup` renders as its last step so the user can see the brand it just wrote. It must never hardcode a color/font/value of its own; every value it displays is read live from `brand.ts`/`fonts.ts`, and it lays out COLORS roles in the order `brand.md` §3 documents them, so it stays a faithful proof of whatever the brand files currently say. Render directly with `cd remotion && npx remotion still src/index.ts BrandProof out/brand.png --frame=70`.
**Spec cross-reference (if any):** ARCHITECTURE.md decision log (brand-triad placeholder pick)
