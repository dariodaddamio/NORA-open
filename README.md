# NORA - Notes for Obsidian from Reels via AI

NORA processes Instagram links from Discord and writes Markdown notes into an Obsidian vault.

## Quick start

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env`, fill only required keys first:
- `DISCORD_TOKEN`
- `OBSIDIAN_VAULT_PATH`
- `OPENROUTER_API_KEY` (recommended)

3. Run:

```powershell
.\.venv\Scripts\python bot.py
```

4. In Discord:
- `/save url:https://www.instagram.com/reel/...`
- `/saveall`

## What it does

- `/save <url>`: process one Instagram URL.
- `/saveall`: scan previous messages in the current channel and process Instagram links that were not processed yet.
- Converts video -> audio -> transcript -> structured Obsidian knowledge notes.
- Stores dedupe state in `processed.json` so repeated runs skip already-processed links.

## Document map

- Architecture: command flow, processing stages, quality gates
- Environment: quick defaults and full variable reference
- Output model: note structure, graph links, naming/migration
- Ops: running locally, multi-device workflow, troubleshooting, tuning

## Detailed architecture

### 1) Command layer (`bot.py`)

- `bot.py` registers Discord slash commands and does lightweight orchestration.
- `/save` processes a single URL immediately.
- `/saveall` scans recent channel history, extracts Instagram URLs, skips duplicates/processed URLs, and runs the same pipeline for each new link.
- Concurrency protection:
  - one `/saveall` job per server at a time
  - progress updates every N items (`SAVEALL_PROGRESS_EVERY`)

### 2) Processing pipeline (`process_link.py`)

For each new URL, NORA runs this sequence:

1. **Download**
   - Calls `yt_dlp` via `python -m yt_dlp` (portable across machines/venv paths).
2. **Audio extraction**
   - Uses `ffmpeg` to convert video to mono 16kHz WAV.
3. **Transcription**
   - Uses `faster-whisper` (`base`, CPU, int8).
4. **Knowledge enrichment** (graph mode)
   - Classify transcript into fixed top-level taxonomy.
   - Extract entities (tool/person/concept/resource etc.) with confidence scores.
   - Generate structured markdown summary.
   - Inject visual context (OCR/keyframe signals) into classifier/entity/summary prompts.
5. **Graph writing**
   - Creates/updates video, topic, entity, and category index notes with bidirectional links.
   - Embeds selected keyframes in `## Visual Highlights`.

### 2.2) Gate and decision matrix

NORA does not blindly summarize every transcript. It runs a staged decision model:

1. **Transcript usefulness gate**
   - checks speech density and quality (`word count`, `unique words`, `alpha ratio`, repetition/noise)
2. **Transcript-caption alignment gate**
   - compares transcript keywords against caption/title metadata
3. **Decision**
   - normal mode (transcript usable)
   - caption-primary mode (transcript weak, caption strong)
   - gate + Discord warning with `Try anyway` button (transcript/caption too weak or strongly mismatched)

### 2.1) Multimodal path (free-first)

When `VISUAL_CONTEXT_ENABLED=true`, NORA runs a lightweight visual path before LLM enrichment:

1. Extract keyframes with `ffmpeg` (`interval` or `scene` mode).
2. Read on-screen text using local OCR (`tesseract`).
3. Rank frames by OCR richness and spread across time.
4. Keep top `MAX_IMAGES_PER_NOTE` frames (capped to 1-3).
5. Persist these images to `Assets/Instagram/...` and embed in the note.

If keyframe/OCR steps fail, NORA continues with transcript-only mode for robustness.

If `PIPELINE_MODE=basic`, NORA falls back to single-note summarization.

### 3) AI model routing

- Preferred path: OpenRouter chat completions (`OPENROUTER_API_KEY` set).
- Fallback path: local Ollama (`OLLAMA_MODEL`) if OpenRouter key is missing.
- Transcript prompts are size-bounded to avoid oversized-context failures.
- Same validation/repair logic is applied regardless of backend.

