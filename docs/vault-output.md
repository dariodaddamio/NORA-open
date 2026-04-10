# Vault output

Back to main [README](../README.md)

## Folder layout

Inside `OBSIDIAN_VAULT_PATH`:

| Path | Role |
|------|------|
| `Instagram Notes/` | Primary video note per reel |
| `Topics/` | Hub notes per normalized topic |
| `Entities/` | Hub notes per entity (tool, concept, etc.) |
| `Indexes/` | Category MOC notes (e.g. `Category - Design.md`) |
| `Assets/Instagram/` | Persisted keyframes for `## Visual Highlights` |

## Video note sections

- YAML frontmatter (metadata for queries/plugins)
- `## TL;DR`, `## Key Ideas`, `## Actionable Takeaways`
- `## Category`, `## Topics`, `## Entities` (wiki-links)
- `## Visual Highlights` (if frames selected)
- `## Verification` (if consistency check enabled)
- `## Context Source` / quality warnings when relevant
- `## Source`, `## Transcript`

## Example (one reel)

- `Instagram Notes/Topographic Effect Image Editing Workflow.md`
- `Topics/topography-effect.md`
- `Entities/photoshop.md`
- `Indexes/Category - Design.md`
- `Assets/Instagram/2026-04-10-topographic-effect-image-editing-workflow/frame-01.jpg`

## Frontmatter (video note)

Common fields include:

- `type`: `video-note`
- `source_url`, `created_at`
- `title_generated_by` — `llm` (title LLM, `TITLE_STYLE=clean`), `heuristic`, `category`, `summary_heading`, or `fallback` (includes failed LLM title, failed summary-heading pick, or repair short-circuit)
- `alignment_score`
- `verification_supported_count`, `verification_uncertain_count`, `verification_contradicted_count`
- `category`, `subtopics`, `entities`, `tags`, `status`
- Transcript/caption quality flags when gated or caption-primary

## Naming

- Default: clean title-based filenames (e.g. `Color Swatching Guide.md`).
- `ALLOW_FILENAME_DATE_PREFIX=false` by default.
- `NOTE_FILENAME_STYLE=human` (spaces) or `slug`.
- Collisions: numeric suffixes `(2)`, `(3)` for different source URLs.
- Migration: `MIGRATE_EXISTING_NOTE_FILENAMES` renames existing Instagram Notes once; `REWRITE_VAULT_LINKS_ON_MIGRATION` fixes wiki-links; `processed.json` paths updated.

## Taxonomy

To customize categories and tags, **create** `taxonomy.json` at the **project root** (same directory as `bot.py`), or copy **`taxonomy.example.json`** from the repo as a starting point. If the file is missing, NORA uses built-in defaults from `process_link.py` (`_load_taxonomy`).

With **`TAXONOMY_MODE=auto`**, when the classifier returns a category that is not in the loaded list, NORA **sanitizes** it (slug-style `a-z`, `0-9`, hyphens) and **appends** it to `TAXONOMY_PATH`, then reloads taxonomy for the same run. If the file is at **`TAXONOMY_AUTO_MAX_CATEGORIES`** or the label is invalid, the note still saves but the category falls back to **`general`** (same as `static` mode). Concurrent bot processes with `auto` are best-effort only.

The **public mirror** repo typically does **not** include personal `taxonomy.json` (it is excluded from export); **`taxonomy.example.json`** is included as a template.

Shape:

- `categories` — top-level buckets
- `tag_prefixes` — e.g. `topic`, `domain`, `tool`, `format`
- `synonyms` — normalization (e.g. `artificial intelligence` → `ai`)

Tips: keep categories lowercase and stable; prefer synonyms over duplicate categories; keep categories broad.

## Visual context

When enabled: keyframes via `ffmpeg`, OCR via **Tesseract** (not a learned vision model), rank by text richness and time spread, embed top 1–3 images in the note. The LLM stages only see **OCR text** in their prompts, not the JPEG pixels. If OCR fails, transcript-only context still runs. Limits and upgrade paths (stronger text models, vision APIs, forks): [stack-and-costs.md](stack-and-costs.md#keyframes-and-ocr-limits-and-improvements).
