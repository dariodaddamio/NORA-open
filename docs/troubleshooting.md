# Troubleshooting

Back to [README](../README.md)

## Commands do not appear

- Ensure OAuth2 scope `applications.commands` was used when inviting the bot.
- Wait ~30–60 seconds after `bot.py` startup for global command sync.

## Failed to process link

- Verify `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`, or Ollama running with `OLLAMA_MODEL`.
- Run `ffmpeg -version` and `python -m yt_dlp --version` in the **same** venv as the bot.

## Instagram download issues

- Update `yt-dlp` (`pip install -U yt-dlp`).
- Set `YTDLP_COOKIES_FROM_BROWSER` or `YTDLP_COOKIES_FILE` if Instagram blocks anonymous access.

## Notes not appearing in the vault

- `OBSIDIAN_VAULT_PATH` must point to the vault **root**, not `.obsidian`.
- Check `processed.json` for stale `url -> path` entries if you moved the vault.
- Restart the bot after changing `.env`.

## Graph notes look too sparse

- Lower `GRAPH_MIN_ENTITY_CONFIDENCE` (e.g. `0.55` → `0.40`).
- Raise `MAX_TOPICS_PER_VIDEO`.

## Visual highlights missing

- `tesseract --version` or set `OCR_TESSERACT_CMD`.
- `VISUAL_CONTEXT_ENABLED=true`
- Increase `MAX_KEYFRAMES_ANALYZED`; ensure `MAX_IMAGES_PER_NOTE` ≥ 1.

## Temp folder still exists after success

- Other jobs may still use `temp/`; root is only removed when empty.
- Set `KEEP_TEMP=false` if you expect cleanup (default in `.env.example`).

## Summaries miss on-screen content

- Enable visual path and try `FRAME_SAMPLING_MODE=scene` or higher `MAX_KEYFRAMES_ANALYZED`.

## Weak or hallucinated claims

- `CONSISTENCY_CHECK_ENABLED=true`
- Tune `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` (higher = stricter).
- `REWRITE_CONTRADICTED_CLAIMS=true` to auto-fix contradictions.
- Inspect `verification_*` frontmatter fields.

## Filename still has date prefix or wrong style

- `ALLOW_FILENAME_DATE_PREFIX=false`, `TITLE_STYLE=clean`, `NOTE_FILENAME_STYLE=human`.

## Migration did not rename old notes

- `MIGRATE_EXISTING_NOTE_FILENAMES=true`
- Remove `.filename_migration_done` in the vault root to force another pass (if your build uses that marker).

## Quality tuning playbook

**Recommended baseline**

- `CONSISTENCY_CHECK_ENABLED=true`
- `REWRITE_CONTRADICTED_CLAIMS=true`
- `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE=0.25`
- `VISUAL_CONTEXT_ENABLED=true`

**If notes are too cautious**

- Lower `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` (e.g. `0.20`).

**If notes still hallucinate**

- Raise `MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE` (e.g. `0.35`–`0.45`).
- Increase `MAX_KEYFRAMES_ANALYZED`.
- Keep `REWRITE_CONTRADICTED_CLAIMS=true`.

See [configuration.md](configuration.md) for all variables.
