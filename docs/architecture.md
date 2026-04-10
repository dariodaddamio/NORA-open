# Architecture

Back to main [README](../README.md) · [How it works (diagrams)](how-it-works.md)

## Command layer (`bot.py`)

- Registers Discord slash commands and lightweight orchestration.
- `/save` processes one URL.
- `/saveall` scans channel history, extracts Instagram URLs, skips duplicates and `processed.json` entries, runs the pipeline per new link.
- Concurrency: one `/saveall` job per server at a time; progress every `SAVEALL_PROGRESS_EVERY` items.

## Processing pipeline (`process_link.py`)

For each new URL (typical `PIPELINE_MODE=graph`):

1. **Download** — `python -m yt_dlp` (portable across venv paths).
2. **Optional metadata** — caption/title when caption context is enabled.
3. **Keyframes + OCR** (if `VISUAL_CONTEXT_ENABLED`) — `ffmpeg` sampling, **Tesseract** OCR on JPEGs; **only OCR text** (not raw images) is fed into later LLM prompts. Rank frames, build visual context string and OCR–transcript alignment. Selected frames are still saved under `Assets/Instagram/...` for the note.
4. **Audio extraction** — `ffmpeg` to mono 16 kHz WAV.
5. **Transcription** — `faster-whisper` (local).
6. **Gates** — transcript quality; transcript–caption alignment; outcomes:
   - Normal (transcript usable)
   - Caption-primary (weak transcript, strong caption)
   - Blocked → Discord message + optional **Try anyway** (`TRANSCRIPT_GATE_ALLOW_FORCE`)
7. **Knowledge enrichment** — classify taxonomy, extract entities, generate markdown summary (**text-only** LLM calls: transcript, caption, and OCR-derived “visual context”); optional verification and contradiction rewrite. If `TAXONOMY_MODE=auto`, a novel sanitized category is merged into `TAXONOMY_PATH` and taxonomy is reloaded before entity extraction and summary.
8. **Graph write** — video note, topic notes, entity notes, category index; persist selected frames under `Assets/Instagram/...`.

If `PIPELINE_MODE=basic`, pipeline collapses to single-note summarization (`summary:basic` LLM stage).

## Gate and decision matrix

1. **Transcript usefulness** — word count, unique words, alpha ratio, repetition/noise heuristics.
2. **Transcript–caption alignment** — keyword overlap vs caption/title.
3. **Decision** — normal, caption-primary, or gate + Try anyway.

## AI routing

- **OpenRouter** when `OPENROUTER_API_KEY` is set.
- **Ollama** when the key is absent: requests go to `http://localhost:11434/api/generate` (host is **not** configurable via `.env` today).
- Prompts are size-bounded; malformed JSON may trigger a **repair** LLM pass, then safe fallbacks.

## LLM stages and logging

Each completion logs:

- `[LLM] START stage=<name> provider=<openrouter|ollama> model=<id>`
- `[LLM] DONE stage=<name> ... (<seconds>s)`
- `[LLM] FAIL stage=<name> ...`
- End of run: `[LLM] SUMMARY calls=<n> elapsed=<seconds>s stages=...`

**Graph mode — typical stages**

| Stage | When |
|-------|------|
| `classify` | Taxonomy classification |
| `entities` | Entity extraction |
| `summary` | Markdown summary |
| `title` | Note title via LLM (**only** when `TITLE_STYLE=clean`; otherwise titles are heuristic / summary heading / category without this stage) |
| `verify` | If `CONSISTENCY_CHECK_ENABLED` |
| `rewrite:contradictions` | If rewrite enabled and contradictions found |
| `repair:classification`, `repair:entities`, `repair:verification` | Malformed model output |
| `classify:fallback`, `entities:fallback` | Primary JSON path threw |

**Basic mode:** `summary:basic`.

Call counts vary: gates short-circuit failed runs; verification/rewrite/repair are conditional.

## Validation, normalization, and repair

- Category forced into allowed taxonomy (fallback `general`).
- Tags normalized to prefixed slugs; dedupe with stable order.
- Entities below `GRAPH_MIN_ENTITY_CONFIDENCE` dropped.
- Malformed classification/entities: repair pass, then safe defaults.
- Malformed verification: repair, then conservative counts.

## Idempotency

- `processed.json` maps `url -> note_path`.
- Skip if URL known and note file exists.
- Stale paths (e.g. after moving vault) may be repaired to `Instagram Notes/<same filename>` before reprocessing.

## Temp cleanup

- Per job: `temp/<job_id>/`.
- On success with default flags: job dir removed; empty `temp/` root removed.
- On failure with `KEEP_TEMP_ON_FAILURE=true`: artifacts kept for debugging.

## Consistency verification

When `CONSISTENCY_CHECK_ENABLED=true`:

- OCR/transcript alignment informs prompts; key claims from the summary are checked (`supported` / `uncertain` / `contradicted`).
- Metrics land in frontmatter and in `## Verification`.

If `REWRITE_CONTRADICTED_CLAIMS=true` and contradictions exist, the summary is rewritten and verification runs again.

## Transcript gate and Try anyway

Low-signal transcripts or caption mismatch (when enabled) can block processing. Discord can show **Try anyway** when `TRANSCRIPT_GATE_ALLOW_FORCE=true`, rerunning with `force_process`. Forced notes carry quality/caption flags and warning sections in the vault.
