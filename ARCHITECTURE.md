# Architecture

This file exists to hold enforced structure and the decision log once a project has real
implementation code — per HOW_TO_USE.md, it's optional for small projects and added when needed.
It was created now because porting the `tools/` scripts (video/audio pipeline) surfaced genuine
product/business decisions that CLAUDE.md says must live here rather than in CODE_MAP.md or as
inline code comments.

## Decision log

- **`tools/gen_vo.mjs`'s locked voice recipe is scoped to that file only — no ported skill calls it.**
  Its default TTS provider is pinned to a specific ElevenLabs PVC voice recipe (voice id,
  `eleven_multilingual_v2` model, style/speed/stability/similarity settings) from a dated
  voice-lab experiment (2026-08-12, recipe #18), sourced from `claude_video_editor`'s
  `docs/ai-clone-guide.md` workflow — a doc that was never ported into this project, so
  `gen_vo.mjs` is currently orphaned tooling with no caller among `.claude/skills/`. If it's ever
  wired back up (e.g. by porting an AI-clone-style feature), the recipe must never be swapped to
  an `eleven_v3` model: v3 lacks this voice's fine-tune and falls back to raw-sample
  reconstruction, causing audible identity drift. Swapping the whole `TTS_PROVIDER` to a different
  vendor is supported (see `gen_vo.mjs`'s `PROVIDERS` dispatch); swapping only the model/settings
  under the existing ElevenLabs provider is not — that would silently break the locked voice
  identity. **This is unrelated to `tools/gen_voice.py`'s own `DEFAULT_VOICE`** (the TTS tool
  `make-short`/`make-ai-short`/`make-vox` actually call, documented separately in
  `CODE_MAP.md`) — the two files pin two different voices for two different purposes; don't
  confuse one recipe for the other when tuning either.

- **SFX chord tone is a deliberate brand choice.** `tools/gen_chords.py` synthesizes music-theory
  chord one-shots with a Rhodes/electric-piano-style additive synth (soft attack, fast-decaying
  upper harmonics) rather than a bright acoustic piano tone, because brand.md's audio identity is
  "calm/premium, felt-not-heard" and that timbre sits under narration better than a percussive
  piano.

- **Only chords are ever synthesized for music-theory shorts — never a melody.** Chord
  progressions are not copyrightable; a named song's melody is. `tools/gen_chords.py` is
  deliberately restricted to triads so these shorts can name real songs without reproducing them.

- **YouTube uploads default to private ("draft mode"), not the requested privacy value.**
  `tools/yt_upload.py` always uploads as private regardless of the `--privacy` flag, because the
  YouTube Data API force-locks every upload from an unaudited Google Cloud project to private —
  requesting anything else just fails silently at review time otherwise. Publishing to public
  requires either the one-time YouTube compliance audit for the Cloud project, or a manual
  publish step in YouTube Studio after upload.

- **Deliverable audio stems are a separate, unducked pipeline stage from audition mixing.**
  `tools/make_stems.py` produces full-length, undocked WAV stems (voice/SFX/music/pickup) meant
  to be handed to an editor's timeline as-is. This is intentionally distinct from
  `tools/mix_sfx.py`/`tools/mix_music.py`, which produce ducked audition *videos* for judging
  cues in context. No ducking is applied at the stems stage — that decision belongs to whoever
  does the final mix, not to this pipeline.

- **"Honest-by-construction" is a house content policy for the physics/geography/probability
  niche shorts, not just one file's implementation taste.** `remotion/src/lib/map.tsx` (real
  Mercator projection — a country's on-screen size change is a computed consequence of
  re-projecting its true coordinates, never a hand-tuned animation), `remotion/src/lib/orbit.tsx`
  (a real numerically-integrated trajectory under Newton's law, not a keyframed arc), and
  `remotion/src/lib/prob.tsx` (a seeded Monte-Carlo sim whose RNG must stay byte-identical to a
  hand-verified scratchpad script) all share one rule: when a short's entire premise is "here is
  what actually happens," the video must derive that outcome from real computation at render
  time, never fake it with an authored animation that merely looks right. `tools/gen_chords.py`
  applies the same policy to audio (real equal-temperament synthesis instead of a generative
  model's approximate pitch). This constrains future niche libs in the same category: a new
  "honest" niche short should compute its payoff the same way, not assert it.

- **The remotion/ backfill's brand triad (brand.md + brand.ts from the video_editor example,
  fonts.ts from the short_creator example) is a deliberate placeholder pick, not a guess at "the
  right" brand.** This project ported skills/tools from two example repos (`claude_short_creator`
  and `claude_video_editor`) in a prior session but never backfilled a working `remotion/` app, so
  a starting brand triad had to be chosen from the two candidates with no user brand yet defined.
  `video_editor`'s `brand.md`/`brand.ts` were picked as the "house default" (an arbitrary but
  necessary tiebreak the user was told about in advance) specifically because `brand.ts` there
  ships a real `BRAND` (wordmark/signoff) placeholder object matching `brand-setup`'s own framing
  of a working-but-generic starting identity, not a stub. `short_creator`'s `fonts.ts` was taken
  instead of `video_editor`'s because it is a strict superset (confirmed by diff): it adds
  `FONT_EDITORIAL` (Source Serif 4), needed by the vox-collage skill's headline component, which
  `video_editor`'s `fonts.ts` lacks entirely. This triad is real and working, not a placeholder
  brand *identity* — but it is expected to be superseded the first time `/brand-setup` runs.
  `brand.md` §8 (Asset & source locations) was hand-merged from both example repos' copies rather
  than picked from one, because the two repos actually use different-but-compatible artifact
  layouts (`videos/video-N/...` for long-form, `shorts/short-N-<niche>/...` for shorts) that both
  need documenting, mirroring the same merge already done in
  `.claude/skills/suggest-sfx/SKILL.md`. **Known inherited inconsistency:** `brand.md` §4 (copied
  verbatim from `video_editor`, untouched by this backfill) states that Claude wordmarks should
  use Source Serif 4 (`FONT_EDITORIAL`) and that Spectral (`FONT_SERIF`) is "retired" for
  wordmarks — but the actual shipped `remotion/src/lib/kit.tsx` (also from `video_editor`) still
  renders its Claude Code wordmark clone with `FONT_SERIF`, and `FONT_EDITORIAL` is used only by
  the unrelated vox-collage headline component. This mismatch predates this backfill and was not
  introduced by it; it is left as-is because fixing §4 was out of scope for this pass, and
  `/brand-setup` will rewrite `brand.md`, `brand.ts`, and `fonts.ts` together anyway.
