# Configuration

Back to main [README](../README.md)

Full template: [`.env.example`](../.env.example). Below is a grouped reference; uncomment or add variables as needed.

**Where “allowed values” come from:** Enum-style strings are interpreted in [`process_link.py`](../process_link.py) (`_cfg()` and related helpers)—there is no separate config schema file. If you set an unknown value, behavior falls through to the default branch (e.g. only `graph` enables graph mode; only `scene` switches scene-based keyframes; only `slug` switches slug filenames). **`TITLE_STYLE`** is validated: unknown values log a config warning and map to **`heuristic`**. **Booleans** accept `true` / `false` / `1` / `yes` / `y` (case-insensitive).

## Discrete string options

| Variable | Set to | Effect |
|----------|--------|--------|
| `PIPELINE_MODE` | `graph` (default) | Full pipeline: taxonomy, entities, topic/index notes, graph write. |
| `PIPELINE_MODE` | `basic` (or any value other than `graph`) | Single summary note per reel; no graph/taxonomy path. |
| `TITLE_STYLE` | `clean` (default) | LLM-generated title (extra LLM call; falls back to heuristics if the model returns junk). |
| `TITLE_STYLE` | `heuristic` | No title LLM: title from first subtopic, else top transcript keywords, else category (same seeding as the old non-`clean` behavior). |
| `TITLE_STYLE` | `summary_heading` | Use the first markdown `# heading` from the generated summary; if missing or generic, same as `heuristic`. Alias: `summary`. |
| `TITLE_STYLE` | `category` | Title seed from the **taxonomy category** string (passed through `_clean_title_text`). If category is empty, falls back like `heuristic`. |
| `TITLE_STYLE` | Aliases | `fallback`, `keywords`, or `messy` → `heuristic` (no extra LLM). |
| `TITLE_STYLE` | Anything else | **Warning** printed; treated as **`heuristic`**. |
| `NOTE_FILENAME_STYLE` | `human` (default) | Filename from title: strip unsafe characters, keep readable spaces. |
| `NOTE_FILENAME_STYLE` | `slug` | Filename from slugified title (URL-safe, consistent). |
| `FRAME_SAMPLING_MODE` | `interval` (default) | Sample frames every `FRAME_INTERVAL_SECONDS` seconds (up to `MAX_KEYFRAMES_ANALYZED`). |
| `FRAME_SAMPLING_MODE` | `scene` | Use ffmpeg scene-change detection instead of fixed intervals (still capped by `MAX_KEYFRAMES_ANALYZED`). |
| `TAXONOMY_MODE` | `static` (default) | Unknown model categories map to `general`. |
| `TAXONOMY_MODE` | `auto` | Append new sanitized categories to `TAXONOMY_PATH` when under cap (see Graph and taxonomy). |

`OPENROUTER_MODEL` and `OLLAMA_MODEL` are **not** fixed enums: use whatever model id your provider exposes (e.g. `openrouter/free`, or a paid route on OpenRouter; Ollama tags like `llama3.1` are normalized to `llama3.1:latest` when needed).

## Turning knobs (higher vs lower)

**Graph and taxonomy**

- **`GRAPH_MIN_ENTITY_CONFIDENCE`** — **Lower** → keep more entities (richer graph, more noise). **Higher** → fewer entities (stricter, sparser notes).
- **`MAX_TOPICS_PER_VIDEO`** — **Higher** → more topic hub links per video. **Lower** → fewer topics.
- **`TAXONOMY_AUTO_MAX_CATEGORIES`** (auto mode) — **Higher** → room for more distinct auto categories before new ones fall back to `general`. **Lower** → hit the cap sooner.

**Visual (OCR)**

- **`MAX_KEYFRAMES_ANALYZED`** / **`MAX_IMAGES_PER_NOTE`** — **Higher** → more frames sampled and more OCR text in prompts (still **text-only** for the LLM), and/or more images embedded in the note (slower runs, more work). **Lower** → faster runs, thinner on-screen hints in prompts.
- **`FRAME_INTERVAL_SECONDS`** (when mode is `interval`) — **Higher** → samples further apart (fewer candidate frames before the cap). **Lower** → denser sampling.

**Summary alignment**

- **`MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE`** — The summary prompt adds extra “alignment is weak, hedge uncertainty” guidance when the parsed alignment score is **below** this threshold. **Raise** it → that stricter guidance appears **more often**. **Lower** it → only the worst alignments trigger it.

