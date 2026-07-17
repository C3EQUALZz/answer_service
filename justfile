# Cross-platform shell configuration
# Use PowerShell on Windows (higher precedence than shell setting)
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
# Use sh on Unix-like systems
set shell := ["sh", "-c"]


[doc("All command information")]
default:
  @just --list --unsorted --list-heading $'Dishka-jobify  commands…\n'

# Linter
[doc("Ruff format")]
[group("linter")]
ruff-format *params:
  uv run --active --frozen ruff format {{params}}

[doc("Ruff check")]
[group("linter")]
ruff-check *params:
  uv run --active --frozen ruff check --exit-non-zero-on-fix {{params}}

_codespell:
  uv run --active --frozen codespell -L Dependant,dependant,selectin

[doc("Check typos")]
[group("linter")]
typos: _codespell
  uv run --active --frozen prek run --all-files typos

[doc("Linter run")]
[group("linter")]
linter: ruff-format ruff-check _codespell

# Static analysis
[doc("Mypy check")]
[group("static analysis")]
mypy *params:
  uv run --active --frozen mypy {{params}}

[doc("Bandit check")]
[group("static analysis")]
bandit:
  uv run --active --frozen bandit -c pyproject.toml -r src

[doc("Semgrep check")]
[group("static analysis")]
semgrep:
  uv run --active --frozen semgrep scan --config auto --error --skip-unknown-extensions src

[doc("Zizmor check")]
[group("static analysis")]
zizmor:
  uv run --active --frozen zizmor .

[doc("Architecture checks with import-linter")]
[group("static analysis")]
import-linter *params:
  uv run --active --frozen lint-imports {{params}}

[doc("Static analysis check")]
[group("static analysis")]
static-analysis: mypy bandit semgrep import-linter

[doc("Run pytest with coverage")]
[group("tests")]
test:
  pytest --cov=src/answer_service --cov-report=term-missing

[doc("Pre-commit modified files")]
[group("pre-commit")]
pre-commit:
  uv run --active --frozen prek run

[doc("Pre-commit all files")]
[group("pre-commit")]
pre-commit-all:
  uv run --active --frozen prek run --all-files

# Migrations
[doc("Generate a new Alembic migration (usage: just migration 'add users table')")]
[group("migrations")]
migration msg:
  uv run --active dotenv -f .env.dev run -- alembic revision --autogenerate -m "{{msg}}"

[doc("Apply all pending Alembic migrations")]
[group("migrations")]
migrate:
  uv run --active dotenv -f .env.dev run -- alembic upgrade head

[doc("Roll back the last Alembic migration")]
[group("migrations")]
migrate-down:
  uv run --active dotenv -f .env.dev run -- alembic downgrade -1

[doc("Show current migration revision")]
[group("migrations")]
migrate-current:
  uv run --active dotenv -f .env.dev run -- alembic current