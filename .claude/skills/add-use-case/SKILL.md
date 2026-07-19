---
name: add-use-case
description: Add a command or query use case end to end — request, handler, ports, DI registration, mediator registration and tests. Use when asked to add a new endpoint, command, query, or background operation to answer_service.
---

# Adding a use case

A use case is only finished when it is **reachable**. Half of it — a handler with
no registration, a port with no adapter — looks done and is not. Work the list
top to bottom and check the last section before reporting.

## 1. Decide command or query

| | Command | Query |
|---|---|---|
| Marker | `Command[TResponse]` | `Query[TResponse]` |
| Pipelines | transaction + events | **none** |
| Handler base | `CommandHandler` | `QueryHandler` |
| Gateways | `*CommandGateway` | `*QueryGateway`, returning a read model |

A query must not mutate. If it needs a transaction, it is a command.

## 2. Domain first, if the concept is new

Add value objects, entity methods and errors in `domain/<context>/` before
touching the application layer. Use the vocabulary AGENTS.md defines for that
context; if the concept is genuinely new, add it there.

Value objects: inherit `ValueObject`, implement `_validate` with `@override`,
raise a `DomainFieldError` subclass declared in the context's `errors.py`.

## 3. The use case

```
application/commands/<context>/<use_case>/
  __init__.py    empty
  command.py     the request dataclass and its response dataclass
  handler.py     the handler
```

- Collaborators in `__init__`, stored as `Final`.
- `handle()` with `@override`.
- Catch `AppError`, never `Exception`.
- Never catch-and-return-success: that makes the transaction pipeline commit
  partially applied work.

Missing ports go in `application/common/ports/`, as `Protocol` with
`@abstractmethod`.

## 4. Wire it — all four places

Forgetting any one of these produces a use case that fails only at runtime.

1. **Adapter** for every new port, in `infrastructure/adapters/`.
2. **`handlers_provider.py`** — add the handler to `provide_all`.
3. **`gateways_provider.py`** — bind each new port to its adapter.
4. **`mediator_provider.py`** — `registry.add_request_handler(TheCommand, TheHandler)`.

If it is triggered by a background task, also register the task name in
`infrastructure/task_manager/tasks/` and derive the id from a `TaskKey` in
`ports/task_manager/task_keys.py`.

## 5. Expose it, if it is public

```
presentation/http/v1/routes/<context>/<use_case>/{handlers.py,schemas.py}
```

Add the sub-router to the context's `router.py`. The route injects
`FromDishka[Sender]` and dispatches — it never touches a gateway. Map the
application DTO to a pydantic schema explicitly.

Add any new error to `ExceptionHandler._ERROR_MAPPING`. The lookup is by exact
type, so an unlisted error answers 500.

## 6. Tests

- Unit: `tests/unit/application/{commands,queries}/test_<use_case>.py`, against
  the in-memory stubs. Cover the success path, each failure, and idempotency if
  the operation can be redelivered.
- Integration: only if the behaviour crosses a boundary. Name ports, not
  implementations, and resolve them with `tests/integration/inject.py`.
- Fixtures in `conftest.py`; builders in `tests/unit/factories/`.

## 7. Before reporting

```sh
just lint && just mypy && uv run pytest -q
```

Then confirm the wiring actually resolves — a graph error surfaces only when the
container is built:

```python
async with container(scope=Scope.REQUEST) as scope:
    await scope.get(TheNewHandler)
```

Say how many tests ran, and name anything you could not verify.
