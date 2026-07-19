# CLAUDE.md

Project instructions live in **[AGENTS.md](AGENTS.md)** — read it before writing
any code. It is the single source of truth for architecture, conventions and
tooling, shared by every agent working on this repository.

This file adds only what is specific to working here interactively.

## Before you start

- `AGENTS.md` — architecture, layer rules, bounded contexts and their
  vocabulary, testing rules, mandatory commands. Use the terms it defines rather
  than inventing synonyms.

## Working agreements

- **Verify by running, not by reading.** This codebase has produced several bugs
  that typed clean and passed review: an Excel file that validated on upload and
  failed in the worker, a DI graph that failed only at container build, a route
  that raised only when FastAPI parsed it. Run the thing.
- **Report what actually happened.** If tests fail, say so and show the output.
  If something is unverified — no Docker, no API key, no live service — say
  which part is unverified rather than implying it works.
- **Prefer finishing over starting.** A port with no adapter, a handler with no
  registration, or a task name nobody registered is worse than not having built
  it, because it looks done.
- When a change touches an area listed under "Things that have bitten us" in
  `AGENTS.md`, re-read that entry first.

## Running things

Integration tests need Docker running (testcontainers starts Postgres).

```sh
uv run pytest tests/unit -q          # fast, no Docker
uv run pytest tests/integration -q   # needs Docker
uv run pytest -q                     # everything
```

Scratch scripts go in the session scratchpad directory, never in the repo.

## Reviewing your own work

Before saying a task is done:

1. `just lint` — clean
2. `just mypy` — clean
3. `uv run pytest -q` — green, and say how many tests ran
4. `just import-linter` — contracts kept, if you moved a module
5. State plainly what you did **not** verify
