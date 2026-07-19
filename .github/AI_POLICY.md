# AI Policy

AI assistants are used on this repository, and that is fine. The rules exist so
that a reviewer can trust a diff without having to guess how it was produced.

## For contributors

- **You own the diff.** Whether you typed it or generated it, you are the author
  and you answer for it in review.
- **Run it.** This codebase has produced several bugs that typed clean and
  passed review: an Excel file that validated on upload and failed in the
  worker, a DI graph that failed only at container build, a route that raised
  only when FastAPI parsed it. `just linter`, `just static-analysis` and the
  test suite are the minimum bar.
- **Report what actually happened.** If tests fail, say so and show the output.
  If a part is unverified — no Docker, no API key, no live service — say which
  part. The pull request template has a section for exactly this.
- **Do not paste secrets into a model.** `.env` files, API keys and production
  connection strings stay out of prompts. The config loaders mark secret fields
  so a startup failure does not log them; do not undo that by hand.
- Disclosure of AI assistance is welcome but not required. Unrunnable or
  unreviewed generated code is not, regardless of disclosure.

## For agents

Agent configuration is checked in and is the source of truth:

- [`AGENTS.md`](../AGENTS.md) — architecture, layer rules, bounded contexts,
  testing rules, mandatory commands. Shared by every agent.
- [`CLAUDE.md`](../CLAUDE.md) — what is specific to working here interactively.
- `.claude/` — permissions, skills and subagents.
- `.codex/` — Codex configuration.

An agent that changes behaviour should update the relevant document in the same
pull request. In particular, a new class of bug belongs in the "Things that have
bitten us" section of `AGENTS.md` — that section is how the next agent avoids
repeating it.

## Automated review

CodeRabbit reviews pull requests (`.coderabbit.yaml`). Its comments are advice,
not an approval: a human code owner still reviews and merges.
