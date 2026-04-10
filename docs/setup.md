# Setup

Back to main [README](../README.md)

See also [open-private-workspace.md](open-private-workspace.md) for how the public mirror relates to a private dev tree and what never belongs on a public remote.

## Prerequisites

- Python 3.10+
- `ffmpeg` on PATH (`ffmpeg -version`)
- Discord bot application and token
- Recommended: [OpenRouter](https://openrouter.ai/) API key for cloud LLM, or [Ollama](https://ollama.com/) for local LLM
- Optional (visual path): [Tesseract](https://github.com/tesseract-ocr/tesseract) for OCR on keyframes (`tesseract --version` or set `OCR_TESSERACT_CMD`)

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with at least `DISCORD_TOKEN`, `OBSIDIAN_VAULT_PATH`, and `OPENROUTER_API_KEY` (or rely on Ollama without the key). See [configuration.md](configuration.md).

## Discord Developer Portal

- **OAuth2 scopes:** `bot`, `applications.commands`
- **Bot permissions:** View Channels, Send Messages, Read Message History
- **Privileged Gateway Intent:** enable **Message Content Intent** under Bot settings (needed for `/saveall` history scans)

Re-invite the bot after scope or permission changes.

## Run

```powershell
.\.venv\Scripts\python bot.py
```

On startup, slash commands sync. Use `/save` with an Instagram URL or `/saveall` in a channel.

## Shared servers: where notes live

NORA is **not** a hosted multi-user service. **Whoever runs `bot.py`** owns the pipeline:

- All notes and assets go to **`OBSIDIAN_VAULT_PATH` on that host** (their disk).
- **Other people in the same Discord server** can use slash commands too, but they **do not** receive copies of the Obsidian files—only what the bot posts in Discord (e.g. “Saved note: `...\something.md`”).
- To let someone else use the same vault, you must **share access yourself** (Obsidian Sync, cloud folder, git, NAS, etc.) or they run **their own** bot + vault on their machine.

If several members trigger `/save` at once, jobs can run in parallel on the host; see [troubleshooting.md](troubleshooting.md) if you need behavior details.

## Multi-device

1. Clone the repo on each machine; use a **local** `.env` per machine (do not commit secrets).
2. Point `OBSIDIAN_VAULT_PATH` at that machine’s vault (or sync the vault separately).
3. Run **one** active bot instance at a time to avoid duplicate processing.

## Daily usage

- `/save url:https://www.instagram.com/reel/...`
- `/saveall` — optional parameters: `max_messages`, `max_new_links`, `oldest_first` (see `SAVEALL_*` in [.env.example](../.env.example))
