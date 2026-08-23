# Workspace layout

The public git mirror ships the Discord bot (`bot.py`, `process_link.py`), install docs, and `tools/topic_merge.py`. Publish copies the tree through [`.public-export-ignore`](../.public-export-ignore).

The development tree adds vault data, harness wiring, brain intake, tests, and agent plans. Those paths are listed in the ignore file.

Keep local env files and `processed.json` out of git remotes. Use your own Discord token; do not commit it.