### 3.1) LLM call breakdown and call-count variability

NORA now logs each LLM completion with stage labels plus timing:

- `[LLM] START stage=<name> provider=<openrouter|ollama> model=<id>`
- `[LLM] DONE stage=<name> ... (<seconds>s)`
- `[LLM] FAIL stage=<name> ...`
- end-of-run aggregate:
  - `[LLM] SUMMARY calls=<n> elapsed=<seconds>s stages=stageA:x, stageB:y`

Stage map in `PIPELINE_MODE=graph`:

- Always expected:
  - `classify`: taxonomy classification
  - `entities`: entity extraction
  - `summary`: markdown summary generation
  - `title`: clean title generation
- Conditional:
  - `verify`: runs when `CONSISTENCY_CHECK_ENABLED=true`
  - `rewrite:contradictions`: runs only when rewrite is enabled and contradictions were found
  - `repair:classification`, `repair:entities`, `repair:verification`: run only when model output is malformed and repair is attempted
  - `classify:fallback`, `entities:fallback`: run only if primary structured extraction path throws and fallback prompt path is used

Stage map in `PIPELINE_MODE=basic`:

- `summary:basic` for single-note summarization flow

Why call counts differ between reels:

- quality gate and caption mismatch decisions can short-circuit runs before later stages
- verification/rewrite and repair stages are conditional by design
- graph mode and basic mode use different stage sets

### 4) Validation, normalization, and repair

- Category is forced into allowed taxonomy values (fallback: `general`).
- Tags are normalized to prefixed slugs (for example `topic/topography`).
- Subtopics and tags are deduplicated with stable ordering.
- Entities below `GRAPH_MIN_ENTITY_CONFIDENCE` are dropped.
- If model output is malformed:
  - NORA tries one repair pass to coerce strict JSON.
  - If repair still fails, NORA writes a safe fallback payload instead of crashing.
- If verification output is malformed:
  - NORA attempts JSON repair.
  - If repair fails, it falls back to conservative verification counts.

### 5) Obsidian graph structure

NORA writes these note families:

- `Instagram Notes/`
  - Primary source note per video (frontmatter + summary + transcript).
- `Topics/`
  - One note per normalized topic, with links back to related videos.
- `Entities/`
  - One note per normalized entity, with links back to related videos.
- `Indexes/`
  - Category MOC notes such as `Category - Design.md`.

This creates natural graph clusters by category/topic/entity over time.

### 5.1) Generated note sections (video note)

Each video note includes:

- YAML frontmatter for metadata/queryability
- LLM summary sections (`## TL;DR`, `## Key Ideas`, `## Actionable Takeaways`)
- `## Category`, `## Topics`, and `## Entities` wiki-links
- `## Visual Highlights` (if images selected)
- `## Verification` (consistency metrics + uncertain claim list)
- `## Source`
- `## Transcript`

### 6) Frontmatter shape (video note)

Video notes include structured metadata that Obsidian plugins/queries can use:

- `type`: `video-note`
- `source_url`
- `created_at`
- `title_generated_by` (`llm` or `fallback`)
- `alignment_score` (0.00-1.00)
- `verification_supported_count`
- `verification_uncertain_count`
- `verification_contradicted_count`
- `category`
- `subtopics` (array)
- `entities` (array)
- `tags` (array)
- `status`

### 7) Idempotency and cache behavior

- `processed.json` stores `url -> note_path`.
- If URL exists and note exists on disk, processing is skipped.
- If cached path is stale (for example machine move), NORA attempts path repair before reprocessing.
- This keeps reruns fast while still resilient to path migration.

## Prerequisites

- Python 3.10+
- ffmpeg available on PATH
- Discord bot application/token
- OpenRouter API key (recommended) or local Ollama setup

## Setup

If you already followed **Quick start**, this section is reference detail.

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2. Copy environment template:

```powershell
Copy-Item .env.example .env
```

3. Fill required values in `.env`:

