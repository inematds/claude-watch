# Changelog

All notable changes to `/watch` are documented here.

## [0.4.1] — 2026-06-21

### Added
- Per-shot **camera-movement classification** via ffmpeg `vidstabdetect` (vid.stab) — opencv-free. `frames.extract_camera_transforms()` runs the detection pass into a temp `.trf`; `pacing.parse_transforms()` reads its local-motion vectors, `pacing.classify_shot_movement()` labels a shot (`static` / `pan-left` / `pan-right` / `tilt-up` / `tilt-down` / `zoom-in` / `zoom-out` / `handheld` / `unknown`) from robust medians — net translation → pan/tilt, radial component → zoom, high magnitude with cancelling directions → handheld — and `pacing.camera_moves_per_shot()` pools vectors per shot. Surfaced as a **Camera movement** line in the report's editorial profile (dominant label ignores `unknown`). Best-effort: an absent vid.stab build or a detect failure degrades to motion-only pacing instead of sinking the watch.
- `compute_pacing(..., camera_labels=...)` attaches a `camera` label to each shot.
- 19 new tests (parser on a real `.trf` sample, per-label classification on synthetic vectors, per-shot pooling, an end-to-end synthetic-pan smoke, and the report line); suite now 39 green.

### Changed
- Pan-vs-tilt dominance is compared in raw pixels (not aspect-normalised), so a short frame's vertical jitter can't outweigh a real horizontal pan.

## [0.3.1] — 2026-06-20

### Added
- Per-shot **motion scoring via ffmpeg `signalstats`** (YDIF luma-delta) — opencv-free. `frames.extract_motion_diffs()` runs a cheap downsampled signalstats pass; `pacing.parse_signalstats()` + `pacing.motion_scores_per_shot()` aggregate it into one normalised score per shot (busiest shot = 1.0). Motion now feeds `select_hero_frames` (the high-motion hero pick is real, no longer a `0.0` stub) and a new **Motion line** in the report's editorial profile. Best-effort: a signalstats failure falls back to motion-less pacing instead of sinking the watch.
- 7 new tests: signalstats parser, per-shot aggregation/normalisation, ffmpeg motion smoke (synthetic moving vs static video), and the report's motion line (present when scored, omitted when not).

### Changed
- `pacing.compute_pacing` refactored to share shot-boundary logic (`_shot_intervals`) with motion scoring, so motion-score length always matches `shot_count`. Removed the old `motion_scores_from_frames` zero-stub.

## [0.2.1] — 2026-06-17

### Changed
- Repointed all distribution references (repo URLs, plugin author/owner, homepage, `SKILL.md` author) from `taoufik123-collab` to `inematds/claude-watch`. Install commands are now `/plugin marketplace add inematds/claude-watch` + `/plugin install watch@claude-watch`. Original-author credit to Bradley Bonanno (`bradautomates/claude-video`, LICENSE, CHANGELOG) is unchanged.

## [0.2.0] — 2026-05-25

Based on [bradautomates/claude-video](https://github.com/bradautomates/claude-video) v0.1.3 by Bradley Bonanno (MIT). Its pipeline (yt-dlp + ffmpeg + Whisper) is preserved; everything below is additive.

### Added
- Scene-change frame extraction in `scripts/frames.py` — `extract_scene_change()` + `select_hero_frames()` using ffmpeg's `select=gt(scene,...)` filter. One frame per detected shot instead of uniform every-N-seconds sampling. Keeps token cost flat on long videos. Uniform sampling still available as a fallback for static/screen-recorded sources.
- 0-10s hook microscope in `scripts/hook.py` — 2 fps frames + word-level Whisper transcript on the opening 10 seconds, so the report can tell you what's on screen *as each word lands*.
- Editorial pacing metrics in `scripts/pacing.py` — shot count, cuts/min, mean + median shot length.
- Structured `report.md` emitter in `scripts/report.py` — fixed-schema ingest-ready report with `<!-- pending Claude fill: ... -->` markers for narrative sections (TL;DR, key moments, hook breakdown, editorial profile, quotable moments, entities, concepts).
- Word-level timestamps in `scripts/whisper.py` (Groq + OpenAI backends extended).
- New CLI flags in `scripts/watch.py`: `--intent`, `--no-scene-change`, `--no-hook-microscope`.
- Step 4.4 (stage to Obsidian vault) + Step 4.5 (ingest gate) in `SKILL.md` — optional auto-save to your Obsidian vault. Path resolved via `$WATCH_VAULT_DIR` or auto-detected from `~/Second brain/`, `~/Documents/Obsidian/`, `~/Obsidian/`. Skips cleanly when no vault is detected.
- 7 unit tests under `scripts/tests/` (stdlib `unittest`, no pytest dependency).

### Changed
- `SKILL.md` is now a v2 contract — describes the structured report, the marker-fill step, and the vault config. Backwards-compatible with /watch invocations that don't care about ingest.
- README documents the added features and the `$WATCH_VAULT_DIR` configuration.

## [0.1.3] — 2026-05-09

### Fixed
- Windows: `video.info.json` is read as UTF-8 (#4). Previously `Path.read_text()` defaulted to cp1252 on Windows and crashed on yt-dlp's UTF-8 output, silently dropping Title/Uploader from the report. Same fix applied to `.env` reads/writes in `whisper.py` and `setup.py`.
- `download.py` now logs info.json parse failures to stderr instead of swallowing them.

### Security
- Hardened subprocess argv against option injection (#2): inserted `--` before the URL in the yt-dlp argv, and tightened `is_url` to reject `-`-prefixed sources and require a non-empty netloc. Resolved video/audio paths to absolute via `Path.resolve()` before passing to `ffmpeg`/`ffprobe`, so a relative path starting with `-` can't be misinterpreted as a flag.

## [0.1.2] — 2026-04-24

### Fixed
- Windows console crash: removed the emoji from the long-video warning in `watch.py`; cp1252 consoles couldn't encode it.
- `setup.py` now prints `winget` / `pip` install commands on Windows instead of "unsupported platform" — matches what the README already promised.

### Changed
- `SKILL.md` notes that on Windows the scripts must be invoked with `python`, not `python3` (the latter is the Microsoft Store stub on Windows).

## [0.1.1] — 2026-04-24

### Fixed
- Added `commands/watch.md` shim so `/watch` is callable when installed as a Claude Code plugin. Without it, the plugin loaded but the skill wasn't exposed as a slash command.
- `scripts/build-skill.sh` now strips `commands/` from the claude.ai `.skill` bundle alongside `hooks/` and `.claude-plugin/`.

## [0.1.0] — 2026-04-24

Initial marketplace release.

### Added
- `/watch <url-or-path> [question]` slash command.
- yt-dlp download with native caption extraction (manual + auto-subs).
- ffmpeg frame extraction with auto-scaled fps (≤2 fps, ≤100 frames, duration-aware budget).
- `--start` / `--end` focused mode with denser frame budget and transcript range filtering.
- Whisper fallback (Groq preferred, OpenAI secondary) for videos without captions.
- `setup.py` preflight: silent `--check`, structured `--json`, and installer that auto-runs `brew install` on macOS.
- Session-start hook that prints a one-line status on first run / partial config.
- `.skill` bundle packaging for claude.ai upload via `scripts/build-skill.sh`.
