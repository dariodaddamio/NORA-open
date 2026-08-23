# Contributing to NORA

Thanks for helping improve NORA. This repository ships the Discord bot and user documentation.

## Before you open a PR

- **Do not** commit `.env`, Discord tokens, cookies, `vault/`, `processed.json`, or paths to your machine.
- Match the existing style in `bot.py` and `process_link.py` (formatting, typing, minimal churn).
- **Tests:** describe how you verified your change (manual `/save`, logs, or local tests you ran).
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