- `DISCORD_TOKEN`
- `OBSIDIAN_VAULT_PATH`
- `OPENROUTER_API_KEY` (recommended)
- Beginner note: start with only the **Required** and **Recommended defaults** sections from `.env.example`; all advanced tuning knobs can stay commented until needed.
- Optional graph settings:
  - `PIPELINE_MODE=graph|basic`
  - `GRAPH_MIN_ENTITY_CONFIDENCE`
  - `MAX_TOPICS_PER_VIDEO`
  - `TAXONOMY_PATH` (defaults to `taxonomy.json`)
  - `OPENROUTER_MODEL` and/or `OLLAMA_MODEL`
  - `VISUAL_CONTEXT_ENABLED`
  - `MAX_KEYFRAMES_ANALYZED`
  - `MAX_IMAGES_PER_NOTE` (1-3)
  - `FRAME_SAMPLING_MODE=interval|scene`
  - `FRAME_INTERVAL_SECONDS`
  - `OCR_TESSERACT_CMD`

### Recommended `.env` for graph mode

```env
PIPELINE_MODE=graph
GRAPH_MIN_ENTITY_CONFIDENCE=0.55
MAX_TOPICS_PER_VIDEO=6
TAXONOMY_PATH=taxonomy.json
VISUAL_CONTEXT_ENABLED=true
MAX_KEYFRAMES_ANALYZED=12
MAX_IMAGES_PER_NOTE=3
FRAME_SAMPLING_MODE=interval
FRAME_INTERVAL_SECONDS=2
OCR_TESSERACT_CMD=tesseract
CONSISTENCY_CHECK_ENABLED=true
MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE=0.25
REWRITE_CONTRADICTED_CLAIMS=false
TITLE_STYLE=clean
ALLOW_FILENAME_DATE_PREFIX=false
NOTE_FILENAME_STYLE=human
MIGRATE_EXISTING_NOTE_FILENAMES=true
REWRITE_VAULT_LINKS_ON_MIGRATION=true
SUBPROCESS_VERBOSE_LOGS=false
EMOJI_LOGS_ENABLED=true
DISCORD_ETA_UPDATE_INTERVAL_SECONDS=10
ETA_BASE_SECONDS=8.0
ETA_PER_VIDEO_SECOND=0.75
ETA_LLM_OVERHEAD_SECONDS=10.0
ETA_HISTORY_PATH=eta-history.json
ETA_HISTORY_WINDOW=200
ETA_MIN_SAMPLES=3
ETA_QUANTILE=0.75
TRANSCRIPT_GATE_ENABLED=true
TRANSCRIPT_MIN_WORDS=20
TRANSCRIPT_MIN_UNIQUE_WORDS=12
TRANSCRIPT_MIN_ALPHA_RATIO=0.55
TRANSCRIPT_GATE_ALLOW_FORCE=true
CAPTION_CONTEXT_ENABLED=true
CAPTION_MISMATCH_GATE_ENABLED=true
CAPTION_MIN_WORDS=6
TRANSCRIPT_CAPTION_MIN_OVERLAP=0.08
CAPTION_PRIMARY_WHEN_TRANSCRIPT_WEAK=true
```

### Environment reference

- Core:
  - `DISCORD_TOKEN`: Discord bot token
  - `OBSIDIAN_VAULT_PATH`: vault root path
- LLM routing:
  - `OPENROUTER_API_KEY`: preferred cloud path
  - `OPENROUTER_MODEL`: OpenRouter model id
  - `OLLAMA_MODEL`: local fallback model
- Graph behavior:
  - `PIPELINE_MODE=graph|basic`
  - `GRAPH_MIN_ENTITY_CONFIDENCE`
  - `MAX_TOPICS_PER_VIDEO`
  - `TAXONOMY_PATH`
- Visual behavior:
  - `VISUAL_CONTEXT_ENABLED`
  - `MAX_KEYFRAMES_ANALYZED`
  - `MAX_IMAGES_PER_NOTE` (1-3)
  - `FRAME_SAMPLING_MODE=interval|scene`
  - `FRAME_INTERVAL_SECONDS`
  - `OCR_TESSERACT_CMD`
