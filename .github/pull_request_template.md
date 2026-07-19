## Summary

<!-- What does this PR do, and why? -->

## Motivation / context

<!-- Link issues; explain the design choice if it is not obvious from the diff. -->

## Changes

-

## Checklist

- [ ] `just linter` is clean (ruff format, ruff check, codespell)
- [ ] `just static-analysis` is clean (mypy, bandit, semgrep, import-linter)
- [ ] `uv run pytest -q` is green — state how many tests ran
- [ ] New behaviour is tested: unit tests for domain / application, integration
      tests for anything crossing a process boundary
- [ ] Fixtures live in `conftest.py`, builders in `tests/unit/factories/`,
      stubs in `tests/unit/stubs/`
- [ ] Integration tests resolve **ports** from the container, never adapters
- [ ] Dependency rule preserved: `presentation → application → domain`
- [ ] Every new error is registered in `ExceptionHandler._ERROR_MAPPING`
- [ ] A schema change ships with an alembic revision, and `just migrate` applies
      cleanly from scratch
- [ ] PR title follows Conventional Commits

## What I did not verify

<!-- No Docker, no API key, no live service — say which part is unverified
     rather than implying it works. -->
