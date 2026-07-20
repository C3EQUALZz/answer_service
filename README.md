<h2 align="center">Answer Service</h2>

*A hybrid-search and RAG microservice over a question-answer catalog — keeps the
catalog in sync with an uploaded CSV/Excel file, indexes it for semantic and
lexical retrieval, and reports on the questions it could not answer.*

Built using the principles of Robert Martin (aka Uncle Bob) and Domain-Driven
Design (DDD).

<p align="center">
  <a href="https://github.com/C3EQUALZz/answer_service/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/C3EQUALZz/answer_service/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/C3EQUALZz/answer_service/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/C3EQUALZz/answer_service/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://codecov.io/gh/C3EQUALZz/answer_service"><img alt="Coverage" src="https://codecov.io/gh/C3EQUALZz/answer_service/branch/master/graph/badge.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.14-blue">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-green"></a>
</p>

---

## Overview

A customer uploads a spreadsheet of question-answer pairs. The service diffs it
against its catalog, applies only what changed, and projects the result into a
vector store. Users then search that catalog; every query is recorded, and the
ones that found nothing become a report of what the catalog is missing.

The file is the source of truth: a pair absent from an upload is deleted, and a
pair whose content is unchanged is skipped.

### Indexing flow

```
HTTP client  →  POST /api/v1/index/sync    (202 Accepted + task_id)
                    │
              file validated, stored, IndexingTask queued
                    │
                    ▼  (taskiq background task)
        mark_indexing_running        → status RUNNING, committed alone
                    │
              run_indexing           → one transaction:
                    │                   SourceFileReader  → rows
                    │                   SyncPlanner       → create/update/delete/skip
                    │                   QA catalog        ← applied
                    │                   domain events     → outbox
                    │
              (on failure) mark_indexing_failed → status FAILED, own transaction
                    │
                    ▼  (cron task, every minute)
              relay_outbox           → schedules one projection task per event
                    │
                    ▼
              upsert_qa_pair         → SearchIndexWriter → Qdrant
```

### Search flow

```
HTTP client  →  POST /api/v1/search
                    │
              QueryRecordingPipeline   ← starts the clock
                    │
              HybridSearchService
                    │
          ┌─────────┴──────────┐       (concurrent)
          ▼                    ▼
   DenseRetriever        LexicalRetriever
   (Qdrant vectors)      (PostgreSQL FTS)
   drops below an        drops below a share
   absolute cosine       of its own best match
          │                    │
          └─────────┬──────────┘
                    ▼
               RrfFusion            → one ranking, rank-based
                    │
                    ▼
          QACatalogQueryGateway     → joins the text, drops what is gone
                    │
                    ▼
              QueryRecordingPipeline → query log (statistics, gap report)
```

Each retriever drops its own weak matches before fusion. Fused scores are
positional, so they carry no relevance signal — a floor applied after fusion
could not tell a good match from a bad one, and the gap report would never fire.

The two are filtered differently because their scores mean different things. A
cosine similarity is a property of the embedding model, so an absolute floor
keeps its meaning as the catalog grows. `ts_rank_cd` is not: it rises with the
number of matched terms, so the same pair scores 1.4 for "orders" and 3.2 for
"how do I track my order". The lexical side is therefore *ranked* relative to
the best match for its own query, which needs no recalibration at any size.

Ranking relative to the best cannot refuse, though — the best always scores 1.0
against itself — so a query matching nothing meaningful is still answered from
its best piece of junk. The lexical side carries a second, absolute floor for
that: the question is weighted above the answer in the search vector, and the
floor sits between the two, so a pair that merely brushed one word of answer
prose is not an answer.

The floors decide which candidates compete; the fusion weights decide how much
each retriever's opinion counts once they do. Dense is weighted 2:1 because
lexical terms are OR-ed, so a pair sharing one word of a natural question would
otherwise outrank the pair the embedding model put first. The ratio is swept
against `tests/quality`, where it moved top-1 accuracy from 69% to 80%.

### Ask flow

```
HTTP client  →  POST /api/v1/ask
                    │
              QueryRecordingPipeline
                    │
              HybridSearchService   → the same retrieval /api/v1/search runs
                    │
              nothing retrieved? ──→ answer: null, recorded as unanswered
                    │                 (the model is never called)
                    ▼
              AnswerGenerator       → Mistral, grounded in the retrieved pairs
                    │
                    ▼
              GroundedAnswer        → refuses to exist without sources
```