- Consistency and title behavior:
  - `CONSISTENCY_CHECK_ENABLED`
  - `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE`
  - `REWRITE_CONTRADICTED_CLAIMS`
  - `TITLE_STYLE=clean`
  - `ALLOW_FILENAME_DATE_PREFIX=false`
  - `NOTE_FILENAME_STYLE=human|slug`
  - `MIGRATE_EXISTING_NOTE_FILENAMES=true|false`
  - `REWRITE_VAULT_LINKS_ON_MIGRATION=true|false`
- Transcript gate behavior:
  - `TRANSCRIPT_GATE_ENABLED=true|false`
  - `TRANSCRIPT_MIN_WORDS`
  - `TRANSCRIPT_MIN_UNIQUE_WORDS`
  - `TRANSCRIPT_MIN_ALPHA_RATIO`
  - `TRANSCRIPT_GATE_ALLOW_FORCE=true|false`
  - `CAPTION_CONTEXT_ENABLED=true|false`
  - `CAPTION_MISMATCH_GATE_ENABLED=true|false`
  - `CAPTION_MIN_WORDS`
  - `TRANSCRIPT_CAPTION_MIN_OVERLAP`
  - `CAPTION_PRIMARY_WHEN_TRANSCRIPT_WEAK=true|false`
- Cleanup behavior:
  - `KEEP_TEMP`
  - `KEEP_TEMP_ON_FAILURE`
  - `SUBPROCESS_VERBOSE_LOGS=true|false` (full raw subprocess output)
  - `EMOJI_LOGS_ENABLED=true|false` (emoji markers in terminal progress logs)
- ETA and status behavior:
  - `DISCORD_ETA_UPDATE_INTERVAL_SECONDS` (how often `/save` updates ETA in Discord)
  - `ETA_BASE_SECONDS` (fixed estimate overhead)
  - `ETA_PER_VIDEO_SECOND` (estimate multiplier per second of video)
  - `ETA_LLM_OVERHEAD_SECONDS` (extra estimate budget for LLM stages)
  - `ETA_HISTORY_PATH` (local adaptive ETA history JSON file)
  - `ETA_HISTORY_WINDOW` (max stored timing samples per stage)
  - `ETA_MIN_SAMPLES` (minimum samples before stage history overrides defaults)
  - `ETA_QUANTILE` (conservative quantile, default p75)
  - Adaptive ETA "training" happens automatically by recording each run's stage timings into the history file.

## Discord setup

In Discord Developer Portal:

- OAuth2 scopes: `bot`, `applications.commands`
- Permissions: View Channels, Send Messages, Read Message History
- Enable `MESSAGE CONTENT INTENT` in Bot settings

Re-invite the bot if needed after scope changes.

## Run locally

```powershell
.\.venv\Scripts\python bot.py
```

On startup, slash commands are synced.

## Daily usage

- `/save url:https://www.instagram.com/reel/...`
- `/saveall` (optional parameters: `max_messages`, `max_new_links`, `oldest_first`)

## Taxonomy customization

Edit `taxonomy.json` to control graph consistency:

- `categories`: fixed top-level categories (required for stable graph clusters)
- `tag_prefixes`: allowed namespaces (`topic`, `domain`, `tool`, `format`)
- `synonyms`: normalization map (for example `artificial intelligence -> ai`)

Tips:

- Keep category names lowercase and stable.
- Prefer adding synonyms instead of adding near-duplicate categories.
- Keep top-level categories broad; let subtopics carry specificity.

## Visual context and image embeds

When `VISUAL_CONTEXT_ENABLED=true`, NORA augments transcript understanding with lightweight frame analysis:

- extract keyframes with `ffmpeg`
- run OCR on frames (via `tesseract`)
- rank frames with text-richness + temporal spread heuristics
- keep only the top 1-3 frames
- persist them to `vault/Assets/Instagram/...`
- embed in video notes under `## Visual Highlights`

