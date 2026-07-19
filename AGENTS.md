# answer_service

Hybrid-search + RAG backend for a FAQ catalog. A customer uploads a CSV/Excel
file of question-answer pairs; the service keeps a catalog in sync with that
file, indexes it for search, answers queries, and reports on what it could not
answer.

## Project Structure

```
src/answer_service/
  domain/          business rules; no dependency on anything below
  application/     use cases, ports, pipelines
  infrastructure/  adapters implementing the ports
  presentation/    HTTP routes and schemas
  setup/           configs, bootstrap, DI container
tests/
  unit/            domain + application + our own infrastructure logic
  integration/     anything crossing a process boundary
```

Rules:

- Dependencies flow inward: `presentation → application → domain`.
- `domain` contains only business logic and imports nothing from other layers.
- `infrastructure` implements interfaces defined in `application`.
- These are **enforced**, not advisory: `just import-linter` fails the build.
  Read `.importlinter` before moving a module.

## Bounded contexts

The domain is a modular monolith split into contexts.

| Context | Package | Owns |
|---|---|---|
| Indexing | `domain/indexing/` | The QA catalog and each synchronization run |
| Search | `domain/search/` | Hybrid retrieval and rank fusion (stateless) |
| Analytics | `domain/analytics/` | What was asked, and what came back |
| Conversation | `domain/conversation/` | Grounded answers and their sources |

Only `ExternalId` crosses a context boundary. Contexts do not import each
other's value objects — Analytics has its own `QueryText` precisely so the
search context can change what it accepts without breaking the log.

Terms worth knowing before changing these contexts:

- **Content Hash** — the fingerprint of a QA pair's content. Synchronization is
  idempotent because a pair is *changed* only when this differs; the source
  `updated_at` is not trusted for that.
- **Sync Plan** — the diff of the file against the catalog: creates, updates,
  deletes and skips. A pair present in the catalog but absent from the file is
  deleted, because the file is the source of truth.
- **Fusion** — Reciprocal Rank Fusion. Each candidate scores `1 / (k + rank)`
  per retriever it appears in, summed. Rank-based, so the two retrievers'
  incompatible score scales never leak into the ranking.
- **Unanswered** — a query that returned nothing. The central idea of Analytics:
  it is a **gap in the catalog**, not a system failure, and the frequent ones
  are the content backlog.
- **Period** — the half-open window `[start, end)` a report covers, so
  consecutive periods tile without counting a boundary query twice.
- **Score Floor** — the minimum a candidate must score to leave its retriever.
  Applied per retriever, never after fusion, and on a different principle each
  side: dense uses an absolute cosine, lexical a fraction of the best match for
  that same query. See "Relevance thresholds" below before changing either.
- **Grounded Answer** — generated text plus the pairs it was written from. It
  refuses to exist without sources: an answer with nothing behind it is the one
  thing this service must not produce.
- **Recordable Query** — the marker a query inherits to be written to the
  journal. `QueryRecordingPipeline` is registered against it, so journalling is
  coverage by type rather than by a call site someone has to remember.

Statistics are **derived, never stored**: totals and rankings are computed from
query logs on read. A stored counter would be the same fact in two places,
reconciled forever.

## Domain layer

```
domain/<context>/
  entities/         Entity[Id] or Aggregate[Id]
  value_objects/    ValueObject subclasses
  services/         BaseDomainService subclasses (stateless)
  factories/        build aggregates; receive EventsCollection via DI
  ports/            Protocols the infrastructure implements
  errors.py
  events.py
```

- Entities and aggregates inherit `Entity` / `Aggregate`.
- Value objects inherit `ValueObject` and implement `_validate()` with
  `@override`. They never override `__post_init__`.
- Domain services inherit `BaseDomainService` and hold no state.
- Use `Entity` rather than `Aggregate` when the type emits no domain events —
  an aggregate drags in an `EventsCollection` nobody drains. `QueryLog` is the
  example.

**Value objects are keyword-only** — except the ones stored as a SQLAlchemy
`composite`, which the ORM builds positionally. Today that is `QAContent` and
`QueryOutcome`. Do not add `kw_only=True` to those without changing the mapping.

## Application layer

```
application/
  commands/<context>/<use_case>/{command.py,handler.py}
  queries/<context>/<use_case>/{query.py,handler.py}
  common/
    mediator/    RequestHandler, PipelineHandler, markers, Sender
    ports/       every interface the infrastructure implements
    query_params/  Pagination, SortingOrder
  pipelines/     TransactionPipeline, EventsPipeline
```

One directory per use case. `command.py` holds the request dataclass and its
response; `handler.py` holds the handler.

Handlers:

- Inherit `CommandHandler[TCommand, TResponse]` or `QueryHandler[...]`.
- Take collaborators in `__init__` and store them as `Final`.
- Implement `handle()` with `@override`.
- **Never catch `Exception`** — catch `AppError` or a specific subclass.
- **Never swallow a failure to report success.** A handler that catches, records
  the failure and returns normally makes the transaction pipeline *commit*
  partially applied work. Let it propagate; record failures in a separate
  command with its own transaction.