One dispatch, not two: retrieval lives in a shared application service rather
than in a second query, so a question is counted once in the statistics.

---

## Tech Stack

### Core Technologies

| Tool                    | Role                                                       |
|-------------------------|------------------------------------------------------------|
| **Python 3.14**         | Primary programming language                               |
| **uv**                  | Dependency and environment management                      |
| **FastAPI**             | HTTP REST API framework                                    |
| **SQLAlchemy asyncio**  | Async ORM for PostgreSQL, **imperative mapping**           |
| **asyncpg**             | PostgreSQL async driver                                    |
| **Qdrant**              | Vector store for QA pair embeddings                        |
| **LangChain + Mistral** | Embedding generation and answer synthesis                  |
| **polars**              | CSV / Excel parsing                                        |
| **Dishka**              | Dependency injection with APP/REQUEST scope management     |
| **TaskIQ + NATS**       | Background task queue (indexing, outbox relay, projection) |
| **Redis**               | TaskIQ result backend and schedule source                  |
| **dature**              | Type-safe configuration loading                            |
| **Adaptix**             | Data mapper (event serialization and domain/DTO mapping)   |
| **Alembic**             | Database schema migrations                                 |
| **structlog**           | Structured logging                                         |
| **uvicorn**             | ASGI server                                                |

### Architecture & Patterns

| Pattern / Concept      | Role                                                             |
|------------------------|------------------------------------------------------------------|
| **Clean Architecture** | Strict layer separation: domain → application → infrastructure   |
| **DDD**                | Aggregates, value objects, domain events, domain services        |
| **CQRS**               | Command and query handlers, separate command/query gateways      |
| **Ports & Adapters**   | All infrastructure accessed through application-layer interfaces |
| **Command Processor**  | An in-house mediator with a pipeline chain around every command  |
| **Outbox Pattern**     | At-least-once event delivery via a transactional outbox table    |
| **RRF**                | Reciprocal Rank Fusion of dense and lexical retrieval            |
| **Bounded Contexts**   | Modular monolith; only `ExternalId` crosses a boundary           |

### Code Quality

| Tool               | Role                                        |
|--------------------|---------------------------------------------|
| **Ruff**           | Formatting and linting (`select = ["ALL"]`) |
| **mypy**           | Static type checking (strict)               |
| **import-linter**  | Enforces the layer and module boundaries    |
| **bandit**         | Security vulnerability scanning             |
| **semgrep**        | Advanced static analysis                    |
| **codespell**      | Spell checking                              |
| **pytest**         | Testing framework (unit + integration)      |
| **testcontainers** | Real PostgreSQL for integration tests       |

---

## Features

- **Incremental catalog sync** — a CSV or Excel upload is diffed against the
  catalog by content fingerprint. Unchanged pairs are skipped, missing pairs are
  deleted, and re-uploading the same file costs nothing.
- **Format sniffing** — the parser decides CSV vs Excel from the file's bytes,
  not its name, because the filename does not survive the task queue.
- **Task lifecycle** — every synchronization run is tracked
  (`QUEUED → RUNNING → SUCCEEDED | FAILED`) with counters and a failure reason,
  and is pollable over HTTP while it runs.
- **Transactional outbox** — domain events are written in the same transaction
  as the state change they describe, then relayed by a cron task.
- **Idempotent projection** — the projector reads the pair's current state
  rather than trusting the event, and the Qdrant point id is a UUIDv5 of the
  external id, so replaying an event changes nothing.
- **Statistics** — catalog size per category, query volume, unanswered rate and
  average latency over a period.
- **Gap report** — the most frequent queries that returned nothing, paginated.
  This is the actionable half: each entry is an FAQ entry worth writing.
- **Hybrid ranking** — Reciprocal Rank Fusion combines the retrievers by rank,
  so their incompatible score scales never leak into the result.
- **Grounded answers** — `/api/v1/ask` writes an answer only from pairs it actually
  retrieved, cites them, and returns nothing at all when the catalog cannot
  ground one. An unanswerable question is a gap report entry, not an error.