If OCR is unavailable, NORA falls back to transcript-only context and still completes.

## Consistency verification

NORA now runs a quality-control stage that compares OCR and transcript signals, then verifies summary claims:

- builds OCR/transcript overlap terms and an alignment score
- passes alignment context into classifier/entity/summarizer prompts
- verifies key claims with statuses:
  - `supported`
  - `uncertain`
  - `contradicted`
- writes verification metrics into frontmatter and adds a `## Verification` section in note body

## Transcript usefulness gate

NORA checks transcript quality before expensive summarization:

- word count threshold
- unique word threshold
- alphabetic character ratio
- repetition/noise heuristics
- transcript-caption topic overlap (when caption context is available)

If transcript is low-signal and gate is enabled:

- `/save` responds in Discord: `No transcript detected (due to ...)`
- includes a `Try anyway` button
- clicking `Try anyway` reruns processing with forced mode

Caption-aware behavior:

- If transcript is weak but caption is strong, NORA can continue in caption-primary mode.
- If transcript and caption strongly mismatch, NORA gates by default (configurable).
- Gate reasons in Discord include mismatch causes when detected.

Forced notes include:

- `transcript_useful: false`
- `transcript_quality_reasons` in frontmatter
- `caption_available`, `caption_primary_context`, and mismatch flags in frontmatter
- `## Transcript Quality Warning` section in note body

### Verification and rewrite loop

If `REWRITE_CONTRADICTED_CLAIMS=true` and contradicted claims are found:

1. NORA rewrites the summary to remove/correct contradicted claims.
2. NORA reruns verification on the rewritten summary.
3. Final note includes updated verification metrics.

This gives a self-correcting loop instead of only warning text.

### How alignment affects strictness

NORA computes an OCR-transcript alignment score and uses it to tune summary behavior:

- higher alignment: allows stronger visual-context claims
- lower alignment: prompt shifts to transcript-grounded, cautious wording
- threshold is controlled by `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE`

## Output structure

NORA writes/updates these locations inside your vault:

- `Instagram Notes/`
  - One primary note per source video
- `Topics/`
  - Topic hub notes linked from multiple videos
- `Entities/`
  - Entity notes (tools/concepts/brands/etc.)
- `Indexes/`
  - Category MOC notes
- `Assets/Instagram/`
  - Persisted selected keyframes used by `## Visual Highlights`

Example logical result for one reel:

- `Instagram Notes/Topographic Effect Image Editing Workflow.md`
- `Topics/topography-effect.md`
- `Entities/photoshop.md`
- `Indexes/Category - Design.md`
- `Assets/Instagram/2026-04-10-topographic-effect-image-editing-workflow/frame-01.jpg`

## Naming behavior

By default, video note filenames are clean title-based:

- `Instagram Notes/Color Swatching Guide.md`

Filename details:

- no forced date prefix by default (`ALLOW_FILENAME_DATE_PREFIX=false`)
- title is generated and sanitized (`TITLE_STYLE=clean`)
- filename style defaults to human-readable with spaces (`NOTE_FILENAME_STYLE=human`)
- on collision with a different source URL, numeric suffixes are added:
  - `.../Color Swatching Guide (2).md`
  - `.../Color Swatching Guide (3).md`
- source metadata remains in frontmatter (`source_url`, `created_at`)

Migration behavior:

- when `MIGRATE_EXISTING_NOTE_FILENAMES=true`, existing notes in `Instagram Notes/` are renamed once using generated clean titles
- when `REWRITE_VAULT_LINKS_ON_MIGRATION=true`, vault wiki-links are rewritten to point at renamed files
- `processed.json` is updated to renamed paths

## Multi-device workflow (laptop/another device)

1. Pull the repo on the other device.
2. Create a local `.env` on that device (do not sync secrets).
3. Ensure ffmpeg/Python are installed there.
4. Start bot on that device:

