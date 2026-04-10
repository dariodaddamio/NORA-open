# Configuration

Back to [README](../README.md)

Full template: [`.env.example`](../.env.example). Below is a grouped reference; uncomment or add variables as needed.

## Core

| Variable | Purpose |
|----------|---------|
| `DISCORD_TOKEN` | Discord bot token |
| `OBSIDIAN_VAULT_PATH` | Absolute path to Obsidian **vault root** (not `.obsidian`) |
| `OPENROUTER_API_KEY` | OpenRouter bearer token (empty = use Ollama for LLM) |
| `OPENROUTER_MODEL` | OpenRouter model id (e.g. `openrouter/free` or a paid model) |
| `OLLAMA_MODEL` | Ollama model when OpenRouter key is absent (e.g. `llama3.1` → normalized to `llama3.1:latest`) |

## Pipeline mode

| Variable | Purpose |
|----------|---------|
| `PIPELINE_MODE` | `graph` (topic/entity/index notes) or `basic` (single summary note) |

## Graph and taxonomy

| Variable | Purpose |
|----------|---------|
| `GRAPH_MIN_ENTITY_CONFIDENCE` | Drop entities below this confidence |
| `MAX_TOPICS_PER_VIDEO` | Cap on subtopics per video |
| `TAXONOMY_PATH` | Path to `taxonomy.json` (defaults apply if missing) |
| `TAXONOMY_MODE` | `static` (default): unknown classifier categories become `general`. `auto`: append sanitized new categories to `TAXONOMY_PATH` (atomic write), then reload for the rest of the run; at cap or on error, behavior matches static for that note |
| `TAXONOMY_AUTO_MAX_CATEGORIES` | Max category count in the JSON file (default `48`, never below built-in default list length + 1) |
| `TAXONOMY_AUTO_MIN_SLUG_LEN` | Min length for a new category slug (default `2`) |
| `TAXONOMY_AUTO_MAX_SLUG_LEN` | Max slug length (default `40`, capped at 80) |

Copy [`taxonomy.example.json`](../taxonomy.example.json) to `taxonomy.json` when you want an explicit starter file (recommended for open-repo clones).

## Visual / multimodal

| Variable | Purpose |
|----------|---------|
| `VISUAL_CONTEXT_ENABLED` | Enable keyframes + OCR context for LLM |
| `MAX_KEYFRAMES_ANALYZED` | Frames to analyze |
| `MAX_IMAGES_PER_NOTE` | Persist/embed 1–3 images |
| `FRAME_SAMPLING_MODE` | `interval` or `scene` |
| `FRAME_INTERVAL_SECONDS` | Seconds between samples (interval mode) |
| `OCR_TESSERACT_CMD` | Tesseract executable (default `tesseract`) |

## Consistency and titles

| Variable | Purpose |
|----------|---------|
| `CONSISTENCY_CHECK_ENABLED` | Post-summary claim verification |
| `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` | Stricter wording when OCR/transcript alignment is low |
| `REWRITE_CONTRADICTED_CLAIMS` | Rewrite summary when contradictions found |
| `TITLE_STYLE` | e.g. `clean` |
| `ALLOW_FILENAME_DATE_PREFIX` | Prefix dates on filenames |
| `NOTE_FILENAME_STYLE` | `human` or `slug` |
| `MIGRATE_EXISTING_NOTE_FILENAMES` | One-time rename pass for Instagram Notes |
| `REWRITE_VAULT_LINKS_ON_MIGRATION` | Rewrite wiki-links after rename |

## Transcript and caption gates

| Variable | Purpose |
|----------|---------|
| `TRANSCRIPT_GATE_ENABLED` | Block low-signal transcripts |
| `TRANSCRIPT_MIN_WORDS` | Minimum word count |
| `TRANSCRIPT_MIN_UNIQUE_WORDS` | Minimum unique words |
| `TRANSCRIPT_MIN_ALPHA_RATIO` | Alphabetic ratio heuristic |
| `TRANSCRIPT_GATE_ALLOW_FORCE` | Allow Discord “Try anyway” override |
| `CAPTION_CONTEXT_ENABLED` | Fetch/use caption metadata |
| `CAPTION_MISMATCH_GATE_ENABLED` | Gate on transcript vs caption mismatch |
| `CAPTION_MIN_WORDS` | Treat caption as “strong” if at least this many words |
| `TRANSCRIPT_CAPTION_MIN_OVERLAP` | Minimum keyword overlap ratio |
| `CAPTION_PRIMARY_WHEN_TRANSCRIPT_WEAK` | Prefer caption when transcript is weak |

## Instagram download

| Variable | Purpose |
|----------|---------|
| `YTDLP_COOKIES_FROM_BROWSER` | e.g. `chrome` |
| `YTDLP_COOKIES_FILE` | Path to cookies file |

## Temp and logging

| Variable | Purpose |
|----------|---------|
| `KEEP_TEMP` | Keep temp dirs on success |
| `KEEP_TEMP_ON_FAILURE` | Keep temp on failure (debug) |
| `SUBPROCESS_VERBOSE_LOGS` | Stream raw subprocess output |
| `EMOJI_LOGS_ENABLED` | Emoji markers in terminal progress logs |

## ETA and Discord updates

| Variable | Purpose |
|----------|---------|
| `DISCORD_ETA_UPDATE_INTERVAL_SECONDS` | How often `/save` updates ETA in Discord |
| `ETA_BASE_SECONDS` | Fixed overhead in estimates |
| `ETA_PER_VIDEO_SECOND` | Per-second-of-video multiplier |
| `ETA_LLM_OVERHEAD_SECONDS` | Extra budget for LLM stages |
| `ETA_HISTORY_PATH` | JSON file for adaptive timing history |
| `ETA_HISTORY_WINDOW` | Max samples per stage |
| `ETA_MIN_SAMPLES` | Samples before history overrides defaults |
| `ETA_QUANTILE` | Conservative quantile (e.g. p75) |

## `/saveall` limits

| Variable | Purpose |
|----------|---------|
| `SAVEALL_DEFAULT_MAX_MESSAGES` | Default scan depth |
| `SAVEALL_DEFAULT_MAX_NEW_LINKS` | Default cap on new links |
| `SAVEALL_HARD_MAX_MESSAGES` | Hard ceiling |
| `SAVEALL_HARD_MAX_NEW_LINKS` | Hard cap on new links |
| `SAVEALL_PROGRESS_EVERY` | Progress update interval |

## Recommended `.env` block (graph mode)

Use as a starting point; merge with [.env.example](../.env.example):

```env
PIPELINE_MODE=graph
GRAPH_MIN_ENTITY_CONFIDENCE=0.55
MAX_TOPICS_PER_VIDEO=6
TAXONOMY_PATH=taxonomy.json
# TAXONOMY_MODE=static
# TAXONOMY_MODE=auto
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

Adaptive ETA and emoji logging defaults are already in `.env.example` under **Recommended defaults**.