- **Journalling by pipeline** — every query that serves a user is recorded by a
  pipeline registered against a marker type, so an endpoint cannot serve a
  request without counting it.

- **Stuck-run reaper** — a run whose worker died stays `RUNNING` forever,
  because the status is committed before the sync starts and nothing else ever
  touches it. A cron sweep fails runs older than an hour, so the status endpoint
  eventually tells the truth.

---

## HTTP API

Every versioned endpoint is served under `/api/v1`. Search and ask return a
`request_id` — the id the query is journalled under — so a caller can look their
own request up in `/api/v1/statistics/queries`, and a `duration_ms` measuring
how long they waited.

### Indexing

| Method | Path                       | Description                                     |
|--------|----------------------------|-------------------------------------------------|
| `POST` | `/api/v1/index/sync`       | Upload a source file; returns `202` + `task_id` |
| `GET`  | `/api/v1/tasks/{task_id}`  | Poll the status of a synchronization run        |

### Search

| Method | Path            | Description                                          |
|--------|-----------------|------------------------------------------------------|
| `POST` | `/api/v1/search`| Hybrid search over the catalog, ranked with scores   |
| `POST` | `/api/v1/ask`   | An answer written from the catalog, with its sources |

### Statistics

| Method | Path                            | Description                                       |
|--------|---------------------------------|---------------------------------------------------|
| `GET`  | `/api/v1/statistics`            | Catalog size and query usage over a period        |
| `GET`  | `/api/v1/statistics/queries`    | The recorded search and ask requests, paginated   |
| `GET`  | `/api/v1/statistics/unanswered` | Queries the catalog could not answer, paginated   |

### Common

| Method | Path            | Description                            |
|--------|-----------------|----------------------------------------|
| `GET`  | `/healthcheck/` | Liveness probe (touches no dependency) |
| `GET`  | `/`             | Service info                           |

### Source file format

The upload must contain these columns; anything else is ignored.

| Column        | Meaning                                          |
|---------------|--------------------------------------------------|
| `external_id` | Stable identifier of the pair, from the customer |
| `question`    | The question text                                |
| `answer`      | The answer text                                  |
| `category`    | Category used for filtering                      |
| `updated_at`  | Timestamp; naive values are read as UTC          |

Constraints the reader and the domain enforce:

- `external_id` must be non-empty and **unique within the file** — a duplicate
  fails the whole synchronization rather than picking a winner.
- `question` non-empty, at most 4096 characters.
- `answer` non-empty, at most 16384 characters.
- `category` non-empty.
- `updated_at` must parse as a timestamp. It does **not** decide whether a pair
  changed — the content hash does.
- The format is sniffed from the file's bytes, not its extension or its
  `Content-Type`.

`examples/qa_catalog_sample.xlsx` is a valid 24-row catalog across five
categories, useful for exercising the upload endpoint.

---

## Background Tasks

Every task reacting to a domain event is registered under that event's class
name, which is how the outbox publisher routes to it without a routing table.

| Task name          | Trigger                    | Action                                     |
|--------------------|----------------------------|--------------------------------------------|
| `IndexingTaskQueued`| A relayed queue event     | Runs the sync, records the outcome         |
| `QAPairAdded` / `QAPairContentUpdated` | A relayed event | Projects the pair into the search index |
| `QAPairRemoved`    | A relayed event            | Clears the pair from the search index      |
| `IndexingStarted` / `IndexingCompleted` / `IndexingFailed` | A relayed event | Consumed and dropped; they have no projection |
| `relay_outbox`     | Cron, every minute         | Publishes pending outbox messages          |
| `reap_stuck_tasks` | Cron, every ten minutes    | Fails runs stuck in `RUNNING` over an hour |

`relay_outbox`, the projections and `reap_stuck_tasks` retry; the indexing task
does not, because recording a failure moves the run to a terminal state that a
retry could not complete.

---

## Quick Start

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (PostgreSQL, Qdrant, NATS, Redis — and for the integration tests)
- A Mistral API key

### Setup

```sh
git clone https://github.com/C3EQUALZz/answer_service
cd answer_service

uv sync --group dev
cp .env.example .env   # then fill in MISTRAL_API_KEY
```

### With Docker