```powershell
.\.venv\Scripts\python bot.py
```

Important: run only one active bot host at a time to avoid overlapping processing.

## Temp file behavior

- Per-run temp files are created under `temp/<job_id>/`.
- Default behavior:
  - delete temp job folder on success
  - delete temp root folder too if it becomes empty
  - keep temp folder on failure (for debugging)
- Controlled by:
  - `KEEP_TEMP`
  - `KEEP_TEMP_ON_FAILURE`

Important:
- Temp cleanup never touches persisted vault assets.
- On successful runs with `KEEP_TEMP=false`, both the job dir and empty temp root are removed.
- On failed runs with `KEEP_TEMP_ON_FAILURE=true`, artifacts are retained for debugging.

## Troubleshooting

- Commands do not appear:
  - ensure `applications.commands` scope was used
  - wait ~30-60 seconds after startup
- `Failed to process link`:
  - verify OpenRouter key/model or Ollama health
  - verify `ffmpeg -version` works
  - verify `python -m yt_dlp --version` works inside the same venv
- Instagram download issues:
  - update `yt-dlp`
  - use cookies (`YTDLP_COOKIES_FROM_BROWSER` or `YTDLP_COOKIES_FILE`)
- Notes are not appearing in the vault:
  - verify `OBSIDIAN_VAULT_PATH` points to the vault root (not `.obsidian`)
  - check `processed.json` for stale cached path entries
  - restart bot after `.env` changes
- Graph notes look too sparse:
  - lower `GRAPH_MIN_ENTITY_CONFIDENCE` (for example from `0.55` to `0.40`)
  - increase `MAX_TOPICS_PER_VIDEO`
- Visual highlights missing:
  - verify `tesseract --version` (or set `OCR_TESSERACT_CMD`)
  - set `VISUAL_CONTEXT_ENABLED=true`
  - raise `MAX_KEYFRAMES_ANALYZED` if frames are too sparse
  - check `MAX_IMAGES_PER_NOTE` is at least `1`
- Temp folder still exists after success:
  - if there are other files/jobs inside `temp`, root deletion is skipped intentionally
  - set `KEEP_TEMP=false`
- Summaries miss visual details:
  - set `VISUAL_CONTEXT_ENABLED=true`
  - try `FRAME_SAMPLING_MODE=scene`
  - increase `MAX_KEYFRAMES_ANALYZED`
- Notes include weak/conflicting claims:
  - set `CONSISTENCY_CHECK_ENABLED=true`
  - increase `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` to make summarization stricter
  - set `REWRITE_CONTRADICTED_CLAIMS=true` to auto-rewrite contradicted claims
  - inspect `verification_*` frontmatter counters for ongoing quality tuning
- Filename still includes date prefix:
  - ensure `ALLOW_FILENAME_DATE_PREFIX=false`
  - ensure `TITLE_STYLE=clean`
  - ensure `NOTE_FILENAME_STYLE=human`
- Existing old filenames were not renamed:
  - set `MIGRATE_EXISTING_NOTE_FILENAMES=true`
  - remove `.filename_migration_done` marker in vault root to rerun migration

## Quality tuning playbook

Recommended baseline:

- `CONSISTENCY_CHECK_ENABLED=true`
- `REWRITE_CONTRADICTED_CLAIMS=true`
- `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE=0.25`
- `VISUAL_CONTEXT_ENABLED=true`

If notes become too cautious:

- lower `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` (e.g. 0.20)
- keep rewrite enabled, but review uncertain claim counts

If notes still hallucinate:

- raise `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` (e.g. 0.35-0.45)
- increase `MAX_KEYFRAMES_ANALYZED`
- keep `REWRITE_CONTRADICTED_CLAIMS=true`

## Files of interest

- `bot.py`: Discord slash commands
- `process_link.py`: processing pipeline, multimodal analysis, and temp cleanup
- `taxonomy.json`: controlled categories, tag prefixes, synonyms
- `.env.example`: configuration reference
- `processed.json`: URL dedupe state