# Open vs private

**NORA-private:** full tree + vault + Opifex wiring + tests.

**NORA-open:** Discord slash bot plus public maintenance helpers. Publish via rsync + [`.public-export-ignore`](../.public-export-ignore).

Ships: `bot.py`, `process_link.py`, user docs, `tools/topic_merge.py`, and starter JSON templates (`topic-merge-map.example.json`, `topic_aliases.example.json`, `taxonomy.example.json`).

Exclude: secrets, vault, Opifex (`opifex.config.mjs`, `package.json`, `AGENTS.md`, brain-intake docs, `.opifex`, …), `tools/brain_ingest.py`, `.github` publish CI, `tests/`.

Keep local env files and `processed.json` off public remotes. Own Discord token; never commit it.
