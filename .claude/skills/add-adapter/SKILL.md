---
name: add-adapter
description: Add a port and the adapter implementing it — Protocol, adapter, error wrapping, DI binding and an integration test. Use when answer_service needs to talk to a new external system, or when replacing how it talks to an existing one.
---

# Adding a port and its adapter

The application says *what* it needs; the infrastructure decides *how*. If the
application layer would have to change when the technology changes, the seam is
in the wrong place.

## 1. The port — `application/common/ports/<area>/<name>.py`

```python
class DenseRetriever(Protocol):
    """One sentence on the role, in the application's vocabulary."""

    @abstractmethod
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        """Returns candidates ordered by similarity, best first.

        Ordering is part of the contract: fusion consumes position, not score,
        so an unordered result would silently corrupt the ranking.
        """
        raise NotImplementedError
```

- Name it after the role, not the technology: `DenseRetriever`, not
  `QdrantClient`; `SearchIndexWriter`, not `QdrantWriter`.
- Speak in domain types. A port taking `list[float]` has leaked the
  implementation into the interface.
- **Write down the guarantees the caller relies on.** Ordering, idempotency, and
  "returns None rather than raising" are contract, not trivia.
- Gateways follow the house style: `add` / `read_by_id` / `update` /
  `delete_by_id`, split into `*CommandGateway` and `*QueryGateway`. Query
  gateways return purpose-built read models and aggregate in the database.

## 2. The adapter — `infrastructure/adapters/<kind>/<technology>_<role>.py`

```python
@final
class QdrantDenseRetriever(DenseRetriever):
    def __init__(self, vector_store: QdrantVectorStore) -> None:
        self._vector_store: Final[QdrantVectorStore] = vector_store

    @override
    async def retrieve(self, criteria: SearchCriteria) -> Sequence[ScoredCandidate]:
        try:
            hits = await self._vector_store.asimilarity_search_with_score(...)
        except Exception as e:
            msg = "Failed to query Qdrant for dense candidates."
            raise SearchIndexError(msg) from e
        return [...]
```

- `@final`, inherit the port explicitly, `@override` on every method.
- Collaborators as `Final`.
- **No library exception may escape.** Wrap it in an `InfrastructureError`
  subclass from `infrastructure/errors.py`, adding one if none fits. An
  unwrapped exception slips past `except AppError` in the transaction pipeline,
  so nothing rolls back.
- Depend on the widest interface that works. `LangChainEmbedder` takes
  `Embeddings`, not `MistralAIEmbeddings`, so the provider picks the vendor.

## 3. Check the library before writing against it

Assumptions about third-party APIs have been wrong here more than once: an
`async_client` parameter that does not exist, an `a*` method that turns out to be
a threadpool wrapper rather than native async, a response class that is
deprecated. Look first:

```python
import inspect
print(inspect.signature(TheClass.__init__))
print(sorted(n for n in dir(TheClass) if not n.startswith("_")))
```

## 4. Wire and register

- Bind it in `ioc/providers/gateways_provider.py`:
  `provider.provide(source=TheAdapter, provides=ThePort)`.
- If constructing it needs a client or a model, add a factory to the relevant
  provider — see the `add-di-provider` skill.
- If it raises a new error type, add that type to
  `ExceptionHandler._ERROR_MAPPING`, or it answers 500.

## 5. Test it in `tests/integration/`

An adapter wrapping a library is not a unit test. Only genuinely self-written
logic — a pure function such as `point_id_of` — belongs in `tests/unit/`.

Resolve the **port** from the container, never the adapter:

```python
@inject
async def test_x(retriever: FromDishka[DenseRetriever]) -> None:
```

Test the decisions, not the library: the empty batch that must not reach the
model, the failure that must surface as an `InfrastructureError`, the guarantee
the port's docstring promised.