**Transcript and caption gates**

- **`TRANSCRIPT_MIN_WORDS`**, **`TRANSCRIPT_MIN_UNIQUE_WORDS`**, **`TRANSCRIPT_MIN_ALPHA_RATIO`** — **Raise** → more reels fail the transcript gate (more “blocked” / Try anyway). **Lower** → easier to pass.
- **`TRANSCRIPT_CAPTION_MIN_OVERLAP`** — **Raise** → transcript and caption must overlap more to avoid mismatch treatment. **Lower** → more lenient.
- **`CAPTION_MIN_WORDS`** — **Raise** → caption must be longer before it counts as a “strong” caption for gating. **Lower** → shorter captions can qualify.

**ETA (Discord progress messages)**

- **`ETA_QUANTILE`** (e.g. `0.75`) — **Higher** (toward `0.99`) → estimates lean on slower historical runs (usually safer, longer quoted ETAs). **Lower** (toward `0.5`) → more optimistic.
- **`ETA_BASE_SECONDS`**, **`ETA_PER_VIDEO_SECOND`**, **`ETA_LLM_OVERHEAD_SECONDS`** — **Raise** → baseline estimates increase. **Lower** → shorter ETAs (may under-shoot).

**`/saveall` limits**

- **`SAVEALL_DEFAULT_MAX_MESSAGES`**, **`SAVEALL_HARD_MAX_MESSAGES`** — **Higher** → scan deeper channel history (slower, more API work). **Lower** → shallower scan.
- **`SAVEALL_DEFAULT_MAX_NEW_LINKS`**, **`SAVEALL_HARD_MAX_NEW_LINKS`** — **Higher** → more new reels processed per `/saveall`. **Lower** → smaller batches.
- **`SAVEALL_PROGRESS_EVERY`** — **Higher** → fewer Discord progress updates. **Lower** → more chatty progress.

**Discord ETA spam**

