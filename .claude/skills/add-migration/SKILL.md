---
name: add-migration
description: Create or change an alembic migration and the imperative SQLAlchemy mapping behind it. Use when adding a table, column or index to answer_service.
---

# Changing the schema

The mapping is **imperative**: the domain class knows nothing about the table.
A schema change therefore touches two files that must agree, plus a migration.

## 1. The table and the mapping

`infrastructure/persistence/models/<aggregate>.py` holds both the `Table` and a
`map_<name>_table()` function. Register the mapping in
`setup/bootstrap/setups/database_setup.py`.

Value objects reach columns through `persistence/models/types.py`:

- **single-field VO** → a `TypeDecorator`; the VO keeps `kw_only=True`
- **multi-field VO, a field is filtered on** → `composite()`; the VO **must not**
  be `kw_only` (SQLAlchemy builds it positionally)
- **multi-field VO, only ever read back whole** → JSONB via a `TypeDecorator`

`SyncStats` is JSONB because nothing filters on it. `QueryOutcome` is a
composite because every statistics query filters on `results_count`.

## 2. Sanity-check before writing the migration

Mappers configure lazily — an error surfaces only when something asks. Force it:

```python
from sqlalchemy.orm import configure_mappers
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

setup_map_tables()
configure_mappers()
print(CreateTable(the_table).compile(dialect=postgresql.dialect()))
```

## 3. The migration

```sh
uv run alembic revision -m "short description"
```

Autogenerate needs a live database; writing the body by hand is fine and often
clearer. Set `down_revision` to the current head.

Then verify without a database:

```sh
uv run alembic upgrade head --sql
```

If it prints `DROP TABLE alembic_version` instead of your DDL, alembic did not
find the revision — check `recursive_version_locations = true` in `alembic.ini`.
Revisions live in dated subdirectories.

## 4. Indexes

Add them for the queries that exist, not the ones imagined. Check the composite
indexes already present before adding a single-column one — a left-prefix index
is dead weight on every insert.

Partial indexes matter here: the relay reads only unprocessed outbox rows, and
the gap report only unanswered queries.

## 5. Tests

Round-trip belongs in `tests/integration/persistence/`, through the **port**:

```python
@inject
async def test_x(store_indexing_task: TaskStorer, gateway: FromDishka[SomeGateway]):
```

A composite or a JSONB column that maps wrong does not raise — it returns
something else. Assert the value that comes back, not just that a row exists.

## 6. Before reporting

```sh
just lint && just mypy
uv run pytest tests/integration/persistence -q   # needs Docker
uv run alembic upgrade head --sql                # migration compiles
```
