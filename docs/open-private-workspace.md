# Open source vs private workspace

Back to main [README](../README.md) · [All docs](README.md)

This project is often maintained as **NORA-private** (full dev tree) with an optional sanitized mirror (**NORA-open**) for sharing code without personal data.

## What the public mirror includes

Publishing uses `rsync` with **`--exclude-from=.public-export-ignore`** (in the **private** repo). The ignore file is **intentionally copied** into **NORA-open** as well, so the list below stays verifiable from a public clone (it is not a secret—only path names).

Paths **omitted** from the mirror (see [`.public-export-ignore`](../.public-export-ignore) in either tree):

- **Secrets and local state:** `.env`, `.venv`, `processed.json`, `eta-history.json` (adaptive ETA timings; not the committed **`eta-history.example.json`** template)
- **Personal content:** `vault/`, `NORA.md`, `agent-transcripts`
- **CI that publishes the mirror:** `.github/` (workflows typically live in the private repo only)
- **Tests and tooling:** `tests/`, `.cursor/`
- **Personal taxonomy:** `taxonomy.json` (defaults in code if absent). **`taxonomy.example.json`** is **not** ignored so it ships as a copy-paste starter.

**NORA-open** clones get application code, **`docs/`**, **`.env.example`**, **`.public-export-ignore`**, **`eta-history.example.json`** (empty ETA history shape), **`taxonomy.example.json`**, and OSS meta files (**`LICENSE`**, **`CONTRIBUTING.md`**, **`CODE_OF_CONDUCT.md`**). **NORA-private** may include a vault, cookies, transcripts, the **`tests/`** tree, and the full **`.github/`** publish workflow.

## Tests (private tree only)

The **`tests/`** directory is **excluded** from **NORA-open** (see [`.public-export-ignore`](../.public-export-ignore)). A **private** checkout may still carry a test suite the maintainer runs locally; that tree is not published with the mirror.

You can **write and run your own tests** whenever you want—for example, a small **`unittest`** that imports `process_link` and checks that a taxonomy category string is **sanitized or rejected** the way you expect. The bot does not depend on tests to run.

## Using NORA locally without leaking your vault

- Keep **`.env`**, **`vault/`**, and **`processed.json`** out of any public remote.
- Create your **own** Discord application and bot token; never commit `DISCORD_TOKEN`.
- Point **`OBSIDIAN_VAULT_PATH`** at a vault directory on your machine (or a path you control). Open clones do not include your notes.

## Updating NORA without publishing secrets

If you maintain a private fork and push a sanitized mirror to **NORA-open**, rely on **`.public-export-ignore`** and review diffs before publish so personal paths and tokens never land on the public repo.