Gateways, not repositories: `CommandGateway` for the write side,
`QueryGateway` for reads, with methods `add` / `read_by_id` / `update` /
`delete_by_id`. Query gateways return purpose-built read models (
`IndexingTaskView`, `CatalogStatistics`) and aggregate in the database — never
load rows to count them in Python.

## Pipelines and the mediator

Commands are dispatched through `Sender` (implemented by `MediatorImpl`), which
wraps the handler in the pipelines registered for its type.

```python
registry.add_pipeline_handlers(Command, TransactionPipeline, EventsPipeline)
```

**Registration order is execution order**: the transaction opens first and
commits last, with events drained inside it. Reversed, events would be published
after the commit and the outbox would stop being atomic with the state change it
describes. Pipelines are registered against the `Command` marker so a command
added later cannot escape them.

Queries are deliberately uncovered — they mutate nothing.

## Events and the outbox

Aggregates record events into a request-scoped `EventsCollection`.
`EventsPipeline` drains it and hands the events to `EventBus`, whose only
implementation writes them to the outbox table **in the same transaction**.
A cron task relays them; a projection task applies them to the search index.

Delivery is at-least-once, so **consumers must be idempotent**. The projector
reads the pair's current state rather than trusting the event payload, and the
Qdrant point id is a UUIDv5 of the external id — replaying an event is
indistinguishable from applying it once.

## Infrastructure

- **Postgres** + SQLAlchemy asyncio + asyncpg, **imperative mapping**
  (`persistence/models/`). The domain knows nothing about the ORM.
- **Qdrant** via `langchain-qdrant`; embeddings via `langchain-mistralai`.
- **taskiq** over NATS JetStream, Redis result backend.
- **dishka** for DI, **FastAPI** for HTTP.

Value objects reach the database through `TypeDecorator`s in
`persistence/models/types.py`. Multi-field value objects are either a
`composite` (when a field is filtered on) or JSONB (when it is only read back
whole).

Adapters wrap third-party errors in `InfrastructureError` subclasses. Never let
a library exception escape an adapter.

## Presentation layer

```
presentation/http/v1/
  common/
    exception_handler.py   ExceptionHandler + ExceptionSchema
    routes/                healthcheck.py, index.py
  middlewares/
  routes/<context>/
    router.py              aggregates the sub-routers
    <use_case>/{handlers.py,schemas.py}
```

- One directory per operation; `handlers.py` defines `<operation>_router`.
- `route_class=DishkaRoute` on every router.
- Inject `FromDishka[Sender]` and dispatch a command or query — routes never
  touch a gateway.
- Map application DTOs to pydantic schemas explicitly, in `schemas.py`.
- Document non-2xx responses with `{"model": ExceptionSchema}`.

**Error mapping is exhaustive and keyed by exact type**
(`ExceptionHandler._ERROR_MAPPING`). An error missing from the table answers 500.
That is deliberate: a forgotten error shows up as a 500 rather than a
plausible-looking 400. **Add every new error to the table.**

Messages for 5xx are replaced with `"Internal server error."` before they reach
the client — they may name a host, a table or a query.

## Testing Rules (Mandatory)

- Tests mirror `src/` structure. Use `unit/` and `integration/`.
- **Arrange / Act / Assert**, separated by blank lines.
- Name tests by behaviour and outcome, not by method name.
- A docstring on a test explains *why the behaviour matters*, not what the code
  does. Most tests need none.
- **Fixtures live only in `conftest.py`.** Builders live in
  `tests/unit/factories/`. Stubs live in `tests/unit/stubs/`. Never define
  either next to a test.
- Use `pytest.mark.usefixtures` for fixtures whose value the test never reads.

What goes where:

| Kind | Home | Rule |
|---|---|---|
| Domain, application handlers, mediator | `tests/unit/` | Never touch IO |
| Anything wrapping a library or a service | `tests/integration/` | |

**Do not test libraries.** Asserting that a fake embedding model is
deterministic tests langchain, not us. Test the decisions we made: the empty
batch that must not reach the model, the format sniffing, the status mapping.

**Integration tests name ports, never implementations.** Resolve them from the
container with `tests/integration/inject.py`:

```python
@inject
async def test_something(
    store_outbox_messages: OutboxSeeder,
    gateway: FromDishka[OutboxCommandGateway],
) -> None:
```

A test that constructs `SqlAlchemyOutboxGateway(session)` is a test of
SQLAlchemy and breaks the day the technology changes.

Integration tests need **Docker** (testcontainers Postgres). Qdrant runs
in-process and embeddings are faked — see `tests/integration/ioc.py`.

## Tooling & Standards (Mandatory)

- Python **3.14**, package manager **uv**, task runner **just**
- Formatting & linting: **ruff** (`select = ["ALL"]`, line length 90)
- Type checking: **mypy**, strict; everything fully annotated
- Testing: **pytest** with coverage

