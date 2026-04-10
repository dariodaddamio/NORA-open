# NORA - Notes for Obsidian from Reels using AI

A local Discord Bot pipeline to turn your doom scrolling into an Obsidian knowledge base.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/chat-Discord-5865F2.svg)](https://discord.com/developers/applications)
[![Obsidian](https://img.shields.io/badge/notes-Obsidian-7C3AED.svg)](https://obsidian.md/)

## Why NORA

- **Motivation:** The Saved Collections feature in Instagram is so hidden and disorganized that I've resorted to sharing links of Instagram reels in my private Discord server, in hopes of referring to them later on... Of course, this was rarely the case. I would end up lost in a sea of links, which were supposed to be organized categories, frantically trying to find a tutorial about Photoshop, a movie recommendation, or even a recipe.
- **Outcome:** This eventually inspired NORA, a way to summarize what's in those reels into a structured, interconnected Obsidian vault.
- **Non-goals:** NORA is not a full social archive, hosted backup service, or guaranteed legal/compliance layer for third-party content — you own your vault and tooling choices.
- **Expansion:** Despite the local limitations, you're free to build on top of this architecture—hosting, sync, extra automation, different models, or anything else your workflow needs.

## Quickstart

**Goal:** run the bot on your PC so **Discord slash commands** (e.g. `/save`, `/saveall`) run the pipeline and write notes into a folder you choose (typically an [Obsidian](https://obsidian.md/) vault). Use **[NORA-open](https://github.com/dariodaddamio/NORA-open)** or any clone; remember to keep **`.env` and your vault off GitHub.**

**Who gets the files:** markdown and assets are written only on **the machine that runs `bot.py`**, under **`OBSIDIAN_VAULT_PATH`**. Everyone else in the server sees **Discord replies** (paths, errors, progress)—not your vault—unless you share that folder yourself (sync, git, network drive, etc.). Details: [docs/setup.md#shared-servers-where-notes-live](docs/setup.md#shared-servers-where-notes-live).

### 0. What you need installed

| Requirement | Why |
|-------------|-----|
| **Python 3.10+** | Runs the bot and pipeline |
| **[ffmpeg](https://ffmpeg.org/)** on your PATH | Extracts audio from reels (`ffmpeg -version` should work) |
| **A Discord bot** | Slash commands and replies |
| **A folder for notes** | `OBSIDIAN_VAULT_PATH` — vault **root** folder (the one that contains or will contain `Instagram Notes/`, not the `.obsidian` folder) |
| **An LLM (pick one)** | **OpenRouter** (API key, optional free models) **or** **Ollama** (local, no OpenRouter key) |

First run will download Whisper weights and can take a few minutes. Optional extras (OCR, stronger models): [docs/setup.md](docs/setup.md).

**Note:** By default, “visual” context is **keyframes + Tesseract OCR**—the LLM gets **OCR text** in its prompts, not images through a vision model, so results can be thin or noisy on busy or stylized reels. Install Tesseract for that path (see [docs/setup.md](docs/setup.md)); disable it with `VISUAL_CONTEXT_ENABLED=false` in `.env` ([docs/configuration.md#visual-keyframes-and-ocr](docs/configuration.md#visual-keyframes-and-ocr)). Limits and improvement options: [docs/stack-and-costs.md#keyframes-and-ocr-limits-and-improvements](docs/stack-and-costs.md#keyframes-and-ocr-limits-and-improvements).

### 1. Clone and install

```powershell
git clone https://github.com/dariodaddamio/NORA-open.git
cd NORA-open
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

*(On macOS/Linux, use `source .venv/bin/activate` instead of `Activate.ps1`.)*

### 2. Create a Discord bot and token

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → name it → open **Bot** → **Add Bot** → under **Token**, **Reset Token** and copy it (this value is `DISCORD_TOKEN` in `.env`). **Never commit it.**
2. In **Bot**, enable **Message Content Intent** (needed for `/saveall` channel scans).
3. Open **OAuth2 → URL Generator**: scopes **`bot`** and **`applications.commands`**. Choose bot permissions (at minimum: View Channels, Send Messages, Read Message History). Open the generated URL, pick your server, invite the bot.

Screenshots, re-invite, and permission detail: **[docs/setup.md](docs/setup.md)**.

### 3. Point NORA at your vault folder

Create or choose a folder (e.g. `C:\Users\you\Documents\MyVault`). Put its **absolute path** in `.env` as `OBSIDIAN_VAULT_PATH`. The bot will create `Instagram Notes/` and related folders there on first success.

### 4. Add an LLM (OpenRouter *or* Ollama)

**Option A — OpenRouter (cloud, includes free models)**

1. Sign up at [openrouter.ai](https://openrouter.ai/), then open **[Keys](https://openrouter.ai/keys)** and create an API key.
2. In `.env`, set `OPENROUTER_API_KEY=` to that key (no quotes needed unless your editor adds them).
3. Leave `OPENROUTER_MODEL=openrouter/free` to start (free-tier availability changes over time; you can swap the id for any model listed on OpenRouter). Billing and limits are on their site.

**Option B — Ollama (local, no OpenRouter)**

1. Install [Ollama](https://ollama.com/) and pull a model, e.g. `ollama pull llama3.1`.
2. In `.env`, **leave `OPENROUTER_API_KEY` empty** (or delete the value after the `=`).
3. Set `OLLAMA_MODEL` to match what you pulled (e.g. `llama3.1`; the pipeline normalizes to `llama3.1:latest` when needed). Keep Ollama running while you use the bot.

More on cost vs privacy: **[docs/stack-and-costs.md](docs/stack-and-costs.md)**. All env vars: **[docs/configuration.md](docs/configuration.md)**.

### 5. Run the bot

```powershell
.\.venv\Scripts\python bot.py
```

Wait until the process stays running with no traceback. Slash commands can take **~30–60s** after startup to appear in Discord.

### 6. Try it

In your server, run **`/save`** and paste an Instagram reel URL, or **`/saveall`** in a channel to scan history. If something fails, start with **[docs/troubleshooting.md](docs/troubleshooting.md)**.

## Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/setup.md](docs/setup.md) | Prerequisites, install, Discord portal detail, run, multi-device |
| [docs/how-it-works.md](docs/how-it-works.md) | High-level flow diagrams; link into the pipeline |
| [docs/architecture.md](docs/architecture.md) | Pipeline stages, gates, LLM stages, idempotency, temp |
| [docs/configuration.md](docs/configuration.md) | Environment variables, discrete modes (`TITLE_STYLE`, pipeline, OCR), tuning notes |
| [docs/vault-output.md](docs/vault-output.md) | Vault folders, note sections, frontmatter, taxonomy |
| [docs/stack-and-costs.md](docs/stack-and-costs.md) | Local vs cloud LLM, cost tiers, OCR limits vs real vision, extension points |
| [docs/open-private-workspace.md](docs/open-private-workspace.md) | NORA-open vs private workspace, mirror excludes, staying safe |
| [docs/extending.md](docs/extending.md) | Where to hook code and main files |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common failures and quality tuning |

**Index:** [docs/README.md](docs/README.md)

**Issues and ideas:** [NORA-open issues](https://github.com/dariodaddamio/NORA-open/issues) — bug reports and feature suggestions welcome there.