- **`DISCORD_ETA_UPDATE_INTERVAL_SECONDS`** — **Higher** → less frequent ETA edits on `/save`. **Lower** → updates more often.

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
| `PIPELINE_MODE` | See [Discrete string options](#discrete-string-options): `graph` vs everything else (`basic` recommended). |

## Graph and taxonomy

| Variable | Purpose |
|----------|---------|
| `GRAPH_MIN_ENTITY_CONFIDENCE` | Drop entities below this confidence ([tuning](#turning-knobs-higher-vs-lower)). |
| `MAX_TOPICS_PER_VIDEO` | Cap on subtopics per video ([tuning](#turning-knobs-higher-vs-lower)). |
| `TAXONOMY_PATH` | Path to `taxonomy.json` (defaults apply if missing) |
| `TAXONOMY_MODE` | `static` (default): unknown classifier categories become `general`. `auto`: append sanitized new categories to `TAXONOMY_PATH` (atomic write), then reload for the rest of the run; at cap or on error, behavior matches static for that note |
| `TAXONOMY_AUTO_MAX_CATEGORIES` | Max category count in the JSON file (default `48`, never below built-in default list length + 1; [tuning](#turning-knobs-higher-vs-lower)) |
| `TAXONOMY_AUTO_MIN_SLUG_LEN` | Min length for a new category slug (default `2`) |
| `TAXONOMY_AUTO_MAX_SLUG_LEN` | Max slug length (default `40`, capped at 80) |

Copy [`taxonomy.example.json`](../taxonomy.example.json) to `taxonomy.json` when you want an explicit starter file (recommended for open-repo clones).

## Visual (keyframes and OCR)

**Note:** “Visual” here means **ffmpeg keyframes + Tesseract OCR** (a free-first path: no paid vision API). The LLM only receives **OCR-derived text** in prompts, not pixels through a vision model—so quality is often modest on busy or stylized reels. Tuning, stronger text models, and possible future vision-style integration are covered in [stack-and-costs.md](stack-and-costs.md#keyframes-and-ocr-limits-and-improvements).

| Variable | Purpose |
|----------|---------|
| `VISUAL_CONTEXT_ENABLED` | Enable keyframes + OCR context for LLM |
| `MAX_KEYFRAMES_ANALYZED` | Frames to analyze ([tuning](#turning-knobs-higher-vs-lower)). |
| `MAX_IMAGES_PER_NOTE` | Persist/embed 1–3 images (clamped 1–3 in code; [tuning](#turning-knobs-higher-vs-lower)). |
| `FRAME_SAMPLING_MODE` | [Discrete string options](#discrete-string-options): `interval` vs `scene`. |
| `FRAME_INTERVAL_SECONDS` | Seconds between samples when mode is `interval` ([tuning](#turning-knobs-higher-vs-lower)). |
| `OCR_TESSERACT_CMD` | Tesseract executable (default `tesseract`) |

## Consistency and titles

| Variable | Purpose |
|----------|---------|
| `CONSISTENCY_CHECK_ENABLED` | Post-summary claim verification |
| `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` | When alignment score is **below** this, summary prompt adds cautious hedging ([tuning](#turning-knobs-higher-vs-lower)). |
| `REWRITE_CONTRADICTED_CLAIMS` | Rewrite summary when contradictions found |
| `TITLE_STYLE` | [Discrete string options](#discrete-string-options): `clean`, `heuristic`, `summary_heading`, `category`. |
| `ALLOW_FILENAME_DATE_PREFIX` | Prefix `YYYY-MM-DD - ` on note filenames |
| `NOTE_FILENAME_STYLE` | [Discrete string options](#discrete-string-options): `human` vs `slug`. |
| `MIGRATE_EXISTING_NOTE_FILENAMES` | One-time rename pass for Instagram Notes |
| `REWRITE_VAULT_LINKS_ON_MIGRATION` | Rewrite wiki-links after rename |

## Transcript and caption gates

| Variable | Purpose |
|----------|---------|
| `TRANSCRIPT_GATE_ENABLED` | Block low-signal transcripts |
| `TRANSCRIPT_MIN_WORDS` | Minimum word count ([tuning](#turning-knobs-higher-vs-lower)) |
| `TRANSCRIPT_MIN_UNIQUE_WORDS` | Minimum unique words ([tuning](#turning-knobs-higher-vs-lower)) |
| `TRANSCRIPT_MIN_ALPHA_RATIO` | Alphabetic ratio heuristic ([tuning](#turning-knobs-higher-vs-lower)) |
| `TRANSCRIPT_GATE_ALLOW_FORCE` | Allow Discord “Try anyway” override |
| `CAPTION_CONTEXT_ENABLED` | Fetch/use caption metadata |
| `CAPTION_MISMATCH_GATE_ENABLED` | Gate on transcript vs caption mismatch |
| `CAPTION_MIN_WORDS` | Treat caption as “strong” if at least this many words ([tuning](#turning-knobs-higher-vs-lower)) |
| `TRANSCRIPT_CAPTION_MIN_OVERLAP` | Minimum keyword overlap ratio ([tuning](#turning-knobs-higher-vs-lower)) |
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
| `DISCORD_ETA_UPDATE_INTERVAL_SECONDS` | How often `/save` updates ETA in Discord ([tuning](#turning-knobs-higher-vs-lower)) |
| `ETA_BASE_SECONDS` | Fixed overhead in estimates ([tuning](#turning-knobs-higher-vs-lower)) |
| `ETA_PER_VIDEO_SECOND` | Per-second-of-video multiplier ([tuning](#turning-knobs-higher-vs-lower)) |
| `ETA_LLM_OVERHEAD_SECONDS` | Extra budget for LLM stages ([tuning](#turning-knobs-higher-vs-lower)) |
| `ETA_HISTORY_PATH` | JSON file for adaptive timing history |
| `ETA_HISTORY_WINDOW` | Max samples per stage |
| `ETA_MIN_SAMPLES` | Samples before history overrides defaults |
| `ETA_QUANTILE` | Quantile over past stage durations for conservative ETAs ([tuning](#turning-knobs-higher-vs-lower)) |

## `/saveall` limits

| Variable | Purpose |
|----------|---------|
| `SAVEALL_DEFAULT_MAX_MESSAGES` | Default scan depth ([tuning](#turning-knobs-higher-vs-lower)) |
| `SAVEALL_DEFAULT_MAX_NEW_LINKS` | Default cap on new links ([tuning](#turning-knobs-higher-vs-lower)) |
| `SAVEALL_HARD_MAX_MESSAGES` | Hard ceiling ([tuning](#turning-knobs-higher-vs-lower)) |
| `SAVEALL_HARD_MAX_NEW_LINKS` | Hard cap on new links ([tuning](#turning-knobs-higher-vs-lower)) |
| `SAVEALL_PROGRESS_EVERY` | Progress update interval ([tuning](#turning-knobs-higher-vs-lower)) |

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