The whole environment — PostgreSQL, NATS (JetStream), Redis, Qdrant, plus the
API, the worker and the scheduler — comes up from one compose file. Migrations
run to completion first; the application services wait on them.

```sh
just up          # everything
just up-deps     # only the backing services, to run the app on the host
just up-dev      # backing services with throwaway defaults, no .env needed
just logs api
just down
```

`up-dev` uses `docker-compose.dev.yaml` — Postgres, NATS, Redis and Qdrant only,
every credential defaulting to a throwaway value — so you can bring the
dependencies up with no configuration and run the app itself on the host with
`--reload`. It publishes the same ports the app expects, so it is a drop-in
substitute for the full stack while developing.

The API, the worker and the scheduler share one image
(`deploy/prod/answer_service/Dockerfile`) and differ only in their command. They
also share the `uploads` volume: the API stages an upload there and the worker
reads it back, possibly minutes later in another container.

### Environment Variables

The excerpt below is the part you are most likely to change. The full set
lives in `setup/bootstrap/sources/` — one factory per config, each naming
the variables it reads.

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=answer_service
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_DRIVER=asyncpg

# SQLAlchemy
DB_POOL_PRE_PING=true
DB_POOL_RECYCLE=3600
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=20
DB_ECHO=false

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME=qa_pairs
QDRANT_USE_HTTPS=false
QDRANT_PREFER_GRPC=false
QDRANT_TIMEOUT_SECONDS=10          # ceiling on a single Qdrant request

# Mistral
MISTRAL_API_KEY=...
MISTRAL_EMBEDDING_MODEL=mistral-embed
MISTRAL_EMBEDDING_DIMENSION=1024
MISTRAL_CHAT_MODEL=mistral-large-latest
MISTRAL_TEMPERATURE=0.0
MISTRAL_MAX_CONCURRENCY=5
MISTRAL_EMBEDDING_TIMEOUT_SECONDS=30   # ceiling on one embedding request
MISTRAL_CHAT_TIMEOUT_SECONDS=60        # ceiling on one chat completion

# NATS
NATS_HOST=localhost
NATS_PORT=4222
NATS_USER=
NATS_PASSWORD=

# Redis — the three databases must differ
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_WORKER_DB=1
REDIS_SCHEDULE_SOURCE_DB=2
REDIS_CACHE_DB=0

# TaskIQ
TASKIQ_SUBJECT=answer_service.tasks
TASKIQ_STREAM_NAME=answer_service_jetstream
TASKIQ_DURABLE=answer_service_durable
TASKIQ_QUEUE=answer_service_workers

# Search relevance — see "Relevance thresholds" in AGENTS.md before changing
SEARCH_DENSE_SCORE_FLOOR=0.64
SEARCH_LEXICAL_RELATIVE_FLOOR=0.35
SEARCH_LEXICAL_ABSOLUTE_FLOOR=0.5
SEARCH_DENSE_WEIGHT=2.0
SEARCH_LEXICAL_WEIGHT=1.0

# Indexing — how long a run may stay RUNNING before the reaper fails it
INDEXING_STUCK_AFTER_SECONDS=3600

# Source file staging — must be shared by the API and the worker
SOURCE_STORAGE_DIRECTORY=var/uploads

# ASGI
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8080
FASTAPI_DEBUG=false
```

> [!NOTE]
> Every config is loaded eagerly at startup. A missing variable fails the boot
> rather than the first request that happens to need it.
>
> The process also refuses to start while Qdrant is unreachable — the vector
> store validates its collection on construction, and every write path needs it.
>
> Both search floors decide which questions the service is allowed to answer at
> all, and getting them wrong does not raise — it silently refuses questions the
> catalog covers, or answers ones it does not. `tests/quality` measures both
> against a live deployment; see "Relevance thresholds" in AGENTS.md before
> changing either, and watch `unanswered_rate` on `/api/v1/statistics` after.

### Running the Services

```sh
# HTTP server
uvicorn answer_service.fastapi_app:create_fastapi_app --factory --host 0.0.0.0 --port 8080

# Background task worker
taskiq worker answer_service.worker_app:create_worker_taskiq_app

