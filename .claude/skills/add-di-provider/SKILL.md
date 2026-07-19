---
name: add-di-provider
description: Wire something into the dishka container — pick a scope, write a provider function, bind a port to an adapter, and verify the graph resolves. Use when adding a provider, changing a scope, or debugging a container that fails to build.
---

# Wiring dishka

Providers are split one function per concern (`setup/ioc/providers/`), each
declaring its own scope. A lifetime mistake is then visible in the file that
made it rather than buried in one long list.

## Choosing a scope

| Scope | For | Examples |
|---|---|---|
| `APP` | Built once, safe to share, expensive to rebuild | engine, sessionmaker, embedding model, Qdrant client, `Registry`, `Chain`, stateless domain services |
| `REQUEST` | Carries per-request state | `AsyncSession`, `EventsCollection`, every gateway, every handler, the pipelines, `Resolver`, `Sender` |

The test is not "is it cheap to build" but **does it hold state belonging to one
request**. A session carries an identity map; a gateway carries a session; a
handler carries a gateway. All three are REQUEST.

Getting this wrong is silent: an APP-scoped gateway serves one request's
uncommitted rows to the next.

## The three ways to provide

```python
# 1. A class dishka can construct — bind it to the port it implements
provider.provide(source=SqlAlchemyOutboxGateway, provides=OutboxCommandGateway)

# 2. A factory function — when construction needs more than its dependencies
provider.provide(create_qdrant_vectorstore, provides=QdrantVectorStore)

# 3. Supplied from outside — configs and the broker exist before the container
provider.from_context(provides=PostgresConfig)
```

**Reach for a factory whenever a constructor takes a value that is not a
dependency.** `RrfFusion(k: int = 60)` made dishka try to resolve `int`, and the
whole graph failed to build:

```python
def make_rrf_fusion() -> RrfFusion:
    """Its only parameter is a tuning constant, not a dependency."""
    return RrfFusion()
```

A factory that yields is a lifecycle: dishka closes it when the scope ends. Put
the cleanup in `finally`, not after the `yield` — the generator may be discarded
without ever being resumed.

## Constructor types must be importable at runtime

dishka reads `__init__` annotations at runtime. Moving a parameter type under
`if TYPE_CHECKING` makes the graph fail to build. `TC001`/`TC002`/`TC003` are
disabled project-wide for exactly this reason — do not "fix" them.

## Adding a provider

1. Write `<concern>_provider.py` returning a `Provider`.
2. Export it from `ioc/providers/__init__.py`.
3. Add it to `setup_providers()` in `ioc/containers/container.py`.
4. If it needs something built before the container, add it to
   `make_container_context()` **and** to `configs_provider` — the two must agree.

## Verify the graph, always

`make_async_container` validates the whole graph eagerly, so a missing factory
or an incompatible scope surfaces there and nowhere else. Type checking will not
catch it.

```python
container = make_container(context)          # raises GraphMissingFactoryError
async with container(scope=Scope.REQUEST) as scope:
    await scope.get(TheThing)                # raises if construction fails
```

For a handler, also check it against the mediator registry — a handler bound in
the registry but missing from `handlers_provider` fails only when a user
triggers it:

```python
for request_type, handler_type in make_registry()._request_handlers.items():
    await scope.get(handler_type)
```

## In tests

Integration tests reuse the production providers and swap only what reaches
outside their control (`tests/integration/ioc.py`). Resolve **ports**, never
adapters, via `tests/integration/inject.py`:

```python
@inject
async def test_x(gateway: FromDishka[OutboxCommandGateway]) -> None:
```

Two concurrent request scopes stand in for two replicas:

```python
async with (
    container(scope=Scope.REQUEST) as first,
    container(scope=Scope.REQUEST) as second,
):
```
