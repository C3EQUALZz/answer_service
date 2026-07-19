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
  uv run --active --frozen codespell -L Dependant,dependant,selectin,aadd

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
  uv run --active --frozen pytest --cov=src/answer_service --cov-report=term-missing

[doc("Unit tests only (no Docker required)")]
[group("tests")]
test-unit *params:
  uv run --active --frozen pytest tests/unit {{params}}

[doc("Integration tests only (needs Docker)")]
[group("tests")]
test-integration *params:
  uv run --active --frozen pytest tests/integration {{params}}

# Emits coverage.xml and junit.xml, which sonar-project.properties points at.
[doc("Run the full suite the way CI does")]
[group("tests")]
test-ci:
  uv run --active --frozen pytest --cov=src/answer_service --cov-report=xml --cov-report=term-missing --junitxml=junit.xml

[doc("Everything CI runs, in CI's order")]
[group("tests")]
ci: linter static-analysis test-ci

# Docker
[doc("Build the production image")]
[group("docker")]
docker-build:
  docker build -f deploy/prod/answer_service/Dockerfile -t answer-service:local .

# --env-file is not optional: `env_file:` only injects variables into the
# containers, while ${VAR:?} interpolation in the compose file itself reads the
# project env file. Without it the credentials resolve empty.
[doc("Start the local environment (postgres, nats, redis, qdrant, app)")]
[group("docker")]
up *params:
  docker compose --env-file .env.dev up -d {{params}}

[doc("Start only the backing services, for running the app on the host")]
[group("docker")]
up-deps:
  docker compose --env-file .env.dev up -d postgres nats redis qdrant

[doc("Stop the local environment")]
[group("docker")]
down *params:
  docker compose --env-file .env.dev down {{params}}

[doc("Tail the logs of the application services")]
[group("docker")]
logs *params:
  docker compose --env-file .env.dev logs -f {{params}}

[doc("Validate the compose file against .env.dev")]
[group("docker")]
compose-config:
  docker compose --env-file .env.dev config --quiet

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
