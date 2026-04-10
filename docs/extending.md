# Extending NORA

Back to main [README](../README.md) · [All docs](README.md)

## Hooks

| Hook | Primary location | Idea |
|------|------------------|------|
| Slash commands, Discord UX | `bot.py` | New commands, views, progress messages |
| Pipeline: download, transcribe, gates, LLM, writers | `process_link.py` | New sources, prompts, stages, STT backend swap |
| Vision / pixels | `process_link.py` (`_llm_chat_completion`, `classify_video`, etc.) | Today only **OCR text** reaches the LLM; true vision needs image+text API calls (e.g. OpenRouter vision models)—see [stack-and-costs.md](stack-and-costs.md#keyframes-and-ocr-limits-and-improvements) |
| Categories and tag rules | `taxonomy.json` (copy from `taxonomy.example.json` if you want a starter file; not shipped in public mirror) | Your vocabulary and synonyms; `TAXONOMY_MODE=auto` appends new categories |
| Note shape and graph links | Writers in `process_link.py` (`_write_graph_notes`, etc.) | Extra folders, frontmatter, sections |
| Quality / gates | Env vars + `assess_*` / `build_obsidian_payload` | Stricter transcript or caption rules |

## Files of interest

- `bot.py` — Discord entrypoints
- `process_link.py` — pipeline, OCR + text LLM stages, note writers
- `taxonomy.example.json` — starter taxonomy (safe to ship publicly); copy to `taxonomy.json` to customize
- `taxonomy.json` — your categories (optional; built-in defaults if absent; omitted from public mirror export)
- `.env.example` — env template
- `processed.json` — URL dedupe (local; do not publish with private vault)
