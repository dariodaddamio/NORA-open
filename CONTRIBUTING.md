# Contributing to NORA

Thanks for helping improve NORA. This repository (**NORA-open**) is the public mirror of the project: application code and docs, without personal vaults or secrets.

## Before you open a PR

- **Do not** commit `.env`, Discord tokens, cookies, `vault/`, `processed.json`, or paths to your machine.
- Match the existing style in `bot.py` and `process_link.py` (formatting, typing, minimal churn).
- **Tests:** the public mirror may not include a `tests/` tree (see [docs/open-private-workspace.md](docs/open-private-workspace.md)). Describe how you verified your change (manual `/save`, logs, or local tests you ran).
- **Docs:** user-visible behavior or new env vars should update `README.md`, `docs/`, and `.env.example` when relevant.

## How to contribute

1. **Fork** [NORA-open](https://github.com/dariodaddamio/NORA-open) and create a branch.
2. Make focused commits with clear messages (imperative mood is fine, e.g. `fix(bot): handle empty URL`).
3. Open a **pull request** against `main` with a short summary of what changed and why.
4. Link an **issue** if one exists, or open an issue first for larger design changes.

## Code of conduct

Be respectful and constructive. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing, you agree your contributions are licensed under the same terms as this project ([LICENSE](LICENSE)).