# Scheduler (fires the cron tasks)
taskiq scheduler answer_service.scheduler_app:create_scheduler_taskiq_app
```

### Database Migrations

```sh
uv run alembic upgrade head
uv run alembic revision -m "description"
```

> [!NOTE]
> Revisions live in dated subdirectories, which is why `alembic.ini` sets
> `recursive_version_locations = true`. Without it alembic silently finds none.

---

## Architecture

### Clean Architecture Layers

```
Presentation → Application → Domain
                   ↑
             Infrastructure
```

The direction is enforced by `import-linter`, not by convention — see
`.importlinter`.

### Bounded Contexts

| Context          | Package             | Owns                                         |
|------------------|---------------------|----------------------------------------------|
| **Indexing**     | `domain/indexing/`  | The QA catalog and each synchronization run  |
| **Search**       | `domain/search/`    | Hybrid retrieval and rank fusion (stateless) |
| **Analytics**    | `domain/analytics/` | What was asked, and what came back           |
| **Conversation** | `domain/conversation/` | Grounded answers and their sources        |

Only `ExternalId` crosses a context boundary. Contexts do not import each
other's value objects — Analytics has its own `QueryText` so the search context
can change what it accepts without breaking the log.

#### Domain Layer

**Location:** `src/answer_service/domain/`

Pure business logic — no frameworks, no IO.

| Aggregate / Entity | Description                                                                      |
|--------------------|----------------------------------------------------------------------------------|
| `QAPair`           | Aggregate root, identified by the source-provided `ExternalId`. Holds `QAContent` |
| `IndexingTask`     | Aggregate root. State machine of one synchronization run, with counters          |
| `QueryLog`         | Entity. One recorded request; emits no events, so not an aggregate               |

**Domain Services:**

| Service       | Responsibility                                                            |
|---------------|---------------------------------------------------------------------------|
| `SyncPlanner` | Diffs the desired pairs against the catalog fingerprints into a `SyncPlan` |
| `RrfFusion`   | Fuses dense and lexical candidates into one ranking by reciprocal rank     |

**Key value objects:** `ExternalId`, `Question`, `Answer`, `Category`,
`QAContent`, `ContentHash`, `SyncStats`, `SyncPlan`, `FailureInfo`,
`SourceReference`, `IndexingTaskStatus`, `SearchQuery`, `TopK`, `CategoryFilter`,
`Score`, `ScoredCandidate`, `RankedResult`, `QueryText`, `QueryOutcome`,
`Latency`, `Period`

**Domain events:** `QAPairAdded`, `QAPairContentUpdated`, `QAPairRemoved`,
`IndexingTaskQueued`, `IndexingStarted`, `IndexingCompleted`, `IndexingFailed`

Concepts worth knowing before changing the domain:

- **Content Hash** — a pair is *changed* only when its content fingerprint
  differs. The source `updated_at` is recorded but never trusted for that.
- **Sync Plan** — creates, updates, deletes and skips, computed in one pass.
- **Unanswered** — a query that returned nothing is a **gap in the catalog**,
  not a system failure.
- **Period** — a half-open window `[start, end)`, so consecutive periods tile
  without counting a boundary query twice.

Statistics are **derived, never stored**: totals and rankings are computed from
query logs on read. A stored counter would be the same fact in two places,
reconciled forever.

#### Application Layer

**Location:** `src/answer_service/application/`

**Commands:**

| Handler                      | Description                                          |
|------------------------------|------------------------------------------------------|
| `EnqueueIndexingHandler`     | Validates and stores an upload, queues the task      |
| `MarkIndexingRunningHandler` | Fixes `RUNNING` in its own transaction; idempotent   |
| `RunIndexingHandler`         | Reads, plans and applies the sync in one transaction |
| `MarkIndexingFailedHandler`  | Records the failure; survives the work's rollback    |
| `RelayOutboxHandler`         | Drains a batch of outbox messages to the transport   |
| `UpsertQAPairHandler`        | Projects a pair's current state onto the index       |
| `RemoveQAPairHandler`        | Clears a pair from the index; safe to replay         |

**Queries:**

| Handler                        | Description                               |
|--------------------------------|-------------------------------------------|
| `GetIndexingTaskHandler`       | Status of one synchronization run         |
| `SearchQAPairsHandler`         | The hybrid ranking for one set of criteria|
| `AskQuestionHandler`           | Retrieves, then grounds one answer in it  |
| `GetStatisticsHandler`         | Catalog and query statistics for a period |
| `ListUnansweredQueriesHandler` | The gap report, ranked and paginated      |

**Ports** (`application/common/ports/`): `IndexingTaskCommandGateway`,
`IndexingTaskQueryGateway`, `QACatalogCommandGateway`, `QACatalogQueryGateway`,
`AnalyticsCommandGateway`, `AnalyticsQueryGateway`, `OutboxCommandGateway`,
`OutboxPublisher`, `EventBus`, `EventSerializer`, `TransactionManager`,
`SourceFileStorage`, `SourceFileReader`, `SearchIndexWriter`, `DenseRetriever`,
`LexicalRetriever`, `AnswerGenerator`, `Embedder`, `TaskScheduler`

#### Infrastructure Layer

**Location:** `src/answer_service/infrastructure/`

| Adapter                              | Port                         | Technology               |
|--------------------------------------|------------------------------|--------------------------|
| `SqlAlchemyQACatalogGateway`         | both catalog gateways        | PostgreSQL + SQLAlchemy  |
| `SqlAlchemyIndexingTaskGateway`      | `IndexingTaskCommandGateway` | PostgreSQL + SQLAlchemy  |
| `SqlAlchemyIndexingTaskQueryGateway` | `IndexingTaskQueryGateway`   | PostgreSQL + SQLAlchemy  |
| `SqlAlchemyAnalyticsGateway`         | both analytics gateways      | PostgreSQL + SQLAlchemy  |
| `SqlAlchemyOutboxGateway`            | `OutboxCommandGateway`       | PostgreSQL, `SKIP LOCKED`|
| `SqlAlchemyTransactionManager`       | `TransactionManager`         | SQLAlchemy async session |
| `QdrantSearchIndexWriter`            | `SearchIndexWriter`          | Qdrant (LangChain)       |
| `QdrantDenseRetriever`               | `DenseRetriever`             | Qdrant (LangChain)       |
| `PostgresLexicalRetriever`           | `LexicalRetriever`           | PostgreSQL FTS + GIN     |
| `LangChainAnswerGenerator`           | `AnswerGenerator`            | Mistral chat             |
| `LangChainEmbedder`                  | `Embedder`                   | Mistral embeddings       |
| `PolarsSourceFileReader`             | `SourceFileReader`           | polars                   |
| `LocalSourceFileStorage`             | `SourceFileStorage`          | Filesystem               |
| `OutboxEventBus`                     | `EventBus`                   | Transactional outbox     |
| `TaskSchedulerOutboxPublisher`       | `OutboxPublisher`            | TaskIQ                   |
| `TaskIQTaskScheduler`                | `TaskScheduler`              | TaskIQ + NATS JetStream  |
| `RetortEventSerializer`              | `EventSerializer`            | Adaptix                  |

The ORM mapping is **imperative** (`persistence/models/`): the domain classes
know nothing about SQLAlchemy. Value objects reach columns through
`TypeDecorator`s — single-field ones directly, multi-field ones either as a
`composite` (when a field is filtered on) or as JSONB (when read back whole).

#### Presentation Layer

**Location:** `src/answer_service/presentation/`

FastAPI routers with `route_class=DishkaRoute`. Each operation lives in its own
directory with `handlers.py` and `schemas.py`. Routes inject `Sender` and
dispatch a command or query — they never touch a gateway.

Errors are mapped to status codes by `ExceptionHandler`, keyed by **exact type**.
An error missing from the table answers 500 on purpose: a forgotten error should
be loud, not disguised as a plausible 400. Messages for 5xx are replaced before
they reach the client, since they may name a host, a table or a query.

### The Mediator

Commands are dispatched through `Sender`, implemented by an in-house
`MediatorImpl` (`infrastructure/mediator/`): a `Registry` maps request types to
handlers and pipelines, a `Resolver` fetches them from Dishka, and a `Chain`
wraps the handler in its pipelines.

```python
registry.add_pipeline_handlers(Command, TransactionPipeline, EventsPipeline)
```

**Registration order is execution order.** The transaction opens first and
commits last, with the events drained inside it. Reversed, events would be
published after the commit and the outbox would stop being atomic with the state
change it describes.

Pipelines are registered against the `Command` marker, so a command added later
cannot escape them. Queries are deliberately uncovered — they mutate nothing.

### Dependency Injection

**Dishka** manages the container, split into one provider function per concern:

| Provider                | Scope   | Contents                                                        |
|-------------------------|---------|-----------------------------------------------------------------|
| `configs_provider`      | APP     | Every config object, supplied from context                      |
| `database_provider`     | APP/REQ | Engine and sessionmaker (APP), `AsyncSession` (REQUEST)         |
| `vector_store_provider` | APP     | Embeddings, chat model, Qdrant client and vector store          |
| `task_manager_provider` | APP/REQ | `ScheduleSource` (APP), `TaskScheduler` (REQUEST)               |
| `domain_provider`       | REQUEST | `EventsCollection`, id generators, factories, domain services   |
| `gateways_provider`     | REQUEST | Every port bound to its adapter                                 |
| `pipelines_provider`    | REQUEST | `TransactionPipeline`, `EventsPipeline`                         |
| `handlers_provider`     | REQUEST | Every command and query handler                                 |
| `mediator_provider`     | APP/REQ | `Registry` and `Chain` (APP), `Resolver` and `Sender` (REQUEST) |

**Key design:** `EventsCollection` is REQUEST-scoped and shared by every
aggregate built during the request, so the events pipeline drains them together.

### Event Flow

```
Command handler
    │
    ▼
