---
name: add-config
description: Add a configuration object — dataclass, env source factory, loader with validators, and its registration in bootstrap, DI and tests. Use when answer_service needs a new setting, credential or connection.
---

# Adding a config

Config is deliberately split into three pieces so the shape, the source and the
validation can change independently. All three plus four registrations are
required — a config that loads but is never handed to the container fails only
when something asks for it.

## 1. The shape — `setup/configs/<name>_config.py`

A plain frozen dataclass with **no dependency on the loader**. If dature is ever
replaced, this file does not change.

```python
@dataclass(slots=True, frozen=True)
class QdrantConfig:
    """One sentence on what this configures.

    Attributes:
        host: ...
    """

    host: str
    port: int = 6333

    @property
    def url(self) -> str:
        """Derived connection strings belong here, not in the adapter."""
        return f"http://{self.host}:{self.port}"
```

Give every optional field a default that is safe in development.

> **Name fields defensively.** `EnvSource` without a prefix matches by field
> name, so a field called `path` will pick up the system `PATH`. This has
> already happened once — hence `log_path` and `directory`.

## 2. The source — `setup/bootstrap/sources/<name>_env_source_factory.py`

```python
class QdrantEnvSourceFactory(SourceFactory):
    """Maps ``QDRANT_*`` environment variables onto :class:`QdrantConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(field_mapping={F[QdrantConfig].host: "QDRANT_HOST"})
```

Map **every** field explicitly. The mapping is what lets the same config come
from TOML, YAML or Vault later by swapping this one class.

## 3. The loader — `setup/bootstrap/loaders/<name>_config_loader.py`

```python
class QdrantConfigLoader(ConfigLoader[QdrantConfig]):
    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> QdrantConfig:
        return load(
            self._source_factory.create(),
            schema=QdrantConfig,
            root_validators=self._root_validators(),
            secret_field_names=("api_key",),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        return (
            V.root(
                lambda c: PORT_MIN <= c.port <= PORT_MAX,
                error_message=f"QDRANT_PORT must be between {PORT_MIN} and {PORT_MAX}",
            ),
        )
```

- Shared bounds live in `loaders/consts.py`.
- **Name the environment variable in the error message**, not the field —
  whoever reads it is editing a `.env`, not the dataclass.
- **Every credential goes in `secret_field_names`.** A failed boot is a log, and
  a leaked key in a log is a leaked key.
- Validate the things that are cheap to get wrong and expensive to notice: port
  ranges, indexes that must differ, dimensions that get baked into a schema.

## 4. Register it — all four places

1. `setups/configs_setup.py` — add the field to `AppConfigs` and load it in
   `setup_configs()`.
2. `setups/configs_setup.py` — add it to `make_container_context()`.
3. `ioc/providers/configs_provider.py` — `provider.from_context(provides=...)`.
4. Whatever consumes it — usually a provider factory function.

Steps 2 and 3 must agree, or the container fails to build.

## 5. Tests

Follow the existing pattern; do not invent a new one.

- `tests/unit/factories/env_data_factories.py` — a `<name>_env(**overrides)`
  returning valid values keyed by real env var names.
- `tests/unit/factories/source_stubs.py` — a `<name>_source_stub(**overrides)`
  built with `StubSourceFactory.mirroring(...)`.
- `tests/unit/setup/` — a loader test.

Cover: the derived connection string, each validator rejecting, the boundary
values being accepted, and **that a secret does not appear in the error output**:

```python
def test_the_api_key_is_masked_in_error_output() -> None:
    stub = qdrant_source_stub(QDRANT_API_KEY="TOP-SECRET", QDRANT_PORT="999999")

    with pytest.raises(DatureConfigError) as excinfo:
        QdrantConfigLoader(stub).load()

    assert "TOP-SECRET" not in render_exception(excinfo.value)
```

Never read the real environment in a test, and never monkeypatch it.

## 6. Finally

Document the variables in the README's environment block, then:

```sh
just lint && just mypy && uv run pytest tests/unit/setup -q
```
