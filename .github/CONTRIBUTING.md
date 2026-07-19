# Contributing

Thanks for taking the time. This document covers the mechanics; the
architecture, the layer rules and the vocabulary live in
[AGENTS.md](../AGENTS.md) — read that before writing code.

## Setup

Requires Python 3.14, [uv](https://docs.astral.sh/uv/),
[just](https://just.systems/) and Docker (integration tests start Postgres via
testcontainers).

```sh
uv sync --group dev
uv run prek install --install-hooks   # lint + conventional commit-msg hooks
cp deploy/env.example .env        # then fill in MISTRAL_API_KEY
docker compose up -d postgres nats redis qdrant
just migrate
```

## The loop

```sh
just linter            # ruff format + ruff check + codespell
just static-analysis   # mypy + bandit + semgrep + import-linter
uv run pytest tests/unit -q          # fast, no Docker
uv run pytest -q                     # everything, needs Docker
```

All four must be clean before a PR. `just test-ci` reproduces exactly what CI
runs, including the coverage report.

## Conventions worth knowing up front

- **No `from __future__ import annotations`.** PEP 649 handles it, and dishka,
  adaptix and pydantic resolve constructor annotations at runtime — moving a
  parameter type under `if TYPE_CHECKING` breaks the container at startup.
  `TC001`/`TC002`/`TC003` are disabled deliberately; do not "fix" them.
- **Accept ruff's autofixes; do not silence a rule.** If a rule is genuinely
  wrong for a file, add a scoped `per-file-ignores` entry with a comment saying
  why.
- **Fixtures live only in `conftest.py`.** Builders go in
  `tests/unit/factories/`, stubs in `tests/unit/stubs/`.
- **Integration tests name ports, never implementations.** A test that
  constructs `SqlAlchemyOutboxGateway(session)` is a test of SQLAlchemy and
  breaks the day the technology does.
- **Do not test libraries.** Test the decisions we made.
- Every new error must be added to `ExceptionHandler._ERROR_MAPPING`; an
  unmapped error answers 500 on purpose.

## Commits and pull requests

Commit messages and PR titles follow
[Conventional Commits](https://www.conventionalcommits.org/) — enforced by the
`conventional-pre-commit` hook locally and by the PR Title workflow on GitHub.

```
feat: adding presentation layer for processing data
fix: replacing deprecated ORJSONResponse in exception handler
test: adding statistics, worker flow and config loader tests
```

Fill in the pull request template, including the "What I did not verify"
section. Reporting that something is untested is useful; implying it works is
not.

## Migrations

```sh
just migration "add query logs table"   # autogenerate
just migrate                            # apply
```

Revisions live in dated subdirectories, which is why `alembic.ini` sets
`recursive_version_locations = true`. Check the generated revision by hand —
imperative mappings and autogenerate do not always agree.