Aggregate.method()      → records into EventsCollection
    │
    ▼
EventsPipeline          → pulls the collection, hands it to EventBus
    │
    ▼
OutboxEventBus          → serialised rows in the outbox table
    │                     [same transaction as the state change]
    ▼
TransactionPipeline     → commit
    ⋮
    ▼  (cron, separate transaction)
RelayOutboxHandler      → OutboxPublisher → one task per message
    │
    ▼
ProjectEventHandler     → SearchIndexWriter → Qdrant
```

Delivery is at-least-once, so consumers are idempotent by construction: the
projector reads current state instead of trusting the payload, and the point id
is derived from the external id.

---

## Development

### Code Quality Tools

```sh
just lint              # ruff format → ruff check → codespell
just mypy              # strict type checking
just bandit            # security analysis
just import-linter     # layer boundaries
just static-analysis   # mypy + bandit + semgrep + import-linter
just pre-commit-all
```

### Running Tests

```sh
uv run pytest -q                    # everything
uv run pytest tests/unit -q         # fast, no Docker
uv run pytest tests/integration -q  # needs Docker
uv run pytest --cov=src/answer_service --cov-report=html
```

Unit tests cover the domain, the application handlers and the mediator, against
in-memory stubs. Integration tests run against a real PostgreSQL started by
testcontainers, with an in-process Qdrant and fake embeddings; they resolve
**ports** from the container rather than naming concrete adapters, so the
persistence technology can change without rewriting them.

A third suite, `tests/quality`, measures retrieval against a **live** deployment
— real embeddings, real Qdrant — over questions worded the way a person would
word them, plus questions the catalog cannot answer and must refuse. It is
marked `quality` and deselected by default; run it once a stack is up and the
sample catalog is uploaded:

```sh
uv run pytest -m quality        # QUALITY_BASE_URL defaults to http://localhost:8080
```

### Continuous Integration

`just ci` runs locally exactly what CI runs, in the same order.

| Workflow | What it guards |
|---|---|
| `ci.yml` | ruff, codespell/typos, mypy, import-linter, bandit, semgrep, the full test suite with coverage, and a gitleaks scan |
| `codeql.yml` | CodeQL `security-extended` for Python, weekly and on every PR |
| `dependency-review.yml` | Blocks a PR introducing a high-severity advisory or a copyleft licence |
| `zizmor.yml` | Static security analysis of the workflows themselves |
| `sonarqube.yml` | SonarQube Cloud, gated on the `ENABLE_SONAR` repository variable |
| `docker.yml` | Builds the image; pushes to GHCR on `master` and on tags |
| `pr-title.yml` | Conventional Commits on the PR title, which becomes the squash commit |
| `labeler.yml` / `labels.yml` | Path-based PR labels, mirroring the layer boundaries |

Third-party actions are pinned to a full commit SHA. CodeRabbit reviews pull
requests against the layer rules (`.coderabbit.yaml`).

Secrets and variables the workflows expect:

| Name | Kind | Needed for |
|---|---|---|
| `SONAR_TOKEN` | secret | SonarQube Cloud |
| `ENABLE_SONAR` | variable | Set to `true` to activate the Sonar workflow |
| `CODECOV_TOKEN` | secret | Coverage upload (optional; the step does not fail CI) |

---

## Project Structure

```
src/answer_service/
├── domain/
│   ├── common/              # Entity, Aggregate, ValueObject, Event, EventsCollection
│   ├── indexing/            # QAPair + IndexingTask aggregates
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── services/        # SyncPlanner
│   │   ├── factories/
│   │   ├── ports/
│   │   ├── errors.py
│   │   └── events.py
│   ├── search/              # stateless: value objects + RrfFusion
│   │   ├── value_objects/
│   │   └── services/
│   ├── conversation/        # stateless: AnswerText, GroundedAnswer
│   │   └── value_objects/
│   └── analytics/           # QueryLog entity
│       ├── entities/
│       ├── value_objects/
│       ├── factories/
│       └── ports/
│
├── application/
│   ├── commands/
│   │   ├── indexing/        # enqueue, mark_running, run, mark_failed
│   │   ├── outbox/          # relay_outbox
│   │   └── search/          # upsert_qa_pair, remove_qa_pair
│   ├── queries/
│   │   ├── indexing/        # get_indexing_task
│   │   ├── search/          # search_qa_pairs
│   │   ├── conversation/    # ask_question
│   │   └── analytics/       # get_statistics, list_unanswered_queries
│   ├── pipelines/           # Transaction, Events, QueryRecording
│   └── common/
│       ├── analytics/       # RecordableQuery marker, ServedQuery
│       ├── mediator/        # handlers, markers, Sender
│       ├── ports/           # every infrastructure interface
│       ├── services/        # HybridSearchService
│       └── query_params/    # Pagination, SortingOrder
│
├── infrastructure/
│   ├── adapters/
│   │   ├── common/          # id generators, OutboxEventBus, event serializer
│   │   ├── langchain/       # LangChainEmbedder, LangChainAnswerGenerator
│   │   ├── messaging/       # TaskSchedulerOutboxPublisher
│   │   ├── persistence/     # SQLAlchemy gateways, transaction manager
│   │   ├── search/          # Qdrant writer + retriever, PostgreSQL FTS retriever
│   │   └── source_file/     # polars reader, local storage
│   ├── mediator/            # Registry, Chain, Resolver, MediatorImpl
│   ├── persistence/
│   │   ├── models/          # tables, imperative mapping, column types
│   │   └── migrations/      # alembic
│   ├── task_manager/        # TaskIQTaskScheduler, task definitions
│   └── errors.py
│
├── presentation/http/v1/
│   ├── common/              # exception handler, healthcheck, index
│   ├── middlewares/
│   └── routes/
│       ├── indexing/        # enqueue_indexing, get_indexing_task
│       ├── search/          # search_qa_pairs
│       ├── conversation/    # ask_question
│       └── statistics/      # get_statistics, list_unanswered_queries
│
├── setup/
│   ├── configs/             # plain dataclasses, no loader dependency
│   ├── bootstrap/
│   │   ├── loaders/         # dature-backed config loaders
│   │   ├── sources/         # env source factories
│   │   └── setups/          # logging, database, http, task manager, scheduler
│   └── ioc/
│       ├── providers/       # one file per concern
│       └── containers/      # container assembly
│
├── fastapi_app.py           # HTTP entry point
├── worker_app.py            # TaskIQ worker entry point
└── scheduler_app.py         # TaskIQ scheduler entry point
```

---

## Contributing

Project rules for humans and agents alike live in **[AGENTS.md](AGENTS.md)** —
layer boundaries, naming, testing rules, and the mistakes this codebase has
already made once.

---

## Versioning

Versioning is managed automatically by
[Hatch VCS](https://hatch.pypa.io/latest/version/) from git tags.

```sh
python -c "from answer_service._version import __version__; print(__version__)"
```

> [!NOTE]
> If the version is stale, delete `src/answer_service/_version.py` and reinstall:
> `uv sync`