Conventions this project insists on:

- **No `from __future__ import annotations`.** PEP 649 handles it.
- **Constructor parameter types must be importable at runtime** — dishka,
  adaptix and pydantic resolve them then. Do not move them under
  `if TYPE_CHECKING`. (`TC001`/`TC002`/`TC003` are disabled for this reason.)
- Store injected collaborators as `Final`.
- `@override` on every overriding method, including `_validate`.
- Avoid `typing.Any`.
- Never use `# type: ignore` without a comment explaining why.

Common commands:

```sh
just lint              # ruff format + ruff check + codespell
just mypy              # type check
just static-analysis   # mypy + bandit + semgrep + import-linter
just test              # pytest with coverage
just migrate           # alembic upgrade head
```

## Code Quality Rules (Mandatory)

**After writing ANY code**, run in this order:

```sh
just lint
just mypy
just static-analysis   # before any commit
uv run pytest -q       # must pass before marking work done
```

Rules:

- Fix ALL ruff and mypy errors before moving on.
- **Accept ruff's autofixes; do not disable a rule to make it quiet.** If a rule
  is genuinely wrong for a file, add a scoped `per-file-ignores` entry with a
  comment saying why.
- `just lint` is the minimum bar after every change.
- Never claim work is done without running the tests and reporting the result.

## Things that have bitten us

Read these before touching the corresponding area.

- **`EnvSource` without a prefix matches by field name.** A field called `path`
  picked up the system `PATH`. Config fields are named `log_path`,
  `directory`, and so on for that reason.
- **The source file's name never crosses the queue.** `read_rows` gets bytes
  only, so the reader sniffs the format from the content. Deciding by extension
  meant Excel validated on upload and failed in the worker.
- **`setup_map_tables` must be called exactly once per process.**
  `map_imperatively` raises on an already-mapped class.
- **Alembic needs `recursive_version_locations = true`** — revisions live in
  dated subdirectories, and without it alembic silently finds none.
- **`async_fallback` does not work on Python 3.12+.** The alembic env uses a
  real async engine with `run_sync`.
- **The process will not start while Qdrant is unreachable** — the vector store
  validates its collection at construction. Deliberate; every write path needs
  it.
- **Every PostgreSQL parser that accepts free text ANDs its terms.**
  `websearch_to_tsquery('a b')` matches only rows holding *both*, and no pair
  holds every word of a natural question — the lexical retriever contributed
  exactly nothing until its terms were OR-ed through
  `to_tsvector`/`tsvector_to_array`/`to_tsquery`.
- **Fused scores carry no relevance signal.** RRF sums `1 / (k + rank)`, so the
  top result scores the same whether it was perfect or terrible. A threshold
  applied after fusion is meaningless; the floors live in the retrievers.
- **`EventsCollection.pull_events()` returns an iterator, and it drains.**
  Anything that reads it — a `len()`, a log line — consumes it, and the events
  are then never published. Materialize once if you need to look.
- **Verify against the running image, not the source tree.** A dense floor
  looked broken for an hour because the container was still running the previous
  build. `docker compose exec api python -c "import inspect; ..."` first.
- **`ts_rank_cd` is not comparable between queries.** It grows with the number
  of matched terms, so the same pair scored 1.4 for "orders" and 3.2 for "how do
  I track my order". An absolute lexical threshold therefore measures query
  length, not relevance — which is why that floor is relative. Normalisation
  flags do not rescue it: the bounded variant still moved 0.58 → 0.76 on that
  same pair.

## Relevance thresholds

`SEARCH_DENSE_SCORE_FLOOR` decides which questions the service is allowed to
answer at all. **The current default is a guess**, set by hand against a
24-pair sample catalog, and no test can tell you it is wrong: a floor that is
too high does not fail, it silently refuses questions the catalog could have
answered, and the users simply leave.

Do not try to calibrate it from synthetic labels. Asking the catalog its own
questions leaks — the identical text is in the index, so it scores ~1.0 and
tells you nothing about paraphrased questions. Inventing nonsense queries fails
the other way: real unanswerable questions are *on topic but uncovered*
("do you ship to Brazil?"), and score far higher than deliberate gibberish. Both
errors widen the gap artificially and yield a threshold that looks well
separated and is not. An earlier calibration script did exactly this and was
deleted for it.

What works today, with no new code: set the floor, then watch `unanswered_rate`
on `/v1/statistics/` and read `/v1/statistics/unanswered`. Sensible on-topic
questions in that list mean the floor is too high; junk means it is working.

What would let it be automated: a "did this answer help" label on served
queries. `QueryLog` already stores the text, the result count and the top score
— the label is the only missing column. With it, choosing the threshold becomes
a measurement (sweep it, compute precision/recall, check the AUC to see whether
*any* threshold separates the classes) instead of a judgement call, and it can
be rechecked on a schedule as the catalog drifts.
